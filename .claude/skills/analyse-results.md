---
name: analyse-results
description: Analyse experiment results using statistical methods appropriate for LLM benchmark comparisons — Mann-Whitney U, Cliff's delta, bootstrap CIs, per-rule breakdowns.
---

# Analyse Experiment Results

Compute and report statistical comparisons for LLM experiment data stored in `scores.csv` files.

## Data Loading Pattern

```python
import pandas as pd
import numpy as np
from scipy import stats

df = pd.read_csv("domains/{domain}/results/scores.csv")
df["model"] = df["model"].str.replace("zai-coding-plan/", "", regex=False)
df = df[df["model"] != "glm-4.7-flash"]  # Exclude from analysis
df["failure_rate"] = 1 - df["auto_score"] / df["scored_rules"]
```

For chart domain, use `fail_count / (pass_count + fail_count)` instead.

## Standard Analyses

### RQ1: Skill Presence Effect

Compare no-skill vs any-skill (markdown + pseudocode pooled):

```python
none = df[df["condition"] == "none"]["failure_rate"]
skill = df[df["condition"].isin(["markdown", "pseudocode"])]["failure_rate"]
U, p = stats.mannwhitneyu(none, skill, alternative="greater")
ratio = none.mean() / skill.mean()  # e.g. "3.5x reduction"
```

### RQ2: Format Comparison

Compare markdown vs pseudocode directly:

```python
md = df[df["condition"] == "markdown"]["failure_rate"]
pc = df[df["condition"] == "pseudocode"]["failure_rate"]
U, p = stats.mannwhitneyu(pc, md, alternative="less")  # one-tailed: PC < MD
delta = cliffs_delta(md.values, pc.values)  # positive = PC better
```

### Cliff's Delta

Use for effect size — better than Cohen's d for non-normal, bounded data:

```python
def cliffs_delta(x, y):
    nx, ny = len(x), len(y)
    count = sum(1 if xi > yj else (-1 if xi < yj else 0)
                for xi in x for yj in y)
    return count / (nx * ny)

def magnitude(d):
    ad = abs(d)
    if ad < 0.147: return "negl."
    elif ad < 0.33: return "small"
    elif ad < 0.474: return "medium"
    else: return "large"
```

### Bootstrap Confidence Intervals

For mean failure rate CIs:

```python
from scipy.stats import bootstrap
rng = np.random.default_rng(42)
res = bootstrap((values,), np.mean, n_resamples=10000,
                confidence_level=0.95, random_state=rng)
ci_low, ci_high = res.confidence_interval
```

### Variance Analysis (Levene's Test)

Compare variability between conditions:

```python
F, p = stats.levene(md_values, pc_values)
variance_ratio = md_values.var() / pc_values.var()
```

## Per-Rule Breakdown

Identify which specific rules drive aggregate differences:

```python
pass_cols = [c for c in df.columns if c.endswith("_pass")]
for col in pass_cols:
    rule = col.replace("_pass", "")
    rates = {}
    for cond in ["none", "markdown", "pseudocode"]:
        rates[cond] = df[df["condition"] == cond][col].astype(float).mean() * 100
    delta = rates["pseudocode"] - rates["markdown"]
    # Flag rules where |delta| > 10pp
```

For rate columns (SQL domain), use `_rate` suffix columns directly (already 0-1 scale).

## Reporting Format

Print results in a format easy to copy into LaTeX:

```
Domain    None%   MD%   PC%   delta   mag.   p
Chart     34.0    5.7   2.8   0.318   small  0.015
```

- Always report: sample sizes (n), means, test statistic, p-value, effect size with magnitude label
- Use one-tailed tests for directional hypotheses (RQ1: skill > none; RQ2: PC < MD)
- Use two-tailed tests for exploratory comparisons (cross-family)
- Report exact p-values, not just significance stars

## Red Flags to Check

1. **Correlated rules** — if two rules have r > 0.95, they may be measuring the same thing (e.g., SQL rules 2 and 5 both triggered by `SELECT * FROM source`)
2. **Ceiling effects** — if both conditions are >95% pass rate, the domain may not discriminate
3. **Extraction failures** — check `extraction_ok` column; >5% failure rate suggests prompt/parser issues
4. **Model-specific patterns** — always break down by model to catch Simpson's paradox
5. **Skill-induced complexity** — skill may hurt specific rules while helping overall (check per-rule for negative deltas)
