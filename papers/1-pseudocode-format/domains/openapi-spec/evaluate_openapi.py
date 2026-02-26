#!/usr/bin/env python3
"""
Evaluate OpenAPI spec experiment results: extract spec, validate structure,
apply 14 automated rule checks, output CSV.

Usage:
    python evaluate_openapi.py                      # Process all results in results/
    python evaluate_openapi.py results/foo.json     # Process specific file(s)
"""

import csv
import json
import os
import re
import sys
from pathlib import Path

# Optional YAML support (PyYAML)
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

SCRIPT_DIR = Path(__file__).parent

# Import shared token extraction from top-level evaluate.py
sys.path.insert(0, str(SCRIPT_DIR.parent.parent))
from evaluate import extract_token_usage, extract_from_permission_denials, TOKEN_FIELDS
RESULTS_DIR = SCRIPT_DIR / "results"
TEST_DATA_DIR = SCRIPT_DIR / "test-data"
OUTPUT_CSV = RESULTS_DIR / "scores.csv"


# ─── Spec Extraction ────────────────────────────────────────────────────────

def extract_spec(raw_output: str) -> tuple[dict | None, str | None]:
    """Extract OpenAPI spec (JSON or YAML) from raw model output.

    Tries in order:
      1. Parse JSONL event stream (opencode format) to get text content
      2. Parse Claude CLI JSON response to extract 'result' field
      3. Extract from ```json or ```yaml fenced code blocks
      4. Direct JSON parse
      5. Direct YAML parse
      6. Find first { ... } block and parse as JSON
    """
    if not raw_output:
        return None, "empty output"

    # Step 0: Handle opencode JSONL format
    text_to_search = raw_output
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
            text_to_search = "\n".join(text_parts) if text_parts else ""

    # Step 1: Handle Claude CLI JSON response wrapper
    try:
        cli_response = json.loads(raw_output)
        if isinstance(cli_response, dict) and "result" in cli_response:
            text_to_search = cli_response["result"]
    except json.JSONDecodeError:
        pass

    # Step 1b: Extract write tool content as fallback candidate
    # (opencode writes files via "write" tool, Haiku hits permission denials on Write)
    write_tool_content = extract_from_permission_denials(raw_output)

    # Try extraction from text_to_search first, then fall back to write tool content
    for candidate in [text_to_search, write_tool_content]:
        if not candidate:
            continue

        # Step 2: Extract from markdown code fences
        fence_patterns = [
            r"```json\s*\n(.*?)\n\s*```",
            r"```yaml\s*\n(.*?)\n\s*```",
            r"```yml\s*\n(.*?)\n\s*```",
            r"```\s*\n(.*?)\n\s*```",
        ]
        for pattern in fence_patterns:
            match = re.search(pattern, candidate, re.DOTALL)
            if match:
                content = match.group(1)
                # Try JSON first
                try:
                    obj = json.loads(content)
                    if isinstance(obj, dict):
                        return obj, None
                except json.JSONDecodeError:
                    pass
                # Try YAML
                if HAS_YAML:
                    try:
                        obj = yaml.safe_load(content)
                        if isinstance(obj, dict):
                            return obj, None
                    except yaml.YAMLError:
                        pass

        # Step 3: Direct JSON parse
        try:
            obj = json.loads(candidate)
            if isinstance(obj, dict):
                return obj, None
        except json.JSONDecodeError:
            pass

        # Step 4: Direct YAML parse
        if HAS_YAML:
            try:
                obj = yaml.safe_load(candidate)
                if isinstance(obj, dict) and ("openapi" in obj or "paths" in obj):
                    return obj, None
            except yaml.YAMLError:
                pass

        # Step 5: Find first { ... } block (brace matching)
        brace_start = candidate.find("{")
        if brace_start >= 0:
            depth = 0
            for i in range(brace_start, len(candidate)):
                if candidate[i] == "{":
                    depth += 1
                elif candidate[i] == "}":
                    depth -= 1
                    if depth == 0:
                        try:
                            obj = json.loads(candidate[brace_start : i + 1])
                            if isinstance(obj, dict):
                                return obj, None
                        except json.JSONDecodeError:
                            break

    return None, "could not extract valid JSON or YAML spec"


# ─── Structure Validation ───────────────────────────────────────────────────

