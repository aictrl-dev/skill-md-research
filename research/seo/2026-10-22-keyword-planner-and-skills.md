# SWE-EVO keyword research and SEO tooling

Observed 22 October 2026. This is a bounded first pass for `/blog/swe-evo-analysis`, not a complete keyword export or a forecast of qualified traffic. The product article was inspected at revision `0527af498b00d5df33781c41fd4b939f996eb9af`.

## Keyword Planner observations

Native Google Ads Keyword Planner, Discover new keywords. Separate United Kingdom and United States requests; English selected; Google Search only; displayed historical window **October 2025–September 2026**. Values below are the native average monthly search **ranges**, not precise counts. Close variants may overlap: do not sum the rows or use range midpoints as measured demand.

| Keyword | UK monthly range | US monthly range | Relevance to this article |
| --- | --- | --- | --- |
| `swe evo` | 10–100 | 10–100 | Primary benchmark intent, supported by existing Search Console exposure |
| `swe evo benchmark` | 10–100 | 10–100 | Primary benchmark intent; potentially overlaps the preceding row |
| `agent harness` | 100–1k | 1k–10k | Strong supporting topic, already in the title and body |
| `harness engineering` | 100–1k | 1k–10k | Related topic with ambiguous suggestions; avoid chasing automotive demand |
| `context engineering` | 100–1k | 1k–10k | Relevant supporting concept; a broad topic is not automatically this page's primary intent |
| `claude code system prompt` | 100–1k | 1k–10k | Relevant source/example; some searchers may want a prompt dump rather than this analysis |
| `agents md` | 100–1k | 1k–10k | Relevant instruction-file discussion; distinguish from format/setup documentation |

All seven rows were read in the rendered results. The first five supporting terms appeared as “Keywords that you provided”; a subsequent text-contains-`swe` filter exposed the two benchmark rows. Three other submitted seeds (`ai coding agent evaluation`, `coding agent benchmark`, `system prompt optimization`) were not fully inspected, so no volume or zero-demand claim is made for them.

The ten-seed discovery generated hundreds of automotive wiring/ECU suggestions. This is evidence that automatic expansion needs intent filtering, not evidence of useful developer traffic. Google showed an account notice that more detailed statistics require campaign activity. No campaign was started, billing changed, keywords saved to a serving campaign, or money spent.

CSV export was attempted, but Chrome blocked the generated download. The table is transcribed from visible UI/DOM observations, not an ingested full CSV. Signed export URLs, account details and billing data are intentionally excluded from this public research record.

