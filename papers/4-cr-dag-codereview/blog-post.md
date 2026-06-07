# Code Review With a Local 12B Model: What a Recall-First, Multi-Pass Pipeline Did and Didn't Find

We wanted a boring answer to a practical question: can a local small model do useful code
review?

Not "summarize this PR." Not "sound like a reviewer." Real defect finding. The setup was
deliberately constrained: `gemma-12B`, one GPU, zero dollars per review, TypeScript review
tasks, and no frontier-model calls in the review loop. The interesting result was not that a
small model became a great reviewer. It did not. The interesting result was that workflow
shape mattered.

The short version: on our setup, single-pass review was recall-bound. The useful local-model strategy was
not to make one pass smarter. It was to run several decorrelated passes, repeat them, sample
hotter, and union the findings. Almost every model-side precision trick we tried bought
precision by throwing away too many true bugs.

## Why We Optimized F2

For this work, F2 was the decision metric: recall counts more than precision. False
positives are not free, but the first job of an automated reviewer is candidate discovery.
A missed bug can ship. A bad finding can be dismissed.

That makes single-pass review a poor shape for the problem. One model call has a hard
coverage ceiling. A filter that made the output look cleaner but removed half the real
defects was not a win. A noisy workflow that found many more real defects often was. Under
F2, recall is the game.

## Review as a DAG, Not a Prompt

The mental model that made the experiments tractable was to treat review as a directed
acyclic graph of artifact-passing nodes.

Model nodes call the LLM and spend the expensive budget. A model node can be a specialist
lens, such as security, correctness, concurrency, validation, or edge cases. It can be a
different framing, such as adversarial or incident-response review. It can also be a
verifier or judge, although those mostly disappointed us.

Script nodes are deterministic and effectively free. They can compute a coverage map from
earlier findings, query a knowledge graph, or, on a better benchmark, run tests and static
analysis. Exact work should not be handed to a probabilistic model if a deterministic
program can do it.

Finally, there is the terminal merge. `union` keeps everything after deduplication. `vote`
also keeps everything but annotates how many independent nodes found the same issue.
`judge` asks a model to filter the result. That terminal operator is not an implementation
detail. It decides whether the workflow is trying to maximize coverage, rank findings, or
prune output.

Once review is a DAG, the design space becomes explicit: model-call budget, breadth versus
depth, sampling temperature, directed versus independent resampling, external evidence, and
terminal merge strategy.

## What Moved the Needle

*Numbers below are single-run on one 20-task benchmark unless noted; treat any difference
under ~0.05 F2 as noise, not signal (see Caveats). The oracle was also revised mid-project,
so early and late figures aren't strictly comparable.*

