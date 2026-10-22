# SWE-EVO article: editorial research and evidence audit

Checked 21 October 2026. This note supports the substantive rewrite of product PR [#6434](https://github.com/aictrl-dev/aictrl/pull/6434). It is separate from the historical Days 1–5 snapshot directory. No new provider/model experiment was run during this revision.

## Editorial decision

Use the question **“What does an agent harness still need as models improve?”** The practical recommendation is to re-test inherited instructions on a model upgrade, preserve the task contract, scope specialist context, and enforce critical boundaries through executable controls. “All tools remove instructions” and “prompts never help frontier models” are stronger than the evidence supports.

## Source audit

| Source | Verified use | Interpretation boundary |
| --- | --- | --- |
| [Anthropic context engineering, 24 July](https://claude.com/blog/the-new-rules-of-context-engineering-for-claude-5-generation-models) | Vendor reports an over-80% system-prompt reduction without measurable coding-evaluation loss; discusses selective skills. | Specific advanced-model configurations; not an independent cross-vendor ablation. |
| [OpenAI, favor leaner prompts](https://developers.openai.com/api/docs/guides/latest-model?model=gpt-6.1-sol#favor-leaner-prompts) | Current primary documentation recommends reducing repetition and simplifying tool descriptions. | Internal evaluation conditions; validate locally. Article deliberately omits generalized percentage gains. |
| [Gloaguen et al. v2](https://arxiv.org/html/2602.11988v2#S4.SS2) | Section4.2 supports the article’s generated-context cost findings and statistical qualifications. | Generated and developer-written files differ; absence of a significant resolution gain is not proof of universal harm. |
| [Lulla et al. v2](https://arxiv.org/abs/2601.20404v2) | Efficiency evidence, 124 PRs across ten repositories. | Different workload and metrics; included as counterevidence to blanket deletion. |
| [SWE-EVO v6](https://arxiv.org/html/2512.18470v6#S4.T2) | Task population and all six selected resolved-rate cells checked directly against Table2. Revision date checked against the arXiv version history. | Headline/table disagreement disclosed; model/harness comparison does not isolate prompt length. |
| [aictrl CLI measurement methodology](https://github.com/aictrl-dev/skill-md-research/blob/2ff21fc34b9d19ea291f13dc7563a486cc214f7f/experiments/headless-cli-benchmark/README.md) | Scripted model, released versions and capture conditions. | Harness overhead, not task quality or billed savings. |

## Recomputed measurement used in the figure

Public source revision: `2ff21fc34b9d19ea291f13dc7563a486cc214f7f` (resolved with `gh api`). GitHub contents API also confirmed both capture artifacts and the older skill-format directory are present at that revision.

- Default [token estimates](https://github.com/aictrl-dev/skill-md-research/blob/2ff21fc34b9d19ea291f13dc7563a486cc214f7f/experiments/headless-cli-benchmark/article-data/sources/token-estimates.json): aictrl0.5.4, nine tools; system608, tools2772, remainder62, first request3442.
- Scoped [token estimates](https://github.com/aictrl-dev/skill-md-research/blob/2ff21fc34b9d19ea291f13dc7563a486cc214f7f/experiments/headless-cli-benchmark/article-data/sources/token-estimates-aictrl-minimal.json): four tools; system608, tools1421, remainder62, first request2091.
- Difference:3442−2091=1351 reference tokens. Relative bar length:2091/3442=60.75%, rounded.
- Each configuration has five completed single-response captures. Counts use `o200k_base` offline, not provider-billed usage. No quality comparison is inferred.

The older skill-format artifacts were inspected but no new aggregate quality figure is published: their rule-compliance setting and model configurations do not establish a result for current frontier-model prompt deletion.

## Figure attribution and proposed experiment

The four-decision context figure and failure-remedy table are labelled **practitioner framework / editorial guidance**. The two-bar figure is labelled **measured overhead**, with pinned primary capture links. The SWE-EVO table is labelled as a source extract. No forecast, synthetic benchmark score or new successful aictrl task run is presented.

Proposed comparison: current instructions; lean instructions preserving requirements; lean instructions plus the relevant specialist skill. Keep model, checkout, settings, tools, permissions and budget fixed; test tool scoping separately. Use held-out behavior checks, preserve failures and interventions, report correctness and cost separately. This is a proposed pilot design, not a completed experiment.

## Review deliverable

Local review: `http://127.0.0.5:3005/blog/swe-evo-analysis`. Product changes stay within the six existing publishing paths. Raw research, lockfiles, signup and agent configuration remain outside the article diff. Browser inspection covered desktop and a375px viewport; structural/a11y/build/test receipts are task-local under `/tmp/aictrl-seo-rewrite-*`. No production deployment or changed-page indexing request occurred during this revision.
