# Experiment Design: KPI & History Reference Effects on Agent Performance

## Status: DRAFT
## Date: 2026-02-22
## Hypothesis: Explicit performance targets with historical context increase agent effort (tokens) and improve outcomes

---

## 1. Research Question

**Does providing explicit KPI targets and historical performance context to an AI agent:**
1. Increase effort (measured by output tokens, reasoning length)?
2. Improve outcomes (measured by rule compliance score)?

This tests whether "motivation framing" — telling a model "your target is 97% and you achieved 80% before" — changes behavior, analogous to how ambitious goals affect human performance.

---

## 2. Experimental Design

### 2.1 Conditions (2 levels)

| Condition | Description | What the Model Receives |
|-----------|-------------|------------------------|
| **markdown** | Baseline | Task + Markdown-formatted skill (from original paper) |
| **markdown+target** | KPI + history | Task + Markdown skill + Performance context (target + history) |

### 2.2 The Target Intervention

For the `markdown+target` condition, we prepend this context before the skill:

```
## Performance Context

Your target for this task is to achieve 97% compliance (X.Y out of N rules).

In previous evaluations on similar tasks:
- The baseline model achieved 55% compliance
- The skill-enhanced markdown model achieved 80% compliance
- The top-performing model achieved 95% compliance

Your current model family has historically achieved 75% compliance on this task type.

To reach the 97% target, pay particular attention to:
- Rule X: [specific guidance] (~20% baseline)
- Rule Y: [specific guidance] (~25% baseline)
...

These rules account for 70% of failures. Focus on:
1. [Specific action item]
2. [Specific action item]
...
```

### 2.3 Domains Tested

| Domain | Rules | Markdown Baseline | Notes |
|--------|-------|-------------------|-------|
| **sql-query** | 14 | 77% (10.7/14) | dbt analytics pipeline |
| **chart** | 15 | 81% (12.2/15) | Visualization specification |

### 2.4 Factorial Structure

| Factor | Levels | Count |
|--------|--------|-------|
| Condition | 2 (markdown, markdown+target) | 2 |
| Task | 3 (simple, medium, complex) | 3 |
| Model | 5 (haiku, opus, glm-4.7-flash, glm-4.7, glm-5) | 5 |
| Repetitions | 5 | 5 |

**Total runs per domain: 2 x 3 x 5 x 5 = 150 runs**

---

## 3. Hypotheses

| ID | Hypothesis | Direction | Metric |
|----|-----------|-----------|--------|
| H1 | markdown+target produces higher compliance than markdown alone | One-tailed | auto_score |
| H2 | markdown+target produces more output tokens than markdown alone | One-tailed | output_tokens |
| H3 | The target effect is larger for weaker models (economy tier) | Two-tailed | model_tier x condition |
| H4 | The target effect is larger for complex tasks | Two-tailed | task_complexity x condition |

---

## 4. File Structure

```
research/kpi-target-experiment/
├── experiment-design.md          # This file
├── README.md                     # Quick start guide
├── scripts/
│   └── run-experiment.sh         # Experiment runner
├── domains/
│   ├── sql-query/
│   │   └── results/              # Output goes here
│   └── chart/
│       └── results/              # Output goes here
└── analysis/
    └── analyze_results.py        # Analysis script (to be created)
```

**Note:** Skills and test-data are read from the original `domains/` folder. Only results are written to our research folder.

---

## 5. How to Run

```bash
# Pilot: 1 run per model, task 1 only (~5 min)
./research/kpi-target-experiment/scripts/run-experiment.sh --domain sql-query --pilot

# Full experiment: 75 runs per domain (~2-3 hours)
./research/kpi-target-experiment/scripts/run-experiment.sh --domain sql-query
./research/kpi-target-experiment/scripts/run-experiment.sh --domain chart
```

---

## 6. Metrics

### 6.1 Primary Outcome Metrics

| Metric | Domain | How Measured |
|--------|--------|--------------|
| **auto_score** | sql-query | 0-14 rules, evaluate_sql.py |
| **pass_count / 15** | chart | 0-15 rules, evaluate_chart.py |

### 6.2 Effort Metrics

| Metric | How Measured | Hypothesis |
|--------|-------------|------------|
| **output_tokens** | From API response usage | H2 |
| **reasoning_tokens** | From API (if available) | H2 |

### 6.3 Derived Metrics

| Metric | Formula | Purpose |
|--------|---------|---------|
| **effort_efficiency** | score / output_tokens | Quality per unit effort |
| **target_gap** | 97% - actual_score | Distance from target |
| **improvement** | (target - baseline) / baseline | Relative gain |

---

## 7. Analysis Plan

### 7.1 Primary Comparison: markdown vs markdown+target

**Model:** Linear Mixed-Effects

```
score ~ condition + model_family + model_tier + task_complexity +
        condition:model_family +
        condition:model_tier +
        condition:task_complexity +
        (1 | task) + (1 | model)
```

### 7.2 Effect Size

- **Cohen's d** for continuous metrics
- Target: detect d = 0.5 (medium) at 80% power

---

## 8. Expected Results

### 8.1 If Hypothesis Confirmed

| Metric | markdown | markdown+target | Delta |
|--------|----------|-----------------|-------|
| score | 80% | 87% | +7pp |
| output_tokens | 500 | 650 | +30% |

### 8.2 If Null Result

| Metric | markdown | markdown+target | Delta |
|--------|----------|-----------------|-------|
| score | 80% | 81% | +1pp (NS) |
| output_tokens | 500 | 510 | +2% (NS) |

---

## 9. Success Criteria

| Outcome | Interpretation | Publication Angle |
|---------|----------------|-------------------|
| H1 confirmed | Target-setting works for LLMs | "Ambitious goals improve AI agent performance" |
| H2 confirmed | Effort allocation is malleable | "LLMs allocate more compute when challenged" |
| Null results | LLMs don't respond to motivation | "Performance capped by capability, not effort" |
