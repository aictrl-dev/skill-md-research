# Knowledge Graph as a Code-Review Edge — Full Research Flow

**Date:** 2026-05-06 → 2026-05-07
**Authors:** experiment harness + Bulat
**Sample:** 10 PRs from `aictrl-dev/aictrl`
**Model:** zai-coding-plan/glm-5.1 throughout
**Stack:** aictrl 0.3.2 CLI + local backend MCP + local Neo4j + local Firestore emulator

## The question

Does giving the production code-review agent access to a Knowledge Graph (callers, impact, co_changes, prior findings, linked issues) produce a measurably better code review than the prod skill alone? If so, by how much, and via what mechanism?

This experiment ran five sequential phases (A → E), each isolating one variable, plus an AK-methodology correction at the end that materially changed the conclusion.

## Setup

- **10 PRs** sampled from `aictrl-dev/aictrl` (mix of trivial / medium / large / noisy)
- **Answer key** built from prior bot reviews + their human verdicts — 83 labelled findings across 8 of 10 PRs (PRs 1776 and 1790 had no human reviews)
- **Scoring:** F1 vs answer key, with fuzzy line matching (±5) and TRUE/FALSE × FIX/DEFER/IGNORE labels
- **Local stack:**
  - aictrl CLI configured per-experiment via `XDG_CONFIG_HOME` to point at `http://localhost:4000/cr-loop/mcp`
  - Local backend MCP routes `record_review_started` / `record_finding` / `record_review_completed` / `query_context` to Firestore emulator + local Neo4j
  - Org `cr-loop` seeded with PR / Issue / Review / Finding nodes from the 10-PR sample
  - **Phase B onward:** local Neo4j additionally indexed with code-domain entities (Function / Class / Interface / File + IMPORTS / CALLS / IMPLEMENTS edges) for the same `cr-loop` org slice
- **Skills under test:** production `code-review` v6.0.0 (Security / Consistency / Bug-Hunter parallel subagents) + production `explore-context` v1.1.0 (`query_context` documentation)

## Phase A — production skill, no useful KG slice

The first sweep: prod code-review skill + prod explore-context skill, run unchanged through aictrl/GLM-5.1 against local MCP. Local KG had only PR/Issue/Finding data for `cr-loop` (no code-domain entities yet).

**Tool-usage observation:** the agent organically called `aictrl_query_context` 55 times across 10 runs — but every call returned `{"results": [], "count": 0}` because there were no code nodes in the cr-loop slice. The Bug Hunter subagent reached for the graph; the graph wasn't there to answer.

**F1 vs original AK:** 0.233 mean. Compared to the throwaway minimal baseline (0.038) and the prepended-KG-context variant (0.069), the prod skill alone delivers a 6× improvement — independent of any KG context. Most of the lift comes from the **skill structure** (parallel subagents + verification), not the context.

## Phase B — production skill, with code-domain KG populated

Indexed `aictrl-dev/aictrl` into local Neo4j with `org_id='cr-loop'`. Encountered two real bugs in `scripts/build-graph.ts`:

1. `EXCLUDED_DIRS` did not include `.claude` — the walker ingested every agent worktree in `.claude/worktrees/`, producing 1.5M+ duplicate nodes
2. `arr.push(...largeArray)` blew the call stack on large edge sets

Both patched in the codebase (`scripts/kg-query/graph-builder.ts`, two one-line fixes). After fix, used a focused indexer (`experiments/cr-loop/scripts/index-pr-files.ts`) that walks the union of changed files across the 10 PRs + 25 sibling files per directory. Final graph: **3,137 Functions / 725 Interfaces / 255 Files / 76 Classes** plus the 81 Findings / 12 Reviews / 10 PullRequests / 5 Issues from the prior load.

**Verification:** `query_context: domain=code, action=search, query="formatDuration"` now returns 6 hits (the file, its test, the function, plus three other call sites). KG genuinely answering queries the agent issues.

**F1 vs original AK:** 0.304 mean — **+30% over Phase A.** The lift comes almost entirely from PRs that were *zero* in Phase A:
- PR 1783: 0 → 0.44
- PR 1782: 0 → 0.25
- PR 1794: 0.48 → 0.69

