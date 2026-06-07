# Experiment Design: Sweeping the DAG Code-Review Design Space

**Status:** design (no results). This document maps a planned experiment sweep onto the
design-space axes defined in `methodology.md` §4. Each experiment is specified as a varied
axis, its levels, the control it is compared against, the terminal operator, the replication
plan, and the success criterion. The intent is to *describe the solution space* — locate the
knees, the budget-neutral wins, and the precision ceiling — not to crown a single winner.

---

## 1. Principles (what makes a result count)

1. **One axis at a time.** Each experiment varies a single design-space axis; all other
   coordinates are held fixed. A comparison that moves two axes (e.g. framing *and* MCP
   availability) is treated as invalid for attribution.
2. **Same task-set, same harness.** Numbers are only compared within the same 20-task
   benchmark and the same execution path. Probe (5-task) vs full (20-task), and direct-CLI
   vs DAG-harness, are never compared across.
3. **Replication before claims.** Single-rep runs (±~0.05 on F2 at small node counts) are
   used only to *filter* candidates. Any reported claim requires **≥3 reps**, with the mean
   and a dispersion estimate; a difference smaller than the measured run-to-run spread is
   reported as null.
4. **F2 is the decision metric**, reported with the precision/recall pair and against both
   the full and real-bug oracle (`methodology.md` §5).
5. **Invariants are checked, not assumed.** Every run reports the harness-integrity
   invariants (e.g. `votes ≤ #model nodes`, excluded-task count) so a corrupted run is
   caught before it enters analysis.

---

## 2. Benchmark, oracle, budget

- **Corpus:** 20 TypeScript review tasks (service-layer code), file- and module-scoped.
- **Oracle:** dual — full set (all confirmed entries) and a real-bug subset (user-impacting,
  impact-tagged); FALSE entries present so hallucinations cost precision.
- **Budget unit:** model-node count per review (script nodes are free). Levels probed:
  1, 3, 5, 10, 15.
- **Replication:** 3 reps per cell for any claim; full 20 tasks (probes may use a 5-task
  real-bug-rich subset for filtering only).

---

## 3. The sweep

Each block names the open question (from `methodology.md` §6), the axis varied, the held-fixed
control, and the success test. "Status" records what exists so far without reporting outcomes.

### E1 — Breadth vs depth at fixed budget
- **Axis:** breadth (distinct lenses) vs depth (resamples of a lens), holding budget constant.
- **Levels:** at budget 15 — {15 distinct lenses} vs {5 lenses × 3 resamples}; secondary
  budgets 5 and 10 to locate the knee.
- **Control:** single pass (budget 1); union terminal throughout.
- **Success:** identify which mechanism yields more real-set recall per node, and the budget
  at which marginal recall flattens.
- **Status:** instantiated at single-rep (breadth saturation and a resampling comparison
  exist); needs 3-rep at the chosen budgets.

### E2 — Which decorrelation axis is most efficient, and do they stack?
- **Axis:** decorrelation kind — {topic lenses} vs {affective framings} vs {sampling
  temperature} — at equal node budget.
- **Levels:** temperature ∈ {0.3, 0.7, 1.1}; framing ∈ {neutral, persona-set}; topic = the
  5-lens panel. Stacking arm: framing × temperature on the same panel.
- **Control:** homogeneous panel at default temperature, union/vote terminal.
- **Success:** rank the three axes by recall gained per model node; determine whether framing
  and temperature (both **budget-neutral**) compose or interfere.
- **Status:** temperature isolated on the 15-node DAG (single-rep, suggestive); framing run
  only standalone at 5 nodes. The *stacked* framing×temperature 15-node arm is the current
  open item (a probe is in flight). Needs 3-rep.

### E3 — Does directing the resample beat independent resampling?
- **Axis:** carry-forward direction — {independent} vs {directed, free-text prior findings}
  vs {directed, structured coverage-map script node}.
- **Levels:** the three direction modes on `5 lenses × 3 rounds`, vote terminal, fixed temp.
- **Control:** independent resampling (no carry-forward) at the same budget.
- **Success:** does any direction mode convert rediscovery into fresh coverage (higher
  recall at equal budget)? Distinguish the *free-text* vs *structured* mechanism.
- **Status:** an earlier directed result exists but was probe/contaminated; the structured
  coverage-map injection was previously a no-op (template-variable defect) and is now
  corrected — so this question is **effectively untested** and is a priority. Needs 3-rep,
  clean harness.

### E4 — Is cross-voter agreement a usable triage signal?
- **Axis:** terminal operator — `union` vs `vote`, and a post-hoc threshold on `votes`.
- **Levels:** independent resamples with `vote`; sweep `min-votes ∈ {1..K}`; calibrate the
  threshold on a train split and evaluate held-out.
