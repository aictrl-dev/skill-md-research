#!/usr/bin/env python3
"""
Evaluate Terraform experiment results: extract HCL from LLM output,
apply automated rule checks (14 rules), output CSV.

Usage:
    python evaluate_terraform.py                  # Process all results in results/
    python evaluate_terraform.py results/foo.json # Process specific file(s)
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

# AWS resource types that support tags
TAGGABLE_RESOURCES = {
    "aws_instance", "aws_s3_bucket", "aws_vpc", "aws_subnet",
    "aws_security_group", "aws_lb", "aws_ecs_cluster", "aws_db_instance",
    "aws_ecs_service", "aws_ecs_task_definition", "aws_cloudwatch_log_group",
    "aws_eip", "aws_nat_gateway", "aws_internet_gateway", "aws_route_table",
    "aws_lb_target_group", "aws_secretsmanager_secret", "aws_iam_role",
    # Note: S3 sub-resources (aws_s3_bucket_versioning, etc.) don't support
    # tags directly — tags go on the parent aws_s3_bucket resource.
}

# Resource types where lifecycle blocks are recommended (stateful)
STATEFUL_RESOURCES = {
    "aws_s3_bucket", "aws_db_instance", "aws_efs_file_system",
    "aws_dynamodb_table", "aws_kms_key", "aws_secretsmanager_secret",
}


# --- Terraform Extraction ----------------------------------------------------

def extract_terraform(raw_output: str) -> tuple[str | None, str | None]:
    """Extract Terraform HCL from raw LLM output.

    Tries multiple strategies:
    1. JSONL (opencode) format - extract text parts
    2. Claude CLI JSON response - extract result field
    3. Fenced code blocks (```hcl, ```terraform, ```tf, ```)
    4. Plain text starting with terraform/provider/resource/variable keywords

    Returns (hcl_text, error). hcl_text is None on failure.
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
    if "resource " not in text_to_search and "variable " not in text_to_search:
        denied_content = extract_from_permission_denials(raw_output)
        if denied_content and ("resource " in denied_content or "variable " in denied_content):
            text_to_search = denied_content

    # Step 2: Try fenced code blocks (most common)
    fence_patterns = [
        r"```(?:hcl|terraform|tf)\s*\n(.*?)\n\s*```",
        r"```\s*\n(.*?)\n\s*```",
    ]
    # Collect ALL fenced blocks and concatenate — LLMs often split into
    # multiple fences (e.g., one per file: main.tf, variables.tf, outputs.tf)
    all_blocks = []
    for pattern in fence_patterns:
        for match in re.finditer(pattern, text_to_search, re.DOTALL):
            candidate = match.group(1).strip()
            if _looks_like_terraform(candidate):
                all_blocks.append(candidate)

    if all_blocks:
        combined = "\n\n".join(all_blocks)
        return combined, None

    # Step 3: Try to find terraform/provider/resource/variable blocks in plain text
    # Look for the first HCL keyword and grab everything from there
    hcl_start = re.search(
        r'^\s*(terraform|provider|resource|variable|data|locals|output)\s',
        text_to_search,
        re.MULTILINE,
    )
    if hcl_start:
        candidate = text_to_search[hcl_start.start():].strip()
        # Trim trailing LLM explanation
        candidate = _trim_trailing_explanation(candidate)
        if _looks_like_terraform(candidate):
            return candidate, None

    return None, "could not extract Terraform HCL from output"


def _looks_like_terraform(text: str) -> bool:
    """Check if text looks like Terraform HCL."""
    keywords = ["resource", "variable", "provider", "terraform", "output", "data", "locals"]
    # Must have at least one HCL block pattern: keyword "type" "name" {
    for kw in keywords:
        if re.search(rf'\b{kw}\s', text):
            return True
    return False


