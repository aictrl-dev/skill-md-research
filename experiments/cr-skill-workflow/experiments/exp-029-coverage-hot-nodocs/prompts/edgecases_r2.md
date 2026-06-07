The coverage map below summarises what previous review passes already found and — more importantly — which symbols and failure modes remain UNEXPLORED. Do NOT re-report anything listed under "Already found"; treat those as known. Spend your effort on the UNEXPLORED symbols and failure modes the map highlights, and report only NEW defects in code the earlier passes did not cover.

{{ coverage.context }}

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
