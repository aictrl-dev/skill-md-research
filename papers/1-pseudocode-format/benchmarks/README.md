# Reproducibility Artifact

This directory packages everything needed to reproduce the evaluation results, statistics, and figures reported in *Pseudocode Beats Prose*.

## Quick Start

```bash
cd papers/1-pseudocode-format
bash benchmarks/run_all_evals.sh
```

The script takes ~2 minutes and requires no GPUs or API keys.

## Prerequisites

- Python 3.10+
- `pip install pandas numpy scipy matplotlib`

## What the Script Produces

| Output | Path |
|--------|------|
| Chart scores | `domains/chart/results-v2/scores_deep.csv` |
| Dockerfile scores | `domains/dockerfile/results/scores.csv` |
| SQL scores | `domains/sql-query/results/scores.csv` |
| Terraform scores | `domains/terraform/results/scores.csv` |
| Paper statistics | printed to stdout |
| Figures 1-4 | `paper/figures/fig{1-4}_*.pdf` |

## Pipeline Steps

1. **Extract** — Unzips `raw_outputs.zip` in each domain's results directory
2. **Evaluate** — Runs each domain's evaluator to score every LLM output against its rubric
3. **Clean up** — Removes extracted JSONs (zips are kept)
4. **Statistics** — Runs `paper/compute_stats.py` to compute all numbers reported in the paper
5. **Figures** — Runs `scripts/generate_figures.py` to produce publication-quality PDFs

## Skill-MD Dataset

The `skill-md-dataset/` directory provides the evaluation benchmark as a standalone artifact:

- 4 domains (chart, dockerfile, sql-query, terraform)
- 2 skill formats per domain (markdown, pseudocode)
- 3 tasks per domain (12 total)
- Evaluation rubrics (13-15 rules per domain)

See [`skill-md-dataset/README.md`](skill-md-dataset/README.md) for the dataset card.

## Documentation

- [`DATASHEET.md`](DATASHEET.md) — Gebru et al. (2021) datasheet for the Skill-MD dataset
- [`LICENSE-DATA`](LICENSE-DATA) — CC-BY-4.0 license for dataset artifacts