def _trim_trailing_explanation(text: str) -> str:
    """Remove trailing LLM explanation after the HCL code.

    Heuristic: if we see a line that starts with common explanation phrases
    after a closing brace, stop there.
    """
    lines = text.split('\n')
    result_lines = []
    brace_depth = 0
    last_close_idx = -1

    for i, line in enumerate(lines):
        stripped = line.strip()
        brace_depth += stripped.count('{') - stripped.count('}')
        result_lines.append(line)
        if brace_depth <= 0 and '}' in stripped:
            last_close_idx = i

    # Check for explanation after the last closing brace at depth 0
    if last_close_idx >= 0 and last_close_idx < len(result_lines) - 1:
        remaining = result_lines[last_close_idx + 1:]
        explanation_starters = [
            "this configuration", "this terraform", "the above",
            "note:", "explanation:", "let me explain", "here's",
            "this creates", "this sets up", "key features",
            "## ", "### ", "**note", "---",
        ]
        for i, line in enumerate(remaining):
            lower = line.strip().lower()
            if lower and any(lower.startswith(s) for s in explanation_starters):
                result_lines = result_lines[:last_close_idx + 1 + i]
                break

    # Remove trailing blank lines
    while result_lines and result_lines[-1].strip() == '':
        result_lines.pop()

    return '\n'.join(result_lines)


# --- Structure Validation ----------------------------------------------------

def validate_structure(tf_text: str) -> tuple[bool, list[str]]:
    """Check that the Terraform config has at least one resource block.

    Returns (is_valid, list_of_errors).
    """
    errors = []

    if not tf_text or not tf_text.strip():
        return False, ["empty terraform configuration"]

    # Must have at least one resource block
    if not re.search(r'\bresource\s+"[^"]+"\s+"[^"]+"\s*\{', tf_text):
        errors.append("no resource blocks found")

    return len(errors) == 0, errors


# --- Helper: Extract blocks from HCL text -----------------------------------

def _find_resource_blocks(tf_text: str) -> list[tuple[str, str, str]]:
    """Find all resource blocks. Returns list of (type, name, body)."""
    results = []
    pattern = r'resource\s+"([^"]+)"\s+"([^"]+)"\s*\{'
    for match in re.finditer(pattern, tf_text):
        rtype = match.group(1)
        rname = match.group(2)
        body = _extract_block_body(tf_text, match.end() - 1)
        results.append((rtype, rname, body))
    return results


def _find_variable_blocks(tf_text: str) -> list[tuple[str, str]]:
    """Find all variable blocks. Returns list of (name, body)."""
    results = []
    pattern = r'variable\s+"([^"]+)"\s*\{'
    for match in re.finditer(pattern, tf_text):
        vname = match.group(1)
        body = _extract_block_body(tf_text, match.end() - 1)
        results.append((vname, body))
    return results


def _find_output_blocks(tf_text: str) -> list[tuple[str, str]]:
    """Find all output blocks. Returns list of (name, body)."""
    results = []
    pattern = r'output\s+"([^"]+)"\s*\{'
    for match in re.finditer(pattern, tf_text):
        oname = match.group(1)
        body = _extract_block_body(tf_text, match.end() - 1)
        results.append((oname, body))
    return results


def _find_data_blocks(tf_text: str) -> list[tuple[str, str]]:
    """Find all data source blocks. Returns list of (type, name)."""
    results = []
    pattern = r'data\s+"([^"]+)"\s+"([^"]+)"\s*\{'
    for match in re.finditer(pattern, tf_text):
        results.append((match.group(1), match.group(2)))
    return results


def _extract_block_body(text: str, open_brace_pos: int) -> str:
    """Extract the body of a block starting at the opening brace position."""
    depth = 0
    start = open_brace_pos
    for i in range(open_brace_pos, len(text)):
        if text[i] == '{':
            depth += 1
        elif text[i] == '}':
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    # Unmatched brace — return everything from start
    return text[start:]


# --- Individual Rule Checks ---------------------------------------------------

def check_rule_1_naming(tf_text: str, task: dict) -> tuple[bool, str]:
    """Rule 1 (NAMING): snake_case resource names with descriptive prefix.
    Bad: sg1, vpc1, r1. Good: app_security_group, main_vpc."""
    resources = _find_resource_blocks(tf_text)
    if not resources:
        return False, "no resources found"

    BAD_NAME = re.compile(r'^[a-z]{1,3}\d*$')  # sg1, vpc1, r1, a, ab
    violations = []
    for rtype, rname, _ in resources:
        if not re.match(r'^[a-z][a-z0-9_]*$', rname):
            violations.append(f"{rtype}.{rname}: not snake_case")
        elif BAD_NAME.match(rname):
            violations.append(f"{rtype}.{rname}: too generic/short")

    if violations:
        return False, "; ".join(violations[:5])
    return True, f"all {len(resources)} resource names are descriptive snake_case"