The first useful shape was a five-specialist union panel. Each lens reviewed the same code
independently. The outputs were unioned. On the full expanded oracle, that single
five-node execution beat the previous "run three times and merge" baseline: full per-run
F1 moved from 0.204 for one baseline run and 0.355 for the union-of-three baseline to
0.439 for the five-specialist panel. Full recall moved from 0.13 to 0.45. (Single run; the
0.355→0.439 step is only marginally above the ±0.05 noise band, so read it as "clearly beat
one pass," not as a precise delta.)

The real-bug subset was harder. The panel found about half of the real defects (on the
post-revision real-bug subset), but precision was low: useful coverage, messy output.

The next improvement was depth. Adding more distinct lenses saturated quickly. Repeating
the proven lenses worked better. Gemma is stochastic; the same lens does not find exactly
the same bugs each time. If you union decorrelated repeats, you get more coverage.

The best run found 28 of 41 real bugs on the full 20-task set, with the highest full-set F2
we observed — though within run-to-run noise of the next-best configurations — from five
lenses resampled three times at hot temperature, unioned.

We then asked whether *directing* the resamples helps — telling later rounds what was
already found, via a computed coverage map, so they "look elsewhere." Once we fixed a bug
that had silently disabled it (see The Silent Eval Bugs) and tested it properly, **directed
coverage gave no benefit — it slightly hurt.** Steering a round off the bugs it would
otherwise re-find didn't get replaced by enough genuinely new ones. So that 28/41 came from
resampling and temperature, not from direction.

What *did* add coverage was decorrelating the rounds by **framing**: round 1 a neutral
auditor, round 2 an adversary assuming a hidden regression, round 3 a 3am-incident
responder. Same lenses, same code, different *stance* — and in a clean like-for-like
comparison it lifted real-bug recall (0.63 → 0.70) over the identical setup without framing.
Diversity across passes is the engine; framing is a near-free way to manufacture more of it.
(Single-rep, so it wants replication — but it's the one decorrelation axis beyond temperature
that clearly paid.)

Temperature was the cheapest lever. In single probe runs, hotter sampling (~1.1) appeared to
raise real-bug recall without obviously hurting precision, and cold sampling found fewer
distinct bugs — but we have not replicated this enough to rule out noise. This fits the broader lesson: once you are unioning repeated passes,
diversity is not a liability. It is the mechanism.

The winning pattern was simple: several defect-focused lenses, repeated; decorrelate the
repeats with **hotter sampling and per-round framing**; union the findings. (We tested
directing the repeats with a computed coverage map — it didn't help.)

## What Did Not Work

Most precision interventions failed under F2.

The LLM judge failed. A strict judge deleted almost everything. A softer judge still
dropped recall much faster than it improved precision.

Confidence gating failed. Gemma's self-reported confidence was not calibrated enough to be
useful. Raising the threshold mostly removed findings, including true positives. Precision
did not improve enough to offset the lost recall.

Consensus voting was real but not an F2 filter. Findings with more votes were more
trustworthy, so vote count is useful for ranking and triage. But thresholding on votes
gave up too many one-off true bugs. The held-out calibration picked "keep all" as the best
F2 choice.

Proof obligations also traded away recall. Asking each finding to include reproduction
steps and a failing test made the output cleaner, but the model became too conservative.

Thinking mode was the extreme version of that behavior. It produced very high precision in
the small probe, but almost no discoveries. As a discovery pass, it was a failure. It might
make sense as a final verifier fed specific candidates.

Knowledge-graph context was marginal. It could nudge precision by helping discount
low-impact or dead code, but it did not produce an F2 gain in this benchmark.

The pattern is important: model-side precision gates made the model quieter. They did not
make it reliably better at separating real defects from plausible false alarms.

Two more non-levers. **Aiming a lens directly at the hardest classes** — a dedicated
authorization / data-flow / cross-function prompt — didn't crack them: it scored 0 of 3
passes on the very authz bugs it was built for. Better *prompting* isn't the fix for the hard
tail. And a **static linter** (semgrep, broad rulesets) flagged essentially nothing across 28
files — because on this code both the misses and the noise are *semantic*, not the syntactic
patterns a linter sees. (The static checks that *would* help — strict-null, typed taint —
need a buildable, type-resolved repo, which isolated snippets deny.)

## The KG Lesson: Available Is Not Used

The knowledge graph was wired into the environment through `explore-context` and an MCP
tool. That did not mean the model used it.

The notes are blunt: Gemma only called `query_context` when the task prompt told it to. The
skill file alone was not enough for a 12B model. Even with explicit prompting, calls were
stochastic, with many reviews making no call at all. If KG evidence matters, fetch it with
a script node and inject it deterministically — though in our runs neither the model-driven
nor the deterministic-prefetch mode produced an F2 gain, so this is about reliability, not a
recovered win.

The general lesson: a tool that is merely available is not part of the workflow. Count
calls. Inspect traces.

## The Silent Eval Bugs

First, shared scratch contamination. A merge step read stale finding files from another
configuration. That inflated recall and agreement counts. The invariant that caught it was
simple: `votes <= number of model nodes`. When a workflow with too few nodes produced an
impossible vote count, the result was obviously corrupted. Without that invariant, the
numbers would have looked like progress. After fixing it and re-merging, affected figures
shifted materially — one configuration's real-bug recall fell from ~0.80 to ~0.68 — so treat
every absolute number here as post-correction.

Second, a fail-open template variable made a coverage-directed treatment a no-op. The
workflow intended to inject a structured coverage map into later rounds, but the prompt
referenced the wrong variable name. The model saw an unresolved placeholder instead of the
coverage context. The treatment did not fail. It silently became the control condition.

Third, line matching was too lenient. Findings with missing or malformed line references
could match too broadly. The methodology now requires file plus line proximity, and
unparseable line references do not match.

The engineering lesson is direct: the evaluation harness is part of the system under test.
Assert invariants, make treatments fail closed, and re-run surprising wins.

## The floor: what's reachable, and what isn't

Two facts about the limit. First, **there is no bug we *never* find** — pool enough diverse
passes and the union reaches every real bug in the set. The ceiling isn't *discovery*, it's
*reliability*. Second, that reliability is wildly uneven: a long tail of real bugs is surfaced
by **fewer than 5% of passes** — one review almost never catches them, which is exactly why
heavy resampling is the recall engine.

And the tail has a shape. The chronically-missed bugs are **authorization/scoping,
cross-function invariants, and data-flow** — defects you only see by tracing values and
permissions *across* the code. They aren't missed for want of a better prompt (we tried that
and it scored zero on them); they're missed because a single-file, single-pass read can't
trace them. The lever that would reach them is **execution and cross-file analysis** — running
the tests, resolving the types — which the isolated-snippet benchmark can't host. That's the
most consequential limitation, and the clearest direction for building this for real.

## How to read this against the vendor numbers

A warning that cuts both ways. Most published AI-review numbers are precision- or
"noise"-focused and rarely report recall at all; several are self-run and don't reproduce
(one vendor's 82% "catch rate" became 45% when a third party re-ran the same repositories);
and many use a "did the developer change the code" proxy instead of a defined oracle. We made
the opposite choices — report recall, split the oracle into all-findings vs user-impacting,
publish the levers that *failed*, and disclose our own evaluation bugs — because those are
what make a result checkable. That is the only sense in which this is "more rigorous": more
*transparent*, not more *capable*. We make no state-of-the-art claim, and on scale we are
behind the field: one model, one small benchmark, mostly single-run. (For the curious, an
ensemble-vote design like ours was also shipped and then *retired* by a major vendor at the
frontier-model tier — a reason to be specific that our bet is about *small local* models, not
a general claim.)

## Caveats

The numbers are not universal. Much of the exploration was single-rep, and the notes call
out roughly plus-or-minus 0.05 noise. Small differences are not discoveries.

This was one local model on one benchmark. The benchmark used isolated snippets, so we
could not run the project, run real tests, or apply static analysis with resolved imports.
That blocks the most promising precision nodes.

The oracle also changed during the work. The team split theoretical findings from real
user-impacting bugs and added confirmed false labels for hallucinated findings. Early and
late numbers need care. Part of the oracle was authored by a strong model that also appears
in our comparisons, which can inflate precision for that model — a circularity we did not
fully control, so we treat recall as the fair metric there.

## Takeaways for Engineers

If you are building local-model code review, do not start by writing one heroic prompt.
Start with a graph. Spend model budget on decorrelated discovery: multiple lenses, repeated
passes, hotter sampling, and a union terminal. Use vote counts for ranking, not filtering,
if recall is your objective. Move exact work into script nodes. If you have a KG, prefetch
the facts deterministically. If you have a buildable repo, run tests and static analysis
instead of asking the model to simulate them.

Most importantly, choose the metric that matches the product. If the tool must avoid
annoying developers, precision-heavy gates may be appropriate. If the tool's job is to
catch defects before they ship, optimize F2 and accept that a small local model is best
used as a high-recall candidate generator.

That is the practical result: Gemma-12B was not a clean reviewer. It was a cheap,
parallel, noisy bug candidate generator. With the right DAG, that was enough to find real
defects.
