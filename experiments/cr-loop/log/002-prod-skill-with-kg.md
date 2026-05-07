# 002 — Production code-review + explore-context, **with code-domain KG populated**

**Date:** 2026-05-06
**Model:** zai-coding-plan/glm-5.1 via aictrl 0.3.2
**Skills:** identical to run 001 — production `code-review` v6.0.0 + `explore-context` v1.1.0
**MCP wiring:** identical — local backend at `http://localhost:4000/cr-loop/mcp`

**One change vs run 001:** local Neo4j now contains code-domain entities for `org_id='cr-loop'`.

## How the KG was populated

The full-tree extractor (`scripts/build-graph.ts`) had two bugs that prevented straightforward use:

1. `EXCLUDED_DIRS` did not include `.claude` → walked every agent worktree, producing 1.5M+ duplicated nodes
2. `arr.push(...largeArray)` blew the call stack on large edge sets

Both patched in `scripts/kg-query/graph-builder.ts` (one-line each). Even with `.claude` excluded the walker still picked up ~75k files (likely scratch / generated dirs); rather than chase further exclusions, **a focused indexer** was used: `experiments/cr-loop/scripts/index-pr-files.ts` walks the union of changed files across the 10 PRs (from `.cr/pr-files.json`), expands with up to 25 sibling `.ts/.tsx` files per directory, and runs `extractIncremental` + `insertAll` against that set.

Final cr-loop graph composition (codebase + PR/Finding data side-by-side):

| Label | Count | Source |
|---|---:|---|
| Function | 3137 | code index |
| DomainField | 1956 | code index |
| Interface | 725 | code index |
| DomainValue | 480 | code index |
| File (code) | 255 | code index |
| DomainEntity | 243 | code index |
| TypeAlias | 192 | code index |
| CSSSelector | 143 | code index |
| Finding | 81 | load-kg.ts (run 000) |
| Class | 76 | code index |
| Collection | 51 | code index |
| Review | 12 | load-kg.ts |
| PullRequest | 10 | load-kg.ts |
| Issue | 5 | load-kg.ts |

**Verification before sweep:** `query_context: domain=code, action=search, query="formatDuration"` returns 6 results — the file, its test, the exported function, plus three other call-sites in `ui/src/pages/`. KG is genuinely answering queries the Bug Hunter would issue.

## Per-PR results

| PR | AK size | n found | precision | recall | F1 | matched verdicts | query_context calls | hit results | record_finding | duration |
|---|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|
| 1776 | 0 | 0 | 0 | 0 | 0 | — | 4 | 142 | 0 | 154s |
| 1735 | 5 | 0 | 0 | 0 | 0 | — | 1 | 10 | 0 | 104s |
| 1781 | 7 | 1 | 1.00 | 0.14 | 0.25 | 1 TRUE/FIX | 2 | 306 | 1 | 308s |
| 1783 | 4 | 1 | 1.00 | 0.29 | **0.44** | 1 TRUE/FIX | 16 | 308 | 1 | 755s |
| 1782 | 8 | 1 | 1.00 | 0.14 | **0.25** | 1 TRUE/DEFER | 3 | 30 | 1 | 349s |
| 1790 | 0 | 3 | 0 | 0 | 0 | — (AK empty) | 11 | 810 | 3 | 1012s |
| 1794 | 10 | 9 | 1.00 | 0.53 | **0.69** | 4 TRUE/FIX, 1 TRUE/DEFER | 6 | 39 | 12 | 736s |
| 1785 | 25 | 14 | 0.75 | 0.35 | 0.48 | 3 TRUE/FIX, 2 TRUE/DEFER, 1 TRUE/IGNORE, **2 FALSE/IGNORE** | 9 | 90 | 14 | 792s |
| 1788 | 18 | 6 | 1.00 | 0.07 | 0.13 | 1 TRUE/FIX | 5 | 61 | 7 | 489s |
| 1803 | 6 | 7 | 1.00 | 0.67 | **0.80** | 3 TRUE/FIX, 1 TRUE/DEFER | 6 | 264 | 8 | 765s |

## Aggregate vs prior runs

