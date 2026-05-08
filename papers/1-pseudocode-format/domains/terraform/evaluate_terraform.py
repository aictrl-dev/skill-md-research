#!/usr/bin/env python3
"""
Evaluate Terraform experiment results: extract HCL from LLM output,
apply automated rule checks (15 rules), output CSV.

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
sys.path.insert(0, str(SCRIPT_DIR.parent.parent / "scripts"))
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
    "aws_eks_cluster", "aws_eks_node_group", "aws_kms_key",
    "aws_dynamodb_table", "aws_lambda_function", "aws_api_gateway_stage",
    "aws_wafv2_web_acl",
}

# Resource types where lifecycle { prevent_destroy = true } is required
STATEFUL_RESOURCES = {
    "aws_s3_bucket", "aws_db_instance", "aws_efs_file_system",
    "aws_dynamodb_table", "aws_kms_key", "aws_secretsmanager_secret",
    "aws_eks_cluster",
}

# Keywords in variable/output names that require sensitive = true
SENSITIVE_KEYWORDS = {
    "password", "secret", "token", "key", "connection_string",
    "private_key", "api_key", "credentials",
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

    # Step 1b: Fallback to permission_denials (models sometimes use Write tool)
    has_hcl = bool(re.search(r'\b(resource|variable)\s+"', text_to_search))
    if not has_hcl:
        denied_content = extract_from_permission_denials(raw_output)
        if denied_content and re.search(r'\b(resource|variable)\s', denied_content):
            text_to_search = denied_content

    # Step 2: Try fenced code blocks (most common)
    fence_patterns = [
        r"```(?:hcl|terraform|tf)\s*\n(.*?)\n\s*```",
        r"```\s*\n(.*?)\n\s*```",
    ]
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
    hcl_start = re.search(
        r'^\s*(terraform|provider|resource|variable|data|locals|output)\s',
        text_to_search,
        re.MULTILINE,
    )
    if hcl_start:
        candidate = text_to_search[hcl_start.start():].strip()
        candidate = _trim_trailing_explanation(candidate)
        if _looks_like_terraform(candidate):
            return candidate, None

    return None, "could not extract Terraform HCL from output"


def _looks_like_terraform(text: str) -> bool:
    """Check if text looks like Terraform HCL."""
    keywords = ["resource", "variable", "provider", "terraform", "output", "data", "locals"]
    for kw in keywords:
        if re.search(rf'\b{kw}\s', text):
            return True
    return False


def _trim_trailing_explanation(text: str) -> str:
    """Remove trailing LLM explanation after the HCL code."""
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

    while result_lines and result_lines[-1].strip() == '':
        result_lines.pop()

    return '\n'.join(result_lines)


# --- Structure Validation ----------------------------------------------------

def validate_structure(tf_text: str) -> tuple[bool, list[str]]:
    """Check that the Terraform config has at least one resource block."""
    errors = []
    if not tf_text or not tf_text.strip():
        return False, ["empty terraform configuration"]
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
    return text[start:]


def _extract_iam_policy_json(body: str) -> list[str]:
    """Extract IAM policy JSON from an HCL resource body.

    Handles both jsonencode({...}) and heredoc (<<EOF...EOF) patterns.
    Returns list of JSON-like strings representing policy documents.
    """
    policies = []

    # Pattern 1: jsonencode({...}) — extract the inner dict
    for match in re.finditer(r'jsonencode\s*\(', body):
        inner = _extract_block_body(body, match.end() - 1)
        if inner:
            # Remove the outer parens
            policies.append(inner[1:-1] if inner.startswith('(') else inner)

    # Pattern 2: heredoc <<EOF ... EOF or <<-EOF ... EOF
    for match in re.finditer(r'<<-?\s*(\w+)\s*\n(.*?)\n\s*\1', body, re.DOTALL):
        policies.append(match.group(2))

    # Pattern 3: inline policy = "..." with escaped JSON
    for match in re.finditer(r'policy\s*=\s*"((?:[^"\\]|\\.)*)"', body):
        policies.append(match.group(1).replace('\\"', '"').replace('\\n', '\n'))

    return policies


def _strip_hcl_comments(text: str) -> str:
    """Remove single-line comments from HCL text."""
    text = re.sub(r'#.*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'//.*$', '', text, flags=re.MULTILINE)
    return text


# --- Individual Rule Checks (15 rules) ---------------------------------------

def check_rule_1_naming(tf_text: str, task: dict) -> tuple[bool, str]:
    """Rule 1 (NAMING): snake_case resource names, descriptive (>3 chars)."""
    resources = _find_resource_blocks(tf_text)
    if not resources:
        return False, "no resources found"

    BAD_NAME = re.compile(r'^[a-z]{1,3}\d*$')
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
    """Rule 2 (VAR_DESCRIPTION): All variables have description attribute."""
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
    """Rule 3 (VAR_TYPE): All variables have type constraint."""
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
    """Rule 4 (OUTPUTS_PRESENT): At least N outputs (N from task min_outputs)."""
    outputs = _find_output_blocks(tf_text)
    min_outputs = task.get("min_outputs", 1)
    if len(outputs) < min_outputs:
        return False, f"{len(outputs)} outputs defined, need >={min_outputs}"
    return True, f"{len(outputs)} outputs defined (need >={min_outputs}): {[o[0] for o in outputs]}"


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


def check_rule_6_lifecycle_stateful(tf_text: str, task: dict) -> tuple[bool, str]:
    """Rule 6 (LIFECYCLE_STATEFUL): prevent_destroy = true on every stateful resource."""
    resources = _find_resource_blocks(tf_text)
    if not resources:
        return False, "no resources found"

    missing = []
    checked = 0
    for rtype, rname, body in resources:
        if rtype in STATEFUL_RESOURCES:
            checked += 1
            has_prevent = re.search(r'prevent_destroy\s*=\s*true', body)
            if not has_prevent:
                missing.append(f"{rtype}.{rname}")

    if not checked:
        return True, "no stateful resources found"
    if missing:
        return False, f"missing lifecycle prevent_destroy on: {missing[:5]}"
    return True, f"all {checked} stateful resources have prevent_destroy = true"


def check_rule_7_locals_for_tags(tf_text: str, task: dict) -> tuple[bool, str]:
    """Rule 7 (LOCALS_FOR_TAGS): locals block exists AND >=50% of taggable resources
    reference local.* for tags."""
    if not re.search(r'\blocals\s*\{', tf_text):
        return False, "no locals block defined"

    resources = _find_resource_blocks(tf_text)
    taggable = [(rtype, rname, body) for rtype, rname, body in resources
                if rtype in TAGGABLE_RESOURCES]

    if not taggable:
        return True, "locals block present, no taggable resources"

    using_local = 0
    for rtype, rname, body in taggable:
        # Check if tags reference local.* (local.common_tags, local.tags, merge(local.*, ...))
        tags_match = re.search(r'\btags\s*=\s*(.*?)$', body, re.MULTILINE)
        if tags_match:
            tags_val = tags_match.group(1).strip()
            if 'local.' in tags_val:
                using_local += 1
            # Also check merge(local.*, ...) on the same or next lines
            elif re.search(r'merge\s*\(.*local\.', body):
                using_local += 1

    pct = using_local / len(taggable) * 100
    if pct >= 50:
        return True, f"{using_local}/{len(taggable)} taggable resources use local.* for tags ({pct:.0f}%)"
    return False, f"only {using_local}/{len(taggable)} taggable resources use local.* for tags ({pct:.0f}%), need >=50%"


def check_rule_8_no_hardcoded_ids(tf_text: str, task: dict) -> tuple[bool, str]:
    """Rule 8 (NO_HARDCODED_IDS): No AMI IDs, 12-digit account numbers,
    region strings outside provider block."""
    violations = []

    if re.search(r'ami-[0-9a-f]{8,17}', tf_text):
        violations.append("hardcoded AMI ID (ami-*)")

    text_no_comments = _strip_hcl_comments(tf_text)
    if re.search(r'(?<!\d)\d{12}(?!\d)', text_no_comments):
        violations.append("possible hardcoded AWS account ID (12 digits)")

    region_pattern = r'"(us|eu|ap|sa|ca|me|af)-(east|west|south|north|central|northeast|southeast|southwest|northwest)-\d"'
    # Remove provider, terraform, and variable blocks — region strings are acceptable there
    text_no_provider = tf_text
    for match in reversed(list(re.finditer(r'(?:provider\s+"[^"]+"|terraform|variable\s+"[^"]+")\s*\{', tf_text))):
        block_body = _extract_block_body(tf_text, match.end() - 1)
        text_no_provider = text_no_provider[:match.start()] + text_no_provider[match.start() + len(match.group()) + len(block_body) - 1:]
    if re.search(region_pattern, text_no_provider):
        violations.append("hardcoded region string in resource block")

    if violations:
        return False, "; ".join(violations)
    return True, "no hardcoded IDs found"


def check_rule_9_provider_pinned(tf_text: str, task: dict) -> tuple[bool, str]:
    """Rule 9 (PROVIDER_PINNED): Provider version pinned in required_providers block."""
    rp_match = re.search(r'required_providers\s*\{', tf_text)
    if not rp_match:
        return False, "no required_providers block found"

    rp_body = _extract_block_body(tf_text, rp_match.end() - 1)
    provider_blocks = re.findall(r'\w+\s*=\s*\{([^}]*)\}', rp_body)
    for pb in provider_blocks:
        if re.search(r'\bversion\s*=\s*"[^"]*"', pb):
            match = re.search(r'\bversion\s*=\s*"([^"]*)"', pb)
            version = match.group(1) if match else "?"
            return True, f"provider version pinned: {version}"

    return False, "required_providers block found but no version constraint"


def check_rule_10_backend_with_locking(tf_text: str, task: dict) -> tuple[bool, str]:
    """Rule 10 (BACKEND_WITH_LOCKING): Backend configured AND dynamodb_table for state locking."""
    has_backend = re.search(r'backend\s+"[^"]+"\s*\{', tf_text)
    has_cloud = re.search(r'\bcloud\s*\{', tf_text)

    if not has_backend and not has_cloud:
        return False, "no backend configuration found"

    if has_backend:
        backend_match = re.search(r'backend\s+"([^"]+)"\s*\{', tf_text)
        backend_type = backend_match.group(1) if backend_match else "?"
        backend_body = _extract_block_body(tf_text, backend_match.end() - 1)
        if re.search(r'\bdynamodb_table\s*=', backend_body):
            return True, f"backend {backend_type} with DynamoDB locking"
        return False, f"backend {backend_type} configured but no dynamodb_table for state locking"

    # Terraform Cloud uses its own locking
    return True, "backend configured: terraform cloud (built-in locking)"


def check_rule_11_iam_least_privilege(tf_text: str, task: dict) -> tuple[bool, str]:
    """Rule 11 (IAM_LEAST_PRIVILEGE): No '*' in Action or Resource in IAM policies.
    No service wildcards (s3:*, ec2:*, etc.)."""
    resources = _find_resource_blocks(tf_text)
    iam_resources = [
        (rtype, rname, body)
        for rtype, rname, body in resources
        if rtype in ("aws_iam_role_policy", "aws_iam_policy", "aws_iam_policy_document")
    ]

    if not iam_resources:
        # Also check inline assume_role_policy on aws_iam_role
        iam_roles = [(rtype, rname, body) for rtype, rname, body in resources
                     if rtype == "aws_iam_role"]
        # If no IAM policy resources at all, this is a fail for tasks that require IAM
        if not iam_roles:
            return False, "no IAM policy resources found"
        # Check assume_role_policy on roles — those are trust policies, not permission policies
        # Permission policies are what we care about
        return False, "no IAM permission policy resources found (aws_iam_role_policy or aws_iam_policy)"

    violations = []
    for rtype, rname, body in iam_resources:
        policy_docs = _extract_iam_policy_json(body)

        # Check both the raw body and extracted policy docs for wildcards
        # HCL jsonencode uses unquoted keys (Action =), JSON uses quoted ("Action":)
        check_texts = [body] + policy_docs

        found_action_wildcard = False
        found_resource_wildcard = False
        found_service_wildcard = False

        for check_text in check_texts:
            # Action = "*" (HCL unquoted key)
            if re.search(r'\bAction\s*=\s*"\*"', check_text):
                found_action_wildcard = True
            # "Action": "*" (JSON quoted key)
            if re.search(r'"Action"\s*:\s*"\*"', check_text):
                found_action_wildcard = True
            # Action = ["*"] or "Action": ["*"]
            if re.search(r'\bAction\s*[:=]\s*\[\s*"\*"\s*\]', check_text):
                found_action_wildcard = True
            # HCL data source style: actions = ["*"]
            if re.search(r'\bactions?\s*=\s*\[\s*"\*"\s*\]', check_text):
                found_action_wildcard = True

            # Resource = "*" (HCL unquoted key)
            if re.search(r'\bResource\s*=\s*"\*"', check_text):
                found_resource_wildcard = True
            # "Resource": "*" (JSON quoted key)
            if re.search(r'"Resource"\s*:\s*"\*"', check_text):
                found_resource_wildcard = True
            # Resource = ["*"] or "Resource": ["*"]
            if re.search(r'\bResource\s*[:=]\s*\[\s*"\*"\s*\]', check_text):
                found_resource_wildcard = True
            # HCL data source style: resources = ["*"]
            if re.search(r'\bresources?\s*=\s*\[\s*"\*"\s*\]', check_text):
                found_resource_wildcard = True

            # Service wildcards: "s3:*", "ec2:*", etc.
            service_wildcards = re.findall(r'"([a-z0-9]+):\*"', check_text)
            if service_wildcards:
                found_service_wildcard = True

        if found_action_wildcard:
            violations.append(f"{rtype}.{rname}: wildcard Action")
        if found_resource_wildcard:
            violations.append(f"{rtype}.{rname}: wildcard Resource")
        if found_service_wildcard:
            violations.append(f"{rtype}.{rname}: service wildcard")

    # Deduplicate
    violations = list(dict.fromkeys(violations))

    if violations:
        return False, "; ".join(violations[:5])
    return True, f"all {len(iam_resources)} IAM policies follow least privilege"


def check_rule_12_sg_no_open_ingress(tf_text: str, task: dict) -> tuple[bool, str]:
    """Rule 12 (SG_NO_OPEN_INGRESS): No 0.0.0.0/0 on non-80/443 ports.
    Checks inline ingress {} blocks and aws_security_group_rule resources."""
    violations = []

    # Check inline security group ingress blocks
    sg_resources = [(rtype, rname, body) for rtype, rname, body in _find_resource_blocks(tf_text)
                    if rtype == "aws_security_group"]

    for rtype, rname, body in sg_resources:
        # Find ingress blocks within the SG body
        for ing_match in re.finditer(r'\bingress\s*\{', body):
            ing_body = _extract_block_body(body, ing_match.end() - 1)
            if _ingress_has_open_cidr(ing_body):
                # Check if it's on a safe port (80, 443)
                port = _extract_port(ing_body)
                if port not in (80, 443):
                    violations.append(f"{rtype}.{rname}: ingress 0.0.0.0/0 on port {port}")

    # Check aws_security_group_rule resources
    sg_rules = [(rtype, rname, body) for rtype, rname, body in _find_resource_blocks(tf_text)
                if rtype == "aws_security_group_rule"]

    for rtype, rname, body in sg_rules:
        if re.search(r'\btype\s*=\s*"ingress"', body):
            if _ingress_has_open_cidr(body):
                port = _extract_port(body)
                if port not in (80, 443):
                    violations.append(f"{rtype}.{rname}: ingress 0.0.0.0/0 on port {port}")

    if violations:
        return False, "; ".join(violations[:5])

    # Count SGs found for detail message
    total_sgs = len(sg_resources) + len(sg_rules)
    if total_sgs == 0:
        return True, "no security groups found"
    return True, f"all {total_sgs} security group entries pass ingress check"


def _ingress_has_open_cidr(block_body: str) -> bool:
    """Check if an ingress block has 0.0.0.0/0 or ::/0."""
    return bool(re.search(r'0\.0\.0\.0/0|::/0', block_body))


def _extract_port(block_body: str) -> int | None:
    """Extract the port from an ingress block (from_port or to_port)."""
    match = re.search(r'\bfrom_port\s*=\s*(\d+)', block_body)
    if match:
        return int(match.group(1))
    match = re.search(r'\bto_port\s*=\s*(\d+)', block_body)
    if match:
        return int(match.group(1))
    return None


def check_rule_13_sensitive_marked(tf_text: str, task: dict) -> tuple[bool, str]:
    """Rule 13 (SENSITIVE_MARKED): Variables/outputs with sensitive keywords
    in the name must have sensitive = true. Keyword-heuristic on all tasks."""
    variables = _find_variable_blocks(tf_text)
    outputs = _find_output_blocks(tf_text)

    violations = []

    for vname, body in variables:
        vname_lower = vname.lower()
        if any(kw in vname_lower for kw in SENSITIVE_KEYWORDS):
            if not re.search(r'\bsensitive\s*=\s*true\b', body):
                violations.append(f"var.{vname}: contains sensitive keyword but not marked sensitive")

    for oname, body in outputs:
        oname_lower = oname.lower()
        if any(kw in oname_lower for kw in SENSITIVE_KEYWORDS):
            if not re.search(r'\bsensitive\s*=\s*true\b', body):
                violations.append(f"output.{oname}: contains sensitive keyword but not marked sensitive")

    if violations:
        return False, "; ".join(violations[:5])

    # Count how many sensitive items we found
    sensitive_vars = [vname for vname, body in variables
                      if re.search(r'\bsensitive\s*=\s*true\b', body)]
    sensitive_outputs = [oname for oname, body in outputs
                         if re.search(r'\bsensitive\s*=\s*true\b', body)]

    if sensitive_vars or sensitive_outputs:
        return True, f"sensitive vars: {sensitive_vars}, outputs: {sensitive_outputs}"
    return True, "no variables/outputs with sensitive keywords found"


def check_rule_14_resource_coverage(tf_text: str, task: dict) -> tuple[bool, str]:
    """Rule 14 (RESOURCE_COVERAGE): >=70% of required resource types present."""
    expected = task.get("resources", [])
    if not expected:
        return True, "no expected resources in task"

    actual_types = set(re.findall(r'resource\s+"([^"]+)"', tf_text))
    found = [r for r in expected if r in actual_types]
    pct = len(found) / len(expected) * 100
    if pct >= 70:
        return True, f"{len(found)}/{len(expected)} resources ({pct:.0f}%)"
    missing = [r for r in expected if r not in actual_types]
    return False, f"only {len(found)}/{len(expected)} resources ({pct:.0f}%), need >=70%. Missing: {missing[:5]}"


def check_rule_15_data_sources_used(tf_text: str, task: dict) -> tuple[bool, str]:
    """Rule 15 (DATA_SOURCES_USED): At least one data block."""
    data_blocks = _find_data_blocks(tf_text)
    if not data_blocks:
        return False, "no data sources defined"
    names = [f"{dtype}.{dname}" for dtype, dname in data_blocks]
    return True, f"{len(data_blocks)} data sources: {names}"


# --- All Checks Registry -----------------------------------------------------

RULE_CHECKS = [
    ("rule_1_naming", check_rule_1_naming),
    ("rule_2_var_description", check_rule_2_var_description),
    ("rule_3_var_type", check_rule_3_var_type),
    ("rule_4_outputs", check_rule_4_outputs),
    ("rule_5_tags", check_rule_5_tags),
    ("rule_6_lifecycle_stateful", check_rule_6_lifecycle_stateful),
    ("rule_7_locals_for_tags", check_rule_7_locals_for_tags),
    ("rule_8_no_hardcoded_ids", check_rule_8_no_hardcoded_ids),
    ("rule_9_provider_pinned", check_rule_9_provider_pinned),
    ("rule_10_backend_with_locking", check_rule_10_backend_with_locking),
    ("rule_11_iam_least_privilege", check_rule_11_iam_least_privilege),
    ("rule_12_sg_no_open_ingress", check_rule_12_sg_no_open_ingress),
    ("rule_13_sensitive_marked", check_rule_13_sensitive_marked),
    ("rule_14_resource_coverage", check_rule_14_resource_coverage),
    ("rule_15_data_sources_used", check_rule_15_data_sources_used),
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
for _rule_name, _ in RULE_CHECKS:
    CSV_FIELDS.append(f"{_rule_name}_pass")
    CSV_FIELDS.append(f"{_rule_name}_detail")
CSV_FIELDS.extend(["auto_score", "scored_rules"])


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

    task = load_task(row["task"])

    raw_output = result.get("raw_output", "")
    row.update(extract_token_usage(raw_output))

    tf_text, extract_error = extract_terraform(raw_output)

    row["extraction_ok"] = tf_text is not None
    row["extraction_error"] = extract_error or ""

    if tf_text is None:
        row["structure_valid"] = False
        row["structure_errors"] = extract_error or "extraction failed"
        for rule_name, _ in RULE_CHECKS:
            row[f"{rule_name}_pass"] = False
            row[f"{rule_name}_detail"] = "no Terraform HCL extracted"
        row["auto_score"] = 0
        row["scored_rules"] = 0
        return row

    struct_ok, struct_errors = validate_structure(tf_text)
    row["structure_valid"] = struct_ok
    row["structure_errors"] = "; ".join(struct_errors) if struct_errors else ""

    auto_score = 0
    scored_rules = 0
    for rule_name, check_fn in RULE_CHECKS:
        passed, detail = check_fn(tf_text, task)
        row[f"{rule_name}_pass"] = passed
        row[f"{rule_name}_detail"] = detail
        scored_rules += 1
        if passed:
            auto_score += 1

    row["auto_score"] = auto_score
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

    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(OUTPUT_CSV, "w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    extraction_ok = sum(1 for r in rows if r["extraction_ok"])
    structure_valid = sum(1 for r in rows if r["structure_valid"])

    print(f"\nResults written to {OUTPUT_CSV}")
    print(f"  Total runs: {len(rows)}")
    print(f"  Extraction ok: {extraction_ok}/{len(rows)}")
    print(f"  Structure valid: {structure_valid}/{len(rows)}")

    print(f"\nAuto-score by condition (max {len(RULE_CHECKS)} rules):")
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
