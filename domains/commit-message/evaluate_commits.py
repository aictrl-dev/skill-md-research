#!/usr/bin/env python3
"""
Evaluate commit message experiment results: extract commit messages,
apply automated rule checks (14 of 14 rules), output CSV.

Usage:
    python evaluate_commits.py                  # Process all results in results/
    python evaluate_commits.py results/foo.json # Process specific file(s)
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

# Valid Conventional Commit types
VALID_TYPES = {
    "feat", "fix", "docs", "style", "refactor", "perf",
    "test", "build", "ci", "chore", "revert",
}

# Words that violate imperative mood at the start of description
IMPERATIVE_BLACKLIST = {
    # Past tense
    "added", "fixed", "removed", "updated", "changed", "refactored",
    "deleted", "moved", "renamed", "replaced", "converted", "migrated",
    "implemented", "created", "resolved", "introduced", "applied",
    # Gerund (-ing)
    "adding", "fixing", "removing", "updating", "changing", "refactoring",
    "deleting", "moving", "renaming", "replacing", "converting", "migrating",
    "implementing", "creating", "resolving", "introducing", "applying",
    # Third person (-s)
    "adds", "fixes", "removes", "updates", "changes", "refactors",
    "deletes", "moves", "renames", "replaces", "converts", "migrates",
    "implements", "creates", "resolves", "introduces", "applies",
    # Past participle used as non-imperative
    "was", "were", "been",
}

MAX_SUBJECT_LENGTH = 50
MAX_BODY_LINE_LENGTH = 72

# Subject line regex: type[(scope)][!]: description
SUBJECT_RE = re.compile(
    r'^(?P<type>[a-z]+)'
    r'(?:\((?P<scope>[^)]*)\))?'
    r'(?P<breaking>!)?'
    r'(?P<sep>:\s?)'
    r'(?P<description>.+)$'
)


# --- Commit Message Extraction ------------------------------------------------

def extract_commit_message(raw_output: str) -> tuple[str | None, str | None]:
    """Extract a commit message from raw LLM output.

    Tries multiple strategies:
    1. JSONL (opencode) format - extract text parts
    2. Claude CLI JSON response - extract result field
    3. Markdown code fences
    4. "commit message:" header followed by the message
    5. Direct match starting with a valid type prefix

    Returns (message, error). message is None on failure.
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
    if not re.match(r'^[a-z]+[(!:]', text_to_search.strip()):
        denied_content = extract_from_permission_denials(raw_output)
        if denied_content and re.match(r'^[a-z]+[(!:]', denied_content.strip()):
            text_to_search = denied_content

    # Step 2: Try markdown code fences (most common)
    fence_patterns = [
        r"```(?:text|commit|git)?\s*\n(.*?)\n\s*```",
    ]
    for pattern in fence_patterns:
        match = re.search(pattern, text_to_search, re.DOTALL)
        if match:
            candidate = match.group(1).strip()
            if _looks_like_commit(candidate):
                return candidate, None

    # Step 3: Try "commit message:" header
    header_patterns = [
        r"(?i)(?:commit\s+message|here(?:'s| is) the commit):?\s*\n+(.*)",
        r"(?i)(?:the commit message):?\s*\n+(.*)",
    ]
    for pattern in header_patterns:
        match = re.search(pattern, text_to_search, re.DOTALL)
        if match:
            candidate = match.group(1).strip()
            # Trim trailing explanation after the commit message
            candidate = _trim_trailing_explanation(candidate)
            if _looks_like_commit(candidate):
                return candidate, None

    # Step 4: Direct match - find lines starting with a valid type prefix
    for line in text_to_search.split('\n'):
        line = line.strip()
        if _looks_like_commit(line):
            # Grab everything from this line onward (may include body/footers)
            start_idx = text_to_search.find(line)
            candidate = text_to_search[start_idx:].strip()
            candidate = _trim_trailing_explanation(candidate)
            return candidate, None

    return None, "could not extract commit message from output"


def _looks_like_commit(text: str) -> bool:
    """Check if text starts with a valid conventional commit subject."""
    first_line = text.split('\n')[0].strip()
    match = SUBJECT_RE.match(first_line)
    if match and match.group('type') in VALID_TYPES:
        return True
    return False


