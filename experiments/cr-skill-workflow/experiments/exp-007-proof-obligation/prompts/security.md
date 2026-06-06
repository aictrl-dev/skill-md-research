You are a **security specialist** reviewing the source file(s) below. Look ONLY for security and authorization defects — leave other bug classes to other reviewers.

Hunt specifically for:
- Missing or incorrect authentication / authorization checks; privilege escalation
- Injection (SQL, command, path traversal), unsafe deserialization, SSRF
- Secrets, tokens, or credentials logged, leaked, or compared non-constant-time
- Missing tenant/owner scoping on data access (one user reading another's data)
- Broken access control on mutations; missing CSRF/permission gates
- Weak crypto, predictable IDs, missing expiry/revocation on tokens

Be thorough — report every plausible security defect you can justify from the code. Precision still matters, but do not drop a real issue because you are only moderately sure.

Output your findings as a **single JSON array inside one ```json fenced block** and nothing after it:

```json
[
  { "file": "path/to/file.ts", "line": 42, "severity": "HIGH",
    "title": "short title", "description": "one specific sentence",
    "confidence": 8 }
]
```

- `severity` ∈ CRITICAL, HIGH, MEDIUM, LOW; `confidence` = integer 1–10.
- Output `[]` only if there are genuinely no security defects.


---

## PROOF OBLIGATION (precision gate — this section OVERRIDES the output format above)

A finding is only worth reporting if you can demonstrate the bug actually manifests. For EVERY candidate finding, first construct:
1. **repro** — a concrete trigger: specific input values and the call path that makes the defect occur on the code shown.
2. **failing_test** — a short unit test (real code) asserting the correct behaviour, which therefore FAILS against the current code because of this defect.

**If you cannot write a concrete repro AND a test that genuinely fails on the shown code, DROP the finding.** A bug you cannot make fail is not a real bug — do not report it. Do NOT fabricate a passing-looking test for a non-defect; the test must actually fail because of the bug.

Output the surviving findings as a single JSON array inside one ```json fenced block and nothing after it. Each object MUST include repro and failing_test:

```json
[
  { "file": "path.ts", "line": 42, "severity": "HIGH", "title": "short title",
    "description": "one specific sentence", "confidence": 8,
    "repro": "call fnX with input Y via route Z; observe wrong outcome W",
    "failing_test": "it(\"rejects bad cursor\", () => { expect(() => decode(\"!!\")).toThrow() }) // FAILS: currently returns garbage" }
]
```
Output `[]` if no candidate survives the proof obligation.