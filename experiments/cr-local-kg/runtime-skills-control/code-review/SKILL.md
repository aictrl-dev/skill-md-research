---
name: code-review
description: Review the provided source file(s) for real defects and emit findings as JSON. Use when asked to review code.
version: "1.0.0"
---

# Code Review (whole-file)

You are reviewing the source file(s) provided in the prompt for **real, specific
defects**: security/authorization flaws, correctness bugs, data-loss / race
conditions, contract or type violations, resource leaks, missing validation, and
error-handling gaps. Ignore style nits.

## How to review

Read the code carefully. For each potential defect ask:
- Is this a real bug or just imperfect style?
- Can this cause data loss, incorrect behaviour, or a security issue?
- Does the error handling cover the failure modes?

Record a finding only when you are confident it is a genuine defect. Do not
inflate findings to seem thorough — precision matters. Output `[]` only if you
are genuinely confident the code is defect-free.

## Output

Output your findings as a **single JSON array inside one ```json fenced block**
and nothing after it:

```json
[
  { "file": "server/lib/x.ts", "line": 42, "severity": "HIGH",
    "title": "short title", "description": "one specific sentence",
    "confidence": 8 }
]
```

- `file` = repo-relative path exactly as shown; `line` = a number or `start-end`.
- `severity` ∈ CRITICAL, HIGH, MEDIUM, LOW. `confidence` = integer 1–10.
