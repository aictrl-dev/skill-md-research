# Experiment Plan: Structured Instruction Formats for AI Agent Performance

## Status: REFINED
## Version: 2.0
## Date: 2026-02-19

---

## 1. Background & Motivation

We ran an internal n=1 pilot comparing two formats for writing AI agent instructions:
- **Format A (Markdown prose)**: 148 lines of natural language with headings and bullet points
- **Format B (Python pseudocode)**: Comparable length using dataclasses, enums, and typed function signatures

The agent was a "story decomposer" that breaks user stories into stack-layer subtasks. Single-run results:

| Metric | Markdown (A) | Pseudocode (B) | Delta |
|--------|-------------|----------------|-------|
| Total tokens | 109,047 | 89,174 | -18.2% |
| Tool calls | 44 | 52 | +18.2% |
| Duration (s) | 272 | 305 | +12.1% |

This is suggestive but unpublishable: n=1, no controls, no statistical tests, confounded by single agent/task/run.

### Prior Art

Three bodies of work inform our design:

1. **Mishra et al. (EMNLP 2023)** — "Prompting with Pseudo-Code Instructions" tested 132 NLP tasks on BLOOM and CodeGen. Found +7-16 F1 points for classification and +12-38% ROUGE-L across all tasks when using pseudo-code prompts vs. natural language. Ablations showed code comments, docstrings, and structural clues all contribute. *Limitation*: tested on traditional NLP tasks, not agentic workflows with tool use.

2. **SkillsBench (arXiv 2602.12670, 2025)** — Benchmarked 86 tasks across 11 domains with 7,308 trajectories. Found curated Skills raise pass rate by +16.2pp but effects vary widely by domain (+4.5pp to +51.9pp). Self-generated Skills provided no benefit. Key design insight: 2-3 focused modules outperform comprehensive documentation (+18.8pp vs. -2.9pp). Used 5 trials per task for variance estimation.

3. **Zheng et al. (arXiv 2411.10541, 2024)** — "Does Prompt Formatting Have Any Impact on LLM Performance?" compared plain text, Markdown, YAML, and JSON across 6 benchmarks on multiple models. Found GPT-3.5-turbo showed >40% variation across formats; GPT-4 was more robust. IoU between optimal formats across model families was often <0.2, meaning format preferences do not transfer across models.

### Gap We Address

No study has systematically compared instruction formats for **multi-step agentic workflows** with tool use, output schema adherence, and real-world task complexity. Mishra et al. tested simple NLP prompts. SkillsBench tested skill presence vs. absence, not skill format. Zheng et al. tested prompt format but on standard benchmarks, not agent specifications.

---

## 2. Research Questions & Hypotheses

### Primary Research Questions

**RQ1 (Efficiency):** Does instruction format affect token consumption and cost in agentic workflows?

**RQ2 (Quality):** Does instruction format affect the functional correctness and completeness of agent outputs?

**RQ3 (Adherence):** Does instruction format affect how reliably agents follow structural and schema constraints?

**RQ4 (Generalization):** Do format effects generalize across agent types, task domains, and model families?

### Hypotheses

| ID | Hypothesis | Direction | Rationale |
|----|-----------|-----------|-----------|
| H1 | Skill conditions (markdown + pseudocode) score higher than no-skill baseline on 15-rule compliance | One-tailed | Tests the "harness effect" — do skills provide value beyond model defaults? |
| H2 | Pseudocode skill scores >= Markdown skill on compliance | One-tailed | Structured formats reduce ambiguity, type annotations create explicit contracts |
| H3 | Pseudocode skill produces fewer output tokens than Markdown skill | One-tailed | Structured formats constrain output shape, no repeated prose |
| H4 | The format effect (H2) holds across both model families (Claude + GLM) | Two-tailed | Zheng et al. found format preferences do not transfer (IoU < 0.2) |

---

## 3. Experimental Design

### 3.1 Independent Variable: Instruction Condition

Three treatment levels:

| Condition | Description | Key Characteristics |
|-----------|-------------|-------------------|
| **No skill** (baseline) | Task data + generic instruction, no style rules | Tests whether skills add value beyond model defaults |
| **Prose Markdown** | Natural language with headings, bullets, examples (159 lines) | Current industry standard for SKILL.md |
| **Python Pseudocode** | Dataclasses, enums, typed function signatures, docstrings (176 lines) | Leverages LLM code-understanding capabilities |

The no-skill baseline is critical: it isolates the "harness effect" (H1). Without it, we cannot distinguish whether skill format matters vs. whether having any skill matters.