- **Control:** keep-all (`min-votes = 1`).
- **Success:** two separate criteria — (a) does a vote threshold improve **F2** held-out
  (precision lever)? (b) failing that, does vote rank real bugs above false positives well
  enough to be a **triage** aid (ranking metric, not F2)?
- **Status:** instantiated single-rep with a held-out calibrator; treat (a)/(b) as distinct
  outcomes. Needs 3-rep.

### E5 — Does heterogeneous capability beat a uniform layer?
- **Axis:** per-node heterogeneity — {homogeneous} vs {capability-mix: KG context on a subset
  of lenses} vs {stance-mix: a different framing per round}.
- **Levels:** KG on 0 / 2 / 5 of the lenses; framing-mix across the 3 rounds.
- **Control:** homogeneous panel, same budget/temperature/terminal.
- **Success:** does targeted external evidence (KG on a subset) capture most of its precision
  benefit while preserving recall, vs blanket use? Does stance-mix add recall over a uniform
  stance?
- **Status:** KG delivery characterised (model-driven vs prefetch) at single-rep; the *mix*
  (subset-KG, per-round framing) is planned. Needs 3-rep.

### E6 — The precision ceiling: can any model-side verifier raise it?
- **Axis:** verification — {none} vs {list-judge} vs {proof-obligation} vs {thinking pass}.
- **Levels:** apply each verifier to a fixed discovery panel.
- **Control:** the discovery panel with no verifier.
- **Success:** does any verifier raise precision **without** surrendering more recall than it
  buys (net F2)? Report the precision/recall trade explicitly.
- **Status:** judges, proof-obligation, confidence-gating, and thinking instantiated
  single-rep (all suggestive of a recall cost). Needs 3-rep to state as a result; this block
  is the empirical backbone of the "negative results" narrative.

### E7 — External execution (benchmark-gated, not runnable here)
- **Axis:** external evidence — {none} vs {static analysis} vs {test execution} as script
  nodes producing objective verdicts.
- **Blocker:** requires a **buildable, runnable** corpus; the present isolated-snippet
  benchmark cannot host these nodes.
- **Success criterion / status:** specified but **deferred**; its existence is the argument
  for the benchmark-design recommendation in §5.

---

## 4. Replication and statistics plan

- **Reps:** 3 per reported cell (resource-permitting 5 for the headline winner and the
  temperature axis). Report mean and min–max (or SD) across reps.
- **Detectability:** the observed single-rep spread is ~±0.05 F2 at small node counts. An
  effect must exceed the measured spread to be claimed; sub-spread differences are reported
  as null, explicitly.
- **Multiple comparisons:** the sweep tests several axes; we pre-register the primary metric
  (real-set F2) and treat all other slices (full-set, precision, recall, novels) as
  descriptive.
- **Ablation:** per-node findings are persisted so any single node can be scored in
  isolation, enabling clean re-merges without re-running the model.

---

## 5. Controls, validity, and benchmark recommendation

- **Internal validity:** one-axis-at-a-time; identical configs except the varied axis
  (verified by diffing experiment definitions, including the model config).
- **Harness integrity:** per-task scratch is isolated; treatment nodes fail-exclude on
  error/empty; matching rejects null/unparsable lines; the `votes ≤ #nodes` invariant is
  asserted per run. Each is a known historical failure mode and is checked, not assumed.
- **Construct validity caveats:** a portion of the oracle was authored by one of the
  baseline systems (circular precision for that baseline — report recall as the fair metric
  there); the real/theoretical split is a human judgement.
- **External validity:** one model, one corpus, one language. Generalisation claims are out
  of scope until a second model and/or corpus is added.
- **Benchmark recommendation (the consequential choice):** move to a **buildable, runnable**
  corpus. This single change unblocks E7 (static analysis + test execution as script nodes)
  — the external-evidence levers most likely to raise the precision ceiling that E6 probes —
  and is the highest-leverage item for future work.

---

## 6. Execution order

1. **E3 (direction, now-corrected coverage)** and **E2-stack (framing × temperature)** —
   highest information value on the recall side; both currently under- or un-tested cleanly.
2. **E6 (verifier battery, 3-rep)** — converts the single-rep negative results into stated
   findings; backbone of the narrative.
3. **E1 (breadth/depth knee, 3-rep at 5/10/15)** — the budget-allocation curve.
4. **E4 (vote-as-triage held-out)** and **E5 (heterogeneous mix)** — secondary levers.
5. **E7** — only after a buildable corpus exists.

Each step is a small, pre-specified sweep whose result lands as one row per cell in the
experiment grid, with the invariants reported alongside.
