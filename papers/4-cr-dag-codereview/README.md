# Paper 4 — Code Review as a DAG (local-LLM ensembles)

**Thesis (systems framing):** an explicit DAG of artefact-passing nodes is a useful way to
*construct and reason about* local-LLM code review. The contribution is the framework + a
map of the design space (topologies, node roles, axes of choice), with ablations that show
which coordinates move the decision metric.

**Status:** methodology-first. We are writing the framework now and using it to decide which
experiments actually describe the solution space — **results are not yet written** (most
current numbers are single-rep; headline claims await ≥3-rep confirmation).

## Contents
- `blog-post.md` — **primary deliverable**: engineering blog post (recall-first DAG review;
  what worked, what didn't, the silent eval bugs). *(written — Codex-drafted via `codex exec`,
  then fact-checked against the corrections)*
- `methodology.md` — framework, node roles, topology catalogue, design-space axes,
  methodological commitments, and the open-question frontier. *(written)*
- `experiment-design.md` — the planned sweep that covers the design space (which axes ×
  which levels, rep counts, success criteria). *(written)*
- `literature-review.md` — related work (3 clusters + positioning + refs). *(written)*

- `RESULTS.md` — held until multi-rep numbers exist. *(deferred)*

## Source material (this repo)
- `experiments/cr-skill-workflow/research/loop.md`, `FINDINGS.md` — research log + findings
- `experiments/cr-skill-workflow/research/RUNBOOK.md` / `.claude/skills/cr-experiment-runner.md`
  — delivery discipline + harness-integrity invariants
- `experiments/cr-skill-workflow/analysis/executive-summary.html` — figures/curves
- Google Sheet `Experiments` tab — per-experiment grid (with Faults/caveats column)
