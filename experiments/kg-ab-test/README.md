# KG-Assisted Code Generation: A/B Experiment

## Hypothesis

GLM-5 via OpenCode produces better code with fewer tokens when it has access to the aictrl Knowledge Graph MCP tools, compared to vanilla file-based exploration.

## Design

A/B test on the same codebase (`kg-blog-update`), same model (`zai-coding-plan/glm-5`), same tasks.

- **Condition A** (Control): No KG MCP - GLM-5 uses only built-in tools (file read, grep, glob, bash)
- **Condition B** (Treatment): KG MCP enabled - GLM-5 also has access to 24 KG tools via `https://aictrl.dev/mcp`
- **1 run per task per condition** (pilot)

## Tasks (Real Backlog Issues)

| # | Difficulty | GitHub Issue | Task | Files Touched |
|---|-----------|-------------|------|---------------|
| 1 | Easy | [#477](https://github.com/byapparov/aictrl/issues/477) | Add `delete_feature` MCP tool | 1 |
| 2 | Medium | [#531](https://github.com/byapparov/aictrl/issues/531) | Org slug uniqueness validation | 2-3 |
| 3 | Hard | [#572](https://github.com/byapparov/aictrl/issues/572) | Move and Delete operations for Epic Tasks | 4-5 |

## Prerequisites

```bash
# 1. Authenticate OpenCode with aictrl MCP (one-time)
opencode mcp auth aictrl

# 2. Verify MCP is connected
opencode mcp list
```

No local backend or Neo4j needed — treatment condition uses production MCP at `aictrl.dev`.

## Running

```bash
# Full experiment (3 tasks x 2 conditions)
./run-experiment.sh

# Single task
./run-experiment.sh --task 1 --condition control
./run-experiment.sh --task 2 --condition treatment
```

## Analysis

```bash
# Extract token metrics from raw JSONL
./analysis/extract-metrics.sh

# Results table
cat analysis/report.md
```

## Scoring

Each task is scored on 5 dimensions (1-5 scale, max 25 points):

1. Compilability
2. Completeness
3. Pattern Adherence
4. Type Safety
5. Correctness

See `eval-rubric.md` for detailed criteria.
