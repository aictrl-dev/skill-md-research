# Commit Message Evaluation Script Review

**File:** `evaluate_commits.py`  
**Rubric:** `evaluation-rubric.md`  
**Reviewer:** Claude  
**Date:** 2026-02-20

## Summary

The commit message evaluator is well-designed for Conventional Commits spec. Clean parsing logic, comprehensive rule coverage (14 rules), and good handling of edge cases like breaking changes. A few regex and logic issues found.

---

## Issues

### 1. Rule 6 Imperative - Incomplete Blacklist (lines 30-40)

```python
IMPERATIVE_BLACKLIST = {
    "added", "fixed", "removed", "updated", "changed", "refactored",
    ...
}
```

**Problem:** Missing common non-imperative words:
- `implemented`, `created`, `deleted` (past)
- `implementing`, `creating`, `deleting` (gerund)
- `implements`, `creates`, `deletes` (third person)
- `was`, `were`, `been` (past of be)

**Fix:** Expand blacklist or use NLP library for verb tense detection.

---

### 2. Subject Regex - Scope Empty Parens (line 46-52)

```python
SUBJECT_RE = re.compile(
    r'^(?P<type>[a-z]+)'
    r'(?:\((?P<scope>[^)]*)\))?'
    ...
)
```

**Problem:** `[^)]*` allows empty scope `feat(): add X`. Rule 3 catches this but the regex should reject it earlier.

**Fix:** Change to `(?P<scope>[^)]+)` to require at least one char, or leave to Rule 3 validation.

---

### 3. Rule 2 Separator - Multi-Space Check (line 374)

```python
if sep == ": ":
    return True, "ok"
```

**Problem:** Only checks exact match `: `. Doesn't detect:
- `:   ` (multiple spaces)
- `:\t` (tab instead of space)
- `:\r` (carriage return)

**Fix:** Use regex `r':[ \t\r]+'` and validate single space, or normalize before check.

---

### 4. Rule 8 Lowercase - Unicode Issue (line 440)

```python
if desc[0].isupper():
    return False, f"starts with uppercase '{desc[0]}'"
```

**Problem:** `isupper()` works on Unicode, so `fix: Änderung` would fail even if lowercase intended. Also, `desc[0].isupper()` on non-letters returns `False` which is correct but implicit.

**Fix:** Explicitly check `desc[0].isalpha() and desc[0].isupper()` to be clear about intent.

---

### 5. Footer Parsing - Multiline Values (lines 317-322)

```python
for fline in footer_lines:
    colon_pos = fline.find(':')
    if colon_pos > 0:
        token = fline[:colon_pos].strip()
        value = fline[colon_pos + 1:].strip()
```

**Problem:** BREAKING CHANGE footers can be multi-line:
```
BREAKING CHANGE: JWT tokens signed with jsonwebtoken are
incompatible with jose. All active sessions will be
invalidated.
```

Only first line captured.

**Fix:** Continuation lines (starting with space) should be appended to previous footer value.

---

### 6. Rule 13 Issue Ref - Incomplete Pattern (lines 501-509)

```python
all_footer_text = " ".join(...)
...
if ref not in all_footer_text and ref not in raw:
    missing.append(ref)
```

**Problem:** Substring match can false-positive:
- Expected `#24` matches `#247` in message
- Expected `ABC-123` matches `ABC-1234`

**Fix:** Use word boundaries: `re.search(r'\b' + re.escape(ref) + r'\b', raw)`

---

### 7. Rule 12 Breaking Change - Token Matching (lines 487, 496)

```python
bc_footers = [f for f in parsed.get("footers", []) if f["token"] == "BREAKING CHANGE"]
```

**Problem:** Strict exact match rejects valid alternatives:
- `BREAKING-CHANGE:` (with hyphen - valid per Conventional Commits spec)
- `Breaking change:` (different case)

**Fix:** Normalize token: `f["token"].upper().replace("-", " ")`

---

### 8. Extraction - Direct Match Returns Early (lines 124-132)

```python
for line in text_to_search.split('\n'):
    line = line.strip()
    if _looks_like_commit(line):
        ...
        return candidate, None  # Returns first match
```

**Problem:** If LLM outputs multiple commit messages, only first is returned. Should maybe take the longest/most complete one.

**Fix:** Collect all candidates and return the one with body (if any).

---

### 9. Rule 9 Blank Line - Edge Case (lines 445-453)

```python
if len(lines) >= 2 and lines[1].strip() == "":
    return True, "blank line present"
```

**Problem:** If commit is:
```
feat: add X
   # <- spaces not empty by strip()
Body here
```

This fails even though it's semantically blank.

**Fix:** Check `lines[1].strip() == ""` is correct, but the issue is if there's only whitespace on line 2. Actually, this is handled correctly. No fix needed - just documenting.

---

### 10. _is_footer_line - Incomplete Token List (lines 202-214)

```python
footer_tokens = [
    "BREAKING CHANGE:", "Refs:", "Fixes:", "Closes:", "Signed-off-by:",
    "Co-authored-by:", "Reviewed-by:", "Acked-by:",
]
```

**Problem:** Missing common footer tokens:
- `Implements:`
- `See-also:`
- `Tested-by:`
- `Cherry-picked-from:`

**Fix:** Expand list or use pattern `^[A-Z][a-z-]+:` for generic footer detection.

---

### 11. Rule 3 Scope - Regex Too Strict (line 386)

```python
if re.match(r'^[a-z][a-z0-9]*(-[a-z0-9]+)*$', scope):
```

**Problem:** Rejects valid scopes:
- `v2` (starts with letter, then digit - should pass)
- `api-gateway-v2` (digit at end - should pass)

Actually, the regex allows these. But it rejects:
- `2024-q1` (starts with digit)
- `my-scope` with trailing hyphen

**Fix:** Allow leading digits: `^[a-z0-9][a-z0-9-]*[a-z0-9]$` or allow and document.

---

## Minor Issues

### Extraction Fallback Pattern (line 100-102)

```python
fence_patterns = [
    r"```(?:text|commit|git)?\s*\n(.*?)\n\s*```",
]
```

Only one pattern in list - why have a loop? Either add more patterns or remove the loop.

### Rule 10 URL Exemption (lines 466-469)

```python
if re.match(r'^https?://', stripped):
    continue
if 'http://' in line or 'https://' in line:
    continue
```

Two checks for same thing - the second catches URLs mid-line but so does the first if we remove `^`. Consolidate.

### Empty Scope Handling (line 384-388)

Rule 3 passes empty parens check but could be caught by regex. Currently handled but inconsistent.

---

## Strengths

1. **Conventional Commits spec compliance** - Good coverage of the full spec
2. **Breaking change handling** - Both `!` and footer detection
3. **Task-aware rules** - Rules 4, 12, 13, 14 adapt to task requirements
4. **Body/footer parsing** - Proper separation and structure
5. **Good rubric examples** - Clear pass/fail examples for each rule

---

## Recommendations

| Priority | Issue | Action |
|----------|-------|--------|
| High | Rule 12 token matching | Normalize: upper + replace hyphen |
| Medium | Rule 6 blacklist | Expand verb list |
| Medium | Rule 13 ref matching | Use word boundaries |
| Medium | Multi-line footer values | Handle continuation lines |
| Low | Rule 3 scope regex | Allow leading digits |
| Low | Footer token list | Add more common tokens |

---

## Files Reviewed

- `evaluate_commits.py` (763 lines)
- `evaluation-rubric.md` (329 lines)