**Format equivalence constraints (Markdown vs Pseudocode only):**
- Both formats encode identical semantic content (same 15 rules, same constraints, same examples)
- Line counts within 15% of each other
- Verified by independent review for semantic equivalence before experiment begins

### 3.2 Task Domain: Chart Specification

Single domain (chart generation) with 3 complexity levels:

| Task | Complexity | Chart Type | Data Points | Key Challenge |
|------|------------|------------|-------------|---------------|
| 1: GDP | Simple | Bar | 5 | Single series, clear comparison |
| 2: AI Models | Medium | Line | 8 | Log scale, annotation required |
| 3: Cloud Revenue | Complex | Multi-line | 24 (8x3) | Crossover detection, legend decision |

**Why chart specification?**
- Produces machine-verifiable output (JSON schema)
- 15 binary rules enable automated + manual scoring
- Context-free (no codebase dependency)
- Novel domain (visual output, not code generation)

### 3.3 Model Factor

Five models across 2 families and 3 capability tiers. This directly tests H4 (cross-model generalization) and addresses the Zheng et al. finding that format preferences don't transfer across model families (IoU < 0.2).

| Model ID | CLI Tool | Family | Tier | Rationale |
|----------|----------|--------|------|-----------|
| `haiku` | Claude Code | Claude | Economy | Tests whether pseudocode helps weaker models more |
| `opus` | Claude Code | Claude | Frontier | Tests ceiling effects at maximum capability |
| `zai-coding-plan/glm-4.7-flash` | OpenCode | GLM | Economy | Cross-family economy tier |
| `zai-coding-plan/glm-4.7` | OpenCode | GLM | Mid-tier | Cross-family mid-tier |
| `zai-coding-plan/glm-5` | OpenCode | GLM | Frontier | Cross-family frontier |

This matrix enables:

1. **Cross-family**: Do Claude and GLM respond to pseudocode the same way? (H4)
2. **Capability tier**: Does pseudocode help weaker models more than stronger ones?
3. **Economy vs Frontier**: Plot format effect size vs model capability

### 3.4 Repetitions

**3 repetitions per cell**.

Justification: single-turn chart generation has lower variance than multi-step agentic workflows. 3 reps is sufficient for estimating within-cell variance on this task type.

Temperature: fixed at model default (not 0, since we want ecologically valid results reflecting real usage). Record exact parameters for reproducibility.

### 3.5 Full Factorial Summary

| Factor | Levels | Count |
|--------|--------|-------|
| Condition | 3 (none, markdown, pseudocode) | 3 |
| Task | 3 (gdp, ai-models, cloud-revenue) | 3 |
| Model | 5 (2 Claude + 3 GLM) | 5 |
| Repetitions | 3 | 3 |

**Total runs: 3 conditions x 3 tasks x 5 models x 3 reps = 135 runs**

This is a focused design that maximizes signal-to-noise per dollar spent.

---

## 4. Metrics & Measurement

### 4.1 Automated Metrics (Primary)

| Metric | How Measured | Unit |
|--------|-------------|------|
| **Total tokens** | Sum of input + output tokens from API response | Integer |
| **Input tokens** | Tokens consumed by system prompt + instruction + context | Integer |
| **Output tokens** | Tokens generated by the model | Integer |
| **Tool calls** | Count of function/tool invocations | Integer |
| **Duration** | Wall-clock time from first API call to final output | Seconds |
| **Schema validation rate** | JSON output validated against JSON Schema per agent | Binary (pass/fail) per run |
| **Schema error count** | Number of schema violations in output | Integer |
| **Output completeness** | % of required output fields populated with non-empty values | Percentage |
| **Cost** | Tokens x per-token price | USD |

### 4.2 Output Quality Scoring (Human Evaluation)

**Blind evaluation protocol:**
- Evaluators see only the input task and the agent's output (not the instruction format that produced it)
- Each output scored by 2 independent evaluators
- Evaluators recruited from team members not involved in instruction authoring

**Rubric (5-point Likert scale):**

| Dimension | 1 (Poor) | 3 (Adequate) | 5 (Excellent) |
|-----------|----------|--------------|----------------|
| **Correctness** | Major factual errors, wrong decomposition | Minor issues, mostly correct | Fully correct, no errors |
| **Completeness** | Missing >50% of expected elements | Missing 1-2 elements | All expected elements present |
| **Actionability** | Output unusable without significant rework | Usable with some editing | Immediately actionable |
| **Structure** | Poorly organized, hard to parse | Reasonable organization | Clear, logical structure |

**Inter-rater reliability target:** Cohen's kappa >= 0.7 (substantial agreement). If kappa < 0.6 after calibration round, revise rubric and re-train evaluators.