def check_rule_2_var_description(tf_text: str, task: dict) -> tuple[bool, str]:
    """Rule 2 (VARIABLES): All variables have description attribute."""
    variables = _find_variable_blocks(tf_text)
    if not variables:
        return False, "no variables defined"

    missing = []
    for vname, body in variables:
        if not re.search(r'\bdescription\s*=', body):
            missing.append(vname)

    if missing:
        return False, f"missing description: {missing}"
    return True, f"all {len(variables)} variables have descriptions"


def check_rule_3_var_type(tf_text: str, task: dict) -> tuple[bool, str]:
    """Rule 3 (VARIABLES): All variables have type constraint."""
    variables = _find_variable_blocks(tf_text)
    if not variables:
        return False, "no variables defined"

    missing = []
    for vname, body in variables:
        if not re.search(r'\btype\s*=', body):
            missing.append(vname)

    if missing:
        return False, f"missing type: {missing}"
    return True, f"all {len(variables)} variables have type constraints"


def check_rule_4_outputs(tf_text: str, task: dict) -> tuple[bool, str]:
    """Rule 4 (OUTPUTS): At least one output block defined."""
    outputs = _find_output_blocks(tf_text)
    if len(outputs) == 0:
        return False, "no outputs defined"
    return True, f"{len(outputs)} outputs defined: {[o[0] for o in outputs]}"


def check_rule_5_tags(tf_text: str, task: dict) -> tuple[bool, str]:
    """Rule 5 (TAGS): Tags on all taggable resources."""
    resources = _find_resource_blocks(tf_text)
    if not resources:
        return False, "no resources found"

    missing = []
    checked = 0
    for rtype, rname, body in resources:
        if rtype in TAGGABLE_RESOURCES:
            checked += 1
            # Check for tags = { or tags = local. or tags = merge( or tags = var.
            # Also accept dynamic "tag" blocks (common in modules)
            has_tags = (
                re.search(r'\btags\s*=', body) or
                re.search(r'dynamic\s+"tags?"', body)
            )
            if not has_tags:
                missing.append(f"{rtype}.{rname}")

    if not checked:
        return True, "no taggable resources found"
    if missing:
        return False, f"missing tags on: {missing[:5]}"
    return True, f"all {checked} taggable resources have tags"


def check_rule_6_lifecycle(tf_text: str, task: dict) -> tuple[bool, str]:
    """Rule 6 (LIFECYCLE): lifecycle blocks on stateful resources. MANUAL CHECK.
    Always returns True with needs_review."""
    return True, "needs_review"


def check_rule_7_var_separation(tf_text: str, task: dict) -> tuple[bool, str]:
    """Rule 7 (STRUCTURE): Variables grouped together, not scattered between resources.
    SEMI — heuristic: check if variable blocks appear between resource blocks."""
    # Extract ordered list of top-level block types
    blocks = re.findall(r'^\s*(resource|variable)\b', tf_text, re.MULTILINE)

    if not blocks or 'variable' not in blocks:
        return True, "needs_review (no variable blocks found)"

    saw_resource = False
    saw_var_after_resource = False
    saw_resource_after_var_after_resource = False

    for b in blocks:
        if b == "resource":
            if saw_var_after_resource:
                saw_resource_after_var_after_resource = True
            saw_resource = True
        elif b == "variable":
            if saw_resource:
                saw_var_after_resource = True

    if saw_resource_after_var_after_resource:
        return False, "variables scattered between resource blocks"
    return True, "variables appear grouped"


def check_rule_8_file_structure(tf_text: str, task: dict) -> tuple[bool, str]:
    """Rule 8 (STRUCTURE): Module file structure mentioned.
    SEMI — check if output mentions file names like main.tf/variables.tf/outputs.tf."""
    file_markers = ["main.tf", "variables.tf", "outputs.tf", "data.tf", "locals.tf"]
    found = [f for f in file_markers if f in tf_text]
    if found:
        return True, f"file structure mentioned: {found}"
    return True, "needs_review (single file output)"


