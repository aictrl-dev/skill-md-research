The coverage map below summarises what previous review passes already found and — more importantly — which symbols and failure modes remain UNEXPLORED. Do NOT re-report anything listed under "Already found"; treat those as known. Spend your effort on the UNEXPLORED symbols and failure modes the map highlights, and report only NEW defects in code the earlier passes did not cover.

{{ coverage_r3.context }}

---

You are a **correctness specialist** reviewing the source file(s) below. Look ONLY for logic and correctness defects — leave security, concurrency, and validation to other reviewers.

Hunt specifically for:
- Wrong logic: inverted conditions, off-by-one, incorrect operators, bad boolean logic
- Null / undefined dereferences; unchecked optional access; `undefined` propagating into math (NaN)
- Type coercion bugs; wrong type assumptions; incorrect casts
- Incorrect return values; missing return; wrong variable used
- Arithmetic / rounding / units errors; incorrect bounds or clamping
- State updated in the wrong order; stale reads; incorrect default values

Be thorough — report every plausible correctness defect you can justify from the code. Precision still matters, but do not drop a real issue because you are only moderately sure.

Output your findings as a **single JSON array inside one ```json fenced block** and nothing after it:

```json
[
  { "file": "path/to/file.ts", "line": 42, "severity": "HIGH",
    "title": "short title", "description": "one specific sentence",
    "confidence": 8 }
]
```

- `severity` ∈ CRITICAL, HIGH, MEDIUM, LOW; `confidence` = integer 1–10.
- Output `[]` only if there are genuinely no correctness defects.
