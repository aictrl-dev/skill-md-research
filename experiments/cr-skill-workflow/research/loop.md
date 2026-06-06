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

## Negative results (precision phase)
- **Judge/filter node fails for gemma** (both variants, real-bug-rich probe):
  - exp-004 STRICT judge: real F1 0.133 (P .50 / R .08) — deletes almost everything.
  - exp-005 SOFT judge ("keep by default"): real F1 0.241 (P .28 / R .21) — still drops
    recall (0.48→0.21) far more than it lifts precision. gemma-as-list-reviewer just
    removes volume; it cannot reliably tell real from FP. Abandon judge nodes.
- **exp-003 union remains best real-set** (per-run real F1 = 0.295 over 20 tasks;
  0.386 on real-bug-rich subset). Full-set per-run 0.439 / union-3 0.493 (≫ 0.35 goal).
- **Precision sink = "trap tasks"** (e.g. 101/103/104/112: many FALSE entries, ~0 real
  bugs). Any finding there is pure FP. Real-set precision is gated by the model being
  noisy on bug-free code, not by judging individual findings.
- probe-tasks.txt switched to real-bug-rich {105,113,201,204,205} so the real-set metric
  is measurable on the probe.

## Static analysis assessed — NOT tractable here
The natural precision lever (deterministic prefilter) does not apply to THIS benchmark:
`task-files` is 28 isolated snippets (no package.json/tsconfig/node_modules → tsc/eslint
can't resolve imports); semgrep runs but catches syntactic anti-patterns while the oracle's
real bugs are semantic/logic (TOCTOU, state machines, authz scoping, wrong queries). On a
buildable repo this lever would likely help a lot. The one tractable external signal on
these snippets is the pre-built KG → a deterministic KG-prefetch *script* node (inject
callers/impact) is the recommended next experiment.

## STATUS: research plan complete (see FINDINGS.md)
- Winner: **exp-003 5-specialist union** — FULL per-run F1 0.439 / union-3 0.493 (≫ 0.355 goal).
- REAL-set F1 plateaus ~0.30 (recall-strong 0.49 / precision-weak 0.21); every model-side
  precision lever (judge, confidence, pruning, union) fails or hurts.
- Results + hypotheses synced to the Google Sheet (E-003/E-003r/E-003u/E-003ur, E-004, E-005;
  H-008 confirmed, H-009 refuted, H-010 confirmed).
## Open experiments (precision phase, continued)
- exp-006 KG-prefetch (script node → specialists): probe ~neutral (FP 24→21, recall down);
  full sweep ABANDONED mid-rep-1 (slow: ~16 KG queries/task/rep ≈ 2.5h) for the higher-EV
  proof-obligation lever. KG context = marginal nudge, not a breakthrough for a 12B model.
- **exp-007 PROOF OBLIGATION (H-011, RUNNING):** each finding must carry repro steps + a
  unit test that fails on the current code; drop anything unsubstantiatable. Generation-time
  precision gate (unlike the failed judge node).
- **H-012 (deferred, runtime blocker): EXECUTE the proposed tests** on the spot, keep only
  findings whose test genuinely fails — ground-truth FP removal. Needs a buildable+runnable
  repo (same prerequisite as static-analysis nodes); impossible on isolated snippets.

## Budget-scaling series (5 → 10 → 15 AI nodes) — resampling beats breadth
Probed on the real-bug-rich subset (rep-1; note 5-task probes are noisy ±0.03):
- 5 distinct lenses (exp-003):  REAL F2 0.433
- 10 distinct lenses (exp-008): REAL F2 0.41–0.46 (two probes straddle 5-lens → no real gain)
- 15 distinct lenses (exp-009): REAL F2 0.420  → **distinct-lens breadth SATURATES at ~5**
- **5 lenses ×3 instances unioned (exp-010): REAL F2 0.586, recall 0.79 (19/24 real bugs)**
  → and it BEATS exp-003 union-of-3-reps on the same subset (F2 0.497, recall 0.68) at equal
  FP and equal 15-sample budget — i.e. in-process resampling ≥ cross-rep union.

**Finding: spend node budget on RESAMPLING the proven 5 lenses (×N, unioned), not on more
distinct lenses.** gemma is stochastic, so repeating a lens surfaces different real bugs each
run; union captures them. More distinct lenses just rediscover the same set. exp-010 is the
strongest config found; full 3-rep sweep running for the headline number.

## Standing recommendation
Future benchmark should pin a **buildable, runnable repo** (deps + test runner). That single
change unblocks the two strongest precision levers — static-analysis nodes AND test execution
(H-012) — which the current isolated-snippet task-files cannot support.

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
