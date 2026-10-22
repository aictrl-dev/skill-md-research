# Numerical readability revision — focused QA

**PASS** for the current article and tracked blog-writing skill. Comparison HEAD: `39fa827b8a19295342a047452932050805dfb5b5` (local WiT commit). QA made no source edits, commits, push or external action.

## Arithmetic and presentation

| Unrounded value | Checked reader-facing value |
| --- | --- |
| 3,442 first-request tokens | 3.4k tokens |
| 2,091 first-request tokens | 2.1k tokens |
| 608 system tokens | about 600 reference tokens |
| 2,772 tool-definition tokens | about 2.8k tokens |
| `(3442 - 2091) / 3442 × 100 = 39.2504…%` | about 39% fewer first-request tokens |
| `100 / 48 = 2.0833…` percentage points | about 2 percentage points |
| 18.75 / 22.92% | 19 / 23% |
| 2.08 / 10.42% | 2 / 10% |
| 4.17 / 39.58% | 4 / 40% |

All mappings round correctly. The relative reduction uses the **unrounded 3,442-token baseline**. Bar geometry remains `60.75%`, correctly derived from `2091 / 3442 × 100 = 60.7496…%`, rather than recomputed from shortened labels. The published-results caption says values are rounded to whole percentages; the token figure states values are rounded and retains its reference-token/provider-billing limit.

Metadata, dates, model identifiers, commands, every source/external/internal href, CSS and article element/attribute structure match HEAD. Raw source links remain unchanged. No decimal percentage remains in reader-facing text; model/version identifiers and CSS geometry are correctly treated separately.

## Writing-rule validation

The tracked `.claude/skills/write-blog-post/SKILL.md` frontmatter is **byte-identical** to HEAD and parses as the same YAML. Its only changes are the numerical-readability section and one attribution-gate checklist item; all pre-existing skill bytes remain unchanged after removing those additions. Markdown fences remain balanced and the final newline is preserved.

The rule covers whole percentages by default, at most two/three significant digits, compact units, correct rounding, relative-change baselines versus percentage points, calculations from unrounded values, raw reproduction data, explicit rounding labels, protection of small nonzero rates, and exact identifiers/versions/dates/commands/URLs/operational thresholds. The publication gate checks rounded labels against unrounded calculations.

## Commands and measurement

- `npm run build:website`: PASS.
- `npx tsx website/tools/lint-marketing-html.ts website/public/blog/swe-evo-analysis.html`: PASS, **0 errors / 6 existing orphan-image warnings** for unrelated assets.
- `node /tmp/aictrl-swe-wit/numerical-check.cjs`: PASS for the mappings, geometry, source/identifier preservation, skill/frontmatter/rule scope and current measurement.
- `git diff --check`: PASS.
- Root's fresh `/tmp/aictrl-swe-wit/rounded/measure.json`, measured **2026-10-22T09:27:31.162Z**, reports **0 findings**, content profile, phone/desktop. Its captured copy contains the new 3.4k/2.1k labels. The older `final/measure.json` still contains old labels and was not used as the current numerical snapshot. The final added unit word “tokens” after “about 2.8k” was checked in source after this measurement; the final hash below includes it. CSS is unchanged, so no broader rerun was needed for that unit word.

The 226-test WiT semantic/SEO/link pass is prior evidence; it was not repeated solely for number labels, as requested. CSS/DOM structure is unchanged. Only the article and tracked skill differ from local HEAD; no package/lockfile/research changes were introduced. Workspace/global skill-copy synchronization is root-owned and was not broadened by QA. No new-head CI, review, merge or live-release result is claimed.

## Final SHA-256

```text
dd6207841afabdc2037d6410e102a259406c2a1a57208c18d6e424aaa9028f8b  website/public/blog/swe-evo-analysis.html
ac984e4b3f51553240b24e7c116775deb0d2ae8287056292c68dd654804cfa60  .claude/skills/write-blog-post/SKILL.md
```

Receipts under `/tmp/aictrl-swe-wit/`: `numerical-results.json`, `numerical-check.cjs`, `numerical-{build,html-lint,structural}.log`, and root's `rounded/measure.json`.