**Calibration protocol:**
1. Both evaluators score the same 10 pilot outputs independently
2. Discuss disagreements, refine rubric interpretations
3. Score another 10 calibration outputs
4. Proceed to main evaluation only if kappa >= 0.7

### 4.3 Derived Metrics

| Metric | Formula | Purpose |
|--------|---------|---------|
| **Token efficiency ratio** | quality_score / total_tokens | Quality per token spent |
| **Cost-quality Pareto** | Plot cost vs. quality across formats | Identifies dominant strategies |
| **Normalized gain** | (metric_treatment - metric_control) / metric_control | Relative improvement, comparable across agents |
| **Consistency** | SD of quality scores across 5 reps | Reliability/predictability of format |

---

## 5. Statistical Analysis Plan

### 5.1 Primary Analyses

**Design structure:** Repeated-measures (within-subjects) across instruction formats, with agent type as blocking factor and task as nested within agent.

**Model:** Linear Mixed-Effects Model (LMM)

```
metric ~ instruction_format + model_family + model_tier + agent_type + task_complexity +
         instruction_format:model_family +
         instruction_format:model_tier +
         instruction_format:agent_type +
         (1 | task) + (1 | model)
```

- Fixed effects: instruction_format (3 levels), model_family (2: Claude, GLM), model_tier (3: economy, mid, frontier), agent_type (4 levels), task_complexity (3 levels)
- Key interactions: format x family (H5: do Claude and GLM respond differently?), format x tier (H6: do weaker models benefit more?)
- Random effects: task (nested in agent), model (nested in family)
- This handles the repeated-measures structure and the nested 2x3 model matrix

**Normality check:** Shapiro-Wilk test on residuals. If non-normal:
- For token/duration metrics: log-transform before analysis (these are typically right-skewed)
- For quality scores: ordinal logistic regression or Wilcoxon signed-rank as fallback

### 5.2 Pairwise Comparisons

For each metric, 3 pairwise comparisons:
1. Skill (md + pseudo pooled) vs. No-skill baseline (H1: harness effect)
2. Pseudocode vs. Markdown (H2: format effect)
3. Cross-model interaction (H4: does format effect hold across families?)

**Multiple comparison correction:** Bonferroni (alpha = 0.05 / 3 = 0.0167 per comparison)

**Effect sizes:**
- Cohen's d for continuous metrics (small: 0.2, medium: 0.5, large: 0.8)
- Cliff's delta for ordinal quality scores (non-parametric effect size)

### 5.3 Power Analysis

Based on our pilot data (18% token reduction):

**Parameters for token efficiency (primary outcome):**
- Expected effect size: Cohen's d = 0.5 (medium, conservative estimate)
- Alpha: 0.05 (two-tailed for quality, one-tailed for efficiency)
- Desired power: 0.80
- Design: paired (within-subjects)

**Required sample size per comparison:**
- Paired t-test, d=0.5, alpha=0.05, power=0.80: **n = 34 pairs**
- With Bonferroni correction (alpha=0.0167): **n = 48 pairs**

We have 32 tasks x 5 reps = 160 observations per format-model combination, well above the 48 required. Even analyzing at the task level (averaging over reps, n=32), we meet the uncorrected threshold and are close to the corrected one.

**For quality scores (ordinal, 5-point):**
- Wilcoxon signed-rank, medium effect, alpha=0.0167, power=0.80: **n = 52 pairs**
- We have 160 scored outputs per format-model combination, exceeding requirements

### 5.4 Sensitivity Analyses

1. **Exclude outlier runs** (>3 SD from mean on tokens or duration) and re-analyze
2. **Stratify by complexity**: test whether format effects differ for simple vs. complex tasks (interaction term)
3. **Model-specific analysis**: report results separately per model family
4. **Evaluator effects**: include evaluator as random effect in quality score models

### 5.5 Pre-registration

Before data collection begins:
- Pre-register hypotheses, analysis plan, and sample sizes on OSF (Open Science Framework)
- Commit the analysis scripts to the repository before running experiments
- Any deviations from pre-registered plan must be declared as exploratory

---

## 6. Practical Execution Plan

### 6.1 Setup (Done)

- Markdown skill written (159 lines)
- Pseudocode skill written (176 lines)
- 3 test tasks with JSON data files
- 15-rule evaluation rubric
- Semantic equivalence verified

### 6.2 Infrastructure

| Component | File | Description |
|-----------|------|-------------|
| **Runner** | `run-experiment.sh` | Iterates 135 combinations, calls CLI tools, saves results |
| **Evaluator** | `evaluate.py` | JSON validation + automated rule checks |
| **Analyzer** | `analyze.py` | Statistical tests + charts |