def _trim_trailing_explanation(text: str) -> str:
    """Remove trailing LLM explanation after the commit message.

    Heuristic: if we see a blank line followed by text that doesn't look
    like a commit body/footer (e.g. "This commit message...", "I chose..."),
    stop there.
    """
    lines = text.split('\n')
    result_lines = []
    blank_seen = False
    in_body = False

    for i, line in enumerate(lines):
        stripped = line.strip()

        if i == 0:
            # Subject line
            result_lines.append(line)
            continue

        if stripped == '':
            blank_seen = True
            result_lines.append(line)
            continue

        if blank_seen and not in_body:
            # First non-blank line after subject
            # Check if it looks like commit body/footer or LLM explanation
            if _is_footer_line(stripped) or _is_body_line(stripped):
                in_body = True
                result_lines.append(line)
            else:
                # Likely LLM explanation, stop here
                # Remove trailing blank lines
                while result_lines and result_lines[-1].strip() == '':
                    result_lines.pop()
                break
        elif in_body:
            # Check for transition to LLM explanation
            if blank_seen and _is_explanation_start(stripped):
                while result_lines and result_lines[-1].strip() == '':
                    result_lines.pop()
                break
            result_lines.append(line)
            blank_seen = False
        else:
            result_lines.append(line)
            blank_seen = False

    # Remove trailing blank lines
    while result_lines and result_lines[-1].strip() == '':
        result_lines.pop()

    return '\n'.join(result_lines)


def _is_footer_line(line: str) -> bool:
    """Check if a line looks like a commit footer."""
    footer_tokens = [
        "BREAKING CHANGE:", "Refs:", "Fixes:", "Closes:", "Signed-off-by:",
        "Co-authored-by:", "Reviewed-by:", "Acked-by:", "Ticket:",
    ]
    for token in footer_tokens:
        if line.startswith(token):
            return True
    # Also match "Refs #123" style
    if re.match(r'^(Refs|Fixes|Closes)\s+#\d+', line):
        return True
    return False


def _is_body_line(line: str) -> bool:
    """Check if a line looks like commit body (not LLM explanation)."""
    # Body lines typically don't start with meta-commentary
    explanation_starters = [
        "this commit", "i chose", "i used", "here's", "here is",
        "the commit", "note:", "explanation:", "---",
    ]
    lower = line.lower()
    for starter in explanation_starters:
        if lower.startswith(starter):
            return False
    return True


def _is_explanation_start(line: str) -> bool:
    """Check if a line is the start of LLM explanation."""
    explanation_starters = [
        "this commit", "i chose", "i used", "here's", "here is",
        "the commit", "note:", "explanation:", "let me explain",
        "the above", "this follows", "this message",
    ]
    lower = line.lower()
    return any(lower.startswith(s) for s in explanation_starters)


# --- Commit Message Parsing ---------------------------------------------------

def parse_commit_message(raw_msg: str) -> dict:
    """Parse a commit message into structured parts.

    Returns dict with keys: subject_line, type, scope, breaking_bang,
    description, body, footers, separator_ok.
    """
    lines = raw_msg.strip().split('\n')
    subject_line = lines[0].strip() if lines else ""

    parsed = {
        "subject_line": subject_line,
        "type": None,
        "scope": None,
        "breaking_bang": False,
        "description": "",
        "separator": "",
        "body": None,
        "footers": [],
        "raw": raw_msg.strip(),
    }

    # Parse subject line
    match = SUBJECT_RE.match(subject_line)
    if match:
        parsed["type"] = match.group("type")
        parsed["scope"] = match.group("scope")  # None if no scope
        parsed["breaking_bang"] = match.group("breaking") == "!"
        parsed["separator"] = match.group("sep")
        parsed["description"] = match.group("description").strip()

    # Parse body and footers
    if len(lines) > 1:
        # Find body and footer sections
        body_lines = []
        footer_lines = []
        in_footer = False
        body_started = False

        for i, line in enumerate(lines[1:], start=1):
            stripped = line.strip()

            if i == 1:
                # Should be blank line
                if stripped == '':
                    continue
                else:
                    # No blank line separator, still treat rest as body
                    body_started = True
                    body_lines.append(line)
                    continue

            if not body_started and stripped == '':
                continue

            body_started = True

            # Check if this is a footer line
            if _is_footer_line(stripped):
                in_footer = True

            if in_footer:
                footer_lines.append(stripped)
            else:
                body_lines.append(line)

        # Trim trailing blank lines from body
        while body_lines and body_lines[-1].strip() == '':
            body_lines.pop()

        if body_lines:
            parsed["body"] = '\n'.join(body_lines)

        # Parse footer lines into structured footers (with multiline support)
        for fline in footer_lines:
            colon_pos = fline.find(':')
            if colon_pos > 0 and _is_footer_line(fline):
                token = fline[:colon_pos].strip()
                value = fline[colon_pos + 1:].strip()
                parsed["footers"].append({"token": token, "value": value})
            elif parsed["footers"]:
                # Continuation line — append to previous footer value
                parsed["footers"][-1]["value"] += " " + fline.strip()

    return parsed


