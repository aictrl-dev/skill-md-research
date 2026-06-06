---
name: code-review
description: Multi-step workflow code review with explicit scan → enrich → filter → output stages.
allowedTools:
  - aictrl_query_context
version: "2.0.0"
---

# Code Review — Structured Workflow

You are reviewing the source file(s) provided in the prompt for **real, specific
defects**: security/authorization flaws, correctness bugs, data-loss / race
conditions, contract or type violations, resource leaks, missing validation, and
error-handling gaps. Ignore style nits.

Work through these four steps in order. Do not skip steps.

---

## Step 1 — Scan

Read the entire file(s). Write a **scratch list** of every suspicious location:
function name, line number, and one-line note. Aim for 10–20 candidates. At this
stage include anything that looks worth investigating — you will filter later.

Format the scratch list as a JSON comment block so you can reference it in later steps:

```json
// scratch
[
  { "fn": "getUserById", "line": 42, "note": "no null check before .id access" },
  ...
]
```

---

## Step 2 — KG Enrichment

For each candidate in your scratch list, run **one** `aictrl_query_context` call
to check real-world impact:

- `{"domain":"code","action":"callers","query":"<functionName>"}` — if zero callers, downgrade or drop.
- `{"domain":"code","action":"impact","query":"<filePath>"}` — understand blast radius.

Annotate each scratch entry with a `callers` count. Keep a running tally of calls
used (hard limit: **8 total** across all candidates — stop enriching once you hit 8).

---

## Step 3 — Filter

Apply these rules to your annotated scratch list:

1. Drop candidates where callers = 0 **and** confidence < 6.
2. Drop style/naming issues (not defects).
3. Promote severity to HIGH for any finding with callers > 5.
4. Keep at most **10 findings** — take the highest-confidence survivors.

---

## Step 4 — Output

Emit the surviving findings as a **single JSON array inside one ```json fenced
block** and nothing after it.

```json
[
  { "file": "server/lib/x.ts", "line": 42, "severity": "HIGH",
    "title": "short title", "description": "one specific sentence",
    "confidence": 8 }
]
```

- `file` = repo-relative path exactly as shown in the prompt.
- `line` = number or `start-end` range.
- `severity` ∈ CRITICAL, HIGH, MEDIUM, LOW.
- `confidence` = integer 1–10.
- Output `[]` only if you are genuinely confident the code is defect-free.