Two precision regressions on PRs that had already worked (1785: 0.56 → 0.48; 1788: 0.24 → 0.13). Pattern: KG context expands the candidate pool. On PRs with broad answer keys this helps; on narrow ones it adds novels that look like FPs to the scorer.

**Tool usage:** 63 `query_context` calls, 2,060 hit results (vs 0 in Phase A). The agent was reaching for the graph in similar volume; now the graph answered.

## Phase C — rewrite `explore-context.md` to drive richer queries

Phase B observation: of all 63 `query_context` calls, **zero** were `callers` / `impact` / `traverse` / `co_changes`. 38% were `code/read`, 33% `code/search`, 24% `code/context`. The agent was using `query_context` as a smarter `cat`/`grep` and never exploiting the graph structure. Also zero calls to `domain=issues` despite the data being there.

Hypothesis: rewriting `explore-context.md` to be more aggressive about graph actions would shift behaviour.

**Wrote `explore-context.md` v2.0** with a "Required Pre-Recording Verification Protocol", reordered action table putting `callers` / `impact` / `co_changes` first, demoted `search` / `read` to "last-resort", added a `domain=issues` section.

**Result on first 5 PRs:** *no behavioural change.* The agent still used only `read` / `search` / `context`. Total calls dropped from 23 to 13.

**Diagnosis:** the subagents are spawned by the orchestrator's `Task` dispatch with a *self-contained prompt* (PR diff + per-concern checklist). They have access to the `aictrl_*` MCP tools but **do not see the orchestrator's loaded skill files**. Editing `explore-context.md` alone cannot change Bug Hunter behaviour.

**Killed Phase C early.** Confirmed: subagent prompt template is the lever, not the explore-context skill content.

## Phase D — edit the subagent prompt template (`MUST verify`)

Found the smoking gun in `code-review/SKILL.md` Step 4 — the explicit "Tool rules" block passed to every subagent:

> You MAY call `aictrl_query_context` to read full-file context for a changed file when the inline patch lacks surrounding code. Keep to under 5 such calls.

This *steers the subagent away from graph actions.* It positions `query_context` as a fallback file reader.

**Replaced the rule** in a v2.0 of code-review/SKILL.md with imperative graph-first guidance:

> You MUST use `aictrl_query_context` to verify every finding before including it in the JSON array. Reach for graph actions FIRST: `callers` (function blast radius — required before flagging), `impact` (file blast radius — required before recommending rename/removal), `co_changes` (historical coupling — required on each changed file), `domain=issues, action=context` (cross-PR finding history). Use `read`/`search` only when the four graph actions did not answer the question.

Plus: "If the function has 0 callers, the bug doesn't matter; drop or downgrade the finding."

**Phase D action distribution:** 317 `query_context` calls across 10 PRs, of which **165** were `callers` / `impact` / `co_changes` / `domain=issues`. Phase B had 0 such calls. Behaviour shifted dramatically.

**But F1 collapsed.** Mean F1 fell to **0.143** — worse than Phase A. The reason:
- Findings emitted: 41 (Phase B) → 15 (Phase D)
- The "MUST verify before including" rule made the agent gate emission on graph queries
- The "drop or downgrade" instruction made the agent over-conservative
- Result: precision climbed to 1.0 across all PRs (no FPs at all) but recall collapsed
- PR 1803: 9 findings → 0 findings; PR 1794: 9 → 1; PR 1785: 14 → 5

The skill-content lever **works** — but the wording matters as much as the lever. "MUST gate on verification" is too strong.

## Phase E — soften to `SHOULD use, no gating`

Rewrote the rule to position graph actions as severity / scope / suppression *informers*, not pre-recording gates:

> You SHOULD use `aictrl_query_context` to inform your findings... use these actions to decide severity, scope, and whether to suppress a duplicate, but do not gate emission on them: when you see a real issue, record it.

Removed the "drop or downgrade if zero callers" instruction. Replaced with: "0 callers is a candidate for dead-code annotation but the original finding still stands if valid."

**Phase E results vs original AK:**
- Mean F1: 0.243 (between B's 0.304 and D's 0.143)
- Findings emitted: 43 (highest of any phase)
- Graph-traversal calls: 70 (vs B's 0, D's 165)
- Per-PR: large recovery on 1781 (0.25 → 0.60), 1785 (0.48 → 0.56), 1788 (0.13 → 0.24)
- But still trailing on 1803 (0.80 → 0.67), 1794 (0.69 → 0.36)