# --- Structure Validation -----------------------------------------------------

def validate_structure(message: str) -> tuple[bool, list[str]]:
    """Check that the commit message has basic valid structure.

    Returns (is_valid, list_of_errors).
    """
    errors = []

    if not message or not message.strip():
        return False, ["empty message"]

    lines = message.strip().split('\n')
    subject = lines[0].strip()

    if not subject:
        errors.append("empty subject line")
        return False, errors

    # Check basic subject format
    match = SUBJECT_RE.match(subject)
    if not match:
        errors.append(f"subject doesn't match conventional commit format: '{subject}'")
        return len(errors) == 0, errors

    commit_type = match.group("type")
    if commit_type not in VALID_TYPES:
        errors.append(f"invalid type: '{commit_type}'")

    return len(errors) == 0, errors


# --- Individual Rule Checks ---------------------------------------------------

def check_rule_1_type(parsed: dict, task: dict) -> tuple[bool, str]:
    """Rule 1: Valid type prefix."""
    t = parsed.get("type")
    if t is None:
        return False, "no type parsed"
    if t in VALID_TYPES:
        return True, f"valid type: {t}"
    return False, f"invalid type: '{t}', must be one of {sorted(VALID_TYPES)}"


def check_rule_2_separator(parsed: dict, task: dict) -> tuple[bool, str]:
    """Rule 2: Correct separator ': ' (colon + single space)."""
    sep = parsed.get("separator", "")
    if sep == ": ":
        return True, "ok"
    if not sep:
        return False, "no separator found"
    # Detect common variants (multi-space, tab, missing space)
    if re.match(r':[ \t]+', sep) and sep != ": ":
        return False, f"separator has extra whitespace: {repr(sep)}, expected ': '"
    return False, f"separator is {repr(sep)}, expected ': '"


def check_rule_3_imperative(parsed: dict, task: dict) -> tuple[bool, str]:
    """Rule 3: Imperative mood - first word not past/gerund/3rd person."""
    desc = parsed.get("description", "")
    if not desc:
        return False, "empty description"
    first_word = desc.split()[0].lower()
    if first_word in IMPERATIVE_BLACKLIST:
        return False, f"'{first_word}' is not imperative mood"
    return True, f"first word '{first_word}' is ok"


def check_rule_4_no_period(parsed: dict, task: dict) -> tuple[bool, str]:
    """Rule 4: No trailing period on description."""
    desc = parsed.get("description", "")
    if desc.rstrip().endswith("."):
        return False, "description ends with period"
    return True, "ok"


def check_rule_5_lowercase(parsed: dict, task: dict) -> tuple[bool, str]:
    """Rule 5: Description starts with lowercase letter."""
    desc = parsed.get("description", "")
    if not desc:
        return False, "empty description"
    # If the description starts with a gitmoji shortcode like :bug:, check
    # the first character after the shortcode instead
    check_str = desc
    gitmoji_match = re.match(r'^:[a-z_]+:\s*', desc)
    if gitmoji_match:
        check_str = desc[gitmoji_match.end():]
    if not check_str:
        return True, "ok (only gitmoji)"
    if check_str[0].isupper():
        return False, f"starts with uppercase '{check_str[0]}'"
    return True, "ok"


def check_rule_6_scope_vocab(parsed: dict, task: dict) -> tuple[bool, str]:
    """Rule 6: Scope must come from task's allowed_scopes list."""
    allowed = task.get("allowed_scopes", [])
    if not allowed:
        return True, "no allowed_scopes defined (auto-pass)"
    scope = parsed.get("scope")
    if scope is None:
        return False, f"no scope present, expected one of {allowed}"
    if scope in allowed:
        return True, f"scope '{scope}' in allowed list"
    return False, f"scope '{scope}' not in allowed_scopes: {allowed}"


def check_rule_7_gitmoji(parsed: dict, task: dict) -> tuple[bool, str]:
    """Rule 7: Description starts with gitmoji shortcode matching the type."""
    gitmoji_map = task.get("gitmoji_map", {})
    if not gitmoji_map:
        return True, "no gitmoji_map defined (auto-pass)"
    commit_type = parsed.get("type", "")
    expected_gitmoji = gitmoji_map.get(commit_type)
    if not expected_gitmoji:
        return True, f"no gitmoji mapping for type '{commit_type}' (auto-pass)"
    desc = parsed.get("description", "")
    expected_prefix = expected_gitmoji + " "
    if desc.startswith(expected_prefix):
        return True, f"description starts with {expected_gitmoji}"
    # Also accept without trailing space if description is just the gitmoji
    if desc == expected_gitmoji:
        return True, f"description is {expected_gitmoji}"
    return False, f"expected description to start with '{expected_prefix}', got '{desc[:30]}'"


