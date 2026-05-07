# `scripts/kg/` — KG-population helpers (require aictrl checkout)

These three scripts depend on the `kg-query/` module in `aictrl-dev/aictrl`:

- `load-kg.ts` — seeds the local Neo4j with PR / Finding / Review / Issue nodes for the experiment org slice
- `build-enriched-prompt.ts` — builds the Phase 0 "enriched" prompt that prepends KG context to the baseline prompt (predates the prod-skill phases A–E; kept for reproducibility of the original 000 report)
- `index-pr-files.ts` — focused codebase indexer that walks the union of changed files across the 10 PRs + 25 sibling files per directory; runs `extractIncremental` + `insertAll` against `org_id='cr-loop'`

All three import from `../../../scripts/kg-query/`, which means they expect to run from inside an `aictrl_main` checkout where that module exists. They will not run standalone in the `skill-md-research` repo.

## Two ways to use them

**Option A — run from inside an `aictrl_main` checkout.** Copy these scripts into `experiments/cr-loop/scripts/kg/` of your aictrl checkout (one of these is what was done in the original experiment). The `../../../scripts/kg-query/...` import paths resolve correctly.

**Option B — vendor the kg-query module.** Symlink or copy the `kg-query/` module from aictrl into a path the imports resolve to. Roughly 10–15 source files; preserve the `neo4j.js` and `graph-builder.js` / `types.js` exports.

Either way, the scripts assume:

- A running Neo4j at `bolt://localhost:7687` (auth `neo4j/knowledge-graph-experiment` by default; override via `NEO4J_URI` / `NEO4J_USER` / `NEO4J_PASS`).
- A `GITHUB_TOKEN` env var for `load-kg.ts` (which calls `gh api` for issue/PR data).
- Node ≥20 with `tsx`. Run `index-pr-files.ts` with `node --stack-size=8000 --import tsx ...` because `extractAll` chains spread-pushes large edge arrays (see the patches noted in `log/004-full-research-flow.md`).

## Why this isn't fully self-contained

The `kg-query` module is part of aictrl's product surface (it powers the production `query_context` MCP tool). It carries the schema, extractors, and validation logic for the actual product. Vendoring it into a public research repo would either (a) duplicate ~10K LOC that drifts from upstream, or (b) require a release/sync workflow we don't have.

For reproducing the experiment numbers from the recorded artefacts (findings JSONs, NDJSON traces, scores), no KG infra is needed — `score.ts` and `extend-answer-key.ts` operate purely on the JSON files in this repo.
