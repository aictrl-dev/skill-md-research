# Manual Evaluation: Pilot Experiment

**Date**: 2026-02-22
**Task**: outline_crud_001_word_count
**Decomposition**: Stack
**Artifacts**: Full

---

## Model: Claude Haiku

### A. Decomposition Compliance (15 points)

| ID | Criterion | Score | Notes |
|----|-----------|-------|-------|
| A1 | Follows stack decomposition | 4 | Lists files in order: Model, Revision, Presenter, Migration, Tests |
| A2 | Steps in correct order | 3 | Missing explicit step numbers, but implied order is correct |
| A3 | Clear inputs/outputs | 2 | Summary only, no explicit step I/O |
| **Subtotal** | | **9/15** |

### B. Gherkin Artifact Quality (15 points)

| ID | Criterion | Score | Notes |
|----|-----------|-------|-------|
| B1 | Valid Gherkin syntax | 0 | **No Gherkin output** |
| B2 | Covers use cases | 0 | Not present |
| B3 | Testable | 0 | Not present |
| **Subtotal** | | **0/15** |

### C. OpenAPI Artifact Quality (15 points)

| ID | Criterion | Score | Notes |
|----|-----------|-------|-------|
| C1 | Valid OpenAPI syntax | 0 | **No OpenAPI output** |
| C2 | Endpoints match requirements | 0 | Not present |
| C3 | Correct types/fields | 0 | Not present |
| **Subtotal** | | **0/15** |

### D. SQL Artifact Quality (15 points)

| ID | Criterion | Score | Notes |
|----|-----------|-------|-------|
| D1 | Valid migration structure | 2 | Mentions migration but **no actual code** |
| D2 | Correct columns/types | 2 | Mentions word_count column |
| D3 | Indexes/constraints | 2 | Mentions index |
| **Subtotal** | | **6/15** |

### E. Code Implementation Quality (25 points)

| ID | Criterion | Score | Notes |
|----|-----------|-------|-------|
| E1 | Correct files identified | 5 | Lists all 6 correct files |
| E2 | Syntactically correct | 1 | **No actual code shown** |
| E3 | Follows patterns | 2 | Describes decorators correctly |
| E4 | Handles edge cases | 2 | Mentions Prosemirror + text formats |
| E5 | Error handling | 1 | Not shown |
| **Subtotal** | | **11/25** |

### F. Test Coverage (15 points)

| ID | Criterion | Score | Notes |
|----|-----------|-------|-------|
| F1 | Unit tests included | 2 | Mentions 5 unit tests, **no code** |
| F2 | Happy path covered | 2 | Mentions coverage |
| F3 | Edge cases covered | 2 | Mentions whitespace, empty |
| **Subtotal** | | **6/15** |

### **Haiku Total: 32/100**

---

## Model: GLM-4.5-Flash

### A. Decomposition Compliance (15 points)

| ID | Criterion | Score | Notes |
|----|-----------|-------|-------|
| A1 | Follows stack decomposition | 5 | Explicit: "Step 1: Database Layer", "Step 2: Model Layer" |
| A2 | Steps in correct order | 5 | DB → Model → Hooks → Helper |
| A3 | Clear inputs/outputs | 4 | Shows reads and writes for each step |
| **Subtotal** | | **14/15** |

### B. Gherkin Artifact Quality (15 points)

| ID | Criterion | Score | Notes |
|----|-----------|-------|-------|
| B1 | Valid Gherkin syntax | 0 | **No Gherkin output** (followed prompt but skipped) |
| B2 | Covers use cases | 0 | Not present |
| B3 | Testable | 0 | Not present |
| **Subtotal** | | **0/15** |

### C. OpenAPI Artifact Quality (15 points)

| ID | Criterion | Score | Notes |
|----|-----------|-------|-------|
| C1 | Valid OpenAPI syntax | 0 | **No OpenAPI output** |
| C2 | Endpoints match requirements | 0 | Not present |
| C3 | Correct types/fields | 0 | Not present |
| **Subtotal** | | **0/15** |

### D. SQL Artifact Quality (15 points)

| ID | Criterion | Score | Notes |
|----|-----------|-------|-------|
| D1 | Valid migration structure | 4 | "Wrote file successfully" but **code not shown in output** |
| D2 | Correct columns/types | 3 | Later edits show word_count column |
| D3 | Indexes/constraints | 2 | Not explicit |
| **Subtotal** | | **9/15** |

### E. Code Implementation Quality (25 points)

| ID | Criterion | Score | Notes |
|----|-----------|-------|-------|
| E1 | Correct files identified | 5 | Document.ts, DocumentHelper.tsx |
| E2 | Syntactically correct | 4 | **Actual code diffs shown!** Valid TypeScript |
| E3 | Follows patterns | 5 | Uses existing decorators (@Default, @Column, @BeforeSave) |
| E4 | Handles edge cases | 4 | Checks null, string vs Prosemirror, changed() |
| E5 | Error handling | 3 | Basic checks but no try/catch |
| **Subtotal** | | **21/25** |

### F. Test Coverage (15 points)

| ID | Criterion | Score | Notes |
|----|-----------|-------|-------|
| F1 | Unit tests included | 1 | **Incomplete** - output cut off |
| F2 | Happy path covered | 1 | Not shown |
| F3 | Edge cases covered | 1 | Not shown |
| **Subtotal** | | **3/15** |

### **GLM-4.5-Flash Total: 47/100**

---

## Comparison

| Section | Max | Haiku | GLM-4.5-Flash |
|---------|-----|-------|---------------|
| A. Decomposition | 15 | 9 | **14** |
| B. Gherkin | 15 | 0 | 0 |
| C. OpenAPI | 15 | 0 | 0 |
| D. SQL | 15 | 6 | **9** |
| E. Code | 25 | 11 | **21** |
| F. Tests | 15 | 6 | 3 |
| **TOTAL** | **100** | **32** | **47** |

---

## Key Findings

### What Worked
- **GLM-4.5-Flash produced actual code diffs** (edit format)
- Both followed stack decomposition strategy
- Both identified correct files to modify

### What Failed
- **Neither produced Gherkin or OpenAPI artifacts** despite "full" format prompt
- **Neither produced complete SQL migration code**
- Haiku: summary only, no actual code
- GLM: incomplete (cut off during execution)

### Critical Gap
The prompt asked for **Gherkin + OpenAPI + SQL artifacts per step**, but both models:
1. Skipped directly to code implementation
2. Ignored artifact format instructions
3. Treated task spec as implementation guide

---

## Recommendations

### For Experiment Design
1. **Separate artifact generation from implementation** - two-phase prompt
2. **Add explicit artifact requirements** - "You MUST output Gherkin before code"
3. **Use structured output format** - JSON with artifact fields

### For Evaluation
1. **Score partial outputs** - what was produced vs expected
2. **Track completion rate** - % of task completed before timeout/cutoff
3. **Measure code correctness** - apply patches and run tests

### For Next Run
1. Try **domain decomposition** to see if different strategy produces artifacts
2. Try **nl (natural language only)** format as baseline
3. Run with **longer timeout** for GLM to complete
