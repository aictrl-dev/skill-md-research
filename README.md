# Pseudocode vs Markdown: Skill Format for LLM Instruction Compliance

Experiment comparing two formats for writing LLM coding skill instructions:

- **Markdown** — prose with tables, code examples, and checklists
- **Pseudocode** — Python dataclasses, enums, and typed validation functions

We measure instruction compliance: given a set of domain-specific rules encoded in both formats, which format produces more rule-conformant outputs?

## Experiment Design

**3 conditions** (no-skill, markdown, pseudocode) x **3 tasks per domain** (simple/medium/complex) x **N models** x **3 repetitions**

Each domain has 14 rules evaluated by automated checkers. The dependent variable is `failure_rate = 1 - (rules_passed / rules_scored)`.

## Domains

| Domain | Output Format | Auto-Scorable Rules | Description |
|--------|--------------|--------------------:|-------------|
| Chart (Vega-Lite) | JSON | 15/15 | Data visualization specifications |
| Commit Message | Plain text | 13/14 | Conventional Commits format |
| OpenAPI Spec | JSON/YAML | 13/14 | REST API specifications |
| Dockerfile | Dockerfile | 10/14 | Container build instructions |
| SQL Query | SQL | 8/14 | Analytical query style |
| Terraform | HCL | 8/14 | Infrastructure as Code |

## Repository Structure

```
domains/
  chart/                    # Original domain (Vega-Lite chart specs)
    skills/                 # Markdown and pseudocode SKILL.md files
    test-data/              # Task JSON files (3 tasks)
    results/                # Raw model outputs + scores.csv
  commit-message/           # Conventional Commits
  dockerfile/               # Docker best practices
  openapi-spec/             # OpenAPI 3.x specifications
  sql-query/                # SQL query style guide
  terraform/                # Terraform/IaC conventions

scripts/
  evaluate.py               # Chart domain evaluator (shared helpers)
  evaluate_deep.py          # Chart domain deep evaluator (15 rules)
  analyze.py                # Single-domain statistical analysis
  analyze_all.py            # Cross-domain aggregation + stats
  bootstrap_ci.py           # Bootstrap confidence intervals
  run-experiment.sh         # Original chart experiment runner
  run-domain-experiment.sh  # Multi-domain experiment runner

prompts/                    # Prompt templates (none/md/pc conditions)
paper/                      # LaTeX paper source (forthcoming)
```

## Running Experiments

### Prerequisites

- Python 3.11+
- `claude` CLI (Anthropic) or `opencode` CLI (for non-Anthropic models)
- API keys for target models

### Single Domain Run

```bash
# Run all conditions for a domain
./scripts/run-domain-experiment.sh --domain dockerfile

# Run a single model
./scripts/run-single-model.sh --domain dockerfile --model haiku
```

### Evaluate Results

```bash
# Score a single domain
python domains/dockerfile/evaluate_dockerfile.py

# Cross-domain analysis
python scripts/analyze_all.py
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
