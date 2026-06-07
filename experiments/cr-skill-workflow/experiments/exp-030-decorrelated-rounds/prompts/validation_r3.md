## Stance for this pass: 3AM PRODUCTION INCIDENT
Production is down and this file is implicated. Work backwards: what failure in THIS code could have caused a real outage, data loss, or corruption? Trace the worst realistic failure path a user/operator would hit.

## Coverage so far — focus ONLY on the UNEXPLORED
{{ coverage_r3.context }}
Do NOT re-report anything under "Already found"; report only NEW defects in code earlier passes did not cover.

---

You are an **input-validation & contract specialist** reviewing the source file(s) below. Look ONLY for validation, contract, and error-handling defects — leave other bug classes to other reviewers.

Hunt specifically for:
- Missing or insufficient input validation (range, format, length, required fields)
- Contract violations: function used in a way that breaks its documented/typed contract
- Error handling gaps: swallowed errors, broad catches that hide failures, missing error paths
- Incorrect or missing handling of failure return values (null/Result/throw not checked)
- Unsafe assumptions about caller-supplied data; trusting external input shape
- Inconsistent invariants between related fields; missing precondition checks

Be thorough — report every plausible validation or contract defect you can justify from the code. Precision still matters, but do not drop a real issue because you are only moderately sure.

Output your findings as a **single JSON array inside one ```json fenced block** and nothing after it:

```json
[
  { "file": "path/to/file.ts", "line": 42, "severity": "HIGH",
    "title": "short title", "description": "one specific sentence",
    "confidence": 8 }
]
```

- `severity` ∈ CRITICAL, HIGH, MEDIUM, LOW; `confidence` = integer 1–10.
- Output `[]` only if there are genuinely no validation or contract defects.
