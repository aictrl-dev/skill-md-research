# OpenAPI Spec Evaluation Script Review

**File:** `evaluate_openapi.py`  
**Rubric:** `evaluation-rubric.md`  
**Reviewer:** Claude  
**Date:** 2026-02-20

## Summary

The OpenAPI evaluator is well-structured with good JSON/YAML extraction and comprehensive rule coverage. The 14 rules cover API design best practices including naming, documentation, and schema organization. Conditional auth rules (13-14) are a nice touch. A few issues found.

---

## Issues

### 1. YAML Dependency Not Handled Gracefully (lines 19-23, 92-98)

```python
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False
```

**Problem:** If PyYAML is not installed:
- YAML fenced blocks fail silently (returns None)
- No warning to user that YAML support is missing

**Fix:** Log a warning at startup if `HAS_YAML` is False, or add a `--check-deps` CLI flag.

---

### 2. Rule 3 Plural Nouns - Incomplete List (lines 348-350)

```python
if lower in ("user", "product", "order", "merchant", "payment",
             "refund", "webhook", "item", "category", "customer",
             "account", "transaction", "invoice", "event"):
```

**Problem:** Hardcoded list misses many common singular nouns:
- `file`, `files` (but `file` passes)
- `report`, `log`, `message`, `comment`
- `tag`, `role`, `permission`
- Domain-specific: `booking`, `subscription`, `review`

**Fix:** Use NLP library for pluralization detection (e.g., `inflect` library) or expand list significantly.

---

### 3. Rule 5 Verb Blacklist - Too Aggressive (lines 384-409)

```python
verb_blacklist = {
    "get", "create", "delete", "update", "fetch", "remove",
    "add", "list", "search", "find", "retrieve", "modify",
    "put", "post", "patch",
}
```

**Problem:** False positives on legitimate nouns:
- `/lists` (the resource is a "list", e.g., todo lists)
- `/settings` (contains "set")
- `/addresses` (contains "add")
- `/deliveries` (contains "deli"... ok, but `/delivery` has "live")

**Fix:** Check word boundaries, not substring matches. Only flag if verb is exact segment match.

---

### 4. Rule 5 Verb Prefix Check (lines 402-409)

```python
for verb in verb_blacklist:
    if lower.startswith(verb) and len(lower) > len(verb):
        next_char = lower[len(verb)]
        if next_char.isupper() or seg[len(verb)].isupper():
            violations.append(...)
```

**Problem:** The `lower[len(verb)]` is already lowercase (since `lower = seg.lower()`), so `next_char.isupper()` is always False. The `seg[len(verb)].isupper()` check is correct but redundant.

**Fix:** Remove the `next_char.isupper()` check, or fix the logic.

---

### 5. Rule 8 Status Codes - PUT Missing (lines 449-453)

```python
expected_map = {
    "get": "200",
    "post": "201",
    "delete": "204",
}
```

**Problem:** PUT and PATCH are not checked. Common expectation:
- PUT -> 200 (or 204 if no body returned)
- PATCH -> 200

**Fix:** Add PUT and PATCH to the map.

---

### 6. Rule 8 - Async POST Logic (lines 465-467)

```python
if method == "post" and ("201" in codes or "202" in codes):
    continue
```

**Problem:** 202 alone is accepted, but 202 is for async operations. A sync POST should have 201. This allows `POST /users` returning only 202 (accepted but processing).

**Fix:** Require 201 OR both 201 and 202. 202 alone should be flagged unless task specifies async.

---

### 7. Rule 9 "default" Response Handling (lines 503-505)

```python
if code_str == "default":
    has_4xx = True
    has_5xx = True
```

**Problem:** A `default` response could be used for success too (e.g., a catch-all that returns 2xx). This grants "free" 4xx/5xx credit.

**Fix:** Only count `default` if the spec doesn't have explicit 4xx/5xx, or require explicit error codes.

---

### 8. Rule 10 $ref Counting - Request Bodies Not Counted (lines 238-289)

```python
def _count_response_schemas(spec: dict) -> tuple[int, int]:
    """Count total response schemas and how many use $ref."""
```

**Problem:** Only counts response schemas, not request body schemas. A spec could pass with inline request bodies but all $ref responses.

**Fix:** Also count request body schemas (`requestBody.content.*.schema`).

---

### 9. Extraction - Brace Matching Breaks on Nested Braces (lines 117-132)

```python
for i in range(brace_start, len(text_to_search)):
    if text_to_search[i] == "{":
        depth += 1
    elif text_to_search[i] == "}":
        depth -= 1
```

**Problem:** Fails on JSON with braces inside strings:
```json
{ "description": "Use {userId} for lookup" }
```

**Fix:** Track string literals and skip braces inside them.

---

### 10. Rule 11 CamelCase - Too Lenient (line 531)

```python
camel_re = re.compile(r"^[a-z][a-zA-Z0-9]*$")
```

**Problem:** Allows all-uppercase after first char:
- `uSERID` passes (should be `userId`)
- `createdAt` passes (correct)
- `cREATEDAT` passes (incorrect but rare)

**Fix:** For strict camelCase, require lowercase except for word starts: `^[a-z]+([A-Z][a-z]*)*$` or use a proper camelCase detector.

---

### 11. Rule 14 Security Applied - Empty Security Object (lines 590-600)

```python
global_security = spec.get("security")
if isinstance(global_security, list) and len(global_security) > 0:
    return True, "ok (global security)"
```

**Problem:** `security: []` (empty array) is technically valid but means "no security required". Should not pass when auth is required.

**Fix:** Check that security array has at least one non-empty object: `[{bearerAuth: []}]` not `[]`.

---

## Minor Issues

### Rule 1 Description Length

The 20-char threshold is arbitrary. A description like "CRUD API for users" (19 chars) would fail. Consider 15 or document the rationale.

### Swagger 2.0 Handling (lines 145-146)

Flags Swagger 2.0 but still evaluates it. Some rules may not apply correctly to Swagger 2.0 format (e.g., `components.schemas` doesn't exist in 2.0).

### Schema Name Case Sensitivity (line 647)

```python
actual_lower = {k.lower(): k for k in schemas.keys()}
```

Case-insensitive schema matching is good but could mask typos (e.g., `user` vs `User`).

---

## Strengths

1. **Dual format support** - Handles both JSON and YAML extraction well
2. **Conditional auth rules** - Rules 13-14 adapt to task requirements
3. **Good extraction fallbacks** - Multiple strategies for finding spec content
4. **Comprehensive outcome checks** - Path presence, schema presence, async 202
5. **Clear rubric** - Good examples and edge case documentation
6. **$ref counting logic** - Handles items, allOf, oneOf, anyOf correctly

---

## Recommendations

| Priority | Issue | Action |
|----------|-------|--------|
| High | Rule 5 verb prefix check | Fix case sensitivity bug |
| High | Rule 8 PUT/PATCH | Add to expected_map |
| Medium | Rule 3 plural nouns | Expand list or use NLP |
| Medium | Rule 14 empty security | Check for non-empty security object |
| Medium | YAML dependency | Log warning when missing |
| Low | Rule 10 request bodies | Include in $ref count |
| Low | Rule 11 strict camelCase | Consider stricter regex |

---

## Files Reviewed

- `evaluate_openapi.py` (850 lines)
- `evaluation-rubric.md` (229 lines)