[Google's metric definitions](https://support.google.com/google-ads/answer/3022575) explain that search volumes are approximate and rounded, and that **competition measures advertisers**, not organic ranking difficulty. API/MCP access should not be assumed to unlock more precise data or bypass account restrictions.

## Search Console cross-check

Use the [existing 21 October query-to-page evidence](2026-10-21-days1-5/2026-10-21-query-opportunities.md), not a claim of a fresh Search Console pull: 22 September–19 October versus 25 August–21 September, Web search, exact SWE canonical page filter.

`swe evo` had 2 clicks / 27 impressions and `swe-evo` 1 click / 41 impressions, each at average position about 8.1. These are small samples, with unknown traffic qualification. Planner's broader demand does not justify abandoning the existing benchmark intent.

## Page recommendations

1. **Keep SWE-EVO as the primary topic and preserve its canonical URL.** The current title already names both SWE-EVO and the agent harness. Adding every broader term to it would weaken the promise.
2. **Consider moving a one-sentence benchmark definition into the opening.** At the inspected revision, the first substantive definition is in section three. Someone arriving for “SWE-EVO benchmark” should understand the benchmark before the prompt-maintenance argument. Candidate wording: “SWE-EVO evaluates coding agents on release-to-release changes in existing software. Here is what its results—and newer prompt research—mean for the instructions, skills and tools in your agent harness.” This is proposed copy, not a shipped change.
3. **Use an informative section heading where it helps readers.** “What is SWE-EVO, and what does it measure?” would make the existing benchmark section easier to locate. Keep the qualification that cross-harness results do not isolate prompt length.
4. **Treat broader terms as supporting intent.** The article already covers `AGENTS.md`, system prompts, tools and context engineering. Add a definition or a descriptive internal link only when it helps comprehension; keyword repetition alone has no demonstrated benefit here.
5. **Reassess after publication and indexing.** Compare query/page impressions, clicks and position over a documented window, then relevant downstream actions where measurement is available. No gain in qualified traffic or conversion has yet been established. The current article refresh is still a PR, not a production intervention.

The benchmark definition is supported by the [authors' paper](https://arxiv.org/abs/2512.18470v6) and [dataset card](https://huggingface.co/datasets/Fsoft-AIC/SWE-EVO). A web search surfaced those primary sources and the authors' repository; this was not a controlled Google rank-position or competitor study.

## Skills assessed

- **[Corey Haines: seo-audit](https://skills.sh/coreyhaines31/marketingskills/seo-audit)** is the closest content-audit fit: query/page mapping, search intent, titles, headings, internal links and prioritization. The full skill and its rankings-push reference were read from the primary repository, head `e85f3cbc2e4a79bf33b2a12e9bdd9087d414735b`. Skills.sh displayed about **234k installs**, and GitHub about **56k repository stars**. Those are adoption indicators, not proof that every checklist item applies. Use character counts as editorial guidance rather than Google limits, and verify current technical claims against Google documentation.
- **[Addy Osmani: seo](https://skills.sh/addyosmani/web-quality-skills/seo)** focuses on rendered-page and technical checks: crawlability, canonicals, metadata, structured data and Lighthouse. Skills.sh displayed about **51k installs**, GitHub about **3k repository stars**. It explicitly distinguishes a technical score from ranking outcomes. It complements keyword research rather than providing keyword demand.
- Semrush has an official keyword-research skill, but live provider metrics depend on its data connection. No Semrush plugin was found in the available plugin search. It was not selected as a new dependency for this first pass.

No SEO skill was installed during this discovery. A skill supplies a workflow; it does not grant account access or invent search-volume data.

## Replacing browser research with MCP

The available plugin catalog returned Windsor.ai for Google Ads/GSC performance data, but its description did not establish Keyword Planner support. No connector was installed on that basis.

Google's [official Google Ads MCP guide](https://developers.google.com/google-ads/api/docs/developer-toolkit/mcp-server) and primary repository list account discovery, GAQL search and resource metadata. It is read-only, but currently does **not expose the keyword-idea and historical-metric RPCs** needed for this study. Installing that server alone would not replace Keyword Planner's UI.

The underlying Google Ads API does support [keyword ideas](https://developers.google.com/google-ads/api/docs/keyword-planning/generate-keyword-ideas) and [historical metrics](https://developers.google.com/google-ads/api/docs/keyword-planning/generate-historical-metrics) directly, without creating a persistent keyword plan.

One candidate is [Nick Cosentino's Keyword Planner MCP](https://github.com/ncosentino/google-keyword-planner-mcp). Its tool registration and Go client were inspected: keyword ideas, historical metrics, forecasts and geo lookup; requests go to Google's API/OAuth endpoints. It is a smaller community project (about 50 stars at inspection), not Google's official server. This was an initial code inspection, not a complete security audit or live integration test.

For recurring research, prefer a local MCP with keyword ideas and historical metrics, explicit country/language/network settings, and a verified read-only tool surface. It still needs a Google Cloud project with appropriate Ads API access and OAuth authorization for the intended customer account. Initial authorization may involve a browser; subsequent queries can avoid UI navigation. Do not infer API credentials from the existing browser login or store credentials in either repository.

No MCP package was installed, OAuth grant created, cloud service deployed, or account permission changed in this pass.
