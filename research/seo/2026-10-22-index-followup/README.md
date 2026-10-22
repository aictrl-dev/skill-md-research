# Existing public setup pages: Google index follow-up

22 October 2026, **12:09–12:10 UTC**. Fresh authenticated Google Search Console URL Inspection reads now report both existing public setup pages as indexed. The [minimal inspection receipt](inspection.json) preserves exact displayed fields; the [21 October inspections](../2026-10-21-days1-5/evidence/2026-10-21-gsc-segments-and-inspection.json) had reported both unknown to Google.

| Existing public URL | 21 October | 22 October |
| --- | --- | --- |
| `https://aictrl.dev/agent` | Unknown to Google | Page is indexed; Google canonical is Inspected URL |
| `https://aictrl.dev/blog/headless-coding-agent-cli-benchmark` | Unknown to Google | Page is indexed; Google canonical is Inspected URL |

Both reports show successful Googlebot smartphone fetches, crawling/indexing allowed, HTTPS and one valid breadcrumb item. Crawl times remain exactly as displayed with **unlabelled timezone**; they are not converted to UTC. The time either page entered the index is unknown. Both already indexed URLs also show a temporary sitemap processing error; its cause and completeness of discovery reporting are unknown.

This follow-up performed **two inspection reads, zero live tests, zero indexing requests and zero setting changes**. The observations establish index/canonical status for these existing public URLs. They do not prove ranking gains, qualified traffic, causality from earlier requests, or production/index status for the latest article and metadata revisions.

## Separate release checkpoint

Metadata source PR [#6451](https://github.com/aictrl-dev/aictrl/pull/6451) merged at **12:00:18 UTC**, after the separate routing PR #6447. Release [#6446](https://github.com/aictrl-dev/aictrl/pull/6446) now has head `c051653756b2ee41642b041a9984dc081d847f7a`, **19 paths**. The [head-specific promotion preflight](promotion-preflight-c051.json), captured 12:02:33 UTC, records conflict-free tree `d93ecdecd2acb609599f9ecf22e75bbc8ddccf1d`, all 19 candidate paths equal, all four metadata files equal reviewed source `57c59605...`, and main's separate open-source-review article preserved.

This is read-only source/tree evidence. Production promotion, current-head CI/deployment/review approval and fresh production-body verification remain pending at this checkpoint; the separately required apex Worker publication is not established. The [earlier partial sandbox Hosting proof and full deployment failure](../2026-10-22-combined-release/README.md) remain historical and head-specific.

Days 1–5 remains incomplete. No successful provider journey, policy approval, new collection, task execution, spending or qualified-acquisition outcome is claimed.

## Current-turn checkpoint — 12:19 UTC

The [fresh c051 sandbox Hosting receipt](sandbox-live-c051.json), captured **12:19:27 UTC**, verifies **nine HTTP 200 responses**, each with bytes and SHA-256 equal to source `c051653756b2ee41642b041a9984dc081d847f7a`. All four reviewed metadata hashes match, including the category/filter discovery surfaces, modified dates, article canonicals and llms.txt. The 12:09–12:10 positive Google index observations above remain separate evidence for the two existing public URLs; they do not establish index status for these latest content revisions.

The runtime boundary matters. The older **ac7** full sandbox deployment [39772435137](https://github.com/aictrl-dev/aictrl/actions/runs/39772435137) succeeded at **12:15:19 UTC**, after the fence drained normally at **12:14:18 UTC**. The **c051** website workflow [39774872026](https://github.com/aictrl-dev/aictrl/actions/runs/39774872026) succeeded at **12:18:13 UTC**, and its [website job](https://github.com/aictrl-dev/aictrl/actions/runs/39774872026/job/119817876640) passed at **12:18:12 UTC**. Its app job `119817879529` was **skipped at 12:15:28 UTC**. Thus current static content is verified, while the latest successfully deployed runtime remains ac7, predating routing PR #6447. The later healthy ac7 drain does not establish a root cause for the earlier fence timeout or the cases in #5392/#4779.

The new [Bug/P1 scope-gate issue #6454](https://github.com/aictrl-dev/aictrl/issues/6454) records the reproduced boundary: the selected fbc→c051 comparison reports app=false/website=true, whereas last-successful ac7→c051 spans ten paths and reports app=true/website=true. The last-successful resolver is inside the app job that the preliminary scope gate skipped. This checkpoint records the defect and existing runtime, not a repair, redeployment or production result. [Issue #6312](https://github.com/aictrl-dev/aictrl/issues/6312) separately distinguishes Firebase Hosting from the custom-domain/apex Worker publication.

Current-head [CI 39774882672](https://github.com/aictrl-dev/aictrl/actions/runs/39774882672) completed **20/20 successful checks at 12:15:59 UTC**, with Static Checks passed. The actual repository-picker E2E executed **one passing test**; selected Gherkin execution remained skipped. Release #6446's readback was **31 successful / six skipped / zero pending or failing**, but **REVIEW_REQUIRED**. Head c051 and its 19-path scope are unchanged; no fresh AI review appeared through the latest poll, whose cap is **12:30:18 UTC**. Metadata PR #6451 is merged. Green checks do not supply the required release approval or production publication.

The owner selected **Gemini 3.8 Flash**. A small isolated CLI check was prepared and validated offline, but no provider request was made because authorized Google configuration was unavailable. A secure configuration-reference question remains pending. This establishes **zero provider requests / USD 0 spend**, not a successful provider result or full journey. No credential values, environment details or other-provider inventory are recorded.

Product issue #4665 was re-read as **OPEN**, unchanged since 17 October; policy PR #6391 remains draft and unapproved. Production promotion, custom-domain Worker publication, approved acquisition/consent semantics, a successful authorized real-provider journey and qualified-traffic outcomes remain outstanding. **The Days 1–5 goal is not complete.**
