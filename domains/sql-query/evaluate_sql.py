#!/usr/bin/env python3
"""
Evaluate dbt-style SQL pipeline experiment results: extract multiple model files
from LLM output, apply per-file rules (1-10) and cross-file rules (11-14),
output CSV.

Usage:
    python evaluate_sql.py                  # Process all results in results/
    python evaluate_sql.py results/foo.json # Process specific file(s)
"""

import csv
import json
import os
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent

# Import shared token extraction from top-level evaluate.py
sys.path.insert(0, str(SCRIPT_DIR.parent.parent))
from evaluate import extract_token_usage, extract_from_permission_denials, TOKEN_FIELDS
RESULTS_DIR = SCRIPT_DIR / "results"
TEST_DATA_DIR = SCRIPT_DIR / "test-data"
OUTPUT_CSV = RESULTS_DIR / "scores.csv"

# Major SQL clauses that should each start their own line
MAJOR_CLAUSES = [
    "WITH", "SELECT", "FROM", "LEFT JOIN", "RIGHT JOIN",
    "CROSS JOIN", "INNER JOIN", "WHERE", "GROUP BY", "HAVING",
    "ORDER BY", "LIMIT",
]

# Keywords that must be uppercase (checked as lowercase matches in output)
LOWERCASE_KEYWORDS = [
    "select", "from", "where", "join", "inner join", "left join",
    "right join", "cross join", "group by", "order by", "having",
    "limit", "with", "as", "on", "and", "or", "in", "between",
    "case", "when", "then", "else", "end", "over", "partition by",
    "sum", "count", "avg", "min", "max", "dense_rank", "row_number",
    "rank", "date_trunc", "extract", "coalesce", "not", "exists",
    "is", "null", "asc", "desc", "preceding", "following",
    "unbounded", "rows", "range", "current row",
]

# Valid layer prefixes for dbt model naming
VALID_PREFIXES = ["stg_", "int_", "fct_", "dim_"]


# --- Multi-File Extraction ---------------------------------------------------

def extract_dbt_models(raw_output: str) -> tuple[dict[str, str] | None, str | None]:
    """Extract dbt model files from raw LLM output.

    Expects output in this format:
        -- models/staging/stg_orders.sql
        ```sql
        ...SQL content...
        ```

    Also handles variations:
        -- stg_orders.sql
        ```sql ... ```

    Returns (models_dict, error). models_dict maps model_name -> sql_text.
    model_name is the filename without .sql extension (e.g., "stg_orders").
    """
    if not raw_output or not raw_output.strip():
        return None, "empty output"

    text_to_search = raw_output

    # Step 0: If JSONL (opencode format), extract text parts
    if '\n' in raw_output and raw_output.lstrip().startswith('{'):
        lines = raw_output.strip().split('\n')
        text_parts = []
        is_jsonl = False
        for line in lines:
            try:
                evt = json.loads(line)
                if isinstance(evt, dict) and 'type' in evt and 'sessionID' in evt:
                    is_jsonl = True
                    if evt['type'] == 'text':
                        text_parts.append(evt['part']['text'])
            except (json.JSONDecodeError, KeyError):
                continue
        if is_jsonl:
            text_to_search = '\n'.join(text_parts) if text_parts else ""

    # Step 1: If Claude CLI JSON response, extract 'result' field
    try:
        cli_response = json.loads(raw_output)
        if isinstance(cli_response, dict) and "result" in cli_response:
            text_to_search = cli_response["result"]
    except json.JSONDecodeError:
        pass

    # Step 1b: Fallback to permission_denials (Haiku sometimes tries Write tool)
    if "SELECT" not in text_to_search.upper() and "WITH" not in text_to_search.upper():
        denied_content = extract_from_permission_denials(raw_output)
        if denied_content and ("SELECT" in denied_content.upper() or "WITH" in denied_content.upper()):
            text_to_search = denied_content

    # Step 2: Extract model blocks — look for filename comment + sql fence pairs
    models = {}

    # Pattern: -- models/path/name.sql or -- name.sql followed by ```sql ... ```
    # We search for all ```sql blocks and look backwards for a filename comment
    lines = text_to_search.split('\n')
    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Look for ```sql opening
        if re.match(r'^```sql\s*$', line, re.IGNORECASE):
            # Look backwards for a filename comment
            model_name = None
            for j in range(i - 1, max(i - 5, -1), -1):
                if j < 0:
                    break
                prev_line = lines[j].strip()
                # Match: -- models/staging/stg_orders.sql or -- stg_orders.sql
                name_match = re.search(r'--\s*(?:models/\S+/)?(\w+)\.sql', prev_line)
                if name_match:
                    model_name = name_match.group(1)
                    break

            # Collect SQL content until closing ```
            sql_lines = []
            i += 1
            while i < len(lines):
                if lines[i].strip().startswith('```'):
                    break
                sql_lines.append(lines[i])
                i += 1

            sql_text = '\n'.join(sql_lines).strip()

            if model_name and sql_text:
                models[model_name] = sql_text
            elif not model_name and sql_text:
                # Try to extract model name from comment header inside SQL
                first_line = sql_text.split('\n')[0].strip()
                name_match = re.search(r'--\s*(?:models/\S+/)?(\w+)\.sql', first_line)
                if name_match:
                    models[name_match.group(1)] = sql_text
                else:
                    # Fallback: use unnamed_N
                    models[f"unnamed_{len(models) + 1}"] = sql_text

        i += 1

    if not models:
        # Fallback: try extracting a single SQL block (backwards compat)
        sql_fence = re.search(r'```sql\s*\n(.*?)\n\s*```', text_to_search, re.DOTALL)
        if sql_fence:
            models["unnamed_1"] = sql_fence.group(1).strip()

    if not models:
        return None, "could not extract any SQL model files from output"

    return models, None


