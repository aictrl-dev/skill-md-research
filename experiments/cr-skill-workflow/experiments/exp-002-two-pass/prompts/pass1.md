Review the source file(s) below for **real, specific defects**: security/authorization
flaws, correctness bugs, data-loss / race conditions, contract or type violations,
resource leaks, missing validation, and error-handling gaps. Ignore style nits.

For each finding you are confident is a genuine defect, record it. If you are
uncertain, omit it. Precision over recall — a false positive is worse than a miss.

Output your findings as a **single JSON array inside one ```json fenced block**
and nothing after it.

```json
[
  { "file": "path/to/file.ts", "line": 42, "severity": "HIGH",
    "title": "short title", "description": "one specific sentence",
    "confidence": 8 }
]
```

- `severity` ∈ CRITICAL, HIGH, MEDIUM, LOW
- `confidence` = integer 1–10
- Output `[]` if the code is defect-free