This looked like a partial recovery, not a clear win. Phase E emitted more findings than B but with lower F1 — many novels.

## The methodology correction — triage the novels

Across the four phases, the agent emitted many findings that didn't match the answer key. The AK was built from prior **bot reviews**; it captures *what bots have flagged before*. When agents reach for graph context, they catch things bots didn't — which the scorer counts as 0 (novel = unscored).

**Approach:** dedupe novels across all phases, manually verify each against the actual code, classify TRUE / FALSE / DUP, and add TRUE ones to an extended answer key.

**Outcome:**
- 62 unique novel findings across all phases
- Verified against source files
- 60 classified TRUE (real findings the bots missed)
- 2 classified FALSE (PR 1803 claims about non-existent fields)
- 3 escalated to FIX action (formatDuration multi-day truncation, skills.ts trim bug, hasFindingsMin enum mismatch)
- 57 classified DEFER (real but stylistic / refactor / consistency items)

**Per-PR AK extension:**
| PR | Original | Extended | Δ |
|---|---:|---:|---:|
| 1776 | 0 | 2 | +2 |
| 1781 | 7 | 9 | +2 |
| 1782 | 8 | 9 | +1 |
| 1785 | 25 | 37 | +12 |
| 1788 | 18 | 29 | +11 |
| 1790 | 0 | 21 | +21 |
| 1794 | 10 | 21 | +11 |
| **Total** | **83** | **143** | **+60** |

PR 1790 is particularly striking: the AK was empty (no human review), so every Phase A/B/E finding was treated as 0 by the scorer. After triage, 21 of those findings are confirmed real.

## Re-scored results — the picture flips

| Phase | Original AK F1 | **Extended AK F1** | Findings emitted | Graph queries | Of which graph-traversal |
|---|---:|---:|---:|---:|---:|
| A — prod skill, empty KG | 0.233 | 0.260 | 37 | 55 | 0 |
| B — prod skill, KG populated | 0.304 | 0.300 | 41 | 63 | 0 |
| D — code-review v2 (MUST) | 0.143 | 0.149 | 15 | 317 | 165 |
| **E — code-review v3 (SHOULD)** | 0.243 | **0.388** | **43** | 234 | 70 |

**Phase E was the winner all along.** Its lower original-AK F1 was a methodology artefact, not a quality regression. With novels credited:

- E vs B: **+29% F1** (0.388 vs 0.300)
- E vs A: **+49% F1** (0.388 vs 0.260)
- D's recall collapse persists — the "MUST verify before including" wording really did suppress real findings, even after AK extension

Most striking per-PR results with extended AK:
- **PR 1790** (no human review): A 0.62 / B 0.16 / E **0.71** — Phase E found 8 of 21 confirmed-true issues
- **PR 1776:** A 0 / B 0 / E **0.80** — Phase E found 1 of 2 confirmed-true issues
- **PR 1781:** A 0.22 / B 0.22 / E **0.55** — Phase E found 3 of 9 vs 1 of 9

## What worked — and why

Three lessons, ordered by leverage:

### 1. The right place to inject KG-usage guidance is the subagent prompt template inside `code-review/SKILL.md`, not `explore-context.md`

Subagents do not auto-load the orchestrator's `-f` skills. They get a self-contained prompt: PR diff + per-concern checklist + a "Tool rules" block. Phase C proved that editing `explore-context.md` alone has zero effect on subagent tool selection. Phase D's behaviour shift came from changing the "Tool rules" block in `code-review/SKILL.md` — same content, different vehicle.

This means: **the production code-review skill is the actual control surface for KG behaviour, not the explore-context skill.**

### 2. The KG provides material lift on top of the skill — but the lift is fragile to wording

- Phase B vs A (extended AK): +0.040 F1 from KG availability alone, no skill changes
- Phase D vs B (extended AK): −0.151 F1 from "MUST verify" wording (the lever moved hard, the wrong direction)
- Phase E vs B (extended AK): **+0.088 F1** from "SHOULD use, no gating" wording

