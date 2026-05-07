# cr-loop — KG-augmented Code-Review Experiment

**Status:** complete · single-seed pilot
**Dates:** 2026-05-06 → 2026-05-07
**Model:** `zai-coding-plan/glm-5.1`
**Sample:** 10 PRs from `aictrl-dev/aictrl`
**Headline:** the right phrasing of the subagent prompt + populated KG produces **F1 0.388**, vs **0.300** for the production-equivalent baseline. **+29% F1 from a single-paragraph prompt change.**

## What this experiment tests

Does giving the production code-review agent access to a Knowledge Graph (callers, impact, co_changes, prior findings, linked issues) produce a measurably better code review than the prod skill alone? If so, by how much, and via what mechanism?

Five sequential phases, each isolating one variable:

| Phase | Variable changed | F1 (orig AK) | F1 (ext AK) |
|---|---|---:|---:|
| **A** | prod skill, empty KG slice (baseline) | 0.233 | 0.260 |
| **B** | prod skill, KG populated with code-domain entities | 0.304 | 0.300 |
| **C** | rewrote `explore-context.md` (failed — didn't propagate to subagents) | — | — |
| **D** | rewrote `code-review.md` subagent prompt: `MUST verify before recording` (recall collapse) | 0.143 | 0.149 |
| **E** | softer rewrite: `SHOULD use, no gating` ⭐ | 0.243 | **0.388** |

Plus an **answer-key extension**: 62 deduplicated novel findings emitted across phases were manually triaged against the actual codebase, and 60 confirmed-true findings were added to an extended AK. **The original AK (built from prior bot reviews) systematically under-credited KG-augmented review** — Phase E was the winner all along; the methodology hid it.

Full narrative: [`log/004-full-research-flow.md`](log/004-full-research-flow.md).
Punchy summary: [`cr-loop-research-summary.html`](cr-loop-research-summary.html).

## What we learned

1. **The lever is in `code-review/SKILL.md`, not `explore-context.md`.** Subagents don't auto-load orchestrator skills — they get a self-contained prompt with the diff + a per-concern checklist + a "Tool rules" block. That tool-rules block is the actual control surface.

2. **KG availability is necessary; the wording around it is sufficient.** +0.04 F1 from KG availability (B vs A). +0.09 F1 from the right prompt wording (E vs B). −0.15 F1 from the wrong wording on the same lever (D vs B). Total swing controlled by one paragraph: **2.6×**.

3. **Bot-built answer-keys systematically under-credit KG-augmented review.** When agents reach for blast radius, cross-PR history, and historical coupling, they catch findings bots typically don't flag — those score as 0 against an AK built from bot reviews. Without a novel-triage feedback loop, every iteration that adds context will *appear* to regress.

## Key tool-usage shift (Phase B → Phase E)

Going from the production-equivalent prompt to the proposed one:

| `query_context` action | B (current) | E (proposed) | Δ |
|---|---:|---:|---:|
| `code/callers` | **0** | **34** | +34 |
| `code/impact` | **0** | **16** | +16 |
| `code/co_changes` | **0** | **10** | +10 |
| `issues/context` | **0** | **9** | +9 |
| `code/search` | 21 | 68 | +47 |
| `code/context` | 15 | 45 | +30 |
| `code/read` | 24 | 26 | +2 |
| (others) | 3 | 17 | +14 |
| **Total** | **63** | **225** | **3.6×** |

Four graph-traversal action types went from 0 calls to 69 — previously unreachable through the agent's organic behaviour, now driven by the rewritten subagent prompt.

**Cost:** ~1.9× total tokens (~46M vs ~24M per 10-PR sweep). Output tokens grow only 1.10× — the bulk of the extra cost is input/cache reads from larger context windows. On the GLM coding plan this is free; on usage-priced APIs the cache-discount keeps the real $/review ratio closer to ~1.7×.

## Layout

```
experiments/cr-loop/
├── README.md                      # this file
├── pr-set.json                    # 10 PRs sampled
├── answer-key.json                # 83 entries (from prior bot reviews)
├── answer-key-extended.json       # 143 entries (after manual novel triage)
├── novels-to-triage.json          # 62 deduplicated novels with provenance
├── data/                          # per-PR enriched data (title, body, diff, bot reviews, verdicts)
│   └── pr-*.json                  # 10 files
├── skills/                        # skill variants under test
│   ├── code-review.SKILL.v3.md   # Phase E winner — recommended for production
│   ├── code-review.SKILL.v2.md   # Phase D failed variant (MUST verify)
│   └── explore-context.SKILL.v2.md  # Phase C failed variant (no propagation)
├── scripts/                       # 14 scripts (9 standalone, 3 require aictrl_main checkout)
│   ├── enrich-pr-set.ts          # fetch PR meta + reviews + verdicts via gh
│   ├── stage-workspaces.sh       # stage .cr/{pr-meta,pr-files}.json per PR
│   ├── score.ts                  # F1 vs answer-key
│   ├── run-prod-skill.sh         # single-PR runner via aictrl CLI + local MCP
│   ├── run-all-prod.sh           # 10-PR sweep
│   ├── read-firestore-findings.sh # pull findings.json from local Firestore
│   ├── collect-novels.ts         # dedupe novels across phases
│   ├── extend-answer-key.ts      # manual-verdict → AK extension
│   └── kg/                       # require aictrl_main checkout (see kg/README.md)
│       ├── load-kg.ts            # seed PR/Finding/Review/Issue nodes
│       ├── index-pr-files.ts     # focused codebase indexer
│       └── build-enriched-prompt.ts  # Phase 0 (baseline) prepended-context prompt builder
├── log/                           # phase reports
│   ├── 000-baseline-vs-enriched.md   # Phase 0 — minimal skill A/B (predates phases A-E)
│   ├── 001-prod-skill-explore-context.md  # Phase A
│   ├── 002-prod-skill-with-kg.md  # Phase B
│   └── 004-full-research-flow.md  # full A → E narrative
├── results/raw/                   # findings.json per phase per PR (sanitized — no patches)
│   ├── phase-A/PR-*.findings.json
│   ├── phase-B/PR-*.findings.json
│   ├── phase-D/PR-*.findings.json
│   └── phase-E/PR-*.findings.json
└── cr-loop-research-summary.html  # executive summary HTML
```

## What's not included

To keep this repo public-friendly:

- **Full session traces** (`*.ndjson`, `*.prompt.md`) — these inline the PR diffs as part of the model context. ~25 MB across phases. Findings JSON (the agent's emitted output) is included; the full session reconstruction is not.
- **Per-experiment aictrl config** — included an `X-Executor-Secret: dev-secret` header for local MCP auth; the actual headers and URL are documented in `scripts/run-prod-skill.sh`.
- **Workspace `.cr/` dumps** — the `gh pr view` / `gh api pulls/N/files` JSON for each PR. Re-fetchable via `scripts/stage-workspaces.sh`.

## Replication

End-to-end replication requires:

1. **A local aictrl backend** with MCP enabled at `localhost:4000/<orgSlug>/mcp` (org seeded in Firestore emulator).
2. **A local Neo4j** for `query_context: domain=code` queries (otherwise calls return empty).
3. **An aictrl CLI** (`zai-coding-plan/glm-5.1` model on the Coder API endpoint).
4. **gh CLI** authenticated to fetch PR metadata.

The KG-population scripts (`scripts/kg/*.ts`) import from `../../../scripts/kg-query/` — intended to run from inside an `aictrl_main` checkout where those modules exist. See `scripts/kg/README.md` for the dependency wiring.

Quick path to a smoke test on one PR (assuming all infra is up):

```bash
# 1. Pre-stage workspace files for PRs in pr-set.json
bash scripts/stage-workspaces.sh

# 2. Seed local Neo4j (PR/Finding/Issue/Review data)
GITHUB_TOKEN=$(gh auth token) npx tsx scripts/kg/load-kg.ts

# 3. Index the target codebase into local Neo4j with org_id=cr-loop
node --stack-size=8000 --import tsx scripts/kg/index-pr-files.ts

# 4. Configure aictrl per-experiment XDG override (see run-prod-skill.sh)
#    Set XDG_CONFIG_HOME to a dir containing aictrl-config/aictrl/aictrl.jsonc
#    pointing the `aictrl` MCP server at http://localhost:4000/cr-loop/mcp.

# 5. Smoke run on PR 1788 with Phase E variant skill
CODE_REVIEW_SKILL=experiments/cr-loop/skills/code-review.SKILL.v3.md \
  CR_LOOP_RUNS_SUBDIR=runs-prod-e \
  bash scripts/run-prod-skill.sh 1788

# 6. Pull findings from local Firestore
bash scripts/read-firestore-findings.sh 1788 <runId>

# 7. Score
CR_LOOP_ANSWER_KEY=answer-key-extended.json \
  npx tsx scripts/score.ts --findings runs-prod-e/1788/<runId>.findings.json
```

## Recommendations

1. **Replace the subagent "Tool rules" block in `code-review/SKILL.md` (production)** with the Phase E "SHOULD use, no gating" wording. One-paragraph diff. Worth +0.088 F1 on this 10-PR sample.

2. **Verify production executor's KG slice has code-domain coverage.** The Phase A → B delta only materialises when `query_context: domain=code` returns real results. The focused-indexer pattern (`scripts/kg/index-pr-files.ts`) is the working blueprint.

3. **Build a novel-triage feedback loop** into the production trend dashboard. Surface emitted-findings-without-AK-match. Flag them for human triage. Without this, every iteration that adds context will look like a regression — exactly what happened in this experiment until we re-triaged manually.

## Caveats

- **Single seed × 10 PRs × 5 phases.** F1 variance can be ~0.01 on the same PR run. Headline deltas are suggestive, not proven. 3-seed averaging would tighten the bars.
- **One model, one repo, one language ecosystem.** Tested on a ~5K-file TypeScript codebase against GLM-5.1. Different models/languages may shift the picture.
- **Manual novel triage has bias.** A second reviewer would catch errors in either direction. Aggregate F1 is moderately sensitive to TRUE/FALSE judgement calls on edge cases.
