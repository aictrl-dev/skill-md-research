# SEO/AEO performance review — 21 October 2026

Status: **Google Search Console performance, AI visibility, indexing, sitemap and settings reviewed; 14-day plan ready**. The [plan](2026-10-22-seo-aeo-14-day-plan.md) is based on current account evidence and the production audit. PostHog MCP was connected on 21 October and its acquisition/proxy-funnel results are now included below. Bing access later recovered partially; the latest execution checkpoint below supersedes that initial gap. No production change, publication or purchase was made during this review.

## What the evidence establishes

| Measure | Observed result | Interpretation |
| --- | --- | --- |
| Production sitemap | 68 URLs, including 30 blog articles | Site has an existing content inventory to improve |
| HTTP responses | 68/68 sitemap URLs returned 200 | Availability verified; Google indexing not established |
| Static metadata | Every sampled sitemap URL has a title, description, one H1 and a self-referencing canonical; no duplicated title/description/canonical values | Generic metadata repair is not the main observed opportunity |
| Static directives and JSON-LD | No noindex directive or JSON-LD parse error detected on sitemap URLs | Does not prove rich-result eligibility, semantic accuracy or rendered behavior |
| Existing PostHog snapshot | 412 raw captured apex-host pageviews, 6–19 October UTC | Existing evidence, not a fresh account query, unique visitors, organic traffic or NSM |
| Snapshot weekly movement | 180 views on 6–12 October; 232 on 13–19 October, +28.9% | All captured channels combined, including possible internal/bot activity; not proof SEO improved |
| PostHog organic visitors / sessions | 106 / 108 versus 48 / 49 in the previous 28-day UTC window | More recorded organic traffic, not proof of more qualified acquisition |
| Organic bounce rate | 70.4% versus 32.7% | Engagement proxy worsened; investigate query mix, next steps and tracking |
| Organic → captured CTA / MCP OAuth / accepted task request | 2 / 0 / 0 people out of 106 entrants, separate ordered 7-day diagnostic funnels | CTA rate 1.89%; zeros do not establish zero real qualification |
| Organic qualified visitors and authoritative activation | Still unknown | Proxy funnels are now measured; identity coverage, signup and executor truth remain unverified |
| Google Web performance, 22 Sep–19 Oct vs 25 Aug–21 Sep | 22 vs 22 clicks; 3,458 vs 4,439 impressions (-22.1%); displayed CTR 0.6% vs 0.5%; average position 8.6 vs 11.2 | Clicks flat while exposure fell; better aggregate position does not establish growth |
| Google Generative AI impressions, same windows | 143 vs 104 (+37.5%) | Positive Google AI visibility signal; not visits or qualified outcomes |
| Google indexing, report updated 12 October | 46 indexed, 540 not indexed across all known domain URLs | Includes subdomains and intentional exclusions; cannot compare directly with the 68-URL live sitemap |
| Bing search/citations, later 3-month view | 0 search clicks /105 impressions; 24 AI citations | Partial recovered evidence; matching-window service error, no qualified referrals established |

The production HTTP audit began **2026-10-21T18:02:15Z**. [All URL-level observations](evidence/2026-10-21-live-site-audit.json), [supplemental checks](evidence/2026-10-21-live-supplement.json), [robots](evidence/2026-10-21-live-robots.txt), [sitemap](evidence/2026-10-21-live-sitemap.xml), and [llms.txt](evidence/2026-10-21-live-llms.txt) are preserved. This is a static HTTP/HTML audit: it does not measure browser rendering, request delivery, field Core Web Vitals, crawler access from search-engine infrastructure, ranking, or indexing.

PostHog source: existing CLI analysis (`docs/marketing/cli-execution/2026-10-21-posthog-baseline.json` in the shared checkout), observed **20 October 23:37:44 UTC**, project **88595**, project timezone **UTC**, `$host = aictrl.dev`. Test-account filtering was disabled and no bot filtering applied. The zero recorded `/agent` and benchmark pageviews in that window are not current performance measurements: the benchmark publication on 20 October lies outside it. Do not treat these zeros as a failed launch or zero actual visitors.

## PostHog MCP findings — added 21 October

