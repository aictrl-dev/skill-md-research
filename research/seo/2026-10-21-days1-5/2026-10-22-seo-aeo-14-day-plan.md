# aictrl SEO/AEO plan — 22 October–4 November 2026

Owner: **seo-product-engineer**. Objective: increase relevant organic discovery and valuable referrals that become qualified visitors and real product use.

**Status: Days 1–5 execution in progress, brought forward to 21 October.** See the [execution record](2026-10-21-days1-5-execution.md) for implemented changes, QA and remaining gates. The original account baseline remains below. The [performance review](performance.md) and [account evidence](evidence/2026-10-21-search-console-review.json) contain the baseline and limits. PostHog MCP acquisition and diagnostic funnels are now reviewed in the [performance report](performance.md); Bing initially returned service unavailable, then recovered partial 3-month Search/AI evidence and native CSVs; the matching comparison and sitemap detail still return service errors. No qualified-conversion or ranking improvement is claimed. Local implementation has begun; no publication or purchase is claimed.

**Baseline:** 22 Google Web clicks in both 28-day windows; impressions **4,439 → 3,458 (-22.1%)**; average position **11.2 → 8.6**; Google Generative AI impressions **104 → 143 (+37.5%)**. Windows: 25 August–21 September versus 22 September–19 October, Pacific dates. Domain scope includes subdomains. The opportunity is to turn existing relevant visibility into qualified product discovery while investigating lost knowledge-graph exposure.

**PostHog amendment:** recorded organic visitors increased **48 → 106**, while organic bounce rose **32.7% → 70.4%**. Only **2 of 106** organic entrants reached a captured website CTA in the separate ordered 7-day diagnostic funnel, with **zero observed** matches to MCP OAuth or accepted task requests. Qualification remains unknown because signup, identity coverage and executor truth are unverified. Verify a useful, measurable content→product journey before expanding paid acquisition. These are UTC, apex-host, test/bot-filtered diagnostics; they are not interchangeable with Pacific-date Google clicks.

**Selected work:** refresh SWE-EVO analysis, skills adoption and knowledge-graph article/product path. Maintain and link the improving workflow article; distribute the new headless benchmark through relevant pages. Homepage title improvement is secondary. Broad AI-code-review ranking is a longer-term topic, not the main fortnight bet.

## Execution corrections — 21 October

