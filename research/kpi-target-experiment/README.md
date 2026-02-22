# KPI Target Experiment

## Status: RUNNING

Started: 2026-02-22 14:50 GMT

### Experiments Running

| Domain | Runs | Status | Results |
|--------|------|--------|---------|
| sql-query | 60 | Running | `research/kpi-target-experiment/domains/sql-query/results/` |
| chart | 60 | Running | `research/kpi-target-experiment/domains/chart/results/` |

### Monitor Progress

```bash
# Check status
watch -n 30 './research/kpi-target-experiment/scripts/check-status.sh'

# Or manually:
echo "SQL: $(ls research/kpi-target-experiment/domains/sql-query/results/*.json | wc -l)/60"
echo "Chart: $(ls research/kpi-target-experiment/domains/chart/results/*.json | wc -l)/60"
```

### Estimated Time

- SQL: ~2-3 hours (60 runs x ~2 min avg)
- Chart: ~2-3 hours (60 runs x ~2 min avg)
- Total: ~3 hours (running in parallel)

---

## Experiment Design

### Hypothesis
Explicit performance targets (97%) with historical context increase agent effort (tokens) and may improve outcomes.

### Conditions Compared

| Condition | Description |
|-----------|-------------|
| markdown (baseline) | Task + Markdown skill (from original paper) |
| markdown+target | Task + Markdown skill + KPI context |

### The KPI Intervention

Prepended to all prompts:
```
IMPORTANT: Output your answer as TEXT only. Do NOT use file writing tools.

## Performance Context

Your target for this task is to achieve 97% compliance...

In previous evaluations:
- Baseline: 73% compliance
- Skill-enhanced: 77% compliance
- Top-performing: 86% compliance

Your model family has historically achieved 76% compliance.

Focus on these low-baseline rules:
- Rule 7: LEFT JOIN only (~35% baseline)
- Rule 8: COALESCE nullable columns (~25% baseline)
...
```

### Models Tested

| Model | Tier | Notes |
|-------|------|-------|
| haiku | economy | Fast, cheap |
| opus | premium | Best quality |
| glm-4.7 | standard | Chinese model |
| glm-5 | premium | Latest Chinese model |

*Note: glm-4.7-flash excluded due to ~40% failure rate*

### Tasks per Domain

**SQL Query (dbt):**
- Task 1: Customer revenue by channel (medium)
- Task 2: Subscription metrics (complex)
- Task 3: Product return rates (medium)

**Chart:**
- Task 1: GDP bar chart (simple)
- Task 2: AI model growth line chart (medium)
- Task 3: Cloud provider multi-series (complex)

### Metrics

| Metric | How Measured | Hypothesis |
|--------|-------------|------------|
| auto_score | Rule compliance | H1: Target improves |
| output_tokens | API response | H2: Target increases |
| effort_efficiency | score / tokens | Exploratory |

---

## File Structure

```
research/kpi-target-experiment/
├── README.md                     # This file
├── experiment-design.md          # Detailed design
├── scripts/
│   ├── run-experiment.sh         # Main runner
│   └── check-status.sh           # Progress checker
├── domains/
│   ├── sql-query/
│   │   └── results/              # SQL outputs
│   └── chart/
│       └── results/              # Chart outputs
└── analysis/
    └── (to be created)
```

---

## Analysis Plan (After Completion)

1. **Evaluate results** using domain evaluators
2. **Compare** markdown vs markdown+target
3. **Statistical tests:**
   - Paired t-test for scores
   - Paired t-test for tokens
   - Effect size (Cohen's d)
4. **Visualizations:**
   - Token distribution by condition
   - Score distribution by condition
   - Per-model effects
