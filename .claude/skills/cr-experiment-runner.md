---
name: cr-experiment-runner
description: Deliver code-review DAG experiments in experiments/cr-skill-workflow correctly — pre-flight config checks, verifying the treatment actually ran, post-run contamination/sanity invariants, and scoring/comparability discipline. Use when running or designing a cr-skill-workflow experiment or sweep, when a result looks surprising (inflated recall, impossible vote counts, suspiciously high scores), or when the user says "run a cr experiment", "run a sweep", or "why do these CR results look off". NOT for the domains/ skill-format paper experiments (use run-experiment for those).
---

# Run a cr-skill-workflow Experiment

Operator discipline for the gemma code-review **DAG** research in
`experiments/cr-skill-workflow`. Each rule here was paid for by a real bug or a
wasted run. Run experiments with `scripts/run-workflow.sh --exp <id> [--rep N] [--task ID]`;
score with `scripts/score.ts`. Research log / results history: `research/loop.md`.

This skill governs the AGENT running the sweeps — not the review model (whose
instructions live in the `code-review` / `explore-context` SKILLs).

## Step 1 — Pre-flight: config must match the hypothesis
- **Load MCP + skills ONLY if the experiment uses model-driven KG.** Otherwise set
  `mcp.aictrl.enabled:false` and `skills.paths:[]` in the experiment's `aictrl.jsonc`.
  Unused tool/skill docs cost ~2.5–3k tokens/node and ~1.5s GPU-idle/node for nothing.
- **Production-faithful KG = direct `aictrl run`** (the `code-review` skill mandates
  `query_context`), NOT the multi-node DAG harness — the DAG never triggers model
  tool-calls (proven 0/655). Don't try to make it.
- Confirm per-experiment `aictrl.jsonc`: `temperature`, `thinking`, `output`
  (`union` | `vote` | `<node>`), and that the AI-node count equals the intended DAG size.

## Step 2 — Verify the treatment actually ran (never trust the config)
- **KG run:** on a smoke task, confirm the tool fired —
  `grep -c permission=aictrl_query_context <log>` > 0, or the prefetch context is
  non-empty. Many "KG" runs fired the tool **0 times**.
- **thinking:** confirm enabled AND accept the cost — ~12× slower, collapses recall
  (perfect precision). Use only as a verification node, never discovery.
- **Script-node treatments** (kg-prefetch, coverage-map) now **fail-exclude** the task
  (`PR-<id>.failed.json`). After a run, check the excluded count — nonzero means the
  treatment was breaking, not that it "worked."

## Step 3 — Post-run sanity invariants (run BEFORE trusting any number)
- **`votes ≤ #AI nodes` and `nLenses ≤ #distinct lenses`** (`scripts/vote-analyze.ts`).
  More voters than nodes ⇒ scratch contamination (stale node files from another
  experiment got merged). This single check caught the worst bug of the project.
- Per-task scratch (`/tmp/cr-wf-scratch/task-<id>-rep-<rep>`) is shared across
  experiments; the harness now wipes it per task. If you bypass the harness, wipe it
  yourself or the `union`/`vote` glob merges other experiments' findings.
- Recover a contaminated run without GPU: `scripts/clean-remerge.ts --exp <id> --write`
  rebuilds the result from the experiment's own legit per-node files.

## Step 4 — Scoring discipline
- Relaxed match = **file + line ±5**, no severity. An unparsable/comma-list line does
  **not** match (don't reward vague locations).
- Track **both** full-set and real-set; **F2 (recall-weighted) is the decision metric**.
- **Comparability:** compare only runs on the **same task-set** AND **same harness**.
  Probe (5 tasks) ≠ full-20; direct-CLI ≠ DAG. Never cross those.
- **Single-rep deltas are noisy (±0.03–0.05)**, worse at low node counts. Decide
  keep/discard on 3-rep or full-20; use 5-task probes only to filter.

## Step 5 — Record
- One row per experiment in the Google Sheet `Experiments` tab (REAL per-run headline).
- Always fill the **Faults / Caveats** column: MCP-loaded-but-unused, PROBE n=5, 1-rep,
  contamination-status, circular-precision. A number without its caveat misleads.
- `answer-key.json` is **never-modify**. If the oracle needs edits, first add a
  file+line+verdict dedup guard to `merge-oracle-review.ts` (it is not idempotent).

## Pitfalls that have actually bitten us
- Shared scratch not cleaned → cross-experiment contamination → inflated recall/votes.
- `|| true` on a treatment node → silent run *without* the treatment.
- `overlap()` true on a null line → vague findings match anything.
- "MCP is on" ≠ "KG is used" — verify the call count.
- Comparing probe vs full-20, or DAG vs single-pass numbers.
- Trusting one rep at 3 nodes (exp-024 swung 0.295↔0.370 across draws).