# --- Helper Functions --------------------------------------------------------

def _remove_paren_content(text: str) -> str:
    """Replace parenthesized content with empty parens to avoid false matches."""
    result = []
    depth = 0
    for ch in text:
        if ch == '(':
            depth += 1
            result.append(ch)
        elif ch == ')':
            depth -= 1
            result.append(ch)
        elif depth == 0:
            result.append(ch)
    return ''.join(result)


def _strip_comments(sql: str) -> str:
    """Remove SQL line comments (--) but keep the structure."""
    lines = []
    for line in sql.split('\n'):
        comment_pos = _find_comment_start(line)
        if comment_pos >= 0:
            lines.append(line[:comment_pos])
        else:
            lines.append(line)
    return '\n'.join(lines)


def _strip_comments_and_strings(sql: str) -> str:
    """Remove SQL comments and string literals to avoid false matches."""
    result = _strip_comments(sql)
    result = re.sub(r"'(?:[^']|'')*'", "'_STR_'", result)
    return result


def _find_comment_start(line: str) -> int:
    """Find the position of -- comment start, ignoring -- inside strings."""
    in_string = False
    for i in range(len(line) - 1):
        if line[i] == "'" and (i == 0 or line[i-1] != "\\"):
            in_string = not in_string
        if not in_string and line[i:i+2] == '--':
            return i
    return -1


def _strip_jinja(sql: str) -> str:
    """Replace {{ ref('...') }} with a plain table reference for SQL analysis."""
    return re.sub(r"\{\{\s*ref\(\s*['\"](\w+)['\"]\s*\)\s*\}\}", r"\1", sql)


# --- Per-File Rule Checks (Rules 1-10) --------------------------------------

def check_rule_1_keywords_upper(sql_text: str, task: dict) -> tuple[bool, str]:
    """Rule 1: All SQL keywords are UPPERCASE."""
    cleaned = _strip_comments_and_strings(_strip_jinja(sql_text))

    violations = []
    for kw in LOWERCASE_KEYWORDS:
        words = kw.split()
        if len(words) == 1:
            pattern = r'(?<![a-zA-Z_])' + re.escape(kw) + r'(?![a-zA-Z_])'
        else:
            pattern = r'(?<![a-zA-Z_])' + r'\s+'.join(re.escape(w) for w in words) + r'(?![a-zA-Z_])'
        if re.search(pattern, cleaned):
            violations.append(kw)

    if violations:
        return False, f"lowercase keywords: {violations[:5]}"
    return True, "ok"


def check_rule_2_clause_per_line(sql_text: str, task: dict) -> tuple[bool, str]:
    """Rule 2: One major clause per line."""
    cleaned = _strip_comments(_strip_jinja(sql_text))

    for line in cleaned.split('\n'):
        stripped = line.strip()
        if not stripped:
            continue
        line_no_parens = _remove_paren_content(stripped)
        upper_line = line_no_parens.upper()
        found = []
        for clause in MAJOR_CLAUSES:
            pattern = r'\b' + re.escape(clause) + r'\b'
            if re.search(pattern, upper_line):
                found.append(clause)
        if len(found) > 1:
            return False, f"multiple clauses on one line: {found}"

    return True, "ok"


