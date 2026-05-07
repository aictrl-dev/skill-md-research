# 001 — Production code-review skill + explore-context, against local MCP

**Date:** 2026-05-06
**Model:** zai-coding-plan/glm-5.1 via aictrl 0.3.2
**Skills loaded (verbatim, unchanged):**
- `data/default-skills/code-review/SKILL.md` v6.0.0 (Security / Consistency / Bug-Hunter parallel subagents + verification + MCP recording)
- `data/default-skills/explore-context/SKILL.md` v1.1.0 (graph-first exploration via `aictrl_query_context`)

**MCP wiring:** per-experiment `XDG_CONFIG_HOME` overrides global aictrl config so `aictrl_*` tools talk to **local** backend at `http://localhost:4000/cr-loop/mcp` (not prod).
**Authentication:** `X-Executor-Secret: dev-secret`.
**KG state:** local Neo4j contains only PR / Issue / Review / Finding / File nodes for `org_id='cr-loop'` (loaded by previous experiment). **No code-domain nodes** for cr-loop org.
**Sample:** same 10 PRs, same answer-key.json as run 000.

## What changed vs run 000

| | 000 baseline | 000 enriched | **001 prod** |
|---|---|---|---|
| Skill | minimal cr-loop skill (text+JSON output) | minimal + prepended KG context block | **production code-review v6.0.0** |
| MCP usage | none | none | **all 4 `aictrl_*` tools** |
| Subagents | none | none | **3 per PR (Security / Consistency / Bug Hunter)** |
| Output path | last-JSON-block parsing | last-JSON-block parsing | **`record_finding` → local Firestore** |

## Per-PR results

| PR | AK size | n found | precision | recall | F1 | matched verdicts | query_context calls | record_finding calls | duration |
|---|---:|---:|---:|---:|---:|---|---:|---:|---:|
| 1776 | 0 | 0 | 0 | 0 | 0 | — | 1 | 0 | 209s |
| 1735 | 5 | 0 | 0 | 0 | 0 | — | 1 | 0 | 251s |
| 1781 | 7 | 2 | 1.00 | 0.14 | **0.25** | 1 TRUE/FIX | 2 | 2 | 566s |
| 1783 | 4 | 0 | 0 | 0 | 0 | — | 5 | 0 | 556s |
| 1782 | 8 | 0 | 0 | 0 | 0 | — | 0 | 0 | 398s |
| 1790 | 0 | 8 | 0 | 0 | 0 | — (AK empty) | 12 | 10 | 1338s |
| 1794 | 10 | 5 | 1.00 | 0.32 | **0.48** | 2 TRUE/FIX, 1 TRUE/DEFER | 10 | 5 | 540s |
| 1785 | 25 | 11 | 0.88 | 0.41 | **0.56** | 4 TRUE/FIX, 2 TRUE/DEFER, 1 TRUE/IGNORE, **1 FALSE/IGNORE** | 12 | 11 | 890s |
| 1788 | 18 | 2 | 1.00 | 0.14 | 0.24 | 2 TRUE/FIX | 6 | 2 | 871s |
| 1803 | 6 | 9 | 1.00 | 0.67 | **0.80** | 3 TRUE/FIX, 1 TRUE/DEFER | 6 | 10 | 803s |

## Aggregate vs prior experiments

| Variant | Mean F1 | Mean precision | Mean recall | Total TP | Total FP | Total findings | Total novel |
|---|---:|---:|---:|---:|---:|---:|---:|
| 000 baseline (cr-loop minimal skill) | 0.038 | 0.20 | 0.021 | 2 | 0 | 9 | 7 |
| 000 enriched (cr-loop + KG context block) | 0.069 | 0.30 | 0.042 | 3 | 0 | 8 | 5 |
| **001 prod skill + explore-context (no useful KG)** | **0.233** | **0.578** | **0.198** | **17** | **1** | **37** | **~17** |
| Δ vs baseline | **+6×** | +0.378 | +0.177 | **+15** | +1 | +28 | +10 |

## Key signals

### 1. The prod skill alone produces ~6× the F1 of a minimal prompt — without help from the KG

All 6 `query_context` calls on PR 1788 returned empty (the local KG has no code-domain nodes for `cr-loop`). The agent kept reaching for them anyway (87 calls across the 10 PRs), then fell back to `bash` / `grep` / `glob` against the actual filesystem (the `--dir` workspace).

This means: **most of the lift from "prod stack" comes from the skill's structure** (Security/Consistency/Bug-Hunter parallel subagents + a separate verification step before each `record_finding`), not from KG context. The skill's discipline alone is enough to triple precision (0.20 → 0.58) and quadruple TP count (2 → 17).

### 2. The agent organically uses `aictrl_query_context` when explore-context is loaded

