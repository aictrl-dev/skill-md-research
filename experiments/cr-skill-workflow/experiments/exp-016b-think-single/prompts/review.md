Review the source file(s) below for ALL classes of real, user-impacting defects: security/authorization flaws, correctness/logic bugs, null/undefined & type errors, concurrency/races, resource leaks & data loss, missing input validation, contract violations, error-handling gaps, and boundary/edge cases. Ignore pure style/naming/comment nits.

Be thorough — report every plausible real defect you can justify from the code.

Output findings as a single JSON array inside one ```json fenced block and nothing after it:
```json
[ { "file": "path.ts", "line": 42, "severity": "HIGH", "title": "short", "description": "one sentence", "confidence": 8 } ]
```
severity ∈ CRITICAL/HIGH/MEDIUM/LOW; confidence 1-10; [] if defect-free.