def check_rule_9_no_hardcoded_ids(tf_text: str, task: dict) -> tuple[bool, str]:
    """Rule 9 (VALUES): No hardcoded AMI IDs, account numbers, or region strings in resources.
    - ami-[0-9a-f]{8,17}: hardcoded AMI
    - 12-digit number: AWS account ID
    - Region string like 'us-east-1' outside provider block"""
    violations = []

    # Check for hardcoded AMI IDs
    if re.search(r'ami-[0-9a-f]{8,17}', tf_text):
        violations.append("hardcoded AMI ID (ami-*)")

    # Check for 12-digit AWS account IDs (not inside comments)
    # Remove single-line comments first
    text_no_comments = re.sub(r'#.*$', '', tf_text, flags=re.MULTILINE)
    text_no_comments = re.sub(r'//.*$', '', text_no_comments, flags=re.MULTILINE)
    if re.search(r'(?<!\d)\d{12}(?!\d)', text_no_comments):
        violations.append("possible hardcoded AWS account ID (12 digits)")

    # Check for region strings in resource blocks (not in provider blocks)
    # Strategy: find region-like strings, then verify they're not inside a provider block
    region_pattern = r'"(us|eu|ap|sa|ca|me|af)-(east|west|south|north|central|northeast|southeast|southwest|northwest)-\d"'
    # Remove provider blocks using brace-counting (handles nested braces)
    text_no_provider = tf_text
    for match in reversed(list(re.finditer(r'(?:provider\s+"[^"]+"|terraform)\s*\{', tf_text))):
        block_body = _extract_block_body(tf_text, match.end() - 1)
        text_no_provider = text_no_provider[:match.start()] + text_no_provider[match.start() + len(match.group()) + len(block_body) - 1:]
    if re.search(region_pattern, text_no_provider):
        violations.append("hardcoded region string in resource block")

    if violations:
        return False, "; ".join(violations)
    return True, "no hardcoded IDs found"


def check_rule_10_provider_pinned(tf_text: str, task: dict) -> tuple[bool, str]:
    """Rule 10 (PROVIDER): Provider version pinned in required_providers block."""
    # Look for required_providers block
    rp_match = re.search(r'required_providers\s*\{', tf_text)
    if not rp_match:
        return False, "no required_providers block found"

    # Extract the required_providers block body
    rp_body = _extract_block_body(tf_text, rp_match.end() - 1)

    # Look for version constraint inside a provider namespace block
    # Pattern: aws = { source = "...", version = "..." }
    provider_blocks = re.findall(r'\w+\s*=\s*\{([^}]*)\}', rp_body)
    for pb in provider_blocks:
        if re.search(r'\bversion\s*=\s*"[^"]*"', pb):
            match = re.search(r'\bversion\s*=\s*"([^"]*)"', pb)
            version = match.group(1) if match else "?"
            return True, f"provider version pinned: {version}"

    return False, "required_providers block found but no version constraint"


def check_rule_11_backend(tf_text: str, task: dict) -> tuple[bool, str]:
    """Rule 11 (BACKEND): Backend configured (terraform { backend '...' {} } or cloud {})."""
    if re.search(r'backend\s+"[^"]+"\s*\{', tf_text):
        match = re.search(r'backend\s+"([^"]+)"\s*\{', tf_text)
        backend_type = match.group(1) if match else "?"
        return True, f"backend configured: {backend_type}"
    # Terraform Cloud / Enterprise uses cloud {} block instead of backend
    if re.search(r'\bcloud\s*\{', tf_text):
        return True, "backend configured: terraform cloud"
    return False, "no backend configuration found"