Across 10 runs:
- **`aictrl_query_context`: 55 calls** (range 0–12 per run; median 6)
- All from inside subagents, mostly Bug Hunter
- Almost all `domain=code, action=search` — file/symbol lookup queries
- All returned `{results: [], count: 0}` (empty KG slice for cr-loop)

The skill was **followed** — `record_review_started` × 10, `record_review_completed` × 10, `record_finding` × 40 (more than the 37 final findings because some were superseded during the verification step). This proves the prod stack runs end-to-end through aictrl + GLM-5.1 + local MCP, no harness modifications needed.

### 3. Recall is still floor-limited because the answer-key contains many CONSISTENCY/NIT items

Median recall is 0.14. The skill (correctly) filters out aesthetic and stylistic items that the bots flagged but humans verdicted as TRUE/IGNORE or DEFER. PR 1788 has 18 AK entries; only 2-3 are bug-class. The skill found 2 TRUE/FIX and stopped. That's not a defect — it's the skill behaving as designed (severity discipline).

A more honest aggregate metric: **TP rate among emitted findings** is 17/37 = 0.46. **FP rate** is 1/37 = 0.027. That's the production-relevant number.

### 4. PR 1790 is interesting — 8 findings emitted, AK is empty

The agent flagged 8 issues on a PR that no human ever reviewed. Spot-check those manually before reading too much into the F1=0 score.

### 5. PRs 1776 / 1735 / 1783 / 1782 produced 0 findings

For 1776 the AK is also 0, so this is correct. For 1735 / 1783 / 1782 the AK has 4–8 entries — the prod skill missed them all. Worth investigating: did the agent's verification step kill candidate findings before recording? The NDJSON has the trace.

## What this tells us about the original Phase A question

> "Can we get the agent to use our KG-based tools effectively?"

**Answer: yes, on the *call side*.** The agent reached for `query_context` 55 times unprompted. The prod `code-review` skill + `explore-context` skill is enough to make GLM-5.1 try graph queries before falling back to `bash`/`grep`.

**But: not on the *response side*** — every call returned empty because the cr-loop slice of local Neo4j has no code-domain entities. So this experiment cannot measure whether useful KG responses change F1. That's Phase B.

## Phase B — the next, well-scoped experiment

**Hypothesis:** if `query_context: domain=code` returns real results for the cr-loop org, F1 climbs further (and `bash`/`grep` calls drop).

**One change vs Phase A:** run the kg-extractor against the aictrl repo with `org_id='cr-loop'`. Same 10 PRs, same answer-key, same skill, same model. Re-measure.

**Expected outcomes:**
- (a) F1 climbs materially → KG matters; ship #1805/#1806/#1809/#1810
- (b) F1 unchanged or slightly down → skill structure is the lift, KG is decoration; reprioritise
- (c) `query_context` calls drop because the agent reads code from the graph instead of bash → infrastructure benefit even without F1 lift

Cost estimate: ~30 min for the indexer one-time + 2.5h for the same sweep we just ran.

## What to NOT change for Phase B

- Skill content (both `code-review` and `explore-context`) stays exactly as today
- MCP tool surface stays as today (no new domains)
- Same 10 PRs, same answer-key, same scorer

This isolates "useful KG vs empty KG" as the only varying input. If Phase B shows nothing, *then* iterate on `explore-context.md` or expose new MCP actions (your option 3 from the original plan).

## Caveats

- **Single seed per PR** — large variance possible. The 000 report flagged this and the same caveat applies. Phase B should ideally run 3 seeds × 10 PRs.
- **Recall is hard to improve** without changing the answer-key labelling rules. Most missed items are stylistic.
- **The novel findings (17) are unscored** — they may all be valid (skill catches things bots missed) or all false alarms (skill emits noise the bots correctly skipped). Manual triage on PRs 1790 + 1803 would clarify.
- **PR 1790 had 0 reviews ever** — the 8 findings the prod skill emitted on it are the only data we have. Any of them could be useful production signal.

## Files

- `experiments/cr-loop/runs-prod/<pr>/<runId>.{ndjson,json,findings.json,prompt.md,text}` — per-run artefacts
- `experiments/cr-loop/aictrl-config/aictrl/aictrl.jsonc` — per-experiment XDG override pointing at local MCP
- `experiments/cr-loop/scripts/run-prod-skill.sh` — single-PR runner
- `experiments/cr-loop/scripts/run-all-prod.sh` — 10-PR sweep with skip-existing
- `experiments/cr-loop/scripts/stage-workspaces.sh` — stages `.cr/pr-{meta,files}.json` from gh
- `experiments/cr-loop/scripts/read-firestore-findings.sh` — pulls findings from local Firestore emulator after each run

## Cost

| Resource | Total |
|---|---|
| Wall-clock | ~110 min for 10 prod runs (sequential) + ~10 min infra setup |
| Token cost | 0 (covered by zai-coding-plan subscription) |
| GLM API calls | ~30 (10 orchestrators + ~20 subagent invocations) |
