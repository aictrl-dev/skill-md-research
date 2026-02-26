# Pseudocode vs Markdown: Skill Format for LLM Instruction Compliance

Experiment comparing two formats for writing LLM coding skill instructions:

- **Markdown** — prose with tables, code examples, and checklists
- **Pseudocode** — Python dataclasses, enums, and typed validation functions

We measure instruction compliance: given a set of domain-specific rules encoded in both formats, which format produces more rule-conformant outputs?

## Repository Structure

This repo contains three research papers, each in its own folder:

```
papers/
├── 1-pseudocode-format/       # Original skill format experiment
│   ├── paper/                 # LaTeX paper source
│   ├── domains/               # 6 domain evaluators + results
│   ├── models/                # SQL model definitions
│   ├── scripts/               # Runner & analysis scripts
│   ├── prompts/               # Prompt templates (none/md/pc)
│   ├── experiment-plan.md     # Experiment design doc
│   ├── experiment-results.html
│   ├── evaluation-rubric.md
│   └── skill-comparison.md
│
├── 2-task-decomposition/      # Task decomposition research
│   ├── literature-review.md
│   ├── experiment-harness/    # Tasks, prompts, scripts, results
│   └── ...
│
└── 3-kpi-targets/             # KPI target experiment
    ├── paper/                 # Paper draft
    ├── domains/               # Chart, SQL, Dockerfile, Terraform
    ├── analysis/              # Analysis scripts & reports
    ├── RESULTS.md
    └── ...

literature-review.md           # Shared across papers
RESEARCH_STATUS.md             # Overall status tracker
```

## Experiment Design

**3 conditions** (no-skill, markdown, pseudocode) x **3 tasks per domain** (simple/medium/complex) x **N models** x **3 repetitions**

Each domain has 14 rules evaluated by automated checkers. The dependent variable is `failure_rate = 1 - (rules_passed / rules_scored)`.

## Domains (Paper 1)

| Domain | Output Format | Scored Rules | Description |
|--------|--------------|-------------:|-------------|
| Chart (Vega-Lite) | JSON | 15/15 | Data visualization specifications |
| Commit Message | Plain text | 14/14 | Conventional Commits format |
| OpenAPI Spec | JSON/YAML | 14/14 | REST API specifications |
| Dockerfile | Dockerfile | 13/14 | Container build instructions (1 manual) |
| SQL Query | SQL | 12/12 | Analytical query style |
| Terraform | HCL | 13/14 | Infrastructure as Code (1 manual) |

## Running Experiments

### Prerequisites

- Python 3.11+
- `claude` CLI (Anthropic) or `opencode` CLI (for non-Anthropic models)
- API keys for target models

### Single Domain Run (Paper 1)

```bash
# Run all conditions for a domain
./papers/1-pseudocode-format/scripts/run-domain-experiment.sh --domain dockerfile

# Run a single model
./papers/1-pseudocode-format/scripts/run-single-model.sh --domain dockerfile --model haiku
```

### Evaluate Results

```bash
# Score a single domain
python papers/1-pseudocode-format/domains/dockerfile/evaluate_dockerfile.py

# Cross-domain analysis
python papers/1-pseudocode-format/scripts/analyze_all.py
```

## Models Tested

| Model | CLI | Provider |
|-------|-----|----------|
| Claude Haiku 4.5 | claude | Anthropic |
| Claude Opus 4 | claude | Anthropic |
| GLM-4.7 | opencode | ZhipuAI |
| GLM-4.7 Flash | opencode | ZhipuAI |
| GLM-5 | opencode | ZhipuAI |

## Key Findings

Across 6 domains:
- **Pseudocode** consistently achieves the lowest failure rate
- **Markdown** improves over no-skill but less than pseudocode
- Effect is strongest on complex tasks (Task 3)
- Both skill formats help smaller models (Haiku) more than larger ones (Opus)

## License

MIT

## Citation

Paper forthcoming.