def check_rule_12_sensitive(tf_text: str, task: dict) -> tuple[bool, str]:
    """Rule 12 (SENSITIVE): Sensitive values marked with sensitive = true.
    Only checked when the task requires sensitive handling."""
    requires_sensitive = task.get("requirements", {}).get("sensitive_values", False)
    if not requires_sensitive:
        return True, "n/a (task does not require sensitive values)"

    # Check variables and outputs for sensitive = true
    variables = _find_variable_blocks(tf_text)
    outputs = _find_output_blocks(tf_text)

    sensitive_vars = [
        vname for vname, body in variables
        if re.search(r'\bsensitive\s*=\s*true\b', body)
    ]
    sensitive_outputs = [
        oname for oname, body in outputs
        if re.search(r'\bsensitive\s*=\s*true\b', body)
    ]

    if not sensitive_vars and not sensitive_outputs:
        return False, "task requires sensitive values but none marked sensitive = true"
    return True, f"sensitive vars: {sensitive_vars}, outputs: {sensitive_outputs}"


def check_rule_13_data_sources(tf_text: str, task: dict) -> tuple[bool, str]:
    """Rule 13 (DATA): Data sources used for lookups when task requires them."""
    requires_data = task.get("requirements", {}).get("data_sources", False)
    if not requires_data:
        return True, "n/a (task does not require data sources)"

    data_blocks = _find_data_blocks(tf_text)
    if not data_blocks:
        return False, "task requires data sources but none defined"
    names = [f"{dtype}.{dname}" for dtype, dname in data_blocks]
    return True, f"{len(data_blocks)} data sources: {names}"


def check_rule_14_locals(tf_text: str, task: dict) -> tuple[bool, str]:
    """Rule 14 (LOCALS): Locals block present for shared/computed values."""
    if re.search(r'\blocals\s*\{', tf_text):
        return True, "locals block present"
    return False, "no locals block defined"


# --- All Checks Registry -----------------------------------------------------

RULE_CHECKS = [
    ("rule_1_naming", check_rule_1_naming),
    ("rule_2_var_description", check_rule_2_var_description),
    ("rule_3_var_type", check_rule_3_var_type),
    ("rule_4_outputs", check_rule_4_outputs),
    ("rule_5_tags", check_rule_5_tags),
    ("rule_6_lifecycle", check_rule_6_lifecycle),
    ("rule_7_var_separation", check_rule_7_var_separation),
    ("rule_8_file_structure", check_rule_8_file_structure),
    ("rule_9_no_hardcoded_ids", check_rule_9_no_hardcoded_ids),
    ("rule_10_provider_pinned", check_rule_10_provider_pinned),
    ("rule_11_backend", check_rule_11_backend),
    ("rule_12_sensitive", check_rule_12_sensitive),
    ("rule_13_data_sources", check_rule_13_data_sources),
    ("rule_14_locals", check_rule_14_locals),
]

# Rules excluded from auto_score (manual-only, cannot be verified deterministically)
EXCLUDED_RULES = {"rule_6_lifecycle"}


# --- Outcome Checks (semantic correctness, not style) ----------------------------

def outcome_resources_present(tf_text: str, task: dict) -> tuple[bool, str]:
    """OUTCOME: All required AWS resource types are defined."""
    expected = task.get("resources", [])
    if not expected:
        return True, "no expected resources in task"
    import re
    # Extract resource type strings from resource blocks
    actual_types = set(re.findall(r'resource\s+"([^"]+)"', tf_text))
    missing = [r for r in expected if r not in actual_types]
    if not missing:
        return True, f"all {len(expected)} expected resources present"
    return False, f"missing {len(missing)}/{len(expected)} resources: {missing[:5]}"


def outcome_resource_coverage(tf_text: str, task: dict) -> tuple[bool, str]:
    """OUTCOME: Percentage of required resources that are present (>=60% to pass)."""
    expected = task.get("resources", [])
    if not expected:
        return True, "no expected resources in task"
    import re
    actual_types = set(re.findall(r'resource\s+"([^"]+)"', tf_text))
    found = [r for r in expected if r in actual_types]
    pct = len(found) / len(expected) * 100
    if pct >= 60:
        return True, f"{len(found)}/{len(expected)} resources ({pct:.0f}%)"
    return False, f"only {len(found)}/{len(expected)} resources ({pct:.0f}%), need >=60%"


