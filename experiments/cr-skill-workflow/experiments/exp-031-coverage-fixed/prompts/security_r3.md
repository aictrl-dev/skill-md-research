The coverage map below summarises what previous review passes already found and — more importantly — which symbols and failure modes remain UNEXPLORED. Do NOT re-report anything listed under "Already found"; treat those as known. Spend your effort on the UNEXPLORED symbols and failure modes the map highlights, and report only NEW defects in code the earlier passes did not cover.

{{ coverage_r3.context }}

---

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
