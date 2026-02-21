# Dockerfile Evaluation Script Review

**File:** `evaluate_dockerfile.py`  
**Reviewer:** Claude  
**Date:** 2026-02-20

## Summary

The evaluation script is well-structured with good separation of concerns (extraction, validation, rule checks). The 14-rule rubric covers key Docker best practices. Below are issues and suggestions.

---

## Issues

### 1. Rule 1 Case Sensitivity Bug (line 191)

```python
if tag == "latest":
    bad.append(f"{image_part} (uses :latest)")
```

**Problem:** Case-sensitive check misses `:LATEST`, `:Latest`.

**Fix:**
```python
if tag.lower() == "latest":
```

---

### 2. Rule 6 Incomplete Broad Copy Detection (line 301)

```python
elif ". ." in args or args.strip().endswith(" .") or args.strip().endswith(" ./"):
```

**Problem:** Misses patterns like:
- `COPY ./src /app`
- `COPY source/ /app/`
- `COPY src dest`

**Fix:** Consider checking for patterns where destination is a path without source-specific files.

---

### 3. Rule 2 Missing User Creation Check

**Problem:** Only verifies `USER appuser` exists, not that the user was created:
```dockerfile
USER appuser  # Fails at runtime if no RUN useradd
```

**Fix:** Consider checking for `useradd`, `adduser`, or `createuser` in RUN instructions before USER.

---

### 4. Rule 8 Partial String Matching (line 352)

```python
if "rm -rf /var/lib/apt/lists" not in args:
```

**Problem:** Matches partial strings. Could match unintended content.

**Fix:** Use regex or more specific pattern matching.

---

### 5. Scoring Inconsistency

**Rubric says:** "Maximum automatable score: 14"

**Code does:** Excludes rule 14 from `auto_score` (line 479), making max score 13.

**Fix:** Update rubric to reflect actual max of 13, or include rule 14 in scoring.

---

## Minor Issues

### Rule 5 WORKDIR Edge Case

The check resets per stage but `COPY --from=builder . .` might legitimately skip WORKDIR in the final stage if copying to root.

---

## Strengths

1. **Multi-format extraction** - Handles JSONL (opencode), Claude CLI JSON, fenced blocks, and plain text well
2. **Per-stage tracking** - RUN adjacency and WORKDIR checks correctly reset at each FROM
3. **Semi-auto rules** - Good heuristic approach for rules 3, 6, 7, 12 that can't be 100% automated
4. **Clear rubric** - evaluation-rubric.md is well-documented with examples

---

## Recommendations

| Priority | Issue | Action |
|----------|-------|--------|
| High | Rule 1 case sensitivity | Add `.lower()` |
| Medium | Rule 6 broad copy detection | Expand patterns |
| Low | Rule 2 user creation | Add optional check |
| Low | Scoring docs | Clarify 13 vs 14 |

---

## Files Reviewed

- `evaluate_dockerfile.py` (655 lines)
- `evaluation-rubric.md` (175 lines)
