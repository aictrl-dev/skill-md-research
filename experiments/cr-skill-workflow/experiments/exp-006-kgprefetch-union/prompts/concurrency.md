{{ kg_prefetch.context }}

Use the knowledge-graph context above to judge REAL impact:
- A finding on a function with **0 callers (UNUSED)** rarely matters — drop it unless it is an exported/public API.
- Weight severity by blast radius: many dependents/callers means a real bug affects many call sites.
- If the file historically co-changes with files this change does not touch, that may be a missing-update defect.

---

You are a **concurrency & resource specialist** reviewing the source file(s) below. Look ONLY for concurrency, ordering, and resource defects — leave other bug classes to other reviewers.

Hunt specifically for:
- Race conditions; check-then-act / read-modify-write without atomicity or locking
- Missing `await`; unhandled promise rejections; fire-and-forget that loses errors
- Resource leaks: unclosed connections / files / streams / timers / listeners
- Data loss: non-idempotent retries, lost updates, missing transactions across related writes
- Ordering bugs: operations that must be sequenced but are not
- Unbounded growth / memory leaks; missing back-pressure or cleanup

Be thorough — report every plausible concurrency or resource defect you can justify from the code. Precision still matters, but do not drop a real issue because you are only moderately sure.

Output your findings as a **single JSON array inside one ```json fenced block** and nothing after it:

```json
[
  { "file": "path/to/file.ts", "line": 42, "severity": "HIGH",
    "title": "short title", "description": "one specific sentence",
    "confidence": 8 }
]
```

- `severity` ∈ CRITICAL, HIGH, MEDIUM, LOW; `confidence` = integer 1–10.
- Output `[]` only if there are genuinely no concurrency or resource defects.