def check_rule_3_table_aliases(sql_text: str, task: dict) -> tuple[bool, str]:
    """Rule 3: Tables aliased with short meaningful names.

    Only checked when multiple tables are referenced (JOIN present).
    Single-table FROM (common in staging models) doesn't need an alias.
    """
    cleaned = _strip_comments(_strip_jinja(sql_text))

    # Extract CTE names
    cte_names = set()
    for match in re.finditer(r'(?:\bWITH\s+|,\s*)(\w+)\s+AS\s*\(', cleaned, re.IGNORECASE):
        cte_names.add(match.group(1).upper())

    table_refs = re.findall(
        r'(?:FROM|JOIN)\s+(\w+)(?:\s+(?:AS\s+)?(\w+))?',
        cleaned, re.IGNORECASE
    )

    # Filter out CTE refs and noise
    real_refs = []
    for table_name, alias in table_refs:
        if table_name.upper() in cte_names:
            continue
        if table_name.upper() in ('SELECT', 'LATERAL', '('):
            continue
        real_refs.append((table_name, alias))

    # Single-table queries don't need aliases (common in staging models)
    if len(real_refs) <= 1:
        return True, "ok (single table, alias not required)"

    unaliased = []
    for table_name, alias in real_refs:
        if not alias or alias.upper() in [c.replace(' ', '') for c in MAJOR_CLAUSES] + ['ON', 'WHERE', 'AND', 'OR', 'INNER', 'LEFT', 'RIGHT', 'CROSS']:
            unaliased.append(table_name)

    if unaliased:
        return False, f"tables without alias: {unaliased}"
    return True, "ok"


def check_rule_4_column_aliases(sql_text: str, task: dict) -> tuple[bool, str]:
    """Rule 4: Computed/aggregated columns use AS alias."""
    cleaned = _strip_comments(_strip_jinja(sql_text))

    agg_pattern = r'(SUM|COUNT|AVG|MIN|MAX|DENSE_RANK|ROW_NUMBER|RANK|DATE_TRUNC|EXTRACT|COALESCE)\s*\('
    matches = list(re.finditer(agg_pattern, cleaned, re.IGNORECASE))

    if not matches:
        return True, "n/a (no aggregations)"

    missing_alias = []
    for match in matches:
        start = match.start()
        paren_start = cleaned.index('(', match.start())
        depth = 0
        end = paren_start
        for i in range(paren_start, len(cleaned)):
            if cleaned[i] == '(':
                depth += 1
            elif cleaned[i] == ')':
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break

        after_paren = cleaned[end:end + 50].strip()
        if after_paren.upper().startswith('OVER'):
            over_paren = cleaned.index('(', end)
            depth = 0
            for i in range(over_paren, len(cleaned)):
                if cleaned[i] == '(':
                    depth += 1
                elif cleaned[i] == ')':
                    depth -= 1
                    if depth == 0:
                        end = i + 1
                        break
            after_paren = cleaned[end:end + 20].strip()

        if not re.match(r'(?i)\s*AS\s+\w+', cleaned[end:end + 30]):
            context_before = cleaned[:start].upper()
            last_select = context_before.split('SELECT')[-1] if 'SELECT' in context_before else context_before
            if 'WHERE' in last_select or 'HAVING' in last_select or 'ON' in last_select or 'GROUP BY' in last_select:
                continue
            # ROW_NUMBER in a CTE filtering context doesn't always need alias in WHERE
            if match.group(1).upper() == 'ROW_NUMBER':
                continue
            if after_paren.startswith(',') or after_paren.startswith('\n') or not after_paren:
                missing_alias.append(match.group(0) + '(...)')

    if missing_alias:
        return False, f"aggregations without AS alias: {missing_alias[:3]}"
    return True, "ok"


def check_rule_5_no_select_star(sql_text: str, task: dict) -> tuple[bool, str]:
    """Rule 5: No SELECT * — always list specific columns."""
    cleaned = _strip_comments(_strip_jinja(sql_text))
    if re.search(r'\bSELECT\s+\*\s*(?:,|\bFROM\b|\n|$)', cleaned, re.IGNORECASE):
        return False, "SELECT * found"
    if re.search(r'\bSELECT\s+\w+\.\*', cleaned, re.IGNORECASE):
        return False, "SELECT table.* found"
    return True, "ok"


