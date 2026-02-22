# Experiment Harness for Task Decomposition Research

**Status**: ✅ Ready to Run

## Quick Start

```bash
# Change to this directory
cd research/task-decomposition/experiment-harness

# Run pilot (3 models, 1 task)
./scripts/run-decomposition-experiment.sh --pilot

# Or run single experiment
./scripts/run-decomposition-experiment.sh \
  --task outline_crud_001_word_count \
  --decomposition stack \
  --artifacts full \
  --rep 1
```

## Directory Structure

```
experiment-harness/
├── codebase/              # Outline codebase (git cloned)
├── tasks/                 # 4 task specifications
│   ├── outline_crud_001_word_count.md
│   ├── outline_workflow_001_approval.md
│   ├── outline_integration_001_slack.md
│   └── outline_uiflow_001_wizard.md
├── prompts/               # Prompt templates
│   ├── decomposition/     # stack, domain, journey
│   └── artifacts/         # nl, gherkin, gherkin_api, full
├── scripts/               # Runner and evaluator
│   ├── run-decomposition-experiment.sh
│   ├── run_experiment.py
│   ├── evaluate.py
│   └── generate-sample-prompt.sh
├── results/               # Experiment outputs
│   └── sample/            # Generated sample prompt
├── README.md              # This file
└── READY_TO_RUN.md        # Verification status
```

## Tasks

| ID | Type | Description | Best Decomp |
|----|------|-------------|-------------|
| outline_crud_001 | CRUD | Add word_count to Documents | Stack |
| outline_workflow_001 | Workflow | Add document approval flow | Domain |
| outline_integration_001 | Integration | Add Slack webhook sharing | Stack |
| outline_uiflow_001 | UI Flow | Add document creation wizard | Journey |

## Decomposition Strategies

| Strategy | Description | Best For |
|----------|-------------|----------|
| `stack` | Layer-by-layer (DB → API → UI) | CRUD, integrations |
| `domain` | Bounded contexts | Workflows, state machines |
| `journey` | User actions | UI flows, wizards |

## Artifact Formats

| Format | Components | Validation |
|--------|------------|------------|
| `nl` | Natural language | Manual |
| `gherkin` | Given/When/Then scenarios | Parser |
| `gherkin_api` | + OpenAPI spec | Parser + Schema |
| `full` | + SQL migration | Full stack |

## Commands

```bash
# See help
./scripts/run-decomposition-experiment.sh --help

# Dry run (no execution)
./scripts/run-decomposition-experiment.sh --task outline_crud_001_word_count --decomposition stack --artifacts full --dry-run

# Pilot (all models on first task)
./scripts/run-decomposition-experiment.sh --pilot

# Full experiment (432 runs)
./scripts/run-decomposition-experiment.sh --full

# Generate sample prompt for review
./scripts/generate-sample-prompt.sh
```

## Sample Prompt

A sample prompt (700 lines, 1,953 words) is generated at:
```
results/sample/prompt_sample.md
```

## Estimated Costs

| Mode | Runs | Est. Cost |
|------|------|-----------|
| Pilot | 3 | ~$17 |
| Full | 432 | ~$2,500 |

## Evaluation

```bash
# Evaluate a single run
python scripts/evaluate.py --run-dir results/outline_crud_001_word_count/stack_full/rep_1
```

Metrics:
- Tests pass
- Migration runs
- API works
- Artifact consistency

## See Also

- `../README.md` - Research overview
- `../QUICK_REFERENCE.md` - One-page cheat sheet
- `../literature-review.md` - Academic literature
- `../implications-aictrl.md` - Product recommendations
