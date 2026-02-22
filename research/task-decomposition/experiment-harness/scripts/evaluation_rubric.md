# Evaluation Rubric for Task Decomposition Experiment

**Version**: 1.0
**Purpose**: Manually score LLM outputs for quality comparison

---

## Scoring Guide

Rate each criterion from **1-5**:
- **5** = Excellent, production-ready
- **4** = Good, minor issues
- **3** = Acceptable, some gaps
- **2** = Poor, significant issues
- **1** = Missing or wrong
- **0** = Not present

---

## Rubric

### A. Decomposition Compliance (15 points)

| ID | Criterion | Score |
|----|-----------|-------|
| A1 | Follows specified decomposition strategy (stack/domain/journey) | /5 |
| A2 | Steps are in correct order for the strategy | /5 |
| A3 | Each step has clear inputs and outputs | /5 |
| **Subtotal** | | **/15** |

### B. Gherkin Artifact Quality (15 points)

| ID | Criterion | Score |
|----|-----------|-------|
| B1 | Valid Gherkin syntax (Feature, Scenario, Given/When/Then) | /5 |
| B2 | Scenarios cover main use cases | /5 |
| B3 | Scenarios are testable/verifiable | /5 |
| **Subtotal** | | **/15** |

### C. OpenAPI Artifact Quality (15 points)

| ID | Criterion | Score |
|----|-----------|-------|
| C1 | Valid OpenAPI/YAML syntax | /5 |
| C2 | Endpoints match task requirements | /5 |
| C3 | Includes correct types and fields | /5 |
| **Subtotal** | | **/15** |

### D. SQL Artifact Quality (15 points)

| ID | Criterion | Score |
|----|-----------|-------|
| D1 | Valid migration file structure (up/down) | /5 |
| D2 | Correct columns and types for task | /5 |
| D3 | Includes indexes and constraints | /5 |
| **Subtotal** | | **/15** |

### E. Code Implementation Quality (25 points)

| ID | Criterion | Score |
|----|-----------|-------|
| E1 | Correct files identified/modified | /5 |
| E2 | Code is syntactically correct | /5 |
| E3 | Code follows existing patterns in codebase | /5 |
| E4 | Handles edge cases | /5 |
| E5 | Includes error handling | /5 |
| **Subtotal** | | **/25** |

### F. Test Coverage (15 points)

| ID | Criterion | Score |
|----|-----------|-------|
| F1 | Unit tests included | /5 |
| F2 | Tests cover happy path | /5 |
| F3 | Tests cover edge cases | /5 |
| **Subtotal** | | **/15** |

---

## Total Score

| Section | Max | Score |
|---------|-----|-------|
| A. Decomposition | 15 | /15 |
| B. Gherkin | 15 | /15 |
| C. OpenAPI | 15 | /15 |
| D. SQL | 15 | /15 |
| E. Code | 25 | /25 |
| F. Tests | 15 | /15 |
| **TOTAL** | **100** | **/100** |

---

## Quick Evaluation Form

```
Run ID: ________________
Model: ________________
Task: ________________
Decomposition: ________________
Artifacts: ________________

A1: _  A2: _  A3: _   | Subtotal: __/15
B1: _  B2: _  B3: _   | Subtotal: __/15
C1: _  C2: _  C3: _   | Subtotal: __/15
D1: _  D2: _  D3: _   | Subtotal: __/15
E1: _  E2: _  E3: _  E4: _  E5: _  | Subtotal: __/25
F1: _  F2: _  F3: _   | Subtotal: __/15

TOTAL: ___/100

Notes:
```