OUTCOME_CHECKS = [
    ("outcome_resources_present", outcome_resources_present),
    ("outcome_resource_coverage", outcome_resource_coverage),
]

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
    "structure_valid",
    "structure_errors",
]
# Add rule columns
for _rule_name, _ in RULE_CHECKS:
    CSV_FIELDS.append(f"{_rule_name}_pass")
    CSV_FIELDS.append(f"{_rule_name}_detail")
CSV_FIELDS.extend(["auto_score", "scored_rules", "needs_manual_review"])
for _outcome_name, _ in OUTCOME_CHECKS:
    CSV_FIELDS.append(f"{_outcome_name}_pass")
    CSV_FIELDS.append(f"{_outcome_name}_detail")
CSV_FIELDS.append("outcome_score")


# --- Task Loading -------------------------------------------------------------

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


# --- Main Evaluation ----------------------------------------------------------

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

    # Load task data for conditional checks
    task = load_task(row["task"])

    # Extract token usage and Terraform HCL from raw output
    raw_output = result.get("raw_output", "")
    row.update(extract_token_usage(raw_output))

    tf_text, extract_error = extract_terraform(raw_output)

    row["extraction_ok"] = tf_text is not None
    row["extraction_error"] = extract_error or ""

    if tf_text is None:
        # Cannot check anything else
        row["structure_valid"] = False
        row["structure_errors"] = extract_error or "extraction failed"
        for rule_name, _ in RULE_CHECKS:
            row[f"{rule_name}_pass"] = False
            row[f"{rule_name}_detail"] = "no Terraform HCL extracted"
        row["auto_score"] = 0
        row["scored_rules"] = 0
        row["needs_manual_review"] = False
        for outcome_name, _ in OUTCOME_CHECKS:
            row[f"{outcome_name}_pass"] = False
            row[f"{outcome_name}_detail"] = "no Terraform HCL extracted"
        row["outcome_score"] = 0
        return row

    # Structure validation
    struct_ok, struct_errors = validate_structure(tf_text)
    row["structure_valid"] = struct_ok
    row["structure_errors"] = "; ".join(struct_errors) if struct_errors else ""

    # Run all rule checks
    auto_score = 0
    scored_rules = 0
    needs_review = False
    for rule_name, check_fn in RULE_CHECKS:
        passed, detail = check_fn(tf_text, task)
        row[f"{rule_name}_pass"] = passed
        row[f"{rule_name}_detail"] = detail
        if rule_name not in EXCLUDED_RULES:
            scored_rules += 1
            if passed:
                auto_score += 1
        if "needs_review" in detail:
            needs_review = True

    row["auto_score"] = auto_score
    row["scored_rules"] = scored_rules
    row["needs_manual_review"] = needs_review

    # Outcome checks (semantic correctness)
    outcome_score = 0
    for outcome_name, check_fn in OUTCOME_CHECKS:
        passed, detail = check_fn(tf_text, task)
        row[f"{outcome_name}_pass"] = passed
        row[f"{outcome_name}_detail"] = detail
        if passed:
            outcome_score += 1
    row["outcome_score"] = outcome_score

    return row


def main():
    # Determine which files to process
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
    structure_valid = sum(1 for r in rows if r["structure_valid"])
    needs_review = sum(1 for r in rows if r["needs_manual_review"])

    print(f"\nResults written to {OUTPUT_CSV}")
    print(f"  Total runs: {len(rows)}")
    print(f"  Extraction ok: {extraction_ok}/{len(rows)}")
    print(f"  Structure valid: {structure_valid}/{len(rows)}")
    print(f"  Needs manual review: {needs_review}/{len(rows)}")

    # Auto-score summary by condition
    print(f"\nAuto-score by condition (max {len(RULE_CHECKS) - len(EXCLUDED_RULES)} scored rules, {len(EXCLUDED_RULES)} excluded):")
    conditions = {}
    for r in rows:
        cond = r["condition"]
        if cond not in conditions:
            conditions[cond] = []
        conditions[cond].append(r["auto_score"])

    for cond in sorted(conditions):
        scores = conditions[cond]
        avg = sum(scores) / len(scores) if scores else 0
        print(f"  {cond}: mean={avg:.1f}, n={len(scores)}")


if __name__ == "__main__":
    main()
