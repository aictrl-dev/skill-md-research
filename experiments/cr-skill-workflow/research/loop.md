# Code Review Research Loop

## Goal
Maximise per-run F1 for Gemma 4 (gemma4:12b-cr) on the 20-task benchmark.

**Baseline** (cr-local-kg treatment, relaxed F1):
- Per-run F1 = 0.204 | Union-of-3 F1 = 0.355
- TP = 34.5 | FP = 45 | FN = 241

## What you control
Edit files in `current/` only:
- `current/skills/code-review/SKILL.md` — for type-1 experiments (single session workflow)
- `current/prompt.md` — the task instruction for type-1 (optional; defaults to a generic review prompt)
- `current/dag.yaml` + `current/prompts/*.md.j2` — for type-2 experiments (chained calls)

Never modify: `answer-key.json`, task files, scoring scripts, or any file outside `current/`.

## Knowledge graph (KG)
`explore-context` is loaded for every experiment from `base-skills/` (shared
infrastructure), and the remote `aictrl` MCP provides the `query_context` tool.
**But gemma only actually calls `query_context` when the task prompt tells it to**
— the skill file alone is not enough for a 12B model. Put the KG instruction in
`prompt.md` (type 1) or the node prompt (type 2). Even then, calls are stochastic
(~1 review in 3 makes a call; this matches the proven cr-local-kg treatment,
which averaged 3.53 calls/review with many 0-call reviews). To raise KG usage,
make the prompt's KG step more forceful or move enrichment into its own DAG node.

## Iteration protocol
1. Read `research/results.tsv` to see what has been tried and what worked.
2. Propose ONE change to `current/` with a clear hypothesis.
3. Run probe: `bash scripts/run-research-loop.sh --eval --probe-only`
4. If probe F1 ≥ baseline × 0.90, run full sweep: `bash scripts/run-research-loop.sh --eval`
5. The loop script commits on improvement, reverts on regression.

## Target & budget
- **Goal: beat the union-of-3 trick (per-run F1 > 0.355) with a single DAG execution.**
- **AI node budget: ≤ 5 model calls per task.** Iterate on DAG *structure* within that budget.
- Recall is the bottleneck (baseline R=0.13, ~34/100 TRUE found). The lever is coverage:
  diverse passes unioned find more distinct true defects than identical reps.

## Hypotheses backlog (try in order)

1. ✅ **exp-001**: 4-step type-1 workflow (scan→enrich→filter→output). Probe F1 ~0.22–0.24.
2. ✅ **exp-002**: Two-pass union chain (pass2 hunts what pass1 missed; output:union).
3. 🔄 **exp-003**: 5-specialist UNION panel (security/correctness/concurrency/validation/
   edgecases, reviewed independently, output:union). Detailed 5-task probe: F1=0.333,
   P=0.455, R=0.263, novels=30 — recall ~2× baseline. Full sweep running.
4. **Next levers if exp-003 < 0.355:**
   - Replace weakest specialist lens with a duplicate of the strongest (measure per-lens TP).
   - Add a 5th-node "second look" that re-reads only high-density files for more recall.
   - Push specialists to be MORE exhaustive (raise finding volume → recall), accept lower P.
   - Precision guard: a final filter node OR confidence threshold to trim FP if P collapses.
   - KG-prefetch node feeding callers/impact into one review node (precision aid).

## Findings
- **exp-003 single-execution F1 ≈ 0.40 on full rep-1 (20 tasks)** — beats the 0.355
  union-of-3 baseline with ONE execution. Recall 0.40 (3× baseline), precision 0.40.
- **gemma confidence is uncalibrated.** `--min-confidence` sweep on exp-003 rep-1:
  conf≥0 F1=0.399, ≥6 0.387, ≥7 0.358, ≥8 0.234, ≥9 0.178. Raising the cutoff only
  loses recall; precision stays ~0.40 until ≥9 (where recall collapses). ⇒ Do NOT
  gate on self-reported confidence. Precision must come from INDEPENDENT signals:
  judge node, KG-verify (callers=0), or cross-specialist vote count (≥2 lenses agree).

## Oracle upgrade (2026-06-06) + REAL-set reframing
Reviewed all 100 original TRUE entries + 80 exp-003 novels by reading source.
- Original oracle: only **38/100 TRUE are real** user-impacting bugs; 62 are theoretical
  (audit-text, dead defensive code, naming). Novels: 5 real, 32 theoretical, 43 not-a-bug.
- Oracle now: **137 TRUE (43 real / 94 theoretical) + 246 FALSE** (the 43 confirmed
  not-a-bug novels became FALSE so hallucinations now cost precision).
- **exp-003 under upgraded oracle:** FULL per-run F1=0.439 (R .45/P .43); union-3=0.493.
  **REAL per-run F1=0.295 (R .49 / P .21)**; union-3 REAL=0.277 (WORSE — union piles on FP).

### Reframed target & lever
- **Optimize REAL-set per-run F1** (currently 0.295). Recall is already strong (0.49);
  **precision (0.21) is the bottleneck** — too many FP + theoretical findings.
- Union-of-reps HURTS the real set → a single precise execution beats merging. Drop the
  union-maximisation instinct; pursue precision.
- Precision levers (confidence is useless — see below): judge/filter node, KG-verify
  script node (dead-code drop), fewer sharper specialists, severity-gating to real-bug
  classes, or a final "is this user-impacting?" gate matching our real/theoretical rubric.

## Notes
- novels (findings matching no oracle entry) are NOT scored as FP under relaxed F1, but a
  high novel count = lots of unverified output. Track it; if recall stalls while novels
  balloon, the model is hallucinating rather than finding real bugs.
- Probes (5 tasks, 1 rep) are NOISY (saw 0.257 vs 0.333 on the same DAG). Use them only to
  filter; trust the full 20×3 sweep for keep/discard decisions.

## What has been tried
(see research/results.tsv)

## Constraints
- No oracle leakage: prompts must not reference known bugs or answer-key content
- Keep KG calls ≤ 8 per review to control latency
- Each experiment must run in ≤ 60 min total (20 tasks × 3 reps)