def validate_structure(spec: dict) -> tuple[bool, list[str]]:
    """Check that the spec is a valid OpenAPI document (has openapi, info, paths)."""
    errors = []

    if "openapi" not in spec:
        # Also accept swagger: "2.0" but flag it
        if "swagger" in spec:
            errors.append("uses Swagger 2.0 instead of OpenAPI 3.0")
        else:
            errors.append("missing 'openapi' version field")

    if "info" not in spec:
        errors.append("missing 'info' block")
    elif not isinstance(spec["info"], dict):
        errors.append("'info' is not an object")

    if "paths" not in spec:
        errors.append("missing 'paths' block")
    elif not isinstance(spec["paths"], dict):
        errors.append("'paths' is not an object")

    return len(errors) == 0, errors


# ─── Task Loading ───────────────────────────────────────────────────────────

def load_task(task_id: str) -> dict | None:
    """Load task JSON from test-data directory."""
    for task_file in TEST_DATA_DIR.glob("task-*.json"):
        with open(task_file) as f:
            task = json.load(f)
        if str(task.get("task_id")) == str(task_id):
            return task
    return None


# ─── Helpers ────────────────────────────────────────────────────────────────

def _get_all_paths(spec: dict) -> list[str]:
    """Return all path strings from the spec."""
    paths = spec.get("paths", {})
    if isinstance(paths, dict):
        return list(paths.keys())
    return []


def _get_all_operations(spec: dict) -> list[dict]:
    """Extract all operations with method, path, operationId, etc."""
    ops = []
    paths = spec.get("paths", {})
    if not isinstance(paths, dict):
        return ops
    http_methods = {"get", "post", "put", "patch", "delete", "options", "head", "trace"}
    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
        for method in http_methods:
            if method in path_item:
                op = path_item[method]
                if not isinstance(op, dict):
                    continue
                status_codes = []
                responses = op.get("responses", {})
                if isinstance(responses, dict):
                    status_codes = [str(k) for k in responses.keys()]
                ops.append({
                    "method": method,
                    "path": path,
                    "operationId": op.get("operationId"),
                    "summary": op.get("summary", ""),
                    "description": op.get("description", ""),
                    "status_codes": status_codes,
                    "security": op.get("security"),
                })
    return ops


def _get_all_schemas(spec: dict) -> dict:
    """Return schemas from components.schemas."""
    components = spec.get("components", {})
    if isinstance(components, dict):
        schemas = components.get("schemas", {})
        if isinstance(schemas, dict):
            return schemas
    return {}


def _get_all_property_names(spec: dict) -> list[str]:
    """Extract all property names from all schemas, including allOf/oneOf/anyOf."""
    names = []
    schemas = _get_all_schemas(spec)

    def _collect_props(schema: dict):
        if not isinstance(schema, dict):
            return
        if "properties" in schema:
            props = schema["properties"]
            if isinstance(props, dict):
                names.extend(props.keys())
        # Recurse into composition keywords
        for combo_key in ("allOf", "oneOf", "anyOf"):
            combo = schema.get(combo_key, [])
            if isinstance(combo, list):
                for item in combo:
                    if isinstance(item, dict):
                        resolved = _resolve_schema_ref(spec, item)
                        if resolved and resolved is not item:
                            _collect_props(resolved)
                        else:
                            _collect_props(item)

    for schema_name, schema in schemas.items():
        _collect_props(schema)
    return names


def _count_response_schemas(spec: dict) -> tuple[int, int]:
    """Count total response schemas and how many use $ref. Returns (total, ref_count)."""
    total = 0
    ref_count = 0
    paths = spec.get("paths", {})
    if not isinstance(paths, dict):
        return 0, 0

    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
        for method in ("get", "post", "put", "patch", "delete"):
            op = path_item.get(method)
            if not isinstance(op, dict):
                continue
            responses = op.get("responses", {})
            if not isinstance(responses, dict):
                continue
            for status_code, response in responses.items():
                if not isinstance(response, dict):
                    continue
                # Check if the response itself is a $ref
                if "$ref" in response:
                    total += 1
                    ref_count += 1
                    continue
                content = response.get("content", {})
                if not isinstance(content, dict):
                    continue
                for media_type, media_obj in content.items():
                    if not isinstance(media_obj, dict):
                        continue
                    schema = media_obj.get("schema")
                    if schema is not None:
                        total += 1
                        if isinstance(schema, dict) and "$ref" in schema:
                            ref_count += 1
                        # Also count $ref inside items (for array responses)
                        elif isinstance(schema, dict):
                            items = schema.get("items", {})
                            if isinstance(items, dict) and "$ref" in items:
                                ref_count += 1
                            # allOf/oneOf/anyOf with $ref
                            for combo_key in ("allOf", "oneOf", "anyOf"):
                                combo = schema.get(combo_key, [])
                                if isinstance(combo, list):
                                    for item in combo:
                                        if isinstance(item, dict) and "$ref" in item:
                                            ref_count += 1
                                            break

    return total, ref_count


