---
name: code-review
description: Review the provided source file(s) for real defects and emit findings as JSON. Use when asked to review code. Pairs with the explore-context skill for knowledge-graph verification.
allowedTools:
  - aictrl_query_context
version: "1.0.0"
---

# Code Review (whole-file)

You are reviewing the source file(s) provided in the prompt for **real, specific
defects**: security/authorization flaws, correctness bugs, data-loss / race
conditions, contract or type violations, resource leaks, missing validation, and
error-handling gaps. Ignore style nits.

## Verify with the knowledge graph FIRST

Load the **explore-context** skill's protocol: every code-touching judgement is a
graph query first. Before recording any finding on a function or file, run at
least one `query_context` query to verify it:

- `{"domain":"code","action":"callers","query":"<functionName>"}` — blast radius.
  Zero callers → the bug may not matter (drop/downgrade). Many callers → raise severity.
- `{"domain":"code","action":"impact","query":"<file path>"}` — what depends on it.
- `{"domain":"code","action":"co_changes","query":"<file path>"}` — tests/files that
  usually change together (flag missing updates).
- `{"domain":"code","action":"search","query":"<symbol>"}` — locate other usages.

Aim for **at least 2 graph queries per finding** before committing it. A finding
recorded with no graph context is a precision failure.

## Output

After your checks, output your findings as a **single JSON array inside one
```json fenced block** and nothing after it:

```json
[
  { "file": "server/lib/x.ts", "line": 42, "severity": "HIGH",
    "title": "short title", "description": "one specific sentence",
    "confidence": 8 }
]
```

- `file` = repo-relative path exactly as shown; `line` = a number or `start-end`.
- `severity` ∈ CRITICAL, HIGH, MEDIUM, LOW. `confidence` = integer 1–10.
- Output `[]` only if you are genuinely confident the code is defect-free.
