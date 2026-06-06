# cr-skill-workflow — Research Findings

Goal: push local Gemma 4 (gemma4:12b-cr) code-review F1 above the union-of-3 baseline
(0.355) with a single smarter DAG, within a 5 AI-node budget. Track full-set and
real-set (user-impacting bugs only) F1.

## Headline result

**exp-003 — 5-specialist UNION panel** (security / correctness / concurrency /
validation / edge-cases, each reviewing independently, findings unioned).

| metric | baseline (1 run) | union-of-3 baseline | **exp-003** |
|---|---|---|---|
| FULL per-run F1 | 0.204 | 0.355 | **0.439** |
| FULL union-of-3 F1 | — | 0.355 | **0.493** |
| FULL per-run recall | 0.13 | — | **0.45** |
| REAL per-run F1 | — | — | 0.295 |
| REAL per-run recall | — | — | **0.49** |
| REAL per-run precision | — | — | 0.21 |

A single 5-node execution (FULL F1 0.439) beats the old run-3×-and-merge trick
(0.355). Recall tripled. **Goal met on the full set.**

## The oracle was rebuilt (and it changed the question)

Reviewed all 100 original TRUE entries + 80 exp-003 novels by reading the real source
(one subagent per PR). Result:
- Only **38/100 original "TRUE" bugs are real** user-impacting defects; 62 are
  theoretical (audit-text inaccuracies, dead defensive code, naming/comments).
- Novels: **5 new real bugs** the oracle missed, 32 theoretical, 43 confirmed not-a-bug.
- Oracle now: **137 TRUE (43 real / 94 theoretical) + 246 FALSE**. The 43 not-a-bug
  novels became FALSE labels so hallucinations now cost precision. Every entry carries
  `impact` + `reason` provenance.

This split is why **real-set F1 (0.295) ≪ full-set F1 (0.439)**: the panel finds ~half
the real bugs (recall 0.49) but precision is only 0.21.

## What moves the needle — and what doesn't

| lever | effect on REAL-set F1 | verdict |
|---|---|---|
| 5-specialist union (exp-003) | 0.295 (0.386 on real-bug-rich tasks) | **best so far** |
| Diverse lenses unioned | recall 0.13→0.49 | the recall engine |
| Confidence threshold gate | only loses recall (gemma confidence uncalibrated) | ✗ useless |
| Strict judge node (exp-004) | 0.133 — deletes everything (R 0.49→0.08) | ✗ fails |
| Soft judge node (exp-005) | 0.241 — still drops recall > lifts precision | ✗ fails |
| Per-lens pruning | union beats every single lens; each adds unique TP | ✗ don't prune |
| Union-of-reps on real set | 0.277 < 0.295 — piles on FP | ✗ for real set |
| Static analysis (tsc/semgrep) | inapplicable — see below | ✗ N/A here |

## Why precision is capped (~0.26) and judges fail

Real-set FP come from the panel re-discovering **plausible-but-wrong patterns that are
exactly the oracle's FALSE traps**, and from firing on **"trap tasks"** (e.g. PR-101/103/
104/112: many FALSE entries, ~0 real bugs — any finding there is pure FP). gemma cannot
tell a real bug from a plausible-but-wrong one when judging a finding list, so judge/
filter nodes just delete volume (including real bugs). Precision needs an **external,
objective signal**, not more model reasoning.

## Why static analysis doesn't rescue it (here)

The natural external signal is static analysis. It is **not tractable on this benchmark**:
- `task-files` is 28 isolated snippets — no package.json/tsconfig/node_modules; imports
  don't resolve, so tsc/eslint can't run meaningfully.
- semgrep runs without resolution but catches *syntactic* anti-patterns; the oracle's real
  bugs are *semantic/logic* (TOCTOU, state machines, authz scoping, wrong queries) that
  pattern matchers miss.
- On a real compilable repo this lever would likely help precision a lot; on this
  isolated-snippet, semantic-bug set it does not apply. (Recommend: future benchmark
  should pin a buildable repo so tsc/eslint/semgrep nodes are usable.)

## KG (knowledge graph) note