### 6.3 Data Collection

**135 runs** across 5 models. Single-turn prompts (not agentic).

Estimated token consumption per run: ~5,000 tokens (prompt + response)

| Model | Runs | Est. Cost |
|-------|------|-----------|
| haiku | 27 | ~$0.20 |
| opus | 27 | ~$5.00 |
| glm-4.7-flash | 27 | ~$0.15 |
| glm-4.7 | 27 | ~$0.80 |
| glm-5 | 27 | ~$2.00 |
| **Total** | 135 | **~$8** |

### 6.4 Evaluation

- 135 outputs scored automatically by `evaluate.py` (JSON validity, 5 automatable rules)
- All 135 outputs scored manually for visual rules (color, font, gridlines)
- At ~2 minutes per output: ~4.5 hours total
- Flag borderline cases for second evaluator

### 6.5 Analysis

| Step | Duration |
|------|----------|
| Run evaluate.py | 5 min |
| Manual scoring | 4-5 hours |
| Run analyze.py | 5 min |
| Review findings | 1 hour |

### 6.6 Total Timeline

| Phase | Duration |
|-------|----------|
| Pilot (5 runs) | 30 min |
| Full runs (135) | 2-3 hours |
| Evaluation | 4-5 hours |
| Analysis | 1-2 hours |
| **Total** | **~1 day** |

---

## 7. Data Contamination & Validity Threats

### 7.1 Threats and Mitigations

