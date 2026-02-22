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

### 2.1 Conditions (4 levels)

| Condition | Description | What the Model Receives |
|-----------|-------------|------------------------|
| **none** | Baseline | Task only, no skill |
| **markdown** | MD skill | Task + Markdown-formatted skill |
| **pseudocode** | PC skill | Task + Pseudocode-formatted skill |
| **pseudocode+target** | PC + KPI & history | Task + Pseudocode skill + Target framing |

### 2.2 The Target Intervention

For the `pseudocode+target` condition, prepend this to the prompt:

```
## Performance Context

Your target for this task is to achieve 97% compliance with the specification (13.5 out of 14 rules passing).

In previous evaluations on similar tasks:
- The baseline model achieved 57% compliance (8/14 rules)
- The skill-enhanced model achieved 86% compliance (12/14 rules)
- The top-performing model achieved 100% compliance (14/14 rules)

Your current model family has historically achieved 80% compliance (11.2/14 rules) on this task type.

To reach the 97% target, pay particular attention to:
- Rule 6: Scope must be from the allowed vocabulary (20% baseline pass rate)
- Rule 7: Gitmoji must be included after type (0% baseline pass rate)
- Rule 11: Signed-off-by footer is required (5% baseline pass rate)
- Rule 13: JIRA-style ticket reference format (5% baseline pass rate)

These 4 rules account for 80% of failures. Focusing on them will maximize your improvement.
```

### 2.3 Factorial Structure

| Factor | Levels | Count |
|--------|--------|-------|
| Condition | 4 (none, md, pc, pc+target) | 4 |
| Task | 3 (simple, medium, complex) | 3 |
| Model | 5 (haiku, opus, glm-4.7-flash, glm-4.7, glm-5) | 5 |
| Repetitions | 5 | 5 |

**Total new runs: 3 tasks x 5 models x 5 reps = 75 runs** (only the pc+target condition)

**Combined analysis: 4 conditions x 3 tasks x 5 models x 5 reps = 300 runs**

---

## 3. Hypotheses

| ID | Hypothesis | Direction | Metric |
|----|-----------|-----------|--------|
| H1 | pc+target produces higher compliance than pseudocode alone | One-tailed | auto_score (0-14) |
| H2 | pc+target produces more output tokens than pseudocode alone | One-tailed | output_tokens |
| H3 | pc+target produces longer reasoning than pseudocode alone | One-tailed | body_word_count |
| H4 | The target effect is larger for weaker models (economy tier) | Two-tailed | model_tier x condition interaction |
| H5 | The target effect is larger for complex tasks | Two-tailed | task_complexity x condition interaction |

---

## 4. Metrics

### 4.1 Primary Outcome Metrics

| Metric | How Measured | Hypothesis |
|--------|-------------|------------|
| **auto_score** | Count of 14 rules passing | H1 |
| **compliance_rate** | auto_score / 14 | H1 |

### 4.2 Effort Metrics

| Metric | How Measured | Hypothesis |
|--------|-------------|------------|
| **output_tokens** | From API response usage | H2 |
| **body_word_count** | Words in commit body | H3 |
| **reasoning_depth** | Number of "What:" details | H3 (exploratory) |

### 4.3 Derived Metrics

| Metric | Formula | Purpose |
|--------|---------|---------|
| **effort_efficiency** | auto_score / output_tokens | Quality per unit effort |
| **target_gap** | 13.5 - auto_score | Distance from target |
| **improvement_over_baseline** | (auto_score - baseline_score) / baseline_score | Relative gain |

---

## 5. Statistical Analysis Plan

### 5.1 Primary Comparison: pseudocode vs pseudocode+target

**Model:** Linear Mixed-Effects Model

```
auto_score ~ condition + model_family + model_tier + task_complexity +
            condition:model_family +
            condition:model_tier +
            condition:task_complexity +
            (1 | task) + (1 | model)
```

**Contrast of interest:** `condition[pseudocode+target] - condition[pseudocode]`

### 5.2 Effect Size

- **Cohen's d** for continuous metrics
- **Risk ratio** for binary outcomes (e.g., reaching 13+ rules)

### 5.3 Power Analysis

With 75 runs per condition (pseudocode vs pc+target):
- Detectable effect size at 80% power, alpha=0.05: **d = 0.46** (medium)
- We are powered to detect medium effects, not small effects

---

## 6. Implementation Plan

### 6.1 File Changes

1. **New skill directory:** `domains/commit-message/skills/commit-style-pseudocode-target/`
   - Contains SKILL.md with the target intervention prepended

2. **Modified runner:** `scripts/run-domain-experiment.sh`
   - Add `pseudocode+target` condition
   - Build prompt with performance context section

### 6.2 Runner Changes

Add to `build_prompt()` function:

```bash
pseudocode+target)
  local skill_content
  skill_content=$(cat "${PSEUDOCODE_SKILL_DIR}/SKILL.md")
  cat <<EOF
## Performance Context

Your target for this task is to achieve 97% compliance with the specification (13.5 out of 14 rules passing).

In previous evaluations on similar tasks:
- The baseline model achieved 57% compliance (8/14 rules)
- The skill-enhanced model achieved 86% compliance (12/14 rules)
- The top-performing model achieved 100% compliance (14/14 rules)

Your current model family has historically achieved 80% compliance (11.2/14 rules) on this task type.

To reach the 97% target, pay particular attention to:
- Rule 6: Scope must be from the allowed vocabulary (20% baseline pass rate)
- Rule 7: Gitmoji must be included after type (0% baseline pass rate)
- Rule 11: Signed-off-by footer is required (5% baseline pass rate)
- Rule 13: JIRA-style ticket reference format (5% baseline pass rate)

These 4 rules account for 80% of failures. Focusing on them will maximize your improvement.

---

Follow these ${domain_label} guidelines:

${skill_content}

---

${task_prompt}
EOF
  ;;
```

### 6.3 Execution Commands

```bash
# Run only the new condition (pc+target) for commit-message domain
./scripts/run-kpi-experiment.sh --domain commit-message --condition pseudocode+target

# Full run (all 4 conditions)
./scripts/run-domain-experiment.sh --domain commit-message
```

---

## 7. Expected Results

### 7.1 If Hypothesis is Confirmed

| Metric | pseudocode | pseudocode+target | Delta |
|--------|------------|-------------------|-------|
| auto_score | 11.2 | 12.5 | +1.3 (+12%) |
| output_tokens | 180 | 220 | +40 (+22%) |
| body_word_count | 65 | 85 | +20 (+31%) |

This would indicate that:
1. **Effort increases**: Models generate more tokens when given ambitious targets
2. **Quality improves**: Additional effort translates to better compliance
3. **Target framing works**: Similar to human goal-setting effects

### 7.2 If Null Result

| Metric | pseudocode | pseudocode+target | Delta |
|--------|------------|-------------------|-------|
| auto_score | 11.2 | 11.3 | +0.1 (NS) |
| output_tokens | 180 | 182 | +2 (NS) |
| body_word_count | 65 | 67 | +2 (NS) |

This would indicate that:
1. LLMs don't respond to motivation framing the way humans do
2. Performance is capped by model capability, not effort allocation
3. The skill format matters, but target-setting doesn't

---

## 8. Threats to Validity

| Threat | Severity | Mitigation |
|--------|----------|------------|
| **Prompt engineering confound** | High | Target text could be confounded with additional instruction. Counter: keep target text separate, same skill content |
| **Historical context may mislead** | Medium | The "80% past performance" is made up. Counter: use actual baseline data from existing runs |
| **Regression to mean** | Low | 5 reps per cell helps estimate true variance |
| **Model sensitivity to framing** | Medium | Test across 5 models in 2 families |
| **Single domain** | Medium | Start with commit-message, replicate to other domains if effect detected |

---

## 9. Timeline

| Step | Duration |
|------|----------|
| Create target condition skill | 30 min |
| Modify runner script | 30 min |
| Run 75 new experiments | 2-3 hours |
| Run evaluation | 10 min |
| Statistical analysis | 1 hour |
| **Total** | ~5 hours |

---

## 10. Extension: Multi-Domain Replication

If the effect is detected in commit-message domain, extend to:

| Domain | Rules | Baseline | Expected Effect |
|--------|-------|----------|-----------------|
| dockerfile | 15 | 45% | Larger (more complex rules) |
| terraform | 18 | 40% | Larger (more complex rules) |
| openapi-spec | 12 | 55% | Medium |
| sql-query | 10 | 60% | Smaller (simpler rules) |

---

## 11. Variations to Test

### 11.1 Target Levels

Test whether target magnitude matters:

| Condition | Target | Description |
|-----------|--------|-------------|
| target-80% | 80% | Achievable (current performance) |
| target-90% | 90% | Stretch (above current) |
| target-97% | 97% | Ambitious (near-perfect) |
| target-100% | 100% | Perfect (possibly demotivating?) |

### 11.2 Framing Variations

| Condition | Framing | Hypothesis |
|-----------|---------|------------|
| challenge | "This task is challenging, only 20% of models pass all rules" | May increase effort |
| competition | "You are competing against other models for the best score" | May increase effort |
| loss-aversion | "Don't lose points on rules 6, 7, 11, 13" | May focus attention |
| growth | "Your model has improved from 60% to 80%, keep growing" | May encourage effort |

---

## 12. Success Criteria

| Outcome | Interpretation | Publication Angle |
|---------|----------------|-------------------|
| H1 confirmed (target improves score) | Target-setting works for LLMs | "Ambitious goals improve AI agent performance" |
| H2 confirmed (target increases tokens) | Effort allocation is malleable | "LLMs allocate more compute when challenged" |
| H1 + H2 confirmed | Motivation framing is effective | "Goal-setting theory applies to AI agents" |
| Null results | LLMs don't respond to motivation | "Performance capped by capability, not effort" |
| Negative results | Target-setting backfires | "Overly ambitious targets degrade performance" |

All outcomes are scientifically valuable and publishable.