The total swing from worst (D, 0.149) to best (E, 0.388) is **0.24 F1 — 2.6×** — controlled entirely by the phrasing of one paragraph in the subagent prompt. The KG is necessary; the wording around it is sufficient.

### 3. The conventional answer-key methodology systematically under-credits KG-augmented agents

When an agent reaches for graph context (cross-PR history, blast radius), it catches different findings than bots typically flag. Those novels score as 0 against an AK built from prior bot reviews. **The methodology under-credited Phase E by 0.145 F1** — enough to flip the ranking from "looks like a regression" to "clear winner".

Implications:
- F1-vs-bot-AK is a useful but biased metric for KG-augmented review
- Production trend dashboards comparing KG-on / KG-off must use either (a) human-graded findings, or (b) a periodic re-triage of agent novels
- Without this correction, every iteration that adds context will *appear* to regress

## What to do with this — recommendations

**Ship `code-review` v3 (Phase E phrasing).** Replace the "Tool rules" block in `data/default-skills/code-review/SKILL.md` with the SHOULD-use, no-gating language. Single-paragraph diff, +0.088 F1 vs current.

**Make sure the executor's KG slice has code-domain coverage**, not just PR/Issue/Finding data. The Phase A vs Phase B delta (+0.04 F1) only materialises when `query_context: domain=code` returns real results. Today's prod execution path needs verification that the org's codebase is indexed.

**Build a production-grade novel-triage loop.** The methodology gap discovered in this experiment is not a one-off — every future skill iteration will produce novels that don't match the prior bot-AK. A dashboard that surfaces (a) emitted findings without AK match, (b) flags them for human triage, (c) feeds confirmed-true ones back into the AK is the missing piece for trustworthy iteration.

**Defer building new MCP `domain` types or query actions** (#1810 et al.) until a Phase F establishes whether further iterations on the SHOULD-use prompt produce additional gains. The lever proven here (subagent prompt phrasing) is much cheaper than tool-surface changes and the experiment shows it's the dominant driver.

## What this experiment cannot claim

- **Statistical significance.** Single seed × 10 PRs × 4 variants. The 000 baseline observed run-to-run F1 variance of ~0.01 on the same PR. The headline +0.088 Phase E vs B delta (extended AK) is suggestive — not proven. A 3-seed sweep of A/B/E would tighten the bars; D is decisively bad and doesn't need re-running.
- **Generalisation to other repos / models / skill stacks.** Tested on a single ~5K-file TypeScript codebase against GLM-5.1 with a focused KG slice. Different language ecosystems and different model providers may shift the picture.
- **The novels' true validity at production scale.** Manual triage on 62 items inevitably has bias. A second reviewer would catch errors in either direction. Some of the "TRUE / DEFER" calls would arguably be "TRUE / IGNORE" or vice versa; aggregate F1 is moderately sensitive to this.

## Files

- `experiments/cr-loop/runs-prod{,-b,-d,-e}/<pr>/<runId>.{ndjson,json,findings.json}` — per-phase run artefacts
- `experiments/cr-loop/answer-key.json` — original AK (83 entries)
- `experiments/cr-loop/answer-key-extended.json` — extended AK (143 entries) after novel triage
- `experiments/cr-loop/novels-to-triage.json` — 62 deduplicated novels with foundIn phase tracking
- `experiments/cr-loop/scripts/{run-prod-skill,run-all-prod,read-firestore-findings,index-pr-files,collect-novels,extend-answer-key,score}.{ts,sh}` — harness
- `data/default-skills/code-review/SKILL.{v2,v3}.md` — Phase D and Phase E variants
- `data/default-skills/explore-context/SKILL.v2.md` — Phase C variant (failed propagation)
- `scripts/kg-query/graph-builder.ts` — `.claude` excluded from indexer + spread→concat fix

## Cost

| Resource | Total |
|---|---|
| Wall-clock — sweeps | ~7h (4 phases × 10 PRs each, mostly serial) |
| Wall-clock — KG indexing | ~30s focused indexer |
| Wall-clock — manual novel triage | ~45 min |
| Token cost | 0 (zai-coding-plan subscription) |
| GLM API calls | ~120 across all sweeps |
| Engineering time (sequential, with context-cap interruptions) | ~12h |