`explore-context` + the `query_context` MCP tool are wired in and fire, but gemma only
calls the tool when the prompt explicitly instructs it, and even then stochastically
(~1 review in 3 — matches the cr-local-kg treatment's 3.53 avg/review). KG mainly helps
precision (drop callers=0 dead code), so it's a minor lever for the recall-strong /
precision-weak profile here; a deterministic KG-prefetch *script* node (inject callers/
impact) would be the way to use it reliably, and is the one external-signal lever that
*is* tractable on these snippets (the KG is pre-built). Left as the top future experiment.

## Conclusion

- **Winning shape: exp-003, the 5-specialist union panel.** Full-set F1 0.439 (per-run) /
  0.493 (union-of-3) — well past the 0.355 goal.
- **Real-set F1 plateaus ~0.30**, recall-strong/precision-weak. Every model-side precision
  lever tried (judge, confidence, pruning, union) fails or hurts. The real ceiling here is
  set by the model confusing plausible-but-wrong with real, which only an external signal
  can break — and the only tractable external signal on this snippet benchmark is the
  pre-built KG (a prefetch script node), the recommended next experiment.

## Precision phase — complete (with F2)

We added **F2** (recall-weighted, β=2) because in code-review triage a missed real bug
usually costs more than a false positive. F2 is the decision metric; it also **flips the
optimal strategy**: under F1, union-of-reps hurts the real set, but under F2 the recall-max
union-of-3 is clearly best.

**Winner (exp-003, 5-specialist union), both metrics:**

| | F1 | F2 |
|---|---|---|
| FULL per-run | 0.439 | 0.446 |
| FULL union-of-3 | 0.493 | **0.571** |
| REAL per-run | 0.295 | 0.387 |
| REAL union-of-3 | 0.277 | **0.425** |

**Every model-side precision lever was tried and none beats recall-max on F1 or F2:**

| lever (REAL-set) | F1 | F2 | precision | recall | novels | verdict |
|---|---|---|---|---|---|---|
| exp-003 union (recall-max) | **0.295** | **0.387** | 0.21 | 0.49 | 103 | best F1/F2 |
| exp-003 union-of-3 | 0.277 | **0.425** | 0.18 | 0.66 | — | best F2 |
| judge node (exp-004/005) | 0.13–0.24 | lower | high | ↓↓↓ | — | fails |
| confidence gate | ↓ | ↓ | flat | ↓ | — | useless |
| KG-prefetch (exp-006) | ~neutral | ~neutral | +.01 | ↓ | — | marginal |
| proof-obligation (exp-007) | 0.211 | 0.181 | **0.29** | 0.17 | **25** | best precision, worst recall |

**Final conclusion:** For Gemma-4-12B on this benchmark, **F1 and F2 are both maximised by
maximising recall** (exp-003 5-specialist union, merged over 3 runs). Every precision
intervention — filtering, confidence, KG context, proof-of-bug — trades away more recall
than it buys. The model's "is this real?" judgment is lossy in every form. **The proof
obligation (repro + failing test) is the standout for a different objective:** it cuts
hallucinations 4× (novels 103→25) and gives the best precision (0.29 real / 0.55 full), so
it is the config of choice if the goal is *"don't spam developers with false positives"*
rather than *"catch the most bugs."*

The only lever that could plausibly beat recall-max on F1 is **objective test execution
(H-012)** — replacing lossy model judgment with ground truth — which is runtime-blocked on
this isolated-snippet benchmark. **Top recommendation: re-run on a buildable, runnable repo**,
which unblocks both static-analysis nodes and test execution.

## Model baselines (single pass, vs full expanded oracle)

| model (1 review pass) | REAL F1 | REAL F2 | REAL P | REAL R (of 43) | FULL F1 | novels |
|---|---|---|---|---|---|---|
| Opus (precision circular*) | 0.730 | 0.665 | 0.87* | 0.628 (27) | 0.573 | 0 |
| Haiku 4.5 (honest) | 0.354 | 0.333 | 0.394 | 0.321 (13) | 0.381 | 12 |
| gemma-12B exp-003 union (5 calls) | 0.295 | 0.387 | 0.21 | 0.49 | 0.439 | 103 |
| gemma-12B exp-011 directed ×3 (15 calls, subset) | ~0.41 | ~0.58 | 0.27 | 0.82 | — | high |

*Opus's findings ARE the original oracle, so it structurally has ~no false positives —
precision is upper-bound, recall is the fair metric. Haiku 4.5 is the honest frontier-tier
reference (run as session subagents, did not define the oracle).

**Reads:**
- A single review pass — even by a strong model — catches only ~⅓ of the real bugs (Haiku
  13/43, recall 0.32; Opus 27/43 circular-favorable). One pass has a hard recall ceiling.
- Model strength shows up as **precision/cleanliness**: Haiku REAL P 0.39 / 12 novels vs
  gemma 0.21 / 103 novels. Stronger model ⇒ more trustworthy per finding.
- **On recall the cheap local ensemble competes/wins**: gemma 5-lens union ≈ Haiku single-pass
  on REAL F1 (0.30 vs 0.35) at $0; gemma directed-resampling (exp-011) far exceeds Haiku's
  single-pass recall (0.82 vs 0.32) — at 15× calls and low precision.
- **Implied best pipeline:** gemma directed-resampling panel as a high-recall generator →
  Haiku/Opus (or test execution) as the precision verifier. Cheap-generator + strong-verifier.

## Honesty caveats
- 5 of the 43 real-bug oracle entries were contributed by exp-003 itself (confirmed via
  independent code reading). exp-003's real recall is therefore mildly self-favorable;
  cross-experiment comparisons on the full 43-real oracle are fair going forward.
- Panel prompts are oracle-blind and bug-class-generic (no known bug referenced), so
  prompt-level overfitting to these 20 tasks is low. Numbers are micro-averaged over
  60 reviews (20 tasks × 3 reps).
