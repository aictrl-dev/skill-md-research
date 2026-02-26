#!/usr/bin/env python3
"""
Evaluate Dockerfile experiment results: extract Dockerfile from raw output,
apply automated rule checks (13 automatable + 1 manual), output CSV.

Usage:
    python evaluate_dockerfile.py                  # Process all results in results/
    python evaluate_dockerfile.py results/foo.json # Process specific file(s)
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
TASK_DATA_DIR = SCRIPT_DIR / "test-data"
OUTPUT_CSV = RESULTS_DIR / "scores.csv"


# --- Dockerfile Extraction ----------------------------------------------------

def extract_dockerfile(raw_output: str) -> tuple[str | None, str | None]:
    """Extract a Dockerfile from raw LLM output.

    Tries multiple strategies:
      1. JSONL (opencode) event stream -> extract text parts
      2. Claude CLI JSON response -> extract 'result' field
      3. Fenced code block: ```dockerfile, ```Dockerfile, ``` with FROM inside
      4. After a "Dockerfile:" or "```" header, plain text starting with FROM
      5. Plain text starting with FROM (unfenced)

    Returns (dockerfile_text, error_or_None).
    """
    if not raw_output:
        return None, "empty output"

    text = raw_output

    # Step 0: JSONL (opencode) — newline-delimited JSON events
    if "\n" in raw_output and raw_output.lstrip().startswith("{"):
        lines = raw_output.strip().split("\n")
        text_parts = []
        is_jsonl = False
        for line in lines:
            try:
                evt = json.loads(line)
                if isinstance(evt, dict) and "type" in evt and "sessionID" in evt:
                    is_jsonl = True
                    if evt["type"] == "text":
                        text_parts.append(evt["part"]["text"])
            except (json.JSONDecodeError, KeyError):
                continue
        if is_jsonl:
            # Use text parts if found, otherwise empty string so fallback triggers
            text = "\n".join(text_parts) if text_parts else ""

    # Step 1: Claude CLI JSON response
    try:
        cli_response = json.loads(raw_output)
        if isinstance(cli_response, dict) and "result" in cli_response:
            text = cli_response["result"]
    except json.JSONDecodeError:
        pass

    # Step 1b: Fallback to permission_denials (model tried Write tool instead of text)
    if "FROM " not in text:
        denied_content = extract_from_permission_denials(raw_output)
        if denied_content and "FROM " in denied_content:
            # Content from Write tool is already a clean Dockerfile — return directly
            return denied_content.strip(), None

    # Step 2: Fenced code block — ```dockerfile or ```Dockerfile
    patterns = [
        r"```[Dd]ockerfile\s*\n(.*?)\n\s*```",
        r"```\s*\n(.*?)\n\s*```",
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, text, re.DOTALL):
            candidate = match.group(1).strip()
            if "FROM" in candidate:
                return candidate, None

    # Step 3: After "Dockerfile:" header, look for FROM block
    header_match = re.search(r"(?:Dockerfile|dockerfile)\s*:\s*\n", text)
    if header_match:
        rest = text[header_match.end():]
        # Take lines until a blank line or end of text
        dockerfile_lines = []
        for line in rest.split("\n"):
            if dockerfile_lines and line.strip() == "" and not line.startswith(" "):
                # Allow one blank line inside, stop on second consecutive
                if dockerfile_lines[-1].strip() == "":
                    break
            dockerfile_lines.append(line)
        candidate = "\n".join(dockerfile_lines).strip()
        if "FROM" in candidate:
            return candidate, None

    # Step 4: Plain text starting with FROM (unfenced)
    from_match = re.search(r"^(FROM\s+\S+.*?)(?:\n\n[A-Z]|\Z)", text, re.DOTALL | re.MULTILINE)
    if from_match:
        candidate = from_match.group(1).strip()
        if len(candidate) > 20:
            return candidate, None

    return None, "could not extract Dockerfile from output"


# --- Structure Validation -----------------------------------------------------

def validate_structure(dockerfile: str) -> tuple[bool, list[str]]:
    """Basic structural validation: must have FROM and CMD/ENTRYPOINT."""
    errors = []
    lines = dockerfile.strip().split("\n")
    instructions = [l.strip() for l in lines if l.strip() and not l.strip().startswith("#")]

    has_from = any(l.upper().startswith("FROM ") for l in instructions)
    has_cmd = any(l.upper().startswith("CMD ") or l.upper().startswith("ENTRYPOINT ") for l in instructions)

    if not has_from:
        errors.append("missing FROM instruction")
    if not has_cmd:
        errors.append("missing CMD or ENTRYPOINT instruction")

    return len(errors) == 0, errors


# --- Load Task Data -----------------------------------------------------------

def load_task(task_id: str) -> dict:
    """Load task JSON for expected values."""
    task_file = TASK_DATA_DIR / f"task-{task_id}-*.json"
    matches = list(TASK_DATA_DIR.glob(f"task-{task_id}-*.json"))
    if matches:
        with open(matches[0]) as f:
            return json.load(f)
    return {}


# --- Helper: Parse Instructions -----------------------------------------------

def _parse_instructions(dockerfile: str) -> list[tuple[str, str]]:
    """Parse Dockerfile into (INSTRUCTION, rest_of_line) tuples.

    Handles line continuations (backslash-newline).
    """
    # Join continuation lines
    joined = re.sub(r"\\\s*\n", " ", dockerfile)
    result = []
    for line in joined.split("\n"):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        # Split into instruction and arguments
        parts = stripped.split(None, 1)
        if parts:
            instruction = parts[0].upper()
            args = parts[1] if len(parts) > 1 else ""
            result.append((instruction, args))
    return result


def _raw_lines(dockerfile: str) -> list[str]:
    """Return non-empty, non-comment lines (no continuation joining)."""
    return [l.strip() for l in dockerfile.split("\n")
            if l.strip() and not l.strip().startswith("#")]


# --- Rule Checks (1-14) -------------------------------------------------------

def check_rule_1_tag(dockerfile: str, task: dict) -> tuple[bool, str]:
    """Rule 1 (BASE): Every FROM must have a specific version tag.

    Pass: all FROM images have a tag that is not 'latest'.
    Fail: any FROM without tag or with :latest.

    Stage aliases (FROM chef AS builder, where 'chef' was defined by an earlier
    FROM ... AS chef) are exempt — they reference a build stage, not a registry image.
    """
    instructions = _parse_instructions(dockerfile)
    from_instructions = [(i, args) for i, args in instructions if i == "FROM"]

    if not from_instructions:
        return False, "no FROM found"

    # Collect stage aliases defined by AS clauses
    stage_aliases = set()
    for _, args in from_instructions:
        parts = args.split()
        # FROM image:tag AS alias  →  parts = ["image:tag", "AS", "alias"]
        for idx, p in enumerate(parts):
            if p.upper() == "AS" and idx + 1 < len(parts):
                stage_aliases.add(parts[idx + 1].lower())

    bad = []
    for _, args in from_instructions:
        # FROM image:tag AS alias  or  FROM image AS alias  or  FROM image:tag
        image_part = args.split()[0] if args.split() else args
        # Handle scratch (special case, no tag needed)
        if image_part.lower() == "scratch":
            continue
        # Handle stage alias references (FROM chef, FROM rust-builder, etc.)
        if image_part.lower() in stage_aliases:
            continue
        if ":" not in image_part:
            bad.append(f"{image_part} (no tag)")
        else:
            tag = image_part.split(":", 1)[1]
            if tag.lower() == "latest":
                bad.append(f"{image_part} (uses :latest)")

    if bad:
        return False, f"unversioned FROM: {', '.join(bad)}"
    return True, "ok"


def check_rule_2_user(dockerfile: str, task: dict) -> tuple[bool, str]:
    """Rule 2 (SECURITY): Non-root USER directive present."""
    instructions = _parse_instructions(dockerfile)
    user_instructions = [(i, args) for i, args in instructions if i == "USER"]

    if not user_instructions:
        return False, "no USER instruction found"

    # Check that at least one USER is non-root
    for _, args in user_instructions:
        user = args.strip().split(":")[0]  # USER user:group
        if user.lower() not in ("root", "0"):
            return True, f"ok (USER {user})"

    return False, "USER is root"


def check_rule_3_secrets(dockerfile: str, task: dict) -> tuple[bool, str]:
    """Rule 3 (SECURITY): No secrets in ENV or ARG.

    SEMI-AUTO: heuristic based on common secret patterns.
    """
    instructions = _parse_instructions(dockerfile)
    secret_patterns = [
        r"password", r"secret", r"token", r"api[_-]?key",
        r"private[_-]?key", r"credential", r"aws[_-]?secret",
    ]
    pattern = re.compile("|".join(secret_patterns), re.IGNORECASE)

    suspects = []
    for instr, args in instructions:
        if instr in ("ENV", "ARG"):
            if pattern.search(args):
                # Check if it's just a variable name without a hardcoded value
                # e.g. ARG API_KEY (no default) is ok, ARG API_KEY=secret is not
                if "=" in args:
                    suspects.append(f"{instr} {args.split('=')[0].strip()}")

    if suspects:
        return False, f"possible secrets: {', '.join(suspects)}"
    return True, "ok"


def check_rule_4_multistage(dockerfile: str, task: dict) -> tuple[bool, str]:
    """Rule 4 (STRUCTURE): Multi-stage build — at least 2 FROM statements."""
    instructions = _parse_instructions(dockerfile)
    from_count = sum(1 for i, _ in instructions if i == "FROM")

    if from_count < 2:
        return False, f"only {from_count} FROM (need >= 2 for multi-stage)"
    return True, f"ok ({from_count} stages)"


def check_rule_5_workdir(dockerfile: str, task: dict) -> tuple[bool, str]:
    """Rule 5 (STRUCTURE): WORKDIR set before first COPY or RUN.

    Handles WORKDIR inheritance: when FROM references a stage alias that had
    WORKDIR set, the child stage inherits it (standard Docker behavior).
    """
    instructions = _parse_instructions(dockerfile)

    # First pass: collect which stage aliases define a WORKDIR
    stage_has_workdir: dict[str, bool] = {}
    current_alias: str | None = None
    for instr, args in instructions:
        if instr == "FROM":
            # Extract alias: FROM image AS alias
            parts = args.split()
            current_alias = None
            for idx, p in enumerate(parts):
                if p.upper() == "AS" and idx + 1 < len(parts):
                    current_alias = parts[idx + 1].lower()
        elif instr == "WORKDIR" and current_alias:
            stage_has_workdir[current_alias] = True

    # Second pass: check per stage
    workdir_seen = False
    for instr, args in instructions:
        if instr == "FROM":
            # Check if this FROM inherits from a stage that had WORKDIR
            image_part = args.split()[0] if args.split() else ""
            workdir_seen = stage_has_workdir.get(image_part.lower(), False)
            continue
        if instr == "WORKDIR":
            workdir_seen = True
            continue
        if instr in ("COPY", "RUN", "ADD"):
            if not workdir_seen:
                # Exception: COPY --from= is copying from another stage, ok without WORKDIR
                if instr == "COPY" and "--from=" in args:
                    continue
                # Exception: system-level operations that use absolute paths
                # and don't depend on the working directory:
                # - user/group creation and permission setup
                # - package manager installs (apt-get, apk, yum, dnf)
                # - cargo install (installs to /usr/local/cargo/bin)
                # - pip install (installs to system or venv at absolute path)
                # - python -m venv /path (creates venv at absolute path)
                if instr == "RUN":
                    args_lower = args.lower()
                    if any(cmd in args_lower for cmd in [
                        "adduser", "addgroup", "useradd", "groupadd",
                        "chown", "chmod", "setcap",
                        "apt-get", "apk add", "yum install", "dnf install",
                        "cargo install", "pip install", "npm install -g",
                        "python -m venv", "python3 -m venv",
                    ]):
                        continue
                return False, f"{instr} before WORKDIR in a stage"

    return True, "ok"


def check_rule_6_deps_first(dockerfile: str, task: dict) -> tuple[bool, str]:
    """Rule 6 (CACHE): Dependency files COPY'd before source code.

    SEMI-AUTO: looks for common dep file patterns before a broad COPY . .
    """
    instructions = _parse_instructions(dockerfile)
    dep_patterns = [
        r"package\.json", r"package-lock\.json", r"yarn\.lock",
        r"requirements\.txt", r"Pipfile", r"pyproject\.toml", r"poetry\.lock",
        r"go\.mod", r"go\.sum", r"Cargo\.toml", r"Cargo\.lock",
        r"pom\.xml", r"build\.gradle",
    ]
    dep_re = re.compile("|".join(dep_patterns))

    # Track per-stage
    found_dep_copy = False
    found_broad_copy = False
    for instr, args in instructions:
        if instr == "FROM":
            found_dep_copy = False
            found_broad_copy = False
            continue
        if instr == "COPY" and "--from=" not in args:
            if dep_re.search(args):
                found_dep_copy = True
            elif ". ." in args or args.strip().endswith(" .") or args.strip().endswith(" ./"):
                if found_dep_copy:
                    # Good: dep files were copied before broad copy
                    pass
                else:
                    found_broad_copy = True

    if found_broad_copy and not found_dep_copy:
        return False, "broad COPY before dependency file COPY"
    if found_dep_copy:
        return True, "ok (deps copied before source)"
    return True, "needs_review (no broad COPY detected)"


def check_rule_7_combined_run(dockerfile: str, task: dict) -> tuple[bool, str]:
    """Rule 7 (LAYERS): RUN commands combined — no more than 2 adjacent RUN lines.

    SEMI-AUTO: counts consecutive RUN instructions.
    """
    instructions = _parse_instructions(dockerfile)
    max_adjacent = 0
    current_run_streak = 0

    for instr, _ in instructions:
        if instr == "FROM":
            current_run_streak = 0
            continue
        if instr == "RUN":
            current_run_streak += 1
            max_adjacent = max(max_adjacent, current_run_streak)
        else:
            current_run_streak = 0

    if max_adjacent > 2:
        return False, f"{max_adjacent} adjacent RUN lines (max 2)"
    return True, f"ok (max {max_adjacent} adjacent)"


def check_rule_8_apt(dockerfile: str, task: dict) -> tuple[bool, str]:
    """Rule 8 (APT): --no-install-recommends + cache cleanup for apt-get install."""
    instructions = _parse_instructions(dockerfile)

    has_apt_install = False
    has_no_recommends = True
    has_cache_cleanup = True

    for instr, args in instructions:
        if instr == "RUN" and "apt-get" in args and "install" in args:
            has_apt_install = True
            if "--no-install-recommends" not in args:
                has_no_recommends = False
            if "rm -rf /var/lib/apt/lists" not in args:
                # Check if cleanup is in the same RUN (could be chained with &&)
                has_cache_cleanup = False

    if not has_apt_install:
        return True, "n/a (no apt-get install)"

    problems = []
    if not has_no_recommends:
        problems.append("missing --no-install-recommends")
    if not has_cache_cleanup:
        problems.append("missing rm -rf /var/lib/apt/lists/*")

    if problems:
        return False, "; ".join(problems)
    return True, "ok"


def check_rule_9_healthcheck(dockerfile: str, task: dict) -> tuple[bool, str]:
    """Rule 9 (HEALTH): HEALTHCHECK instruction present."""
    instructions = _parse_instructions(dockerfile)
    has_healthcheck = any(i == "HEALTHCHECK" for i, _ in instructions)

    if has_healthcheck:
        return True, "ok"
    return False, "no HEALTHCHECK instruction"


def check_rule_10_expose(dockerfile: str, task: dict) -> tuple[bool, str]:
    """Rule 10 (DOCS): EXPOSE instruction present."""
    instructions = _parse_instructions(dockerfile)
    expose_instructions = [(i, args) for i, args in instructions if i == "EXPOSE"]

    if not expose_instructions:
        return False, "no EXPOSE instruction"

    ports = [args.strip() for _, args in expose_instructions]
    return True, f"ok (EXPOSE {', '.join(ports)})"


def check_rule_11_label(dockerfile: str, task: dict) -> tuple[bool, str]:
    """Rule 11 (DOCS): At least one LABEL present."""
    instructions = _parse_instructions(dockerfile)
    has_label = any(i == "LABEL" for i, _ in instructions)

    if has_label:
        return True, "ok"
    return False, "no LABEL instruction"


def check_rule_12_exec_form(dockerfile: str, task: dict) -> tuple[bool, str]:
    """Rule 12 (ENTRY): CMD/ENTRYPOINT in exec form (JSON array).

    SEMI-AUTO: checks if CMD/ENTRYPOINT args start with '['.
    """
    instructions = _parse_instructions(dockerfile)
    problems = []

    for instr, args in instructions:
        if instr in ("CMD", "ENTRYPOINT"):
            args_stripped = args.strip()
            if not args_stripped.startswith("["):
                problems.append(f"{instr} uses shell form: {args_stripped[:50]}")

    if problems:
        return False, "; ".join(problems)

    # Check we found at least one CMD or ENTRYPOINT
    has_entry = any(i in ("CMD", "ENTRYPOINT") for i, _ in instructions)
    if not has_entry:
        return True, "needs_review (no CMD/ENTRYPOINT found)"
    return True, "ok"


def check_rule_13_no_add(dockerfile: str, task: dict) -> tuple[bool, str]:
    """Rule 13 (COPY): No ADD when COPY suffices.

    ADD is acceptable only for extracting tarballs (.tar, .tar.gz, .tgz)
    or fetching remote URLs.
    """
    instructions = _parse_instructions(dockerfile)
    bad_adds = []

    for instr, args in instructions:
        if instr == "ADD":
            args_lower = args.lower()
            # Allow if extracting tar
            if any(ext in args_lower for ext in [".tar", ".tgz", ".gz", ".bz2", ".xz"]):
                continue
            # Allow if fetching URL
            if args_lower.startswith("http://") or args_lower.startswith("https://"):
                continue
            bad_adds.append(args.strip()[:60])

    if bad_adds:
        return False, f"unnecessary ADD: {'; '.join(bad_adds)}"
    return True, "ok"


def check_rule_14_dockerignore(dockerfile: str, task: dict) -> tuple[bool, str]:
    """Rule 14 (IGNORE): .dockerignore considered.

    MANUAL: Cannot verify from Dockerfile alone. Always returns True with needs_review.
    """
    return True, "needs_review"


# --- Rule Registry -------------------------------------------------------------

RULE_CHECKS = {
    "rule_1_tag": check_rule_1_tag,
    "rule_2_user": check_rule_2_user,
    "rule_3_secrets": check_rule_3_secrets,
    "rule_4_multistage": check_rule_4_multistage,
    "rule_5_workdir": check_rule_5_workdir,
    "rule_6_deps_first": check_rule_6_deps_first,
    "rule_7_combined_run": check_rule_7_combined_run,
    "rule_8_apt": check_rule_8_apt,
    "rule_9_healthcheck": check_rule_9_healthcheck,
    "rule_10_expose": check_rule_10_expose,
    "rule_11_label": check_rule_11_label,
    "rule_12_exec_form": check_rule_12_exec_form,
    "rule_13_no_add": check_rule_13_no_add,
    "rule_14_dockerignore": check_rule_14_dockerignore,
}

# Rules excluded from auto_score (manual-only, cannot be verified from Dockerfile alone)
EXCLUDED_RULES = {"rule_14_dockerignore"}


# --- Outcome Checks (semantic correctness, not style) ----------------------------

def outcome_correct_port(dockerfile: str, task: dict) -> tuple[bool, str]:
    """OUTCOME: EXPOSE declares the correct port for this task."""
    expected_port = task.get("port") or task.get("requirements", {}).get("port")
    if not expected_port:
        return True, "no specific port required by task"
    expected_port = str(expected_port)
    expose_lines = re.findall(r'^\s*EXPOSE\s+(.+)', dockerfile, re.MULTILINE | re.IGNORECASE)
    all_ports = []
    for line in expose_lines:
        all_ports.extend(re.findall(r'\b(\d+)\b', line))
    if expected_port in all_ports:
        return True, f"port {expected_port} exposed"
    if not all_ports:
        return False, f"no EXPOSE found, expected port {expected_port}"
    return False, f"exposed ports {all_ports}, expected {expected_port}"


def outcome_target_names(dockerfile: str, task: dict) -> tuple[bool, str]:
    """OUTCOME: Multi-target builds have all required --target names."""
    if not task.get("multi_target"):
        return True, "n/a (not a multi-target build)"
    expected_targets = task.get("targets", [])
    if not expected_targets:
        return True, "no target names specified in task"
    from_as = re.findall(r'^\s*FROM\s+\S+.*?\s+[Aa][Ss]\s+(\S+)', dockerfile, re.MULTILINE)
    actual = {t.lower() for t in from_as}
    missing = [t for t in expected_targets if t.lower() not in actual]
    if not missing:
        return True, f"all {len(expected_targets)} targets found: {expected_targets}"
    return False, f"missing targets: {missing} (found: {sorted(actual)})"


def outcome_runtime_match(dockerfile: str, task: dict) -> tuple[bool, str]:
    """OUTCOME: Base image matches the expected runtime/language."""
    runtime = task.get("runtime", "")
    if not runtime or runtime == "multi":
        return True, "n/a (no single runtime or multi-service)"
    from_lines = re.findall(r'^\s*FROM\s+(\S+)', dockerfile, re.MULTILINE | re.IGNORECASE)
    if not from_lines:
        return False, "no FROM instruction found"
    # Map runtime to expected base image keywords
    runtime_keywords = {
        "node": ["node"],
        "python": ["python"],
        "go": ["golang", "go"],
        "java": ["openjdk", "eclipse-temurin", "java", "maven", "gradle"],
        "rust": ["rust"],
        "ruby": ["ruby"],
    }
    keywords = runtime_keywords.get(runtime, [runtime])
    for img in from_lines:
        img_lower = img.lower()
        if any(kw in img_lower for kw in keywords):
            return True, f"runtime '{runtime}' matched in FROM {img}"
    return False, f"runtime '{runtime}' not found in FROM images: {from_lines}"


OUTCOME_CHECKS = [
    ("outcome_correct_port", outcome_correct_port),
    ("outcome_target_names", outcome_target_names),
    ("outcome_runtime_match", outcome_runtime_match),
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
    "rule_1_tag_pass",
    "rule_1_tag_detail",
    "rule_2_user_pass",
    "rule_2_user_detail",
    "rule_3_secrets_pass",
    "rule_3_secrets_detail",
    "rule_4_multistage_pass",
    "rule_4_multistage_detail",
    "rule_5_workdir_pass",
    "rule_5_workdir_detail",
    "rule_6_deps_first_pass",
    "rule_6_deps_first_detail",
    "rule_7_combined_run_pass",
    "rule_7_combined_run_detail",
    "rule_8_apt_pass",
    "rule_8_apt_detail",
    "rule_9_healthcheck_pass",
    "rule_9_healthcheck_detail",
    "rule_10_expose_pass",
    "rule_10_expose_detail",
    "rule_11_label_pass",
    "rule_11_label_detail",
    "rule_12_exec_form_pass",
    "rule_12_exec_form_detail",
    "rule_13_no_add_pass",
    "rule_13_no_add_detail",
    "rule_14_dockerignore_pass",
    "rule_14_dockerignore_detail",
    "auto_score",
    "scored_rules",
    "needs_manual_review",
]
for outcome_name, _ in OUTCOME_CHECKS:
    CSV_FIELDS.append(f"{outcome_name}_pass")
    CSV_FIELDS.append(f"{outcome_name}_detail")
CSV_FIELDS.append("outcome_score")


# --- Main Evaluation -----------------------------------------------------------

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

    # Load task data for rule checks that need expected values
    task_id = result.get("task", "")
    task = load_task(task_id)

    # Extract token usage and Dockerfile from raw output
    raw = result.get("raw_output", "")
    row.update(extract_token_usage(raw))

    dockerfile, extract_error = extract_dockerfile(raw)

    row["extraction_ok"] = dockerfile is not None
    row["extraction_error"] = extract_error or ""

    if dockerfile is None:
        # Cannot check anything else
        row["structure_valid"] = False
        row["structure_errors"] = extract_error
        for name in RULE_CHECKS:
            row[f"{name}_pass"] = False
            row[f"{name}_detail"] = "no Dockerfile extracted"
        row["auto_score"] = 0
        row["scored_rules"] = 0
        row["needs_manual_review"] = False
        for outcome_name, _ in OUTCOME_CHECKS:
            row[f"{outcome_name}_pass"] = False
            row[f"{outcome_name}_detail"] = "no Dockerfile extracted"
        row["outcome_score"] = 0
        return row

    # Structure validation
    struct_ok, struct_errors = validate_structure(dockerfile)
    row["structure_valid"] = struct_ok
    row["structure_errors"] = "; ".join(struct_errors) if struct_errors else ""

    # Automated rule checks
    auto_score = 0
    scored_rules = 0
    needs_review = False
    for name, check_fn in RULE_CHECKS.items():
        passed, detail = check_fn(dockerfile, task)
        row[f"{name}_pass"] = passed
        row[f"{name}_detail"] = detail
        if name not in EXCLUDED_RULES:
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
        passed, detail = check_fn(dockerfile, task)
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
        # Exclude non-result files
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
    extracted = sum(1 for r in rows if r["extraction_ok"])
    struct_valid = sum(1 for r in rows if r["structure_valid"])
    needs_review = sum(1 for r in rows if r["needs_manual_review"])

    print(f"\nResults written to {OUTPUT_CSV}")
    print(f"  Total runs: {len(rows)}")
    print(f"  Extraction ok: {extracted}/{len(rows)}")
    print(f"  Structure valid: {struct_valid}/{len(rows)}")
    print(f"  Needs manual review: {needs_review}/{len(rows)}")

    # Auto-score summary by condition
    print(f"\nAuto-score by condition (max {len(RULE_CHECKS) - len(EXCLUDED_RULES)} scored rules, {len(EXCLUDED_RULES)} excluded):")
    conditions: dict[str, list[int]] = {}
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
