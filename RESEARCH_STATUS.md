# Research Status Summary

**Last updated**: 2026-02-26

---

## Completed Work

### 1. Pseudocode vs Markdown Skill Format (Original)

| Component | Status | Location |
|-----------|--------|----------|
| Experiment design | Done | `papers/1-pseudocode-format/experiment-plan.md` |
| 6 domain evaluators | Done | `papers/1-pseudocode-format/domains/*/evaluate_*.py` |
| Runner scripts | Done | `papers/1-pseudocode-format/scripts/run-*.sh` |
| Analysis scripts | Done | `papers/1-pseudocode-format/scripts/analyze*.py` |
| Results | Collected | `papers/1-pseudocode-format/domains/*/results/` |

### 2. Task Decomposition Research

| Component | Status | Location |
|-----------|--------|----------|
| Literature review | Done | `papers/2-task-decomposition/literature-review.md` |
| Product implications | Done | `papers/2-task-decomposition/implications-aictrl.md` |
| Enterprise decomposition | Done | `papers/2-task-decomposition/enterprise-decomposition.md` |
| Codebase selection | Done | `papers/2-task-decomposition/codebase-selection.md` |
| Experiment design | Done | `papers/2-task-decomposition/experiment-enterprise.md` |
| Task specs (4) | Done | `papers/2-task-decomposition/experiment-harness/tasks/` |
| Prompts (7) | Done | `papers/2-task-decomposition/experiment-harness/prompts/` |
| Runner scripts | Done | `papers/2-task-decomposition/experiment-harness/scripts/` |
| Outline codebase | Cloned | `papers/2-task-decomposition/experiment-harness/codebase/` |

### 3. KPI Targets Experiment

| Component | Status | Location |
|-----------|--------|----------|
| Experiment design | Done | `papers/3-kpi-targets/experiment-design.md` |
| Results | Done | `papers/3-kpi-targets/RESULTS.md` |
| Domains | Done | `papers/3-kpi-targets/domains/` |
| Analysis | Done | `papers/3-kpi-targets/analysis/` |
| Paper | Done | `papers/3-kpi-targets/paper/` |

---

## Files Created This Session

```
papers/2-task-decomposition/
├── README.md (updated)
├── QUICK_REFERENCE.md (new)
├── literature-review.md (new)
├── implications-aictrl.md (new)
├── enterprise-decomposition.md (new)
├── experiment-design.md (new)
├── experiment-enterprise.md (new)
├── codebase-selection.md (new)
│
└── experiment-harness/
    ├── README.md (new)
    ├── tasks/
    │   ├── outline_crud_001_word_count.md (new)
    │   ├── outline_workflow_001_approval.md (new)
    │   ├── outline_integration_001_slack.md (new)
    │   └── outline_uiflow_001_wizard.md (new)
    ├── prompts/
    │   ├── decomposition/
    │   │   ├── stack.md (new)
    │   │   ├── domain.md (new)
    │   │   └── journey.md (new)
    │   └── artifacts/
    │       ├── nl.md (new)
    │       ├── gherkin.md (new)
    │       ├── gherkin_api.md (new)
    │       └── full.md (new)
    └── scripts/
        ├── run-decomposition-experiment.sh (new)
        ├── run_experiment.py (new)
        └── evaluate.py (new)
```

**Total**: 24 new files, ~6,000 lines of documentation

---

## Key Hypotheses

### Skill Format (Paper 1)
- H1: Pseudocode > Markdown > No-skill for instruction compliance
- H2: Effect stronger on complex tasks
- H3: Effect stronger on smaller models

### Task Decomposition (Paper 2)
- H1: Stack decomposition wins for CRUD
- H2: Domain decomposition wins for workflows
- H3: Journey decomposition wins for UI flows
- H4: Full artifacts (Gherkin+API+SQL) best for backend tasks
- H5: Gherkin-only best for frontend tasks

---

## Next Steps

### Immediate
1. Run pilot experiment: `./run-decomposition-experiment.sh --pilot`
2. Analyze pilot results
3. Decide on full experiment scope

### Short-term
1. Run full decomposition experiment (432 runs)
2. Analyze task type × decomposition interactions
3. Document findings

### Medium-term
1. Integrate findings into aictrl.dev planning tool
2. Build validation layer for intermediate artifacts
3. Implement caching for common transformation patterns

---

## Product Impact for aictrl.dev

| Finding | Feature Implication |
|---------|---------------------|
| Decomposition improves quality | Generate structured plans before execution |
| Artifacts enable verification | Add schema validation at each step |
| Caching intermediate IRs saves cost | Implement artifact cache |
| Different tasks need different strategies | Auto-select decomposition strategy |

---

## Commands Quick Reference

```bash
# Run decomposition experiment
cd papers/2-task-decomposition/experiment-harness
./scripts/run-decomposition-experiment.sh --pilot

# Evaluate results
python scripts/evaluate.py --run-dir results/outline_crud_001/stack_full/rep_1

# Run original skill format experiment
cd papers/1-pseudocode-format
./scripts/run-domain-experiment.sh --domain chart
```