| Variant | Mean F1 | Mean precision | Total findings | Total TPs (TRUE/*) | Total FPs (FALSE/IGNORE caught) | Total query_context calls | Total non-empty results |
|---|---:|---:|---:|---:|---:|---:|---:|
| 000 baseline | 0.038 | 0.20 | 9 | 2 | 0 | 0 | 0 |
| 000 enriched | 0.069 | 0.30 | 8 | 3 | 0 | 0 | 0 |
| 001 prod skill, **empty KG** | 0.233 | 0.578 | 37 | 17 | 1 | 55 | 0 |
| **002 prod skill, populated KG** | **0.304** | **0.675** | **41** | **19** | **2** | **63** | **2060** |
| Δ 002 vs 001 | **+0.071** (+30%) | +0.097 | +4 | +2 | +1 | +8 | **+2060** |

## Key signals from the A/B

### 1. KG presence drives F1 up by ~30%

Three PRs went from 0 → non-zero F1 because the KG context gave the agent something to anchor on:
- **PR 1783 (+0.44)** — caught 1 TRUE/FIX it had previously missed entirely
- **PR 1782 (+0.25)** — same pattern
- **PR 1794 (+0.21)** — caught 4 TRUE/FIX and 1 TRUE/DEFER vs 2/1 previously

These are all **mid-size PRs** where the agent had something to chase but no obvious hook. KG context appears to provide that hook.

### 2. Two regressions worth understanding

- **PR 1785 (-0.08)** — Phase A caught 1 FALSE/IGNORE; Phase B caught 2. Same Bug Hunter, more aggressive when the KG surfaced patterns. Precision dropped from 0.88 to 0.75. Possible cause: the agent saw multiple call-sites of the function in the KG and over-generalised the bug claim.
- **PR 1788 (-0.11)** — Phase A: 2 findings, both TRUE/FIX. Phase B: 6 findings, only 1 matched. The KG context made the agent emit more candidate findings, most of which weren't in the answer key. The novel findings might be valid but they hurt the F1 metric.

The pattern is consistent: **KG context expands the candidate pool**, which shifts the precision/recall balance. On PRs where the answer key is broad, that helps. On PRs where the answer key is narrow, it adds novels that look like FPs to the scorer.

### 3. KG calls now actually work — 2060 hit results across 63 calls

Phase A: 55 calls, 0 hits. Phase B: 63 calls, 2060 hits. The agent reaches for the KG roughly the same number of times in both phases (median 6 per PR), but the response quality jumps from "always empty" to "mostly substantive". This validates that the agent's organic use of `query_context` is reproducible — it'll pull in whatever data the org slice provides.

### 4. Bash calls went *up* in Phase B, not down

| | Phase A | Phase B |
|---|---:|---:|
| Total `bash` calls | (not measured per-PR) | 239 |
| Median `bash`/PR | (not measured) | 9 |

The hypothesis was that real KG responses would let the agent skip the `bash`/`grep` filesystem step. **Wrong.** The agent uses KG to *find* candidates and `bash` to *verify* them by reading actual file contents. The two are complementary, not substitutable. (See PR 1794: 60 `bash` calls + 6 `query_context`.)

This means the cost story for KG is "additive context", not "compute substitution".

### 5. Findings recorded vs ended up in Firestore

| PR | record_finding calls | Findings in DB |
|---|---:|---:|
| 1788 | 7 | 6 |
| 1785 | 14 | 14 |
| 1794 | 12 | 9 |

Several PRs had `record_finding` calls greater than the eventual stored count. Two interpretations: (a) the prod skill's verification step rejects some findings before commit (working as designed), (b) some `record_finding` calls deduplicate at the storage layer. Either way, this is data the trend dashboard should expose — *call rate vs persist rate* is a clean signal of the skill's self-filtering.

## What the cr-loop experiment now tells us about #1805 / #1806 / #1809 / #1810

- **#1805 (cross-PR finding lookups via KG):** the +30% F1 increase from KG availability is real, single-seed. Worth implementing — but the bigger win is unblocking PRs 1783 / 1782 (zero-finding → useful) more than improving already-good PRs. Triage the implementation around "PRs where the agent currently emits 0".

- **#1806 (linked issues in agent context):** PR 1788 has 18 AK entries, the prod skill caught 1. That gap won't close from issue links. Issue linking helps with *contextual relevance* (deferring stylistic items the team always defers) — that's a precision lift, not a recall lift, and the experiment doesn't measure it well.

- **#1809 / #1810 (richer query_context surface, e.g. domain=pull-requests):** the agent's `query_context` calls in Phase B were almost all `domain=code, action=search`. None reached for the PR/Finding data we loaded. Either the explore-context skill needs prompting to surface the cross-PR query path, or we expose it as a separate `domain` (the proposal in #1810). Worth testing **before** committing implementation effort.

## Caveats

- **Single seed per PR** — same caveat as 000 / 001. Variance possible. Phase C (3 seeds × 10 PRs) would dampen this by ~1.7×.
- **Recall ceiling** — the prod skill correctly filters stylistic items. ~50–70% of the answer-key entries are NIT/CONSISTENCY items the skill skipped. F1 cannot exceed ~0.7 by design.
- **PR 1790 had 8 → 3 findings** (Phase A → Phase B). The 3 Phase B findings might be valid (the AK is empty so we can't score them) but the count drop suggests the agent's verification is more aggressive when it has KG context.
- **The novel findings (~17–22 per phase) are unscored** — treating them as either all-valid or all-FP would shift F1 substantially in either direction. Manual triage on a few would clarify.
- **The focused index covers only PR-touched files + siblings.** It is not a full-codebase KG. Some queries would have returned more / different results against a full index. Expanding the index is cheap (the script is parameterised); not done because the question being asked here is "does *any* KG help" — and the answer is yes.

## Recommendation

**Ship the cross-PR finding lookup (#1805) — but as a v0 that targets the zero-finding-PR case first.** That's where the 30% lift is concentrated; it's also where production users are most disappointed today.

**Defer the new domain proposal (#1810) until we test whether the agent organically reaches for `domain=issues`** when prompted via `explore-context.md`. Today it never did across 20 runs. That's an `explore-context` skill problem, not a tool surface problem — solvable by editing skill content for ~free, then re-measuring.

**Phase C** (3-seed averaging across the same 10 PRs, both with and without KG) would let us claim significance on the +30% delta. ~5h compute, free on the GLM coding plan. Recommended before committing implementation effort to #1805.

## Files

- `experiments/cr-loop/runs-prod-b/<pr>/<runId>.{ndjson,json,findings.json}` — Phase B run artefacts
- `experiments/cr-loop/scripts/index-pr-files.ts` — focused KG indexer (the workaround)
- `scripts/kg-query/graph-builder.ts` — `.claude` added to EXCLUDED_DIRS, two `push(...spread)` replaced with `concat` (lines 47, 372, 377)

## Cost

| Resource | Total |
|---|---|
| Wall-clock (sweep) | ~85 min for 10 prod runs |
| Wall-clock (KG index) | ~30s focused indexer + 10s load-kg.ts |
| Token cost | 0 (zai-coding-plan subscription) |
| GLM API calls | ~30 (10 orchestrators + ~20 subagent invocations) |