def check_rule_6_comment_header(sql_text: str, task: dict) -> tuple[bool, str]:
    """Rule 6: First line(s) should be a -- comment describing the model."""
    stripped = sql_text.strip()
    if stripped.startswith('--'):
        first_line = stripped.split('\n')[0].strip()
        comment_text = first_line.lstrip('-').strip()
        if len(comment_text) > 3:
            return True, "ok"
        return False, "comment header is too short or empty"
    return False, "missing comment header"


def check_rule_7_left_join_only(sql_text: str, task: dict) -> tuple[bool, str]:
    """Rule 7: LEFT JOIN only — no INNER JOIN for analytics."""
    cleaned = _strip_comments_and_strings(_strip_jinja(sql_text))
    if re.search(r'\bINNER\s+JOIN\b', cleaned, re.IGNORECASE):
        return False, "INNER JOIN found (use LEFT JOIN for analytics)"
    # Also check for plain JOIN (which defaults to INNER)
    # But only flag if there's a FROM + JOIN pattern without LEFT/RIGHT/CROSS prefix
    # Find JOINs that aren't prefixed with LEFT/RIGHT/CROSS
    for match in re.finditer(r'\bJOIN\b', cleaned, re.IGNORECASE):
        pos = match.start()
        before = cleaned[:pos].rstrip()
        # Check the word before JOIN
        if not re.search(r'\b(LEFT|RIGHT|CROSS|INNER)\s*$', before, re.IGNORECASE):
            return False, "plain JOIN found (use LEFT JOIN for analytics)"
    return True, "ok"


def check_rule_8_coalesce_unknown(sql_text: str, task: dict) -> tuple[bool, str]:
    """Rule 8: Nullable dimensions wrapped with COALESCE to '(unknown)'."""
    nullable_cols = task.get("nullable_dimension_columns", [])
    if not nullable_cols:
        return True, "n/a (no nullable dimensions in task)"

    cleaned = _strip_comments(_strip_jinja(sql_text))
    upper = cleaned.upper()

    # Check if COALESCE is used at all
    if 'COALESCE' not in upper:
        return False, f"no COALESCE found (expected for: {nullable_cols})"

    # Check that '(unknown)' string is present
    if "'(unknown)'" not in cleaned.lower().replace(' ', ''):
        # Also check without parens in case model uses 'unknown'
        if "'unknown'" in cleaned.lower():
            return False, "COALESCE uses 'unknown' instead of '(unknown)'"
        return False, "COALESCE present but '(unknown)' string not found"

    return True, "ok"


def check_rule_9_row_number_dedup(sql_text: str, task: dict) -> tuple[bool, str]:
    """Rule 9: ROW_NUMBER dedup before aggregation."""
    if not task.get("requires_deduplication"):
        return True, "n/a (dedup not required)"

    cleaned = _strip_comments(_strip_jinja(sql_text))
    upper = cleaned.upper()

    if 'ROW_NUMBER' not in upper:
        return False, "ROW_NUMBER not found (dedup required)"

    # Check for PARTITION BY (needed for meaningful dedup)
    if 'PARTITION BY' not in upper:
        return False, "ROW_NUMBER without PARTITION BY"

    return True, "ok"


def check_rule_10_one_cte_per_file(sql_text: str, task: dict) -> tuple[bool, str]:
    """Rule 10: One CTE per file (single WITH block, no nesting)."""
    cleaned = _strip_comments_and_strings(_strip_jinja(sql_text))

    # Count WITH keyword occurrences at the top level
    with_count = len(re.findall(r'\bWITH\b', cleaned, re.IGNORECASE))

    if with_count > 1:
        return False, f"multiple WITH blocks found ({with_count})"

    if with_count == 1:
        # Count CTE names (comma-separated CTEs count as multiple)
        cte_names = re.findall(r'(?:\bWITH\s+|,\s*)(\w+)\s+AS\s*\(', cleaned, re.IGNORECASE)
        if len(cte_names) > 1:
            return False, f"multiple CTEs in one file: {cte_names}"

    return True, "ok"


# Per-file rules registry
PER_FILE_RULES = [
    ("rule_1_keywords_upper",    check_rule_1_keywords_upper),
    ("rule_2_clause_per_line",   check_rule_2_clause_per_line),
    ("rule_3_table_aliases",     check_rule_3_table_aliases),
    ("rule_4_column_aliases",    check_rule_4_column_aliases),
    ("rule_5_no_select_star",    check_rule_5_no_select_star),
    ("rule_6_comment_header",    check_rule_6_comment_header),
    ("rule_7_left_join_only",    check_rule_7_left_join_only),
    ("rule_8_coalesce_unknown",  check_rule_8_coalesce_unknown),
    ("rule_9_row_number_dedup",  check_rule_9_row_number_dedup),
    ("rule_10_one_cte_per_file", check_rule_10_one_cte_per_file),
]


