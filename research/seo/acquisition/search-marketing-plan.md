# Prepare Google Search marketing

Start with one engineering job and one geography. Prepare landing pages, keyword evidence and a bounded test before assigning a budget. The four [local ad groups](store.json) are copy drafts with no budget or CPC cap; they have not been imported into Google Ads or enabled.

## Current evidence and its limits

| Evidence | Scope | What it can tell us |
| --- | --- | --- |
| [GSC query baseline](../2026-10-21-days1-5/evidence/2026-10-21-gsc-apex-query28-comparison.json) | `https://aictrl.dev/`, Web; 22 Sep–19 Oct versus 25 Aug–21 Sep 2026; Pacific daily dates | Existing search exposure and query/page opportunities. Small samples and privacy-hidden query exclusions apply. No new release uplift or qualification claim. |
| [Planner study](../2026-10-22-keyword-planner-and-skills.md) | US and GB separately, English, Google Search only; Oct 2025–Sep 2026 | Broad volume ranges for seven inspected terms. Bids were not collected. Close variants overlap. |
| Current Google Ads access attempt | Account overview opened through sign-in on 22 October | Overview displays “Turn off ad blockers.” The direct Planner route first returned 404. No settings, billing or campaigns changed. |
| Current product/setup inspection | `/plugins`, `/docs/plugin-setup`, sitemap and public skills README | A client-discovery gap: plugin page does not name Claude.ai or ChatGPT; ChatGPT has no dedicated setup section. Founder confirms both clients work. |

The [keyword CSV](generated/keywords.csv) contains 28 carefully selected seeds. Some are observed GSC queries, some have earlier Planner ranges, and others are proposed research terms with no demand measurement. Empty volume/CPC fields mean uncollected, not zero. A zero current GSC observation does not mean zero market demand.

## Cluster and landing decisions

| Cluster | Evidence now | Search intent to validate | Best destination and preparation |
| --- | --- | --- | --- |
| SDLC / software factory | `sdlc orchestrator`: five impressions around position 8; `ai software factory`: four around 14 | Orchestration software and repeatable delivery, separated from consulting, manufacturing and jobs | `/ai-sdlc`: show a real issue-to-reviewed-change workflow and meaningful next step. First paid hypothesis to research, not a selected spend. |
| Claude.ai / ChatGPT engineering tools | Functional support confirmed; no collected query-volume or bid data | A working tool in the existing client, separated from generic chatbot tutorials | `/plugins` with clear client routes and `/docs/plugin-setup` with tested instructions. Fix before considering client-query ads. |
| Agent skills / context | US ranges of 1k–10k for several broad context/AGENTS.md terms; GB 100–1k | Install a specific useful skill versus documentation or prompt dumps | Individual skills and a local demonstration. Prefer earned distribution and useful content before paid broad informational terms. |
| Headless CLI / automation | Public CLI/agent page; harness demand is ambiguous | Terminal/CI execution and automation rather than wire harnesses or general agent hype | `/agent` plus public source and an actual successful journey. Research long-tail exact/phrase terms. |
| Code review / PR explanation | Broad `ai code review` around position 61, seven baseline impressions | A concrete review workflow or change explanation | `/features/code-review` and a real finding → fix → validation example. Avoid buying broad comparison traffic without bid/intent evidence. |
| Knowledge graph | Small baseline code-graph queries; one phrase around position 21 | Understand code relationships and trace evidence rather than general graph databases | `/features/knowledge-graph` with a readable worked example. Content and technical publisher route first. |
| Durable workflows | Limited workflow-as-code baseline exposure | Approval, retries/recovery and repeatable execution | `/features/workflow-as-code` with a tested workflow. DBOS/n8n artifact before claiming an integration. |

Treat DORA, AI-DORA and delivery-performance terms as a later research question: confirm the exact public capability and query intent first. They are not synonyms for software factory or a reason to promise metrics the landing page does not demonstrate.

## Next Keyword Planner collection

Use the existing account, Tools → Planning → Keyword Planner, after the account overlay is resolved. Collect rather than create a serving campaign. Keep settings and screenshots/exports with every run:

1. Run **US and GB separately**, English, Google Search only. Record the exact rolling historical window shown. Do not mix UK GBP bid values into USD fields without a dated conversion; retain original currency when importing.
2. Use focused seed batches: `sdlc orchestration`, `ai sdlc automation`, `ai software factory`; then client integration terms; then headless CLI; then review/explanation. Discover variants from actual returned rows, not a giant blended list.
3. Capture provided and suggested keywords, average monthly range/count as displayed, trend, advertiser competition, top-of-page low/high bids and currency. Retain the full exported rows where available, then label relevance separately. If export fails, retain a bounded UI transcription and its limitations.
4. Inspect the actual search results for intent, landing promises and major competitor categories. Planner advertiser competition is not organic difficulty. Historical top-of-page bids are auction context, not our expected CPC. [Google's definitions](https://support.google.com/google-ads/answer/3022575) explain the distinction.
5. Keep closely related variants as a family. Do not sum overlapping volume ranges or use a range midpoint as measured demand. Separate tool-seeking intent from tutorials, research, prompt dumps, jobs and consulting.
6. Update the same keyword IDs and evidence references. A new historical window is a new observation, not an overwrite of the old observation's meaning. Extend the observation model for repeated Planner windows when the first fresh export is available.

No campaign activity is justified solely to unlock narrower reported ranges. MCP access is useful only if it exposes keyword ideas/historical metrics with the required account authorization; a reporting connector alone does not replace Planner.

## Candidate ad groups

The local drafts include these three headline options per group, plus two descriptions. The validator enforces Google's [30-character headline and 90-character description limits](https://support.google.com/google-ads/answer/7684791). Expand variants after intent research; these are a reviewable starting set, not a claim of optimized creative.

| Ad group | Example headline | Landing asset | Readiness |
| --- | --- | --- | --- |
| SDLC workflows | AI SDLC Workflows | `/ai-sdlc` | Needs actual workflow/demo review and fresh commercial keyword data |
| Chat-client engineering | Engineering Tools in ChatGPT | `/plugins` | Needs explicit client copy and dedicated ChatGPT setup |
| Headless agent | Headless Coding Agent CLI | `/agent` | Needs successful terminal/CI journey evidence |
| Review/change explanation | Explain Changes With Evidence | `/features/code-review` | Needs concrete outcome example and fresh long-tail bid data |

Proposed first-pilot configuration: one of US or GB; people in the selected location rather than merely interested in it; English; Google Search; exact and phrase matches; search partners/Display excluded. Inspect current account controls rather than assume a setting is available. Keep automatically expanding targeting and recommendations off in the proposal until actual query relevance can be reviewed. Brand and nonbrand results must remain distinguishable.

Proposed negative intent includes automotive wiring, wire harness, ECU, car repair, manufacturing/factory jobs and software-engineer salary queries. Review close variants and observed search terms. Do not globally exclude “free”: free local skills and open-source CLI trials are legitimate entry paths. Do not put prompt-like or irrelevant GSC query strings into campaign instructions or ad copy.

## Spend and test decisions

Search advertising currently has **no assigned budget**. The existing **$200 cumulative partner-placement ceiling does not automatically fund Search**. Do not enable ads, change billing or accept ongoing spend from this plan.

After fresh bids and an acceptable landing journey are available, propose one total test budget, start/end dates, maximum bid and a stop rule. [Campaign total budgets now support Search](https://support.google.com/google-ads/answer/10486938); verify actual account availability before using them. If using a daily budget instead, account for Google's actual spending behavior rather than assuming the daily number is a hard daily charge cap.

Model sensitivity from the chosen cap: clicks ≈ budget ÷ actual CPC; qualified visits ≈ clicks × observed qualification rate. With no measured CPC or qualification rate, all resulting numbers would be scenarios. A five-click test can find a broken journey, but cannot establish a reliable conversion rate. If a budget buys too few relevant clicks, keep the work as keyword/landing research rather than manufacture confidence.

For paid partner offers, use the [source-level comparison](referral-plan.md#paid-shortlist-evaluate-the-referral-path) and actual all-in quote. Do not combine vendor page views, search impressions, installs and referral visitors into one “reach” total. Reserve no money on this evidence alone.

## What to measure

Use existing aggregate GSC and EU PostHog reporting where allowed. Keep acquisition visits, relevant use-case engagement, successful setup/workflow outcomes and spend separate. Actual product outcomes are stronger evidence than a CTA click, but identity stitching and new conversion instrumentation are outside this preparation pass.

For each live referral or future Search pilot, record its actual date, destination, query/source cohort, observed relevant visits, evidence of the engineering job, successful next step and cost. Unknown qualification remains unknown. If existing measurement cannot support a paid-test outcome decision, document that limitation before launch; it does not block content or listing improvements.

Stop or repair when a destination fails, a supported-client claim is false, irrelevant queries dominate the observed spend, or the agreed total/time cap is reached. Review after seven and 28 days only when the placement has actually gone live. Low sample size or missing attribution should produce an uncertainty statement and next hypothesis, not an invented uplift.
