# KPI Target Experiment - Final Results

## Experiment Status

| Domain | Runs | Extraction Rate | Status |
|--------|------|-----------------|--------|
| SQL Query | 62/60* | 62/62 (100%) | Complete |
| Chart | 58/60 | TBD | Near Complete |

*Extra runs due to pilot files included

---

## Key Finding: KPI Target Framing Improves Quality

**Score improvement: +17.6% (9.41 → 11.06 out of 12)**

---

## SQL Query Domain Results

### Overall Summary

| Model | Baseline Score | Target Score | Score Δ | Baseline Tokens | Target Tokens | Token Δ |
|-------|---------------|--------------|---------|-----------------|---------------|---------|
| haiku | 9.35 | **10.87** | +1.51 (+16%) | 913 | 1104 | +21% |
| opus | 9.97 | **11.21** | +1.24 (+12%) | 858 | 951 | +11% |
| glm-4.7 | 8.61 | **11.06** | **+2.45 (+28%)** | 1382 | 1422 | +3% |
| glm-5 | 9.69 | **11.13** | +1.44 (+15%) | 1175 | 2022 | **+72%** |

### Statistical Summary

| Metric | Baseline | Target | Change |
|--------|----------|--------|--------|
| **Mean Score** | 9.41/12 | **11.06/12** | **+1.66 (+17.6%)** |
| Mean Tokens | 1079 | 1354 | +275 (+25.5%) |

### Per-Task Breakdown

| Model | Task | Baseline | Target | Token Δ | Score Δ |
|-------|------|----------|--------|---------|---------|
| haiku | 1 | 9.89 | 11.39 | +21% | +1.50 |
| haiku | 2 | 9.16 | 10.68 | +25% | +1.52 |
| haiku | 3 | 9.01 | 10.43 | +23% | +1.42 |
| opus | 1 | 10.17 | 11.50 | +9% | +1.33 |
| opus | 2 | 9.80 | 11.35 | -2% | +1.55 |
| opus | 3 | 9.93 | 10.71 | +35% | +0.78 |
| glm-4.7 | 1 | 9.35 | 11.17 | +14% | +1.81 |
| glm-4.7 | 2 | 9.10 | 11.14 | 0% | +2.05 |
| glm-4.7 | 3 | 7.39 | **10.85** | -1% | **+3.46** |
| glm-5 | 1 | 9.20 | 11.50 | +41% | +2.30 |
| glm-5 | 2 | 10.71 | 10.50 | +5% | -0.21 |
| glm-5 | 3 | 9.17 | 11.45 | +274%* | +2.28 |

*GLM-5 task 3 showed extreme token variance (some runs used 4000+ tokens)

---

## Hypothesis Validation

| Hypothesis | Result | Evidence |
|------------|--------|----------|
| H1: Target improves scores | **CONFIRMED** | +17.6% improvement across all models |
| H2: Target increases tokens | **PARTIALLY CONFIRMED** | +25.5% on average, but glm-4.7 showed minimal change |
| H3: Effect larger for weaker models | **CONFIRMED** | glm-4.7 (+28%) > haiku (+16%) > opus (+12%) |

---

## Key Observations

### 1. Quality Improves for ALL Models
- Every model showed score improvement (+1.2 to +2.5 points)
- Largest improvement: **glm-4.7 (+28%)**
- Smallest improvement: **opus (+12%)** - but opus had highest baseline

### 2. Effort-T Quality Trade-off Varies by Model
- **haiku**: More tokens (+21%) → better quality (+16%)
- **opus**: Slightly more tokens (+11%) → better quality (+12%)
- **glm-4.7**: Same tokens (+3%) → **much better quality (+28%)**
- **glm-5**: Many more tokens (+72%) → better quality (+15%)

### 3. GLM-4.7 Shows Most Efficient Improvement
- Only +3% more tokens but +28% better scores
- Suggests the KPI framing improved *focus* not just *effort*

### 4. Extraction Rate 100%
- 62/62 runs extracted successfully
- The "IMPORTANT: Output TEXT only" instruction fixed GLM tool-use issues

---

## The Intervention

Added to all prompts (both conditions for A/B validity):

```
IMPORTANT: Output your answer as TEXT only. Do NOT use file writing tools. 
Do NOT create files. Just output the content in text format using markdown code fences.
```