# ─── Rule Check Functions ───────────────────────────────────────────────────

def check_rule_1_plural_nouns(spec: dict, task: dict | None) -> tuple[bool, str]:
    """Rule 1: Plural nouns for collections (heuristic check)."""
    paths = _get_all_paths(spec)
    if not paths:
        return False, "no paths defined"

    # Known singular -> plural mappings for common API nouns
    singular_flags = []
    for path in paths:
        segments = [s for s in path.split("/") if s and not s.startswith("{")]
        # Skip version prefixes like v1, v2
        segments = [s for s in segments if not re.match(r"^v\d+$", s)]
        for seg in segments:
            # Check for common singular forms that should be plural
            # Only flag if the segment looks like a bare singular noun
            lower = seg.lower()
            if lower in ("user", "product", "order", "merchant", "payment",
                         "refund", "webhook", "item", "category", "customer",
                         "account", "transaction", "invoice", "event",
                         "report", "log", "message", "comment", "tag",
                         "role", "permission", "booking", "subscription",
                         "review", "file", "session", "notification",
                         "setting", "address", "delivery"):
                singular_flags.append(f"'{seg}' in {path} should be plural")

    if singular_flags:
        return False, "; ".join(singular_flags[:3])
    return True, "ok"


def check_rule_2_kebab_case(spec: dict, task: dict | None) -> tuple[bool, str]:
    """Rule 2: Kebab-case path segments (no camelCase, no underscores)."""
    paths = _get_all_paths(spec)
    if not paths:
        return False, "no paths defined"

    violations = []
    for path in paths:
        segments = [s for s in path.split("/") if s and not s.startswith("{")]
        for seg in segments:
            # Skip version prefixes like v1
            if re.match(r"^v\d+$", seg):
                continue
            # Kebab-case: lowercase letters, digits, hyphens only
            if seg != seg.lower():
                violations.append(f"'{seg}' has uppercase in {path}")
            if "_" in seg:
                violations.append(f"'{seg}' has underscore in {path}")

    if violations:
        return False, "; ".join(violations[:3])
    return True, "ok"


def check_rule_3_no_verbs(spec: dict, task: dict | None) -> tuple[bool, str]:
    """Rule 3 (SEMI-auto): No verbs in path segments. Uses blacklist."""
    verb_blacklist = {
        "get", "create", "delete", "update", "fetch", "remove",
        "add", "list", "search", "find", "retrieve", "modify",
        "put", "post", "patch",
    }
    paths = _get_all_paths(spec)
    if not paths:
        return False, "no paths defined"

    violations = []
    for path in paths:
        segments = [s for s in path.split("/") if s and not s.startswith("{")]
        for seg in segments:
            # Check if any blacklisted verb appears as an exact segment
            lower = seg.lower()
            if lower in verb_blacklist:
                violations.append(f"verb '{seg}' in {path}")
            else:
                # Check for camelCase verbs as prefix: getUsers, createOrder
                # The original segment (not lowered) must have uppercase after the verb
                for verb in verb_blacklist:
                    if lower.startswith(verb) and len(seg) > len(verb):
                        if seg[len(verb)].isupper():
                            violations.append(f"verb prefix '{verb}' in '{seg}' in {path}")
                            break

    if violations:
        return False, "; ".join(violations[:3])
    return True, "ok"


def check_rule_4_operation_id(spec: dict, task: dict | None) -> tuple[bool, str]:
    """Rule 4: operationId on all operations."""
    ops = _get_all_operations(spec)
    if not ops:
        return False, "no operations found"

    missing = [f"{o['method'].upper()} {o['path']}" for o in ops if not o.get("operationId")]
    if missing:
        return False, f"missing operationId on: {', '.join(missing[:3])}"
    return True, f"ok ({len(ops)} operations)"


