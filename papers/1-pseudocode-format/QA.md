# Q&A: Anticipated Reviewer Questions

## Q: Are the repeated runs truly independent, or are they cached/deterministic?

**The runs are genuinely independent.** Every run has a distinct timestamp, session ID, UUID, token count, and inference duration, confirming separate API calls.

More importantly, **94% of (model, condition, task) cells produce different output text across repetitions**, even when their rubric scores are identical.

### Why do scores look identical on the violin plots?

29.8% of cells have zero score variance across repetitions. This is expected for two reasons:

1. **Discrete rubrics with ceiling effects.** Each domain uses 12-15 binary pass/fail rules. A 13-point rubric naturally produces ties — two different Dockerfiles can both score 12/13. Strong models (especially Opus) with structured prompts frequently hit the ceiling score.

2. **Structured prompts constrain the output space.** The no-skill condition has only 14% zero-variance cells, while Markdown (42%) and pseudocode (33%) have more — because the skill file narrows the range of plausible outputs. This is consistent with RQ5's finding that pseudocode reduces variance.

### Breakdown by model

| Model | Zero-Variance Cells | Notes |
|---|---|---|
| Haiku 4.5 | 25.0% | Moderate variation |
| Opus 4.6 | 66.7% | Highest — ceiling effects on structured tasks |
| GLM-4.7 | 13.9% | Healthy variation |
| GLM-4.7-flash | 7.4% | Most variable (includes some score=0 failures) |
| GLM-5 | 30.6% | Moderate variation |

### Breakdown by condition

| Condition | Zero-Variance Cells | Mean Score Variance |
|---|---|---|
| No skill (baseline) | 14.0% | 2.862 |
| Markdown | 42.1% | 1.931 |
| Pseudocode | 33.3% | 1.924 |

### Bottom line

Score-level ties are an artifact of coarse-grained binary rubrics, not API caching. The bootstrap CIs and RQ5 variance analysis are statistically meaningful — zero-variance cells produce zero-width CIs, which is a legitimate reflection of genuine consistency, not a methodological flaw.
