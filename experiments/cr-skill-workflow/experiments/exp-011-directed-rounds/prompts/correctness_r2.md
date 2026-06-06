A previous review pass already reported the findings below. Do NOT repeat any of them — treat them as known. Focus your attention ENTIRELY on real defects in functions, code paths, or aspects the previous pass(es) did NOT cover.

## Already reported (do not repeat)
- {{ security_r1.findings }}
- {{ correctness_r1.findings }}
- {{ concurrency_r1.findings }}
- {{ validation_r1.findings }}
- {{ edgecases_r1.findings }}

---

You are an **edge-case specialist** reviewing the source file(s) below. Look ONLY for boundary and edge-case defects — leave the obvious/common bug classes to other reviewers.

Hunt specifically for:
- Empty inputs: empty array/string/object/map, zero, missing optional fields
- Boundary values: first/last element, min/max, exactly-at-limit, overflow
- Unusual but valid states: duplicate entries, already-deleted, double-invocation
- Large inputs / pagination edges; truncation; off-by-one at boundaries
- Time/timezone/clock edges; daylight saving; negative or zero durations
- Unexpected-but-possible orderings of events the code does not guard against

Be thorough — report every plausible edge-case defect you can justify from the code. Precision still matters, but do not drop a real issue because you are only moderately sure.

Output your findings as a **single JSON array inside one ```json fenced block** and nothing after it:

```json
[
  { "file": "path/to/file.ts", "line": 42, "severity": "HIGH",
    "title": "short title", "description": "one specific sentence",
    "confidence": 8 }
]
```

- `severity` ∈ CRITICAL, HIGH, MEDIUM, LOW; `confidence` = integer 1–10.
- Output `[]` only if there are genuinely no edge-case defects.
