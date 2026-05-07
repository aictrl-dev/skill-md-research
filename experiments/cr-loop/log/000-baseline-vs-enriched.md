# 000 — Baseline vs Enriched (single-run A/B across 10 PRs)

**Date:** 2026-05-06
**Skill version:** 0.1.0 (cr-loop-baseline)
**Model:** zai-coding-plan/glm-5.1
**Sample:** 10 PRs from `aictrl-dev/aictrl`, 83 labelled findings in answer key (extracted from `/reply-to-code-review` verdict sidecars)
**Variants:**
- **baseline** — title + body + diff
- **enriched** — same prompt + KG context block: linked issues (FIXES/CLOSES/IMPLEMENTS edges) + prior findings on changed files (across other PRs, with TRUE/FALSE verdicts)

## Per-PR results

| PR | Category | n_baseline | n_enriched | F1 baseline | F1 enriched | Δ F1 | Notes |
|---|---|---|---|---|---|---|---|
| 1776 | trivial | 0 | 0 | 0 | 0 | 0 | No findings either way; AK is empty (0 reviews ever recorded) |
| 1735 | trivial | 0 | 0 | 0 | 0 | 0 | Both variants produced no findings; 5 labels in AK missed |
| 1781 | medium | 1 | 0 | **0.250** | 0 | **−0.250** | **Regression** — baseline caught a TRUE/FIX, enriched produced zero findings |
| 1783 | medium | 0 | 2 | 0 | **0.444** | **+0.444** | **Biggest win** — enriched caught a TRUE/FIX baseline missed; +1 novel |
| 1782 | medium | 0 | 0 | 0 | 0 | 0 | Both produced no findings; 8 labels in AK missed |
| 1790 | medium | 0 | 0 | 0 | 0 | 0 | AK is empty (no verdicts recorded yet) |
| 1794 | large | 2 | 0 | 0 | 0 | 0 | Baseline produced 2 novel; enriched dropped to 0 findings (possible context-overload) |
| 1785 | large | 3 | 2 | 0 | **0.121** | **+0.121** | Baseline 3 novel (no AK match); enriched matched 1 TRUE/FIX + 1 novel |
| 1788 | noisy | 1 | 2 | 0.129 | 0.129 | 0 | Both caught the formatDuration day-rollover TRUE/FIX; enriched added 1 novel (softened actionableCount NIT) |
| 1803 | noisy | 2 | 2 | 0 | 0 | 0 | Both produced 2 novel findings each; no AK matches |

## Aggregate

| Variant | Mean precision | Mean recall | Mean F1 | Total TP | Total FP | Total novel |
|---|---|---|---|---|---|---|
| baseline | 0.20 | 0.021 | **0.038** | 2 | 0 | 7 |
| enriched | 0.30 | 0.042 | **0.069** | 3 | 0 | 5 |
| **Δ** | +0.10 | +0.020 | **+0.031** | **+1** | 0 | −2 |

## Decision-criteria check (from issue #1811)

| Criterion | Threshold | Result | Verdict |
|---|---|---|---|
| Treatment surfaces ≥1 TP-Material missed by baseline on ≥3 of 10 PRs | ≥3 | **1** (PR 1783 only) | ❌ not met |
| Treatment correctly suppresses ≥3 FP-Recurrent findings | ≥3 | **0** (no FPs raised in either variant in this run) | ❌ not applicable |
| Treatment doesn't introduce >1 new FP per PR on average | <1.0 | **0.0** | ✅ |
| Cost (tokens, latency) within 2× baseline | ≤2× | latency ~1.5×, prompt size ~1.05× | ✅ |

**Strict reading:** doesn't meet the proceed threshold for #1805/#1810 implementation.

## What this single-run signal hides — important caveats

### 1. The baseline skill is too conservative

7 of 20 runs produced **zero findings**. The skill's "filter aggressively" instruction is being interpreted as "almost always emit nothing." The answer key has 14+ labelled findings on most PRs and the model surfaces 0–2.

