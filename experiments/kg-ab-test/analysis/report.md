# KG A/B Experiment Results

**Date**: YYYY-MM-DD
**Model**: zai-coding-plan/glm-5
**Codebase**: kg-blog-update (aictrl)

## Token Usage

| Task | Condition | Prompt | Completion | Reasoning | Cached | Total | API Calls | Duration |
|------|-----------|--------|------------|-----------|--------|-------|-----------|----------|
| 1-easy | control | | | | | | | |
| 1-easy | treatment | | | | | | | |
| 2-medium | control | | | | | | | |
| 2-medium | treatment | | | | | | | |
| 3-hard | control | | | | | | | |
| 3-hard | treatment | | | | | | | |

## Automated Checks

| Task | Condition | Compiles | Lints | UI Compiles | UI Lints |
|------|-----------|----------|-------|-------------|----------|
| 1-easy | control | | | N/A | N/A |
| 1-easy | treatment | | | N/A | N/A |
| 2-medium | control | | | N/A | N/A |
| 2-medium | treatment | | | N/A | N/A |
| 3-hard | control | | | | |
| 3-hard | treatment | | | | |

## Quality Scores

| Task | Condition | Compilability | Completeness | Patterns | Types | Correctness | Total |
|------|-----------|---------------|--------------|----------|-------|-------------|-------|
| 1-easy | control | | | | | | /25 |
| 1-easy | treatment | | | | | | /25 |
| 2-medium | control | | | | | | /25 |
| 2-medium | treatment | | | | | | /25 |
| 3-hard | control | | | | | | /25 |
| 3-hard | treatment | | | | | | /25 |

## Key Comparisons

### Token Reduction

| Task | Control Tokens | Treatment Tokens | Reduction % |
|------|---------------|-----------------|-------------|
| 1-easy | | | |
| 2-medium | | | |
| 3-hard | | | |
| **Average** | | | |

### Quality Delta

| Task | Control Quality | Treatment Quality | Delta |
|------|----------------|-------------------|-------|
| 1-easy | /25 | /25 | |
| 2-medium | /25 | /25 | |
| 3-hard | /25 | /25 | |
| **Average** | | | |

### Efficiency (Quality per Kilo-Token)

| Task | Control | Treatment | Improvement |
|------|---------|-----------|-------------|
| 1-easy | | | |
| 2-medium | | | |
| 3-hard | | | |

## Findings

### Hypothesis Validation

> **Hypothesis**: GLM-5 produces better code with fewer tokens when it has access to KG MCP tools.

**Result**: TBD

### Observations

1. ...
2. ...
3. ...

### Limitations

- Single run per condition (no statistical power)
- Same model version assumed across all runs
- Local environment variations (caching, load)