def check_rule_5_description(spec: dict, task: dict | None) -> tuple[bool, str]:
    """Rule 5: description or summary on all operations."""
    ops = _get_all_operations(spec)
    if not ops:
        return False, "no operations found"

    missing = []
    for o in ops:
        has_desc = bool(o.get("description", "").strip())
        has_summary = bool(o.get("summary", "").strip())
        if not has_desc and not has_summary:
            label = o.get("operationId") or f"{o['method'].upper()} {o['path']}"
            missing.append(label)

    if missing:
        return False, f"missing description/summary on: {', '.join(missing[:3])}"
    return True, f"ok ({len(ops)} operations)"


def check_rule_6_camel_case(spec: dict, task: dict | None) -> tuple[bool, str]:
    """Rule 6: camelCase property names in schemas."""
    camel_re = re.compile(r"^[a-z][a-zA-Z0-9]*$")
    prop_names = _get_all_property_names(spec)
    if not prop_names:
        return True, "needs_review (no schemas with properties)"

    violations = [name for name in prop_names if not camel_re.match(name)]
    # Deduplicate
    violations = sorted(set(violations))
    if violations:
        return False, f"non-camelCase: {', '.join(violations[:5])}"
    return True, f"ok ({len(prop_names)} properties checked)"


def check_rule_7_contact(spec: dict, task: dict | None) -> tuple[bool, str]:
    """Rule 7: info.contact present with email or url."""
    info = spec.get("info", {})
    if not isinstance(info, dict):
        return False, "info is not an object"

    contact = info.get("contact", {})
    if not isinstance(contact, dict):
        return False, "info.contact missing"
    has_email = bool(contact.get("email"))
    has_url = bool(contact.get("url"))
    if not has_email and not has_url:
        return False, "info.contact has no email or url"

    return True, "ok"


def _resolve_schema_ref(spec: dict, schema: dict | None) -> dict | None:
    """Resolve a $ref in a schema to the actual schema object."""
    if not isinstance(schema, dict):
        return schema
    ref = schema.get("$ref")
    if not ref or not isinstance(ref, str):
        return schema
    # Parse #/components/schemas/SomeName
    prefix = "#/components/schemas/"
    if ref.startswith(prefix):
        schema_name = ref[len(prefix):]
        schemas = _get_all_schemas(spec)
        return schemas.get(schema_name)
    return None


def _resolve_param_ref(spec: dict, param: dict) -> dict:
    """Resolve a $ref in a parameter to the actual parameter object."""
    if not isinstance(param, dict):
        return param
    ref = param.get("$ref")
    if not ref or not isinstance(ref, str):
        return param
    prefix = "#/components/parameters/"
    if ref.startswith(prefix):
        param_name = ref[len(prefix):]
        components = spec.get("components", {})
        if isinstance(components, dict):
            params = components.get("parameters", {})
            if isinstance(params, dict):
                resolved = params.get(param_name)
                if isinstance(resolved, dict):
                    return resolved
    return param