def check_rule_8_body_why_what(parsed: dict, task: dict) -> tuple[bool, str]:
    """Rule 8: Body must contain both Why: and What: section headers."""
    body = parsed.get("body")
    if not body:
        return False, "no body present (Why: and What: sections required)"
    body_lower = body.lower()
    has_why = False
    has_what = False
    for line in body_lower.split('\n'):
        stripped = line.strip()
        if stripped.startswith("why:"):
            has_why = True
        if stripped.startswith("what:"):
            has_what = True
    if has_why and has_what:
        return True, "both Why: and What: sections found"
    missing = []
    if not has_why:
        missing.append("Why:")
    if not has_what:
        missing.append("What:")
    return False, f"missing sections: {', '.join(missing)}"


def check_rule_9_body_word_count(parsed: dict, task: dict) -> tuple[bool, str]:
    """Rule 9: Body word count between task.body_min_words and task.body_max_words."""
    min_words = task.get("body_min_words")
    max_words = task.get("body_max_words")
    if min_words is None and max_words is None:
        return True, "no word count constraints (auto-pass)"
    body = parsed.get("body", "") or ""
    word_count = len(body.split()) if body.strip() else 0
    if min_words is not None and word_count < min_words:
        return False, f"body has {word_count} words, minimum is {min_words}"
    if max_words is not None and word_count > max_words:
        return False, f"body has {word_count} words, maximum is {max_words}"
    return True, f"body has {word_count} words (range: {min_words}-{max_words})"


def check_rule_10_trailer_format(parsed: dict, task: dict) -> tuple[bool, str]:
    """Rule 10: All footers must use git-trailer Key: value format."""
    footers = parsed.get("footers", [])
    if not footers:
        return True, "no footers present"
    bad_footers = []
    for f in footers:
        token = f.get("token", "")
        value = f.get("value", "")
        # Token must be a word (possibly with hyphens or spaces for BREAKING CHANGE)
        if not token:
            bad_footers.append(f"empty token")
            continue
        if not re.match(r'^[A-Za-z][A-Za-z0-9 -]*$', token):
            bad_footers.append(f"invalid token: '{token}'")
            continue
        if not value.strip():
            bad_footers.append(f"empty value for token '{token}'")
    if bad_footers:
        return False, f"invalid trailer(s): {'; '.join(bad_footers)}"
    return True, f"all {len(footers)} footer(s) in Key: value format"


def check_rule_11_signed_off_by(parsed: dict, task: dict) -> tuple[bool, str]:
    """Rule 11: Must have Signed-off-by footer matching task.signed_off_by."""
    expected = task.get("signed_off_by")
    if not expected:
        return True, "no signed_off_by required (auto-pass)"
    sob_footers = [
        f for f in parsed.get("footers", [])
        if f["token"] == "Signed-off-by"
    ]
    if not sob_footers:
        # Also check raw message as fallback
        raw = parsed.get("raw", "")
        if f"Signed-off-by: {expected}" in raw:
            return True, f"Signed-off-by found in raw message"
        return False, f"missing Signed-off-by footer, expected '{expected}'"
    for sob in sob_footers:
        if sob["value"].strip() == expected.strip():
            return True, f"Signed-off-by matches: {expected}"
    actual_values = [s["value"].strip() for s in sob_footers]
    return False, f"Signed-off-by value mismatch: got {actual_values}, expected '{expected}'"


def check_rule_12_breaking_footer(parsed: dict, task: dict) -> tuple[bool, str]:
    """Rule 12: BREAKING CHANGE footer when task.breaking_change=true, value >= 10 chars."""
    task_breaking = task.get("breaking_change", False)
    if not task_breaking:
        return True, "n/a (not a breaking change)"
    bc_footers = [
        f for f in parsed.get("footers", [])
        if f["token"].upper().replace("-", " ") == "BREAKING CHANGE"
    ]
    if not bc_footers:
        return False, "missing BREAKING CHANGE footer"
    value = bc_footers[0]["value"]
    if len(value.strip()) < 10:
        return False, f"BREAKING CHANGE footer too short: '{value.strip()}'"
    return True, f"BREAKING CHANGE footer present ({len(value.strip())} chars)"