| Threat | Severity | Mitigation |
|--------|----------|------------|
| **Author bias** | High | Different authors write different formats; semantic equivalence review |
| **Task selection bias** | Medium | Tasks sourced from real work items, complexity-stratified, pilot-tested |
| **Evaluation bias** | High | Blind evaluation (evaluators don't see instruction format) |
| **Order effects** | Low | Randomized run order; each run is independent (no conversation history) |
| **Model training data contamination** | Medium | Our instructions are private/internal, never published; tasks are novel |
| **Overfitting to one model** | High | Test on 2+ model families |
| **API behavior changes during experiment** | Medium | Pin model version IDs; complete all runs for one model within 1 week |
| **Temperature/sampling variance** | Medium | 5 repetitions per cell; report variance alongside means |
| **Hawthorne effect on evaluators** | Low | Evaluators blind to hypotheses (they score outputs, not formats) |

### 7.2 What We Cannot Control

- Model weights may have been updated between our pilot and the experiment (mitigated by pinning model versions)
- API latency varies by time of day (duration metric has noise; report as secondary, not primary)
- Tokenization differences across model families mean raw token counts are not directly comparable cross-model (normalize by within-model baseline)

---

## 8. Publication Strategy

### 8.1 What to Share Publicly

| Shareable | Rationale |
|-----------|-----------|
| Instruction format templates (anonymized) | Core contribution; others need to replicate |
| Aggregated metrics (means, CIs, effect sizes) | Standard for academic publication |
| Statistical analysis code | Reproducibility |
| Task descriptions (anonymized) | Replicability |
| Evaluation rubric | Methodological contribution |
| General agent patterns (decomposer, reviewer, planner, designer) | Already well-known archetypes |

### 8.2 What to Keep Proprietary

| Proprietary | Rationale |
|-------------|-----------|
| Full instruction content (production versions) | Competitive advantage; our actual Skills |
| Internal agent architecture details | Product IP |
| Specific tool implementations | Product IP |
| Customer/project data in tasks | Privacy |
| Internal team structure / org details | Privacy |

### 8.3 Publication Format Options

| Format | Audience | Timeline | Pros | Cons |
|--------|----------|----------|------|------|
| **Blog post (recommended first)** | Practitioners, engineering leaders | Week 8 | Fast to publish, high reach, drives product awareness | Less credible, no peer review |
| **arXiv preprint** | Researchers, informed practitioners | Week 9 | Citable, establishes priority, no review wait | No peer review stamp |
| **Industry conference (EMNLP Industry Track, NeurIPS Datasets)** | Academic + industry | Week 10 + review cycle | Peer-reviewed credibility, networking | 4-6 month review cycle, might be rejected |
| **White paper / technical report** | Enterprise buyers, CTOs | Week 8-9 | Lead generation, detailed, no length limit | Narrow audience |

**Recommended approach: Blog post first, arXiv preprint second, conference submission third.**

### 8.4 Framing Without Revealing Architecture

The paper/post should be framed as:

> "We study how the format of agent instructions affects AI agent performance across multiple task types, comparing natural language Markdown, Python pseudocode, and hybrid formats."

This is a general contribution to the field of AI agent instruction design. The specific agents and tasks are examples; the methodology and findings generalize. We do not need to reveal that these agents are part of a specific product.

**Abstraction layers:**
- "Story decomposer" becomes "a task decomposition agent"
- "Code reviewer" becomes "a code analysis agent"
- "Test scenario planner" becomes "a test generation agent"
- "Feature designer" becomes "a requirements specification agent"

---

## 9. Design Rationale

### Why 135 Runs (Not 2,880)

The original v1 design called for 4 agents x 8 tasks x 6 models x 5 reps = 2,880 runs (~$4,100). This refined v2 design focuses on a single well-controlled domain (chart specification) with fewer but more meaningful runs:

| v1 Design | v2 Design | Change |
|-----------|-----------|--------|
| 4 agent types | 1 task domain (charts) | Focus on format effect, not agent variety |
| 3 formats (md/pseudo/hybrid) | 3 conditions (none/md/pseudo) | Replace hybrid with no-skill baseline |
| 6 models | 5 models | Drop mid-tier Claude (Sonnet) |
| 5 reps | 3 reps | Lower variance in single-turn tasks |
| 2,880 runs | 135 runs | 95% cost reduction |
| ~$4,100 | ~$8 | Executable immediately |

### Why This Is Still Publishable

- **No-skill baseline** enables the harness effect measurement (H1), which is novel
- **5 models across 2 families** enables cross-model analysis (H4)
- **3 reps x 9 cells per model** = 27 observations per model, sufficient for non-parametric tests
- **Automated evaluation** reduces human effort to borderline visual rules only
- If results are strong, scale up: add more tasks, more reps, more models

---

## 10. Success Criteria

The experiment is "successful" regardless of outcome direction. Both results are valuable:

| Finding | Implication | Publication angle |
|---------|-------------|-------------------|
| Skills help (H1 confirmed) | Skills provide measurable value over model defaults | "Skills raise compliance by X points — they're not just documentation" |
| Pseudocode >= Markdown (H2 confirmed) | Structured format is at least as good, possibly better | "Pseudocode skills match or beat prose — switch without risk" |
| Pseudocode uses fewer tokens (H3 confirmed) | Cost savings with equal quality | "Same quality, fewer tokens: pseudocode saves X%" |
| Format effect holds cross-model (H4 confirmed) | Universal recommendation | "Works on Claude and GLM alike" |
| No format difference (H2 null) | Format is preference, not optimization | "Format doesn't matter; focus on content quality" |
| Skills don't help (H1 null) | Model defaults are sufficient for this domain | "For chart generation, skills add no value" |
| Claude vs GLM differ (H4 null) | Format recommendations are model-specific | "Match your instruction format to your model family" |

---

## 11. References

1. Mishra, M., Kumar, P., Bhat, R., Murthy, R., Contractor, D., & Tamilselvam, S. (2023). Prompting with Pseudo-Code Instructions. *EMNLP 2023*, pp. 15178-15197. https://aclanthology.org/2023.emnlp-main.939/

2. SkillsBench: Benchmarking How Well Agent Skills Work Across Diverse Tasks. *arXiv:2602.12670* (2025). https://arxiv.org/abs/2602.12670

3. Zheng, Y. et al. (2024). Does Prompt Formatting Have Any Impact on LLM Performance? *arXiv:2411.10541*. https://arxiv.org/abs/2411.10541

4. TheAgentCompany: Benchmarking LLM Agents on Consequential Real World Tasks. *arXiv:2412.14161* (2024). https://arxiv.org/abs/2412.14161

---

## Appendix A: Checklist Before Starting

- [x] Markdown skill written (159 lines)
- [x] Pseudocode skill written (176 lines)
- [x] Semantic equivalence verified (15 rules in both formats)
- [x] 3 tasks created with JSON data files
- [x] Evaluation rubric finalized (15 binary rules)
- [x] No-skill baseline prompt designed (fair comparison)
- [ ] run-experiment.sh tested with pilot runs (1 per CLI tool)
- [ ] evaluate.py validated on sample output
- [ ] analyze.py validated on sample CSV
- [ ] Model access confirmed for all 5 models
- [ ] OpenCode CLI installed and working

## Appendix B: Recommended Analysis Tooling

- **Statistics:** R (lme4 for mixed models, effsize for Cohen's d) or Python (statsmodels, pingouin)
- **Visualization:** matplotlib/seaborn for figures, with publication-quality formatting
- **Data pipeline:** Structured JSONL logs -> pandas DataFrame -> analysis scripts
- **Reproducibility:** Seed all random number generators, version-lock all dependencies