def check_rule_8_rfc7807(spec: dict, task: dict | None) -> tuple[bool, str]:
    """Rule 8: RFC 7807 error schema - error responses (4xx, 5xx, default) must
    reference a schema with properties: type, title, status, detail."""
    required_fields = {"type", "title", "status", "detail"}
    paths = spec.get("paths", {})
    if not isinstance(paths, dict):
        return False, "no paths"

    error_schemas_found = 0
    compliant_schemas = 0

    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
        for method in ("get", "post", "put", "patch", "delete"):
            op = path_item.get(method)
            if not isinstance(op, dict):
                continue
            responses = op.get("responses", {})
            if not isinstance(responses, dict):
                continue
            for code, response in responses.items():
                code_str = str(code)
                # Check if this is an error response (4xx, 5xx, or default)
                is_error = False
                if code_str == "default":
                    is_error = True
                elif len(code_str) == 3 and code_str[0] in ("4", "5"):
                    is_error = True
                if not is_error:
                    continue

                if not isinstance(response, dict):
                    continue

                # Get the schema from the response
                # Handle response-level $ref (e.g. #/components/responses/Error)
                if "$ref" in response:
                    ref = response["$ref"]
                    prefix = "#/components/responses/"
                    if isinstance(ref, str) and ref.startswith(prefix):
                        resp_name = ref[len(prefix):]
                        comp_responses = spec.get("components", {}).get("responses", {})
                        if isinstance(comp_responses, dict) and resp_name in comp_responses:
                            response = comp_responses[resp_name]
                        else:
                            error_schemas_found += 1
                            continue
                    else:
                        error_schemas_found += 1
                        continue

                content = response.get("content", {})
                if not isinstance(content, dict):
                    continue
                for media_type, media_obj in content.items():
                    if not isinstance(media_obj, dict):
                        continue
                    schema = media_obj.get("schema")
                    if schema is None:
                        continue

                    error_schemas_found += 1
                    # Resolve $ref if present
                    resolved = _resolve_schema_ref(spec, schema)
                    if resolved is None:
                        continue

                    # Check for required fields in properties
                    props = resolved.get("properties", {})
                    if isinstance(props, dict):
                        prop_names = set(props.keys())
                        if required_fields.issubset(prop_names):
                            compliant_schemas += 1

    if error_schemas_found == 0:
        return False, "no error response schemas found"
    if compliant_schemas == 0:
        return False, f"0/{error_schemas_found} error schemas have type+title+status+detail"
    return True, f"{compliant_schemas}/{error_schemas_found} error schemas are RFC 7807 compliant"


def check_rule_9_cursor_pagination(spec: dict, task: dict | None) -> tuple[bool, str]:
    """Rule 9: Cursor pagination - list endpoints (GET returning arrays) must use
    {data: [], nextCursor, hasMore} envelope."""
    if not task or not task.get("requires_pagination"):
        return True, "n/a (pagination not required)"

    paths = spec.get("paths", {})
    if not isinstance(paths, dict):
        return False, "no paths"

    list_endpoints_found = 0
    compliant_endpoints = 0

    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
        # List endpoints: GET on a collection resource (path does NOT end with /{id})
        op = path_item.get("get")
        if not isinstance(op, dict):
            continue
        # Skip paths ending with a path parameter (single resource)
        path_segments = [s for s in path.rstrip("/").split("/") if s]
        if path_segments and path_segments[-1].startswith("{"):
            continue

        # Check the 200 response schema
        responses = op.get("responses", {})
        if not isinstance(responses, dict):
            continue
        success_resp = responses.get("200") or responses.get("201")
        if not isinstance(success_resp, dict):
            continue

        content = success_resp.get("content", {})
        if not isinstance(content, dict):
            continue
        for media_type, media_obj in content.items():
            if not isinstance(media_obj, dict):
                continue
            schema = media_obj.get("schema")
            if schema is None:
                continue
            # Resolve $ref
            resolved = _resolve_schema_ref(spec, schema)
            if resolved is None:
                continue
            # Check if this looks like a list endpoint (has an array somewhere)
            props = resolved.get("properties", {})
            if not isinstance(props, dict):
                # Maybe the schema itself is an array
                if resolved.get("type") == "array":
                    list_endpoints_found += 1
                continue

            # Check for data array, nextCursor string, hasMore boolean
            list_endpoints_found += 1
            has_data = False
            has_next_cursor = False
            has_has_more = False

            for prop_name, prop_schema in props.items():
                if not isinstance(prop_schema, dict):
                    continue
                name_lower = prop_name.lower()
                if name_lower == "data" and prop_schema.get("type") == "array":
                    has_data = True
                # Accept camelCase variations
                if name_lower in ("nextcursor", "next_cursor", "cursor"):
                    if prop_schema.get("type") == "string" or prop_schema.get("type") is None:
                        has_next_cursor = True
                if name_lower in ("hasmore", "has_more"):
                    if prop_schema.get("type") == "boolean" or prop_schema.get("type") is None:
                        has_has_more = True

            if has_data and has_next_cursor and has_has_more:
                compliant_endpoints += 1

    if list_endpoints_found == 0:
        return True, "no list endpoints found"
    if compliant_endpoints == 0:
        return False, f"0/{list_endpoints_found} list endpoints have cursor pagination (data+nextCursor+hasMore)"
    return True, f"{compliant_endpoints}/{list_endpoints_found} list endpoints have cursor pagination"