def check_rule_13_ticket_ref(parsed: dict, task: dict) -> tuple[bool, str]:
    """Rule 13: Must have Ticket: PROJ-123 footer (JIRA-style, not #123)."""
    jira_project = task.get("jira_project")
    jira_number = task.get("jira_number")
    if not jira_project or not jira_number:
        return True, "no jira_project/jira_number in task (auto-pass)"
    expected_ref = f"{jira_project}-{jira_number}"
    # Check footers for Ticket token
    ticket_footers = [
        f for f in parsed.get("footers", [])
        if f["token"] == "Ticket"
    ]
    for tf in ticket_footers:
        if expected_ref in tf["value"]:
            return True, f"Ticket footer contains {expected_ref}"
    # Fallback: search raw message for Ticket: PROJ-NNN
    raw = parsed.get("raw", "")
    if re.search(r'Ticket:\s*' + re.escape(expected_ref), raw):
        return True, f"Ticket ref {expected_ref} found in raw message"
    return False, f"missing Ticket: {expected_ref} footer"


def check_rule_14_subject_length(parsed: dict, task: dict) -> tuple[bool, str]:
    """Rule 14: Full subject line <= 50 characters."""
    subject = parsed.get("subject_line", "")
    length = len(subject)
    if length <= MAX_SUBJECT_LENGTH:
        return True, f"length={length} <= {MAX_SUBJECT_LENGTH}"
    return False, f"length={length} > {MAX_SUBJECT_LENGTH}"


# --- All Checks Registry -----------------------------------------------------

RULE_CHECKS = [
    ("rule_1_type", check_rule_1_type),
    ("rule_2_separator", check_rule_2_separator),
    ("rule_3_imperative", check_rule_3_imperative),
    ("rule_4_no_period", check_rule_4_no_period),
    ("rule_5_lowercase", check_rule_5_lowercase),
    ("rule_6_scope_vocab", check_rule_6_scope_vocab),
    ("rule_7_gitmoji", check_rule_7_gitmoji),
    ("rule_8_body_why_what", check_rule_8_body_why_what),
    ("rule_9_body_word_count", check_rule_9_body_word_count),
    ("rule_10_trailer_format", check_rule_10_trailer_format),
    ("rule_11_signed_off_by", check_rule_11_signed_off_by),
    ("rule_12_breaking_footer", check_rule_12_breaking_footer),
    ("rule_13_ticket_ref", check_rule_13_ticket_ref),
    ("rule_14_subject_length", check_rule_14_subject_length),
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
for rule_name, _ in RULE_CHECKS:
    CSV_FIELDS.append(f"{rule_name}_pass")
    CSV_FIELDS.append(f"{rule_name}_detail")
CSV_FIELDS.extend(["auto_score", "scored_rules"])


# --- Task Loading -------------------------------------------------------------

def load_task(task_id: str) -> dict:
    """Load task JSON from test-data directory."""
    # Try all JSON files in test-data/
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

    # Load task data for comparison
    task = load_task(row["task"])

    # Extract token usage and commit message from raw output
    raw_output = result.get("raw_output", "")
    row.update(extract_token_usage(raw_output))

    message, extract_error = extract_commit_message(raw_output)

    row["extraction_ok"] = message is not None
    row["extraction_error"] = extract_error or ""

    if message is None:
        # Cannot check anything else
        row["structure_valid"] = False
        row["structure_errors"] = extract_error or "extraction failed"
        for rule_name, _ in RULE_CHECKS:
            row[f"{rule_name}_pass"] = False
            row[f"{rule_name}_detail"] = "no commit message extracted"
        row["auto_score"] = 0
        row["scored_rules"] = 0
        return row

    # Structure validation
    struct_ok, struct_errors = validate_structure(message)
    row["structure_valid"] = struct_ok
    row["structure_errors"] = "; ".join(struct_errors) if struct_errors else ""

    # Parse commit message
    parsed = parse_commit_message(message)

    # Run all rule checks
    auto_score = 0
    scored_rules = 0
    for rule_name, check_fn in RULE_CHECKS:
        passed, detail = check_fn(parsed, task)
        row[f"{rule_name}_pass"] = passed
        row[f"{rule_name}_detail"] = detail
        scored_rules += 1
        if passed:
            auto_score += 1

    row["auto_score"] = auto_score
    row["scored_rules"] = scored_rules

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

    print(f"\nResults written to {OUTPUT_CSV}")
    print(f"  Total runs: {len(rows)}")
    print(f"  Extraction ok: {extraction_ok}/{len(rows)}")
    print(f"  Structure valid: {structure_valid}/{len(rows)}")

    # Auto-score summary by condition
    print(f"\nAuto-score by condition ({len(RULE_CHECKS)} scored rules, 0 excluded):")
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