- Current marketing source is `website/public/`, not this older checkout's `ui/public/`. The execution branch starts at `79596feb5f4c0e35b726e04378bf191277933fe6` from `origin/sandbox`.
- The accepted separate web/account cohort direction in [#4665](https://github.com/aictrl-dev/aictrl/issues/4665) and [draft policy PR #6391](https://github.com/aictrl-dev/aictrl/pull/6391) supersedes this plan's proposed anonymous-to-account joining. Existing captured history is diagnostic; authentication does not grant analytics consent. No new tracking is enabled by this SEO batch. Qualified source attribution remains unmeasured until a compatible approved contract exists. Do not fill the gap with fingerprinting, identity parameters or inferred joins.
- `/blog/from-agent-factory-to-workflow` currently contains a film-production case study. Preserve that firsthand account. The first batch uses the coding-harness article `/blog/framework-matters` for a relevant contextual benchmark link. The existing skills article remains scheduled for substantive review on Day 7, not falsely reported as refreshed now.
- Account access recovered partially. The execution record includes exact SWE-EVO query rows, non-reconciling device/country rows and all five selected URL inspections. The existing published benchmark passed a Google live test and received an accepted indexing request. Apex28-/14-day comparison totals are now read. Manual actions/security report no issues; CWV lacks sufficient field data. Bing later recovered partial 3-month Search/AI evidence while its matching comparison errors. Complete available apex28-/14-day Web and AI page/country/device tables are now retained in the latest execution checkpoint; complete selected-page geographic/device tables are retained, while their repeated headline/segment discrepancy remains unresolved. No search setting or unpublished-page recrawl was changed.
- Single-period Google AI Filter views also supplied all 56 daily rows across the two 28-day windows, reconciling to 104→140 apex impressions and the fixed 14-day 59→81 split. This closes the daily evidence gap despite the comparison Days view omitting its table. Source revision `41f35fd` passed CI after one bounded rerun of an existing UI assertion race; #6136 remains open. The [current checkpoint](2026-10-21-days1-5-execution.md#current-verification-checkpoint--21-october-2144-utc) records remaining provider, policy, review and actual-release requirements.

## Strategy and decisions

Improve the existing discovery-to-product path first. The site has 68 available sitemap pages, including 30 articles, with sound static metadata. Spend the fortnight on measurement, three evidence-rich topic paths, and a small referral experiment. Limit scope to **three substantial page improvements and at most one new practical guide**. Change the selected scope only when day-1/day-2 drilldowns contradict the current page-level evidence.

| Option considered | Benefit | Cost/limitation | Decision |
| --- | --- | --- | --- |
| Refresh existing pages and add contextual links | Reuses original research and setup material; fast to verify | Actual search upside needs GSC; indexing lag remains | Primary approach |
| Publish many generic AI articles or a page for every query variation | Broad topic coverage | Weak product intent, diluted effort and little unique evidence | Exclude from this sprint |
| Buy an SEO/AEO subscription | Convenient reporting | Consumes the small budget before existing accounts are used | Use existing Google/Bing/PostHog accounts |
| Pay for relevant partner exposure | Potential qualified referrals independent of ranking | Fit and conversions unproven | Up to two bounded pilots after tracking works |
| Broad metadata/schema/crawler rewrite | Can repair proven discovery faults | Current static audit found no widespread fault; policy-change risk | Only fix observed account/runtime problems |

Google's [current AI optimization guide](https://developers.google.com/search/docs/fundamentals/ai-optimization-guide) favors useful first-hand material and established SEO practices. It does not support special AI markup or `llms.txt` as Google ranking tactics. Treat concise answers, methods, examples and tables as reader improvements, not a promise of citation.

## Days 1–2: refine the reviewed baseline and verify implementation hypotheses

The Google review has already established 28-day totals, comparison pages, selected queries, AI impressions, indexing reasons, sitemap status and AI inclusion. Preserve that baseline. The tasks below deepen page-query attribution, segmentation and qualification before publishing changes. Use existing authenticated accounts; PostHog acquisition aggregates are already available; authoritative outcome joins and Bing remain follow-up work. Keep the remaining measurement limits explicit while continuing independent improvements.

**Google Search Console**

- Inspect the domain property and the relevant apex URL-prefix property if present. Keep app/subdomain traffic separate; avoid mixing a domain total with apex-only analytics. Export the latest **complete** 28 days and previous 28 days; also compare complete 14-day windows. Let `E` be the latest finalized day actually shown: recent 28 days are `E-27…E`, previous are `E-55…E-28`. Exclude or label preliminary days.
- Export Web performance totals and query/page/country/device breakdowns. Preserve report filters and totals; page/query rows need not sum to property totals because of aggregation and hidden queries. Separate brand variants (`aictrl`, `ai ctrl`, `aictrl.dev`) from non-brand queries with verified filters; retain an unclassified remainder rather than claiming complete query coverage. Inspect 90-day context for trends and seasonality.
- Build a **query-to-page opportunity table**: query/theme, intent, current URL, clicks, impressions, CTR, position, comparable-period changes, country/device, relevant product action, proposed intervention, confidence. Compare CTR within similar position/device/intent groups, not a universal CTR benchmark. Prefer relevant pages with observed demand and positions roughly 4–20; at low volume use broader themes and counts rather than fabricated uplift.
- Inspect Page indexing reasons, submitted sitemap status and last read, manual actions/security issues, and mobile Core Web Vitals when field data exists. Inspect the top three opportunity URLs plus `/agent` and the benchmark for indexed status, Google-selected canonical and crawl date. HTTP 200 is not proof of indexing. Newly published pages get a separate maturity note.
- Read **Settings → Search generative AI**, including inherited controls. Record whether the actual property is included. If excluded, investigate the deliberate policy and prepare a proposed change; do not silently change it. Inspect the **Generative AI performance (Search)** report: impressions by page/date/country/device and comparable windows. If the report is absent, record its absence and possible insufficient impressions; do not turn missing data into zero visibility. This report is an overlapping view of Search performance, not an extra traffic total, and does not supply an exact prompt-level conversion funnel. [Report definition](https://support.google.com/webmasters/answer/16984139?hl=en), [inclusion controls](https://support.google.com/webmasters/answer/16908024).

**Bing Webmaster Tools**

- Export Search Performance, indexing/site scan and sitemap evidence for the same dates where available. Keep Bing's metric definitions and timezone attached.
- Review **AI Performance** citations, cited pages and grounding queries. If available with sufficient data, use **Topics Portfolio** and its opportunity queries to refine the shortlist. These are sampled/directional citation signals, not qualified visits, rank or complete market share. A missing Topics tab is not proof of zero demand. [Bing AI Performance](https://www.bing.com/webmasters/help/ai-performance-9f8e7d6c), [Topics Portfolio](https://blogs.bing.com/webmaster/2026/10/introducing-topics-portfolio-beta-in-ai-performance/).

**PostHog, project 88595 — acquisition baseline reviewed; verify outcome coverage**

- The metric catalog was checked and is empty. Existing results are ad hoc, not a canonical NSM. Inspect event schema and existing dashboards before adding new definitions. Use Web Analytics/typed queries for channels, landing pages and visitors where sufficient; use documented SQL only if the needed joins exceed those tools.
- Recompute latest complete 28-/14-day production traffic by landing page and source: Google, Bing, other organic, identified AI referrers, each partner, direct/unknown. Confirm available referrer/session/UTM properties rather than inventing event fields. Filter apex host for acquisition and include app host only for verified downstream joins; exclude sandbox, development, identified internal accounts and scanners using validated rules.
- Verify actual signup, demo completion, product installation/connection and executor-start semantics against application truth. Track raw visitors → qualified visitors → first executor start → successful result. The existing `cta_clicked` event is an intermediate action; its `location` is supported by the deployed tracking script, but delivery and campaign linkage still need runtime verification. Do not equate GitHub clicks with installs or demo clicks with bookings.
- Verify consented anonymous-to-account and cross-domain joins. Use cohort analysis only where linkage exists; otherwise show coverage and unassigned outcomes separately. Read-only evidence checks should not create fake conversions; label/exclude any necessary controlled self-test.

GSC daily dates are Pacific Time; the existing PostHog snapshot is UTC. Preserve source-native charts and normalize timestamps for any actual reconciliation. GSC query privacy/truncation prevents exact query-to-person attribution. [Google dimensions and limitations](https://support.google.com/webmasters/answer/17011259?hl=en).

**Day-2 deliverable:** augment the existing Google and PostHog baselines with page-filtered query/device/country evidence and verified outcome coverage. Run one consented, internally labelled/excluded journey from a selected landing page through its intended CTA, successful signup/connection and executor lifecycle where applicable. Prove identity linkage and event meaning or document the exact break. Confirm or revise the three refreshes and measurement gaps. The initial selection is already supported by the account review; do not replace unknown conversions with guessed numbers.

## Selected page work and acceptance criteria

| Priority / path | Current evidence and work | Product next step / verification |
| --- | --- | --- |
| 1 · `/blog/swe-evo-analysis` | 1,632 impressions, 6 clicks, position 8.0; previous 1,344/1/8.5. Refresh the answer to what SWE-EVO measures, how it differs from other coding benchmarks, and practical limits. Preserve original sources and distinguish task quality from harness overhead. Inspect page-filtered queries before revising title/snippet. | Link readers needing runtime/cost evaluation to the headless benchmark and released agent setup. Verify evidence links and actual supported setup. Target hypothesis: CTR from computed 0.37% toward 0.7% over a comparable future 28-day window at similar query/position mix; this is an experiment target, not a forecast or day-14 pass/fail claim. |
| 2 · `/blog/skill-md-adoption-trajectory` | 454 impressions, zero clicks, position 6.8; previous 530/1/7.1. Verify actual query intent. Refresh dated adoption facts against original sources; separate historical trajectory from current install/governance/evaluation guidance. Improve the title only if the visible answer matches. | Relevant contextual links to `/plugins`, `/docs/skills` and the skill-evals evidence. At least two useful links, accurate setup and dates, documented title/content version. Target hypothesis: at least 3 clicks at comparable 28-day exposure without increasing irrelevant demand; qualification stays primary. |
| 3 · `/blog/knowledge-graph-agentic-ai` and `/features/knowledge-graph` | Article impressions 913 → 328, average position 11.0 → 12.4; 1 current click. Feature has 10 impressions and position 9.8, with only two linking sitemap pages. Inspect query changes and current index/canonical status; add a concrete code dependency/impact example and clarify supported capabilities. | Link evidence → product example → `/docs/knowledge-graph`. Add at least two relevant contextual linking pages to the feature. Recovery target is stable/improving relevant impressions and qualified actions, not restoring all historical queries indiscriminately. |
| Supporting · `/blog/from-agent-factory-to-workflow` | Search 137 impressions/1 click; AI impressions 2 → 33. Preserve its first-hand account; improve practical navigation and answer accuracy without a wholesale rewrite. | Link an existing working workflow example and setup path; keep illustrative film content distinct from measured product execution. |
| Supporting · `/agent` and `/blog/headless-coding-agent-cli-benchmark` | New benchmark is linked only from `/agent` and `/blog` in the live crawl; absent from the reviewed prepublication window. | Add two relevant contextual linking pages. Inspect current Google URL status before any legitimate recrawl request. No failure claim based on historical zero pageviews. |
| Secondary · homepage and code-review feature | Homepage already has 7 clicks at position 3.7; code-review feature 88 impressions, zero clicks at 20.5, while the broad query is around position 61. | Proposed homepage title: **AI Workflow Orchestration for Engineering Teams \| aictrl**. Test only after higher-priority work. Preserve hero. Code-review content work can follow evidence but should not consume the whole fortnight. |

These are **three substantial refreshes**, with supporting links and small copy fixes. A new guide may replace a refresh only if a verified page-query gap cannot be answered by the current pages; cap at one. Start with useful existing pages rather than query-variant proliferation.

Keep definitions and supporting evidence in accessible HTML. Use author/review dates, original data and limitations where meaningful. Change `dateModified` only for actual substantive updates. Existing schema parses; add or alter it only to match visible content and an applicable supported type. Do not spend the sprint chasing FAQ rich results or adding unverified review ratings. Small `llms.txt` alignment is capped at 30 minutes and has no claimed Google ranking effect.

## Fourteen-day execution schedule

SEO owns the work and reporting. Engineering and onboarding owners are collaborators for code, instrumentation and activation; this plan does not claim they have already accepted assignments. Estimated effort is a planning allowance, approximately **25–30 hours**, adjusted after the account review. Implementation follows repository skills, checks, release and approval requirements.

| Day/date | Work and owner | Deliverable / check |
| --- | --- | --- |
| 1 · Thu 22 Oct | SEO: deepen existing GSC review with selected-page query/segment and current index checks; inspect Bing if accessible | Preserve 28-day baseline; classify stale exclusions and selected-page intent; AI inclusion is already Include |
| 2 · Fri 23 Oct | SEO + analytics/onboarding: validate the content→CTA→signup/connection→execution journey and identity links; inspect four script gaps | Controlled self-check excluded; actual successful outcomes and executor truth mapped; failures scoped before instrumentation changes |
| 3 · Sat 24 Oct | SEO + engineering: prepare verified measurement repair and SWE-EVO search/content changes | Reviewable changes; no collection/consent bypass; verified event names and exclusions |
| 4 · Sun 25 Oct | SEO: prepare SWE-EVO refresh and evidence trail | Exact copy, sources, setup path, acceptance checks ready |
| 5 · Mon 26 Oct | SEO + engineering: validate and release first batch through normal workflow | Live URLs verified, change timestamps, canonical/indexing checks and legitimate submission/recrawl actions recorded |
| 6 · Tue 27 Oct | SEO: contextual links into selected pages; baseline fixed AEO prompt panel | Link map; reproducible observation sheet; initial citation/accuracy evidence if tools available |
| 7 · Wed 28 Oct | SEO: first checkpoint, finish skills-adoption refresh | Confirm indexing/measurement, review Google/Bing complete data; correct blockers, avoid reacting to one-day rank noise |
| 8 · Thu 29 Oct | SEO: knowledge-graph article/product-path refresh | Runnable example or original evidence, clear next action, no duplicate query targeting |
| 9 · Fri 30 Oct | SEO + engineering: release second batch; minor product-description alignment | Live verification; updated real lastmod dates; `llms.txt` four-pillar wording consistent |
| 10 · Sat 31 Oct | SEO: shortlist three relevant partner placements, including a free option | Audience/placement/terms evidence, destination, UTM and cost; no unsupported audience estimates |
| 11 · Sun 1 Nov | SEO: prepare one free submission and up to two small paid pilots | Reviewable copy and budgets; proceed only after the outcome-measurement gate, under existing authority and verified payment/access conditions |
| 12 · Mon 2 Nov | SEO: verify accepted/live placements, destination and measurement | Actual page URLs and dates, receipt/reservation reconciliation; pending submissions remain labelled pending |
| 13 · Tue 3 Nov | SEO: repeat the AEO panel; inspect conversions and new relevant queries | Same prompt/engine/locale settings, cited URLs and accuracy; no manual panel results substituted for market rank |
| 14 · Wed 4 Nov | SEO: compare mature data, report completed work and next decisions | Before/after by page/source, qualified outcomes, spend, limits and continue/change/stop decisions; schedule longer follow-up |

If account access is delayed, keep the dates for independent work but shift any dependent selection/measurement checkpoint explicitly. Do not backdate a baseline or pretend a future step occurred.

## AEO measurement that can guide decisions

Use first-party Google Generative AI impressions and Bing citations where available. Keep them separate from organic clicks, referral visits and qualified outcomes. Google AI impressions overlap the overall Search data, so do not add them to a total. Bing citation volume is not a ranking or proof of a visit.

As a qualitative supplement, use the same eight unbranded questions on Google AI search, Bing/Copilot and ChatGPT Search when accessible:

1. What is a headless coding agent, and when should a team use one?
2. How can I run a coding agent in GitHub Actions without interactive prompts?
3. How can I compare coding-agent CLI startup, memory and token overhead?
4. How can an engineering team measure AI code-review quality?
5. How can I give AI review agents codebase dependency context?
6. How should a team govern and evaluate reusable SKILL.md instructions?
7. How can I trigger an AI workflow from a GitHub issue or pull request?
8. How can I trace an AI-generated finding back to code and execution evidence?

Run in clean conversations on days 6 and 13, recording exact prompt, engine/model label, date/time, locale, web-search state, cited URLs and any inaccurate aictrl claims. Do not mention aictrl in the question, repeatedly nudge the model, or count unsupported brand mentions as citations. Report successful observations and inaccessible/no-answer cases separately. This small panel is qualitative and variable; it cannot establish broad AEO market share or a causal uplift. Replace questions only before the first baseline and record why.

## Partner budget and economics

The existing allocation is **USD 200 total across all runs**. This review spent **USD 0** and made no commitments; historical spend elsewhere has not been reconciled, so actual available balance is **unverified**, not assumed USD 200.

For this fortnight propose **up to USD 100** across at most two one-time pilots, each capped at **USD 50 all-in**, leaving the rest uncommitted if available. Reconcile prior spend and reserve the actual authorized amount before checkout. No compulsory spend and no recurring/uncapped commission commitment.

Select placements only when a specific relevant engineering audience, visible page position, accurate copy, usable destination and measurable outbound link are verified. Do not start a paid pilot until the controlled landing-to-successful-outcome journey is measurable; if it cannot be verified this fortnight, retain the budget and continue free work. Prefer a free integration/resource listing where the product genuinely fits. Reject pay-for-rank links, broad “AI tools” traffic bundles and authority-score-only pitches. Paid relationships should be disclosed and links appropriately qualified under platform/search policy.

Use stable source-specific UTMs and record views/visitors separately from successful signup/setup. Review each live placement at 7 and 28 elapsed days; a day-12 placement will not have mature results by day 14. If tracking is broken or audience relevance is poor, make no further commitment. Continue a placement only with credible qualified engagement or a documented low-volume hypothesis; set an acceptable cost ceiling from actual customer economics, not an invented CAC number. Outreach messages still need explicit sending authorization under the agent brief; prepare drafts without treating this planning request as permission to send.

## Scorecard and decision rules

**NSM:** unique qualified visitors from organic search or eligible partner referrals in a rolling 28-day window, following the agent's agreed identity/window contract. Count each person once where verified identity joins permit it; report measured units and coverage otherwise. Qualification requires an observed successful signup, verified demo request or product installation/connection. A click alone is not qualification. Track executor starts, successful results and mature follow-up beside it.

| Level | What to record | Day-7 / day-14 decision |
| --- | --- | --- |
| Delivery | Baseline coverage; three selected improvements; relevant new links; repaired verified measurement gaps; actual live dates | Finish or fix missing acceptance evidence before expanding scope |
| Discoverability | Indexed/eligible selected URLs, selected canonicals, crawl dates and blockers | Fix genuine exclusion/canonical issues first; absent indexing of a new page alone is not proof the content failed |
| Search demand | Relevant non-brand impressions/clicks, query/page CTR and position by device/country | Continue where the intended query mix improves; investigate irrelevant demand or mismatched snippet; avoid changes driven by a tiny sample |
| AEO | Google AI impressions, Bing citations/cited pages, qualitative prompt observations | Check inclusion and factual accuracy; improve weak evidence paths; do not invent a universal “AEO position” |
| Value | Qualified visitors, qualification rate, first executor starts, successful results and coverage by source/page | A traffic gain without qualification prompts intent/CTA/onboarding investigation; do not call it an NSM win |
| Economics | Settled spend, commitments, qualified referrals and cost where denominator is positive | Stop further spend on poor fit/broken measurement; keep incomplete pilots pending to their real review date |

No credible numerical traffic-growth forecast can be set from the available evidence. Day 2 should refine the observed search baseline and establish an outcome baseline if access permits. The selected-page CTR/click targets above are explicit hypotheses; qualified-visitor growth cannot be numerically targeted honestly until that baseline exists. On 4 November report only dates finalized in each source, mark conversion cohorts immature where necessary, and schedule **18 November** for a longer SEO follow-up plus each partner's actual 28-day review. Fourteen days is an execution and early-signal window, not a guarantee of ranking changes.

## Original review boundary

Google Search Console was actually inspected and the selected work above reflects its page/query, AI and indexing evidence. The plan is ready; implementation and later results are future work. Fresh PostHog MCP acquisition and diagnostic-funnel evidence is incorporated. Qualified-visitor and authoritative activation baselines remain unknown because the necessary identity/signup/executor contracts are not yet verified. Bing, country/device drilldowns, individual URL inspection and current query-to-page joins are bounded operational follow-up, with no unsupported claims that they were completed during this review. The $200 allocation remains intact as an authority limit; no spending or balance reconciliation is claimed.

This paragraph preserves the initial planning boundary. The execution corrections and linked current checkpoint above supersede its pending account-capture and implementation statements; release and qualified outcomes remain unproved.