def check_rule_10_rate_limit_headers(spec: dict, task: dict | None) -> tuple[bool, str]:
    """Rule 10: Rate-limit headers on success responses (2xx).
    Must document X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset."""
    required_headers = {"x-ratelimit-limit", "x-ratelimit-remaining", "x-ratelimit-reset"}
    paths = spec.get("paths", {})
    if not isinstance(paths, dict):
        return False, "no paths"

    success_responses_found = 0
    compliant_responses = 0

    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
        for method in ("get", "post", "put", "patch", "delete"):
            op = path_item.get(method)
            if not isinstance(op, dict):
                continue
            responses = op.get("responses", {})
            if not isinstance(responses, dict):
                continue
            for code, response in responses.items():
                code_str = str(code)
                # Check if this is a success response (2xx)
                if not (len(code_str) == 3 and code_str.startswith("2")):
                    continue
                if not isinstance(response, dict):
                    continue

                success_responses_found += 1
                headers = response.get("headers", {})
                if not isinstance(headers, dict):
                    continue
                # Case-insensitive header name matching
                header_names_lower = {h.lower() for h in headers.keys()}
                if required_headers.issubset(header_names_lower):
                    compliant_responses += 1

    if success_responses_found == 0:
        return False, "no success (2xx) responses found"
    if compliant_responses < success_responses_found:
        return False, f"{compliant_responses}/{success_responses_found} success responses have rate-limit headers"
    return True, f"{compliant_responses}/{success_responses_found} success responses have rate-limit headers"


def check_rule_11_idempotency_key(spec: dict, task: dict | None) -> tuple[bool, str]:
    """Rule 11: POST and PUT operations must accept an Idempotency-Key request header."""
    paths = spec.get("paths", {})
    if not isinstance(paths, dict):
        return False, "no paths"

    post_put_ops = 0
    compliant_ops = 0

    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
        # Get path-level parameters
        path_params = path_item.get("parameters", [])
        if not isinstance(path_params, list):
            path_params = []

        for method in ("post", "put"):
            op = path_item.get(method)
            if not isinstance(op, dict):
                continue
            post_put_ops += 1

            # Combine path-level and operation-level parameters
            op_params = op.get("parameters", [])
            if not isinstance(op_params, list):
                op_params = []
            all_params = path_params + op_params

            has_idempotency = False
            for param in all_params:
                if not isinstance(param, dict):
                    continue
                # Resolve $ref if present (e.g. $ref: "#/components/parameters/IdempotencyKey")
                resolved = _resolve_param_ref(spec, param)
                if (resolved.get("in") == "header" and
                        isinstance(resolved.get("name"), str) and
                        resolved["name"].lower() == "idempotency-key"):
                    has_idempotency = True
                    break

            if has_idempotency:
                compliant_ops += 1

    if post_put_ops == 0:
        return True, "n/a (no POST/PUT operations)"
    if compliant_ops == 0:
        return False, f"0/{post_put_ops} POST/PUT operations have Idempotency-Key header"
    return True, f"{compliant_ops}/{post_put_ops} POST/PUT operations have Idempotency-Key header"


def check_rule_12_examples(spec: dict, task: dict | None) -> tuple[bool, str]:
    """Rule 12: Example values on schema properties (>= 80% must have 'example')."""
    schemas = _get_all_schemas(spec)
    total_props = 0
    with_example = 0

    def _count_examples(schema: dict):
        nonlocal total_props, with_example
        if not isinstance(schema, dict):
            return
        props = schema.get("properties", {})
        if isinstance(props, dict):
            for prop_name, prop_schema in props.items():
                total_props += 1
                if isinstance(prop_schema, dict) and "example" in prop_schema:
                    with_example += 1
        # Recurse into composition keywords
        for combo_key in ("allOf", "oneOf", "anyOf"):
            combo = schema.get(combo_key, [])
            if isinstance(combo, list):
                for item in combo:
                    if isinstance(item, dict):
                        resolved = _resolve_schema_ref(spec, item)
                        if resolved and resolved is not item:
                            _count_examples(resolved)
                        else:
                            _count_examples(item)

    for schema_name, schema in schemas.items():
        _count_examples(schema)

    if total_props == 0:
        return True, "no properties found"
    ratio = with_example / total_props
    if ratio < 0.80:
        return False, f"{with_example}/{total_props} ({ratio:.0%}) have examples (need >= 80%)"
    return True, f"{with_example}/{total_props} ({ratio:.0%}) have examples"