# --- Cross-File Rule Checks (Rules 11-14) -----------------------------------

def check_rule_11_jinja_ref(models: dict[str, str], task: dict) -> tuple[bool, str]:
    """Rule 11: Non-staging models reference predecessors via {{ ref('model_name') }}."""
    non_staging = {name: sql for name, sql in models.items()
                   if not name.startswith("stg_") and not name.startswith("unnamed")}

    if not non_staging:
        return False, "no non-staging models found"

    missing_ref = []
    for name, sql in non_staging.items():
        if not re.search(r'\{\{\s*ref\(', sql):
            missing_ref.append(name)

    if missing_ref:
        return False, f"models without ref(): {missing_ref}"
    return True, "ok"


def check_rule_12_layer_naming(models: dict[str, str], task: dict) -> tuple[bool, str]:
    """Rule 12: stg_ prefix for staging, int_ for intermediate, fct_/dim_ for marts."""
    bad_names = []
    for name in models:
        if name.startswith("unnamed"):
            bad_names.append(name)
            continue
        if not any(name.startswith(prefix) for prefix in VALID_PREFIXES):
            bad_names.append(name)

    if bad_names:
        return False, f"invalid prefixes: {bad_names}"
    return True, "ok"


CROSS_FILE_RULES = [
    ("rule_11_jinja_ref",         check_rule_11_jinja_ref),
    ("rule_12_layer_naming",      check_rule_12_layer_naming),
]


# --- CSV Field Definitions ---------------------------------------------------

CSV_FIELDS = [
    "run_id",
    "model",
    "condition",
    "task",
    "task_complexity",
    "rep",
    "duration_ms",
    *TOKEN_FIELDS,
    "extraction_ok",
    "extraction_error",
    "model_count",
    "model_names",
]

# Add per-file rule columns (pass rate + detail)
for rule_name, _ in PER_FILE_RULES:
    CSV_FIELDS.append(f"{rule_name}_rate")
    CSV_FIELDS.append(f"{rule_name}_detail")

# Add cross-file rule columns (binary pass + detail)
for rule_name, _ in CROSS_FILE_RULES:
    CSV_FIELDS.append(f"{rule_name}_pass")
    CSV_FIELDS.append(f"{rule_name}_detail")

CSV_FIELDS.extend(["auto_score", "scored_rules"])


# --- Task Loading ------------------------------------------------------------

def load_task(task_id: str) -> dict:
    """Load task JSON from test-data directory."""
    for task_file in TEST_DATA_DIR.glob("*.json"):
        try:
            with open(task_file) as f:
                task = json.load(f)
            if str(task.get("task_id")) == str(task_id):
                return task
        except (json.JSONDecodeError, KeyError):
            continue
    return {}


# --- Main Evaluation ---------------------------------------------------------

