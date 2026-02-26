# Research Status Summary

**Last updated**: 2026-02-22

---

## Completed Work

### 1. Pseudocode vs Markdown Skill Format (Original)

| Component | Status | Location |
|-----------|--------|----------|
| Experiment design | Done | `experiment-plan.md` |
| 6 domain evaluators | Done | `domains/*/evaluate_*.py` |
| Runner scripts | Done | `scripts/run-*.sh` |
| Analysis scripts | Done | `scripts/analyze*.py` |
| Results | Collected | `domains/*/results/` |

### 2. Task Decomposition Research (NEW)

| Component | Status | Location |
|-----------|--------|----------|
| Literature review | Done | `research/task-decomposition/literature-review.md` |
| Product implications | Done | `research/task-decomposition/implications-aictrl.md` |
| Enterprise decomposition | Done | `research/task-decomposition/enterprise-decomposition.md` |
| Codebase selection | Done | `research/task-decomposition/codebase-selection.md` |
| Experiment design | Done | `research/task-decomposition/experiment-enterprise.md` |
| Task specs (4) | Done | `research/task-decomposition/experiment-harness/tasks/` |
| Prompts (7) | Done | `research/task-decomposition/experiment-harness/prompts/` |
| Runner scripts | Done | `research/task-decomposition/experiment-harness/scripts/` |
| Outline codebase | Cloned | `research/task-decomposition/experiment-harness/codebase/` |

---

## Files Created This Session

```
research/task-decomposition/
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

### Skill Format (Original)
- H1: Pseudocode > Markdown > No-skill for instruction compliance
- H2: Effect stronger on complex tasks
- H3: Effect stronger on smaller models

### Task Decomposition (NEW)
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
cd research/task-decomposition/experiment-harness
./scripts/run-decomposition-experiment.sh --pilot

# Evaluate results
python scripts/evaluate.py --run-dir results/outline_crud_001/stack_full/rep_1

# Run original skill format experiment
cd /home/bulat/code/skill-md-research
./scripts/run-domain-experiment.sh --domain chart
```