def check_rule_13_security_scheme(spec: dict, task: dict | None) -> tuple[bool, str]:
    """Rule 13: Security scheme defined (only when task requires auth)."""
    requires_auth = False
    if task:
        requires_auth = task.get("requires_auth", False)
        if not requires_auth:
            reqs = task.get("requirements", {})
            requires_auth = reqs.get("auth", False)
    if not requires_auth:
        return True, "n/a (auth not required)"

    components = spec.get("components", {})
    if not isinstance(components, dict):
        return False, "no components block (auth required)"
    schemes = components.get("securitySchemes", {})
    if not isinstance(schemes, dict) or len(schemes) == 0:
        return False, "no securitySchemes defined (auth required)"
    return True, f"ok ({', '.join(schemes.keys())})"


def check_rule_14_security_applied(spec: dict, task: dict | None) -> tuple[bool, str]:
    """Rule 14: Security applied to operations (only when task requires auth)."""
    requires_auth = False
    if task:
        requires_auth = task.get("requires_auth", False)
        if not requires_auth:
            reqs = task.get("requirements", {})
            requires_auth = reqs.get("auth", False)
    if not requires_auth:
        return True, "n/a (auth not required)"

    # Check global security — must have at least one non-empty security requirement
    # security: [] means "no auth required" per OpenAPI spec, so reject it
    global_security = spec.get("security")
    if isinstance(global_security, list) and len(global_security) > 0:
        has_non_empty = any(
            isinstance(req, dict) and len(req) > 0 for req in global_security
        )
        if has_non_empty:
            return True, "ok (global security)"

    # Check per-operation security
    ops = _get_all_operations(spec)
    ops_with_security = [o for o in ops if o.get("security") is not None]
    if ops_with_security:
        return True, f"ok ({len(ops_with_security)}/{len(ops)} ops have security)"

    return False, "security not applied globally or per-operation"


# ─── Main Evaluation ────────────────────────────────────────────────────────

AUTOMATED_CHECKS = {
    "rule_1_plural_nouns": check_rule_1_plural_nouns,
    "rule_2_kebab_case": check_rule_2_kebab_case,
    "rule_3_no_verbs": check_rule_3_no_verbs,
    "rule_4_operation_id": check_rule_4_operation_id,
    "rule_5_description": check_rule_5_description,
    "rule_6_camel_case": check_rule_6_camel_case,
    "rule_7_contact": check_rule_7_contact,
    "rule_8_rfc7807": check_rule_8_rfc7807,
    "rule_9_cursor_pagination": check_rule_9_cursor_pagination,
    "rule_10_rate_limit_headers": check_rule_10_rate_limit_headers,
    "rule_11_idempotency_key": check_rule_11_idempotency_key,
    "rule_12_examples": check_rule_12_examples,
    "rule_13_security_scheme": check_rule_13_security_scheme,
    "rule_14_security_applied": check_rule_14_security_applied,
}

# Rules excluded from auto_score (none for OpenAPI — all 14 are deterministic/heuristic)
EXCLUDED_RULES = set()


# --- Outcome Checks (semantic correctness, not style) ----------------------------

def outcome_paths_present(spec: dict, task: dict) -> tuple[bool, str]:
    """OUTCOME: All required API paths are defined."""
    expected = task.get("expected_paths", [])
    if not expected:
        return True, "no expected paths in task"
    actual = set(spec.get("paths", {}).keys())
    missing = [p for p in expected if p not in actual]
    if not missing:
        return True, f"all {len(expected)} expected paths present"
    return False, f"missing {len(missing)}/{len(expected)} paths: {missing[:5]}"


def outcome_schemas_present(spec: dict, task: dict) -> tuple[bool, str]:
    """OUTCOME: All required schema definitions exist."""
    expected = task.get("expected_schemas", [])
    if not expected:
        return True, "no expected schemas in task"
    schemas = spec.get("components", {}).get("schemas", {})
    actual_lower = {k.lower(): k for k in schemas.keys()}
    missing = [s for s in expected if s.lower() not in actual_lower]
    if not missing:
        return True, f"all {len(expected)} expected schemas present"
    return False, f"missing {len(missing)}/{len(expected)} schemas: {missing}"