def evaluate_run(result_file: Path) -> dict:
    """Evaluate a single run result file."""
    with open(result_file) as f:
        result = json.load(f)

    row = {
        "run_id": result.get("run_id", result_file.stem),
        "model": result.get("model", ""),
        "condition": result.get("condition", ""),
        "task": result.get("task", ""),
        "task_complexity": result.get("task_complexity", ""),
        "rep": result.get("rep", ""),
        "duration_ms": result.get("duration_ms", ""),
    }

    task = load_task(row["task"])

    raw_output = result.get("raw_output", "")
    row.update(extract_token_usage(raw_output))

    # Extract multiple model files
    models, extract_error = extract_dbt_models(raw_output)

    row["extraction_ok"] = models is not None
    row["extraction_error"] = extract_error or ""

    if models is None:
        row["model_count"] = 0
        row["model_names"] = ""
        for rule_name, _ in PER_FILE_RULES:
            row[f"{rule_name}_rate"] = 0.0
            row[f"{rule_name}_detail"] = "no models extracted"
        for rule_name, _ in CROSS_FILE_RULES:
            row[f"{rule_name}_pass"] = False
            row[f"{rule_name}_detail"] = "no models extracted"
        row["auto_score"] = 0.0
        row["scored_rules"] = 0
        return row

    row["model_count"] = len(models)
    row["model_names"] = "; ".join(models.keys())

    # --- Per-file rules: apply to each model, compute pass rate ---
    auto_score = 0.0
    scored_rules = 0

    for rule_name, check_fn in PER_FILE_RULES:
        passes = 0
        applicable = 0
        details = []

        for model_name, sql in models.items():
            # Rules 7/8/9 are context-dependent — skip non-applicable models
            # Skipped models are excluded from denominator (not auto-passed)
            if rule_name == "rule_8_coalesce_unknown":
                # Only check in non-staging models (where LEFT JOINs to dims happen)
                if model_name.startswith("stg_"):
                    continue
            elif rule_name == "rule_9_row_number_dedup":
                # Only check in int_ and unnamed models (where dedup belongs)
                if model_name.startswith("stg_") or model_name.startswith("fct_") or model_name.startswith("dim_"):
                    continue
            elif rule_name == "rule_7_left_join_only":
                # Only check in models that have JOINs
                cleaned = _strip_comments_and_strings(_strip_jinja(sql))
                if not re.search(r'\bJOIN\b', cleaned, re.IGNORECASE):
                    continue

            applicable += 1
            passed, detail = check_fn(sql, task)

            if passed:
                passes += 1
            else:
                details.append(f"{model_name}: {detail}")

        # If no models were applicable but the task requires this feature, score 0
        if applicable == 0:
            if rule_name == "rule_7_left_join_only" and task.get("requires_left_join"):
                rate = 0.0
                details = ["no models with JOINs found"]
            elif rule_name == "rule_8_coalesce_unknown" and task.get("nullable_dimension_columns"):
                rate = 0.0
                details = ["no non-staging models found"]
            elif rule_name == "rule_9_row_number_dedup" and task.get("requires_deduplication"):
                rate = 0.0
                details = ["no int_ models found for dedup"]
            else:
                rate = 1.0  # Rule not applicable for this task
        else:
            rate = passes / applicable

        row[f"{rule_name}_rate"] = round(rate, 4)
        row[f"{rule_name}_detail"] = "; ".join(details[:3]) if details else "ok"
        scored_rules += 1
        auto_score += rate

    # --- Cross-file rules: binary pass/fail ---
    for rule_name, check_fn in CROSS_FILE_RULES:
        passed, detail = check_fn(models, task)
        row[f"{rule_name}_pass"] = passed
        row[f"{rule_name}_detail"] = detail
        scored_rules += 1
        if passed:
            auto_score += 1.0

    row["auto_score"] = round(auto_score, 2)
    row["scored_rules"] = scored_rules

    return row


def main():
    if len(sys.argv) > 1:
        files = [Path(f) for f in sys.argv[1:] if f.endswith(".json")]
    else:
        if not RESULTS_DIR.exists():
            print(f"No results directory found at {RESULTS_DIR}")
            sys.exit(1)
        files = sorted(RESULTS_DIR.glob("*.json"))
        files = [f for f in files if f.name != "scores.csv"]

    if not files:
        print("No result files found.")
        sys.exit(1)

    print(f"Evaluating {len(files)} result files...")

    rows = []
    for f in files:
        try:
            row = evaluate_run(f)
            rows.append(row)
        except Exception as e:
            print(f"  ERROR processing {f.name}: {e}")

    # Write CSV
    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(OUTPUT_CSV, "w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    # Summary
    extraction_ok = sum(1 for r in rows if r["extraction_ok"])

    print(f"\nResults written to {OUTPUT_CSV}")
    print(f"  Total runs: {len(rows)}")
    print(f"  Extraction ok: {extraction_ok}/{len(rows)}")

    # Auto-score summary by condition
    n_scored = len(PER_FILE_RULES) + len(CROSS_FILE_RULES)
    print(f"\nAuto-score by condition (max {n_scored}):")
    conditions = {}
    for r in rows:
        cond = r["condition"]
        if cond not in conditions:
            conditions[cond] = []
        conditions[cond].append(r["auto_score"])

    for cond in sorted(conditions):
        scores = conditions[cond]
        avg = sum(scores) / len(scores) if scores else 0
        print(f"  {cond}: mean={avg:.2f}, n={len(scores)}")

    # Model count summary
    print(f"\nModel count by condition:")
    for cond in sorted(conditions):
        cond_rows = [r for r in rows if r["condition"] == cond]
        counts = [r["model_count"] for r in cond_rows]
        avg = sum(counts) / len(counts) if counts else 0
        print(f"  {cond}: mean={avg:.1f} files")


if __name__ == "__main__":
    main()
