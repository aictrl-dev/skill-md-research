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