def outcome_async_202(spec: dict, task: dict) -> tuple[bool, str]:
    """OUTCOME: Async operations return 202 Accepted when task requires it."""
    if not task.get("has_async_operations"):
        return True, "n/a (no async operations required)"
    paths = spec.get("paths", {})
    found_202 = False
    for path, methods in paths.items():
        for method, op in methods.items():
            if method.lower() == "post" and isinstance(op, dict):
                responses = op.get("responses", {})
                if "202" in responses:
                    found_202 = True
                    break
        if found_202:
            break
    if found_202:
        return True, "202 Accepted response found on POST operation"
    return False, "no 202 Accepted response found (async operations required)"


OUTCOME_CHECKS = {
    "outcome_paths_present": outcome_paths_present,
    "outcome_schemas_present": outcome_schemas_present,
    "outcome_async_202": outcome_async_202,
}

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
for rule_name in AUTOMATED_CHECKS:
    CSV_FIELDS.append(f"{rule_name}_pass")
    CSV_FIELDS.append(f"{rule_name}_detail")
CSV_FIELDS.extend(["auto_score", "scored_rules", "needs_manual_review"])
for outcome_name in OUTCOME_CHECKS:
    CSV_FIELDS.append(f"{outcome_name}_pass")
    CSV_FIELDS.append(f"{outcome_name}_detail")
CSV_FIELDS.append("outcome_score")


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

    # Load the task for context-dependent checks (auth rules)
    task_id = result.get("task", "")
    task = load_task(task_id)

    # Extract token usage and spec from raw output
    raw = result.get("raw_output", "")
    row.update(extract_token_usage(raw))

    spec, extract_error = extract_spec(raw)

    row["extraction_ok"] = spec is not None
    row["extraction_error"] = extract_error or ""

    if spec is None:
        row["structure_valid"] = False
        row["structure_errors"] = extract_error
        for name in AUTOMATED_CHECKS:
            row[f"{name}_pass"] = False
            row[f"{name}_detail"] = "no valid spec extracted"
        row["auto_score"] = 0
        row["scored_rules"] = 0
        row["needs_manual_review"] = False
        for outcome_name in OUTCOME_CHECKS:
            row[f"{outcome_name}_pass"] = False
            row[f"{outcome_name}_detail"] = "no valid spec extracted"
        row["outcome_score"] = 0
        return row

    # Structure validation
    structure_ok, structure_errors = validate_structure(spec)
    row["structure_valid"] = structure_ok
    row["structure_errors"] = "; ".join(structure_errors) if structure_errors else ""

    # Automated rule checks
    auto_score = 0
    scored_rules = 0
    needs_review = False
    for name, check_fn in AUTOMATED_CHECKS.items():
        passed, detail = check_fn(spec, task)
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
    for outcome_name, check_fn in OUTCOME_CHECKS.items():
        passed, detail = check_fn(spec, task)
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
    extract_ok = sum(1 for r in rows if r["extraction_ok"])
    struct_valid = sum(1 for r in rows if r["structure_valid"])
    needs_review = sum(1 for r in rows if r["needs_manual_review"])

    print(f"\nResults written to {OUTPUT_CSV}")
    print(f"  Total runs: {len(rows)}")
    print(f"  Extraction OK: {extract_ok}/{len(rows)}")
    print(f"  Structure valid: {struct_valid}/{len(rows)}")
    print(f"  Needs manual review: {needs_review}/{len(rows)}")

    # Auto-score summary by condition (max 14 automatable rules)
    print(f"\nAuto-score by condition (max {len(AUTOMATED_CHECKS) - len(EXCLUDED_RULES)} scored rules, {len(EXCLUDED_RULES)} excluded):")
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

    # Per-rule pass rate
    print("\nPer-rule pass rate:")
    for name in AUTOMATED_CHECKS:
        passed = sum(1 for r in rows if r.get(f"{name}_pass"))
        total = len(rows)
        pct = (passed / total * 100) if total > 0 else 0
        print(f"  {name}: {passed}/{total} ({pct:.0f}%)")


if __name__ == "__main__":
    main()
