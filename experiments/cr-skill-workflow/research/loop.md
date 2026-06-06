# Code Review Research Loop

## Goal
Maximise per-run F1 for Gemma 4 (gemma4:12b-cr) on the 20-task benchmark.

**Baseline** (cr-local-kg treatment, relaxed F1):
- Per-run F1 = 0.204 | Union-of-3 F1 = 0.355
- TP = 34.5 | FP = 45 | FN = 241

## What you control
Edit files in `current/` only:
- `current/skills/code-review/SKILL.md` — for type-1 experiments (single session workflow)
- `current/dag.yaml` + `current/prompts/*.md.j2` — for type-2 experiments (chained calls)

Never modify: `answer-key.json`, task files, scoring scripts, or any file outside `current/`.

## Iteration protocol
1. Read `research/results.tsv` to see what has been tried and what worked.
2. Propose ONE change to `current/` with a clear hypothesis.
3. Run probe: `bash scripts/run-research-loop.sh --eval --probe-only`
4. If probe F1 ≥ baseline × 0.90, run full sweep: `bash scripts/run-research-loop.sh --eval`
5. The loop script commits on improvement, reverts on regression.

## Hypotheses backlog (try in order)

1. ✅ **exp-001**: Structured 4-step workflow (scan→enrich→filter→output) — did it beat baseline?
2. ✅ **exp-002**: Two-pass chain (pass 2 hunts for what pass 1 missed)
3. **Next**: KG pre-fetch node — inject callers/impact for all functions before the review model runs
4. Confidence threshold tuning — raise minimum confidence to reduce FP
5. Module-scope: cross-file summarisation before reviewing individual files
6. Iterative refinement: a third pass that only re-examines dropped candidates

## What has been tried
(see research/results.tsv)

## Constraints
- No oracle leakage: prompts must not reference known bugs or answer-key content
- Keep KG calls ≤ 8 per review to control latency
- Each experiment must run in ≤ 60 min total (20 tasks × 3 reps)