This is a **skill problem**, not a context problem. The aggregate F1 is dominated by zero-finding cases; small differences between variants get lost in the noise.

### 2. Run-to-run variance is large

We observed two PR 1788 baseline runs in this session:
- **First baseline (11:38):** raised `actionableCount` as MAJOR (FALSE/IGNORE in AK) AND `formatDuration` (TRUE/FIX) — F1 0.121, precision 0.50, **1 FP**.
- **Second baseline (13:06):** raised only `formatDuration` — F1 0.129, precision 1.00, **0 FP**.

Same skill, same prompt, same model, different output. **Single-run comparisons cannot distinguish small variant effects from sampling noise.**

The earlier-session enriched run on 1788 demonstrably *softened* the actionableCount finding from MAJOR/bug to NIT/consistency in response to the FALSE/IGNORE prior context — a real qualitative effect. But across 20 fresh runs, that effect doesn't show up in the F1 numbers.

### 3. Enriched dropped findings on PR 1794 and PR 1781 (regressions)

**PR 1794:** baseline produced 2 novel findings; enriched produced **0**. Possible cause: the enriched prompt is 76K chars; the model may have decided to be more conservative or context-overloaded.

**PR 1781:** baseline matched one TRUE/FIX; enriched produced 0. Same hypothesis.

Both regressions are small absolute counts (1–2 findings), but they're real and worth investigating. **Larger context isn't always better.**

## Qualitative observation that matters more than the F1

Across the answer key's 83 labelled findings, the most important signal is **PR 1788 actionableCount, qualitatively suppressed by enriched**. This is exactly the recurrence-check pattern we hypothesised — even though it doesn't budge a single-run F1, repeated across 1000+ PRs at production scale, suppressing repeat FPs is the noise reduction that matters.

The single-run experiment cannot prove or disprove this at meaningful significance. To get there we need:
1. **Multiple seeds per (PR, variant)** — average over 3–5 runs to dampen variance
2. **A skill that actually finds the AK-labelled findings** — the current minimal skill misses 80%+ of them
3. **Or:** drop F1 vs answer-key as the metric and grade qualitative outcomes (severity-softening, FP suppression) on a sample manually

## Recommendation

**Don't proceed to implement #1805/#1810/#1806 yet** based on this evidence alone. But **don't kill them either** — the qualitative signal is real, just buried under variance.

Three concrete next steps in priority order:

1. **Make the skill thorough enough to actually find the AK findings.** Either copy the production code-review skill (which dispatches Security/Consistency/Bug-Hunter subagents) and re-run, or relax the "filter aggressively" instruction. Without recall ≥ 0.3 on the baseline, variant deltas aren't measurable.

2. **3-seed averaging** — run each (PR, variant) 3 times, take the mean F1. Cuts the variance by ~√3 ≈ 1.73× and would have made the PR 1788 actionableCount-suppression visible across runs.

3. **Then iterate** — autoresearch-style loop (agent edits skill.md based on log/, runs all PRs, scores). With (1)+(2) in place, the loop has signal to chase.

Each of these is ~half a day. The whole experiment then becomes meaningful evidence for or against #1805/#1810 implementation.

## Files

- `pr-set.json` — 10 PRs
- `data/pr-{N}.json` — enriched per-PR data (bodies, diffs, bot reviews, verdicts)
- `answer-key.json` — 83 labelled findings
- `skill.md` — baseline cr-loop skill
- `runs/{N}/*.json` — 20 review runs with NDJSON traces
- `prompts/{N}/{baseline,enriched}.md` — exact prompts used
- `scripts/{enrich-pr-set,build-enriched-prompt,run-review,score,load-kg,run-all}.ts/sh` — harness

## Cost

| Resource | Total |
|---|---|
| Wall-clock | ~110 min for 20 runs (mostly serial) + ~5 min infra |
| Token cost | All runs reported cost: 0 (covered by zai-coding-plan subscription) |
| GLM API calls | 20 |