For target condition, also prepended:

```
## Performance Context

Your target for this task is to achieve 97% compliance (13.6/14 rules).

In previous evaluations:
- Baseline: 73% compliance
- Skill-enhanced: 77% compliance  
- Top-performing: 86% compliance

Your model family has historically achieved 76% compliance.

To reach the 97% target, pay particular attention to:
- Rule 7: LEFT JOIN only (~35% baseline)
- Rule 8: COALESCE nullable columns (~25% baseline)
...
```

---

## Conclusion

**KPI target framing significantly improves output quality** across all tested LLM models (+17.6% on average). 

The mechanism varies:
- Some models (haiku, glm-5) increase effort (more tokens)
- Some models (glm-4.7) improve focus (same tokens, better quality)
- Premium models (opus) show smaller gains due to higher baseline

This suggests that **motivation framing works for LLMs** similarly to how ambitious goals affect human performance - with individual variation in how the "motivation" manifests.

---

## Gemini 3.1 Pro Extension (February 2026)

Extended the main pseudocode vs markdown experiment to include **Gemini 3.1 Pro** (Google) as a 5th model / 3rd family.

### Experiment Setup

- **Model**: gemini-3.1-pro-preview via Gemini CLI (`gemini -p ... -m gemini-3.1-pro-preview --output-format json --sandbox false`)
- **Conditions**: none, markdown, pseudocode (same skill files as original experiment)
- **Domains**: chart, sql-query, dockerfile, terraform (all 4)
- **Tasks**: 3 per domain, 3 reps each = **108 runs total**
- **Runner script**: `research/kpi-target-experiment/scripts/run-gemini-experiment.sh`

### Results Summary

| Domain     | None FR | Markdown FR | Pseudocode FR |
|------------|---------|-------------|---------------|
| Chart      | 28.2%   | 2.7%        | 0.8%          |
| SQL        | 47.2%   | 0.3%        | 0.2%          |
| Dockerfile | 9.4%    | 3.4%        | 1.7%          |
| Terraform  | 29.9%   | 7.7%        | 6.0%          |
| **Pooled** | **28.7%** | **3.5%**  | **2.2%**      |

### Key Findings

1. **Largest skill lift of any model**: 28.7% → 2.2% (best skill), 92% relative reduction
2. **Lowest overall failure rate**: Gemini 3.1 Pro achieves 2.2% FR with pseudocode, the best of all 5 models
3. **Consistent pseudocode advantage**: positive direction in all 4 domains (delta range: 0.11 to 0.25)
4. **Near-perfect SQL compliance**: both skill formats achieve <1% FR on SQL (vs 47% baseline)
5. **Very tight HDI**: MDI width 8.5pp (MD) / 7.7pp (PC) — extremely consistent output
6. **P(FR < 10%)**: 97.2% (MD), 100% (PC)

### Impact on Paper

Adding Gemini increases the paper from 629 → **737 runs**, 4 → **5 models**, 2 → **3 families**.

Key updated pooled statistics:
- Skill vs none: 36.3% → 10.0% (Cliff's delta = 0.770, large)
- Pseudocode vs markdown: 11.4% → 8.5% (delta = 0.140, p = 0.003)
- Variance ratio: 1.70 (Levene F = 7.45, p = 0.007)

### Technical Notes

- Gemini CLI wrapper output includes `session_id`, `response`, `stats` fields; model response is inside `response`
- Some outputs contain Node.js warnings before JSON; parser finds first `{` to start JSON extraction
- Token fields: `input`, `prompt`, `candidates` (output), `thoughts` (thinking), `cached`
- jq `--rawfile` needed for capturing large outputs (vs `--arg` which silently truncates)

---

## Files

- Experiment design: `research/kpi-target-experiment/experiment-design.md`
- SQL results: `research/kpi-target-experiment/domains/sql-query/results/`
- Chart results: `research/kpi-target-experiment/domains/chart/results/`
- Gemini runner: `research/kpi-target-experiment/scripts/run-gemini-experiment.sh`
- Gemini pilot: `research/kpi-target-experiment/scripts/run-gemini-pilot.sh`
- Statistics: `research/kpi-target-experiment/scripts/compute_paper_stats.py`
- KPI target runner: `research/kpi-target-experiment/scripts/run-experiment.sh`
