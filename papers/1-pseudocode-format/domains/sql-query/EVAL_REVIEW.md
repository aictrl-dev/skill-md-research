# SQL Evaluation Script Review

**File:** `evaluate_sql.py`  
**Rubric:** `evaluation-rubric.md`  
**Reviewer:** Claude  
**Date:** 2026-02-20

## Summary

The SQL evaluator is comprehensive with 14 rules covering style, structure, and performance. It includes outcome checks (semantic correctness) alongside style rules. Well-documented rubric with clear examples. Below are issues found.

---

## Issues

### 1. Rule 6 SELECT * Pattern Bug (lines 375-378)

```python
if re.search(r'\bSELECT\s+\*\s', cleaned, re.IGNORECASE):
    return False, "SELECT * found"
```

**Problem:** Requires whitespace after `*`, won't match:
- `SELECT *FROM table` (no space)
- `SELECT\n    *\nFROM` (newline before FROM)
- `SELECT *, id` (comma after *)

**Fix:**
```python
if re.search(r'\bSELECT\s+\*\s*(?:,|FROM\b)', cleaned, re.IGNORECASE):
```

---

### 2. Rule 4 Nested Parenthesis Handling (lines 298-323)

```python
for i in range(paren_start, len(cleaned)):
    if cleaned[i] == '(':
        depth += 1
```

**Problem:** Simple parenthesis counter fails on nested functions:
```sql
SUM(COALESCE(x, (SELECT MAX(y) FROM t)))
```
Could misidentify the closing paren.

**Fix:** Consider using a proper SQL parser or more robust bracket matching.

---

### 3. Rule 3 CTE Name False Positive (line 274)

```python
if table_name.upper() in ('SELECT', 'LATERAL', '('):
    continue
```

**Problem:** Doesn't check if "table" is a CTE defined earlier. This would flag:
```sql
WITH cte AS (...)
SELECT * FROM cte  -- flags "cte" as unaliased
```

**Fix:** Extract CTE names from WITH clause and exclude them.

---

### 4. Rule 9 Column Comparison (line 457)

```python
if col == gc or col.split('.')[-1] == gc.split('.')[-1]:
```

**Problem:** Strips schema qualification, causing false matches:
- `public.users.id` matches `audit.users.id` (different schemas)
- `o.id` matches `c.id` (different tables)

**Fix:** Require full match or track which table each column belongs to.

---

### 5. Extraction SELECT Pattern (line 106)

```python
if upper.startswith(('SELECT ', 'SELECT\n', 'WITH ', 'WITH\n')) or stripped.startswith('--'):
```

**Problem:** Misses:
- `SELECT\t` (tab instead of space)
- `SELECT(` (function call, unlikely but possible)
- `(SELECT` (subquery in expression)

**Fix:** Use regex `\bSELECT\b` or `\bWITH\b` with word boundaries.

---

### 6. String Literal Escaping (line 615)

```python
result = re.sub(r"'[^']*'", "'_STR_'", result)
```

**Problem:** Doesn't handle escaped quotes:
- `'it''s'` (SQL standard escaping)
- `E'escape\'` (PostgreSQL)
- `N'unicode'` (SQL Server)

**Fix:** Use more robust pattern or handle escaped quotes separately.

---

### 7. Rule 8 Subquery Detection (line 396)

```python
has_subquery = bool(re.search(r'\bFROM\s*\(', cleaned, re.IGNORECASE))
```

**Problem:** Misses subqueries with newlines:
```sql
FROM
    (SELECT ...)
```

**Fix:** Use `\s*` instead of `\s*` or `\s+` pattern that spans lines.

---

### 8. Rules 10 and 13 Overlap

Both check for `YEAR()`, `MONTH()`, `DAY()` on columns:
- **Rule 10** (date_handling): Flags anywhere in query
- **Rule 13** (sargable): Only flags in WHERE clause

**Problem:** Same bad pattern penalized twice. If `YEAR(o.date)` in WHERE, fails both rules.

**Fix:** Consider consolidating or documenting that double-penalty is intentional.

---

### 9. Outcome Score Not in auto_score

The `outcome_score` is calculated separately (lines 964-972) but not included in `auto_score`. Rubric doesn't clarify if outcome checks should affect main score.

**Fix:** Document scoring model: is it 14 style rules + 3 outcome checks = 17 total, or are they separate metrics?

---

### 10. Rule 2 OVER() False Positive (line 244)

```python
pattern = r'\b' + re.escape(clause) + r'\b'
if re.search(pattern, upper_line):
    found.append(clause)
```

**Problem:** `ORDER BY` inside `OVER(ORDER BY ...)` counts as a major clause, but shouldn't.

**Fix:** Detect if clause is inside parentheses (likely window function or subquery).

---

## Minor Issues

### Rule 12 Comment Detection (line 517)

Only detects `--` comments. Block comments `/* ... */` at query start would fail.

### Rule 14 Indentation Heuristic (lines 559-593)

Very basic - only checks that *some* lines are indented and SELECT columns are indented. Doesn't verify consistent indentation depth.

### Keyword List Incomplete (lines 31-40)

Missing some common keywords:
- `UNION`, `INTERSECT`, `EXCEPT`
- `DISTINCT`, `ALL`
- `NULLS` (in ORDER BY)
- `LATERAL`

---

## Strengths

1. **Dual scoring** - Style rules (auto_score) + semantic outcome checks (outcome_score)
2. **Comprehensive extraction** - Handles JSONL, Claude JSON, fenced blocks, plain text
3. **Good comment handling** - `_find_comment_start` correctly ignores `--` inside strings
4. **Well-documented rubric** - Clear examples for each rule with edge cases

---

## Recommendations

| Priority | Issue | Action |
|----------|-------|--------|
| High | Rule 6 SELECT * pattern | Fix regex |
| High | Rule 3 CTE false positives | Track CTE names |
| Medium | Rule 9 column matching | Preserve table qualification |
| Medium | String escaping | Handle `''` escapes |
| Low | Rule 10/13 overlap | Document or consolidate |
| Low | Keyword list | Add UNION, DISTINCT, etc. |

---

## Files Reviewed

- `evaluate_sql.py` (1037 lines)
- `evaluation-rubric.md` (407 lines)
