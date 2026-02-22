---
name: review-paper
description: Conduct a multi-perspective review of a research paper by assembling parallel reviewer agents with different expertise profiles.
---

# Review Paper

Simulate a review panel for a research paper by launching parallel expert agents, then synthesizing their feedback into prioritized action items.

## Review Panel Composition

Launch 3 parallel agents, each with a different persona:

### 1. ML/AI Researcher
Focus: methodology, statistical validity, related work coverage, novelty claims
- Are the experimental controls appropriate?
- Are effect sizes reported alongside p-values?
- Is the related work complete and fairly positioned?
- Are limitations and threats honestly discussed?

### 2. Practitioner Engineer
Focus: practical applicability, "so what" factor, clarity for non-academics
- Can someone implement this in their workflow tomorrow?
- Are the domain examples relatable to working engineers?
- Is the paper jargon-free enough for a tech blog reader?
- Are there concrete takeaways in the conclusion?

### 3. Evaluation/Benchmark Expert
Focus: evaluator design, metric validity, reproducibility
- Are the scoring rules well-defined and non-overlapping?
- Could another team reproduce the evaluation independently?
- Are there confounds between rules (correlated failures)?
- Is the failure rate metric appropriate vs alternatives?

## Synthesis Process

After all 3 reviewers complete:

1. **Identify consensus** — issues raised by 2+ reviewers are highest priority
2. **Categorize** — structural (missing section), numerical (wrong stat), narrative (unclear claim), cosmetic (formatting)
3. **Prioritize** — rank by impact on paper acceptance/clarity
4. **Create action items** — each item should be specific and actionable, not vague

## Common Issues Found in Empirical LLM Papers

- Missing per-rule/per-task granularity (only aggregate numbers shown)
- No concrete examples of model outputs (good and bad)
- Overstating effect sizes without practical significance discussion
- Insufficient description of evaluation methodology for reproducibility
- Related work as literature dump rather than positioning the contribution
- Missing cost/latency analysis (practitioners care about this)
- No guidance on when NOT to use the proposed approach

## Output Format

```markdown
## Consensus Issues (raised by 2+ reviewers)
1. [Issue] — [Specific action]

## Individual Reviewer Highlights
### Reviewer 1 (ML Researcher)
- ...

### Reviewer 2 (Practitioner)
- ...

### Reviewer 3 (Eval Expert)
- ...

## Prioritized Action Items
1. [Highest impact] ...
2. ...
```
