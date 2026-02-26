# Experiment Harness for Task Decomposition Research

## Directory Structure

```
experiment-harness/
  codebase/              # Outline codebase (git clone)
  tasks/                 # Task specifications
    outline_crud_001_word_count.md
    outline_workflow_001_*.md (TODO)
    outline_integration_001_*.md (TODO)
    outline_uiflow_001_*.md (TODO)
  prompts/               # LLM prompts (TODO)
    decomposition/
      stack.md
      domain.md
      journey.md
    artifacts/
      natural_language.md
      gherkin_only.md
      gherkin_openapi.md
      full_artifacts.md
  results/               # Experiment results (TODO)
  scripts/               # Runner scripts (TODO)
    run_experiment.py
    evaluate.py
```

## Quick Start

```bash
# 1. Clone codebase (already done)
cd experiment-harness
git clone --depth 1 https://github.com/outline/outline.git codebase

# 2. Install dependencies (for evaluation)
cd codebase
yarn install

# 3. Run a single experiment (TODO)
python ../scripts/run_experiment.py --task outline_crud_001 --decomposition stack --artifacts full

# 4. Evaluate results (TODO)
python ../scripts/evaluate.py --run-dir results/outline_crud_001/stack_full/rep_1
```

## Current Status

| Component | Status |
|-----------|--------|
| Codebase cloned | Done |
| Task specs | 4/4 complete |
| Prompts | Done (3 decomp + 4 artifacts) |
| Runner scripts | Done (Python scaffolding) |
| Evaluation scripts | Done (Python scaffolding) |

## Task Specs

| Task ID | Type | Description | Status |
|---------|------|-------------|--------|
| outline_crud_001 | CRUD | Add word_count to Documents | Done |
| outline_workflow_001 | Workflow | Add document approval flow | Done |
| outline_integration_001 | Integration | Add Slack webhook sharing | Done |
| outline_uiflow_001 | UI Flow | Add document creation wizard | Done |

## Hypotheses to Test

| ID | Hypothesis | Metric |
|----|------------|--------|
| H1 | Stack decomposition wins for CRUD | success_rate |
| H2 | Gherkin + OpenAPI + SQL > other formats | success_rate |
| H3 | Cross-artifact validation catches 60% errors | errors_caught / total |
| H4 | All artifacts valid → 90% success | correlation |

## Evaluation Metrics

```python
success = (
    tests_pass AND              # yarn test passes
    migration_runs AND          # yarn db:migrate succeeds
    api_works AND               # endpoints respond correctly
    artifact_consistency > 0.9  # Gherkin → OpenAPI → SQL aligned
)
```

## Next Steps

1. Create remaining task specs (workflow, integration, uiflow)
2. Write decomposition prompts (stack, domain, journey)
3. Write artifact format prompts (NL, Gherkin, Gherkin+API, Full)
4. Build runner script
5. Build evaluation script
6. Run experiments
7. Analyze results
