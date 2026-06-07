The coverage map below summarises what previous review passes already found and — more importantly — which symbols and failure modes remain UNEXPLORED. Do NOT re-report anything listed under "Already found"; treat those as known. Spend your effort on the UNEXPLORED symbols and failure modes the map highlights, and report only NEW defects in code the earlier passes did not cover.

{{ coverage_r2.context }}

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