Read project **88595**, timezone **UTC**, through PostHog MCP. The governed metric catalog is empty, so these are **ad hoc diagnostic results**, not an approved NSM definition. [Exact query inputs/results and limits](evidence/2026-10-21-posthog-mcp-review.json). Queries are read-only; no dashboard, event configuration or stored data was changed.

Acquisition scope is `$host = aictrl.dev`, project internal/test filters enabled, and, for the comparison below, `$virt_is_bot = false`. The project excludes configured internal email addresses and localhost/127.0.0.1; unknown anonymous internal activity may remain. Bot classification is heuristic, and the absence of captured crawlers cannot establish that they never crawl the site. [PostHog bot handling](https://posthog.com/docs/web-analytics/managing-bot-traffic).

| Diagnostic | 22 Sep–19 Oct UTC | 25 Aug–21 Sep UTC | Interpretation |
| --- | --- | --- | --- |
| All-channel visitors after filters | 419 | 265 | +58.1%, recorded visitor identities rather than verified qualified people |
| All-channel sessions | 480 | 317 | Sources and repeat use need separate analysis |
| All-channel pageviews | 638 | 566 | Different measure/filter/window from the original 412-view snapshot |
| Organic-search visitors | 106 | 48 | +120.8%; not a Google-only acquisition claim |
| Organic-search sessions | 108 | 49 | Source classification happens at session level |
| Organic-search pageviews | 131 | 58 | Pageviews do not establish qualification |
| Organic-search bounce rate | 70.37% | 32.65% | +37.72 percentage points; do not optimize volume alone |
| Organic-search mean session duration | 81.2 seconds | 96.9 seconds | Directional engagement diagnostic at low volume |

Current human-classified channel visitor counts are Direct 269, Organic Search 106, Email 20, Organic Social 12, Referral 7, Organic Video 5 and AI 5. Visitors may appear in more than one channel, so **do not sum these to recreate the 419 overall visitors**. The AI group has `utm_source=chatgpt.com` but its referring-domain breakdown is direct/missing. Describe it as AI-classified, ChatGPT-tagged acquisition, not verified independent referrals or citations. Current PostHog classifies AI as a separate channel; keep it separate from classic organic search. [PostHog channel change](https://posthog.com/docs/web-analytics/changelog).

The referring-domain query (internal/test filters on, before explicit bot filtering) reports 93 visitor identities for `www.google.com`. That does **not** reconcile to Search Console's 22 domain-property clicks. Dates use UTC versus Pacific, scopes and identity/session metrics differ, referrers can repeat/be copied, and tracking can be incomplete. The size of the discrepancy needs validation; do not explain it away or claim Google traffic grew from these different measures.

Selected organic landing pages after bot/test filtering:

| Landing page | Visitors | Captured views | Session bounce rate |
| --- | --- | --- | --- |
| From agent factory to workflow | 7 | 7 | 71.4% |
| SWE-EVO analysis | 6 | 7 | 33.3% |
| Skills adoption trajectory | 2 | 2 | 100% |
| Knowledge graph article | 1 | 1 | 0% |

Small denominators prevent a stable page-quality ranking from bounce rates. The broader organic table also shows `/docs` at 7 visitors/100% bounce, `/features/code-review` at 7/71.4%, `/plugins` at 5/100% and `/pricing` at 5/100%. This supports inspecting the content→setup path; it does not establish that those pages never convert. Web Analytics bounce is an event/session diagnostic and must not be interpreted as direct evidence of dissatisfaction. [Web Analytics definitions and conversion goals](https://posthog.com/docs/web-analytics/start-here).

Three **separate ordered 7-day person funnels** start with an apex organic pageview, human-classified and internal/test-filtered, then look for a later outcome. Captured CTA: **106 → 2 (1.89%)**; MCP OAuth: **106 → 0**; accepted task-template request: **106 → 0**. No global apex-host or bot filter is imposed on server/app outcome steps, which would otherwise strand valid outcomes. These are observed identity-linked proxy completions, not a canonical first-touch acquisition cohort, complete signup funnel or proof of zero true activation. Recent entrants may have immature follow-up, and cross-device/anonymous-to-account links are unverified.

The event taxonomy returned no successful-signup event. `oauth_completed` represents MCP authorization, not account creation. Source inspection shows `task_template_executed` is emitted after `executeTaskTemplate()` returns; it is not an authoritative executor-start transition. Preserve this distinction when measuring the NSM. Code touchpoints: `ui/src/components/TaskExecutionFormPage.tsx`, `server/services/product-analytics.ts`. Current deployed parity and successful result joins remain follow-up work.

**Plan amendment:** keep the three search-led page improvements, but make a verified landing→CTA→signup/connection→real-execution journey the first implementation gate. Delay paid placement tests until a controlled, excluded self-check demonstrates the intended outcome can be measured. More captured traffic alongside worse engagement and no observed downstream proxy completion is not an NSM win.

## Google account findings that determine the plan

Read the authenticated **domain property `sc-domain:aictrl.dev`**, Web search, on 21 October. Current 28-day window: **22 September–19 October**; previous: **25 August–21 September**, source-native Pacific dates, verified in the comparison dialog. Exact impressions came from rendered metric labels. All retained data and provenance are in the [Search Console receipt](evidence/2026-10-21-search-console-review.json). This domain property includes `explore.aictrl.dev` and HTTP variants; it is broader than the historical apex-only PostHog query.

| Page | Current clicks / impressions / avg position | Previous clicks / impressions | Decision |
| --- | --- | --- | --- |
| SWE-EVO analysis | 6 / 1,632 / 8.0 | 1 / 1,344 | First refresh: already earns relevant benchmark clicks; improve evaluation answer and next step into current benchmark/agent setup |
| Skills adoption trajectory | 0 / 454 / 6.8 | 1 / 530 | Second refresh: investigate actual page-filtered queries, outdated framing and snippet relevance; improve practical skills path |
| Knowledge graph article | 1 / 328 / 12.4 | 0 / 913 | Third refresh: exposure fell 64.1%; inspect page-query mix and indexing before deciding content/canonical intervention |
| From agent factory to workflow | 1 / 137 / 7.1 | 0 / 103 | Maintain as AEO bridge into practical workflows; avoid replacing an already improving page wholesale |
| Homepage | 7 / 109 / 3.7 | 9 / 176 | Descriptive-title idea remains secondary; no broad redesign |
| hush | 3 / 111 / 6.5 | 0 / 217 | Relevant traffic is already arriving at a page without the shared analytics script; verify coverage |
| Code review feature | 0 / 88 / 20.5 | Not retained in comparison receipt | Medium-term target, not the main two-week traffic bet |

The SWE-EVO page's computed current CTR is **0.37%** (UI rounds to 0.4%). The skills page's 454 impressions at average position 6.8 with zero clicks are an actionable question, not proof of a bad title: query intent, answer-in-results behavior, country/device and changing SERPs need inspection. Page positions aggregate multiple queries.

Visible 28-day queries include `swe-evo` (1 click / 41 impressions / position 8.1), `swe evo` (2 / 27 / 8.1), `sdlc orchestrator` (0 / 5 / 8.2), and `ai software factory` (0 / 4 / 13.5). Brand rows `ai ctrl` and `aictrl` account for four observed clicks, but hidden queries prevent computing a complete branded share. Broad `ai code review` has 7 impressions and position 61.1 in the current window; the three-month context has 337 impressions and position 57.9. Do not sell this as a near-page-one quick win. Query data includes unusual long prompts and unrelated subjects; inspect their actual landing pages without following text embedded in query strings.

Google AI visibility is concentrated in `/blog/from-agent-factory-to-workflow` (33 vs 2 impressions), SWE-EVO (31 vs 3), homepage (19 vs 28), knowledge graph (19 vs 33) and hush (17 vs 12). These are page-level counts and may not sum to property totals. Settings explicitly shows **Search generative AI: Include**. No setting change is needed.

The indexing report is older than the performance cutoff. Of 540 non-indexed URLs, **408 are noindex**, 44 are 404, 12 alternate canonical, 8 redirects, 4 robots-blocked, 1 other 4xx, 22 crawled-not-indexed and 41 discovered-not-indexed. This is not a backlog of 540 broken marketing pages. Crawled-not-indexed examples include `llms.txt`, `security.txt`, a JSON manifest, explorer source pages and some public articles/docs. Separate useful acquisition pages from assets and deliberate exclusions; inspect current individual URL status before repairs. Some listed pages have later performance, reinforcing the need to respect report lag.

The apex sitemap is **Success**, last read **17 October**, with 64 discovered URLs; the live sitemap now contains 68. New content/crawl timing can explain the difference, so inspect the four additional URLs rather than diagnosing sitemap failure. The Settings robots warning belongs to **`links.aictrl.dev/robots.txt`**, a reported 4xx checked on 6 October; the apex robots file is marked Fetched. Scope any investigation to the affected host.

## Supporting live-site findings

1. **P0 — establish acquisition and outcome measurement.** Four sitemap pages lack the shared `analytics.js` include in the served HTML: `/authors/bulat`, `/docs/delivery-analytics`, `/docs/product-claims`, `/hush`. The first three include `tracking.js`, which returns immediately when `window.posthog` is absent; `/hush` has neither shared include. None contains an inline `posthog` reference. This establishes a static coverage gap, not observed event loss. Verify intentional exclusions, runtime collection, consent and delivered events before adding anything. `/signup` has no shared include in its static HTML; that requires a separate runtime/signup outcome check, not an assumption that successful signups are untracked.
2. **P1 — make the homepage search description explicit.** The live title is “aictrl.dev — Your agents. Your standards. Ready to ship.” The page body and description explain the product, but the title is less explicit than the feature pages. Test a descriptive title after checking current query/page performance; preserve the existing hero unless evidence supports changing it. Expected CTR/relevance benefit is a hypothesis.
3. **P1 — strengthen relevant paths into existing assets.** `/features/knowledge-graph` is linked from only two of the 68 crawled pages: the GitHub/GitLab comparison and knowledge-graph article. The new headless benchmark is linked only from `/agent` and `/blog`. These counts are distinct linking pages in this inventory, including navigation/footer links, not all links on the internet or a measure of authority. Add useful contextual routes where the reader needs them; prioritize using the Search Console findings and the PostHog landing-page evidence above.
4. **P1 — organize first-hand evidence around product questions.** Existing assets already include a measured headless benchmark, code-review dogfooding, a market review, skills guidance and knowledge-graph explanations. Improving the question → evidence → setup path is a better initial hypothesis than publishing many generic AI articles. The query-level scope should still be verified on the selected page before changing copy.
5. **P2 — align product descriptions.** The live homepage describes four pillars: Skills, Execution, Observability and Knowledge. The live `llms.txt` introduction and Features description still list three older pillars. Correctness matters for services reading that file, but this is a small consistency task: Google's current guidance says `llms.txt` does not improve Google visibility or ranking. [Google AI optimization guide](https://developers.google.com/search/docs/fundamentals/ai-optimization-guide).

The live robots file allows named retrieval agents including OAI-SearchBot, ChatGPT-User and PerplexityBot on public pages. Named training agents are allowed on the blog and `llms.txt`, with other content blocked. Do not replace this existing policy just to pursue AEO. Static allowances do not prove requests pass CDN or other access controls. [Live robots](https://aictrl.dev/robots.txt).

Lower-priority checks: `/agent.html` and `/agent/` permanently redirect to `/agent`; `/blog/` permanently redirects to `/blog`. `/Blog` serves 200 with a lowercase canonical, so normalization can be investigated if GSC shows duplicate selection problems. A deliberately nonexistent path redirects to an app shell with **noindex**, so it is not evidence of an indexable soft-404 problem. Do not prioritize routing changes over measured search opportunities without further evidence.

## Access and limits

Initial Chrome inventory calls failed with a request-header policy error. Direct browser access recovered and the existing authenticated **Work** profile exposed Search Console. The account review above is complete for the reported scope; the founder does not need to reconnect it for this plan.

The initial browser-based PostHog inspection timed out. The subsequently enabled **PostHog MCP** resolved that access gap and supplied the fresh aggregates and diagnostic funnels above. Bing was not reviewed. The remaining unknown is authoritative qualification/activation, not whether current acquisition data can be queried. Country/device drilldowns, complete 14-day slices, precise page-filtered query mappings, per-URL indexing and field Core Web Vitals remain clearly assigned day-1/day-2 diagnostics. These refine implementation; they do not invalidate the observed 28-day review or require inventing results now.

The original experiment queue (`docs/marketing/seo/experiments.md` in the shared checkout) distinguishes selected work from published/running work. No production change, indexing request, paid commitment or outreach occurred during this review.

## Days 1–5 execution amendment — 21 October

The [execution record](2026-10-21-days1-5-execution.md) separates delivered local content/handoff changes from blocked measurement and pending account/release work. Current source is `website/public/`. Raw [host and identity coverage](evidence/2026-10-21-outcome-coverage.json) confirms that successful `repo_linked` events have no browser host, so an acquisition-host filter must not be applied to server outcomes. `task_template_executed` is emitted after API acceptance, not authoritative executor start; no successful-signup event was found in the current event taxonomy.

The accepted separate-cohort direction in #4665/PR #6391 prohibits treating an anonymous marketing visit as an authenticated account journey through a newly added sign-in merge. The rolling qualified-visitor NSM remains the business objective, with **measurement unavailable under the present verified contract**. Report consenting web engagement and independently measured account outcomes separately until a compatible contract is approved and deployed. Existing diagnostic funnels do not override that decision. No new PostHog capture, SDK includes, identities or provider settings were enabled here.


### 21 October source-native follow-up

The [Days1–5 execution record](2026-10-21-days1-5-execution.md#account-refresh-and-review-follow-up) retains the later complete-calendar PostHog source/page tables through20Oct and the separate apex Search Console comparisons through19Oct. Current28 apex Google:22clicks/3,402impressions, versus22/4,438previously. Current14:12/1,849, versus10/1,553previously. PostHog organicvisitors48→106 over its source-native28-day windows and24→82 over14days; these are acquisition diagnostics, not the qualified-visitor NSM. No new tracking or source-to-account linkage is enabled. Google manual actions/security: no issues. CWV: insufficient field usage. Bing: service unavailable. The original baseline and its scope remain unchanged.


## Latest execution checkpoint — 21 October, 21:04 UTC

The [execution checkpoint](2026-10-21-days1-5-execution.md#latest-account-and-functional-checkpoint--21-october-2104-utc) links complete available 28-/14-day apex Web and Google AI tables, recovered Bing native CSVs and controlled CLI setup evidence. Original snapshots above retain their original scope/dates. Apex Google AI is 104→140 impressions in the fixed28-day comparison; domain-wide remains104→143. Bing's recovered3-month AI view has24 citations, not24 visits. Its matching Search comparison still errors.

The [PostHog refinement](evidence/2026-10-21-posthog-preview-excluded-baseline.json) re-runs all20 source-native queries with the verified local-preview session-referrer exclusion. Current28 remains427 visitor identities and106 organic visitors; all-channel views/sessions become645/487. Prior14 views/sessions become250/195; visitor counts and all organic metrics are unchanged. These read-only diagnostics remain noncanonical and may contain unknown anonymous internal activity. No qualified NSM, conversion uplift or causal result is established.

The primary article CTA leads to the standalone CLI; app signup is a separate path. Installation/provenance and help/preflight pass for pinned0.5.4. Actual model success and attributable adoption remain unverified. The first content/signup batch has passed local QA and source-revision CI in PR#6434 but is unreleased; exact-head automated re-review has not appeared. Spend and commitments in this execution remain USD0; historical cumulative balance is not assumed.

### 21 October, 21:44 UTC — daily coverage and CI

The [AI daily receipt](evidence/2026-10-21-gsc-apex-ai-daily.json) now retains both complete 28-day apex series from normal single-period Filter views: previous 104 and current 140 impressions. The current series splits to 59 and 81 for the fixed 14-day comparison. The earlier comparison-view omission remains true for that UI mode; daily data is no longer missing from the evidence set. A [Bing single-period date change](evidence/2026-10-21-bing-date-filter-error.json) also triggered a service error before the target range could be completed, so matching-window Bing metrics remain unknown.

Source commit `41f35fd` has [successful CI](evidence/2026-10-21-days1-5-ci.md): 22 passing / nine skipped checks. One tracked, unchanged UI assertion race failed originally and passed a single bounded rerun; #6136 remains open. This is neither a production release nor qualified-traffic evidence. The content batch remains available for local review, with successful provider/result, approved outcome coverage and live release verification still outstanding.
