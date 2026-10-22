# SWE-EVO keyword implementation — 22 October 2026

Follow-up to the [Keyword Planner study](2026-10-22-keyword-planner-and-skills.md), whose observations and limits remain unchanged. Research PR #15 merged into main at `4887646ed441e4108d96aee89d259f26a0223b0e`; its reviewed research contents match head `e8a55e7de15cecad35ea0cd570d007c61db8339c` byte-for-byte. This follow-up uses a new branch after that merge.

## Bounded implementation

The existing Search Console exposure for `swe evo` / `swe-evo` and the Planner ranges support retaining the benchmark as the primary intent. `Agent harness` remains a supporting term in the existing title. No volume ranges are summed, advertiser competition is not organic difficulty, and unrelated automotive suggestions are excluded.

| Surface | Change | Reader benefit |
| --- | --- | --- |
| Article opening | Defines SWE-EVO as a benchmark for release-to-release software changes in the first sentence | Benchmark searchers understand the subject before the prompt-maintenance argument |
| Benchmark heading | “What is SWE-EVO, and what does it measure?” | Makes the existing answer easier to locate |
| Description | Explicitly names the benchmark, leaner prompts and the practical instruction/skill/tool comparison | Aligns the search/share promise with the actual content |
| Discovery surfaces | Same description in HTML, Open Graph, Twitter, both JSON-LD nodes, blog index and RSS | Keeps summaries consistent |
| Dates | SWE-EVO visible update, JSON-LD modification date, index update label and sitemap lastmod agree on 22 October | Records the substantive revision; original publication/RSS dates are preserved |
| CLI benchmark | Contextual links back to the SWE-EVO definition and proposed comparison | Connects operational overhead to the separate question of task quality |

Existing product PR #6434 already connects the framework article to the CLI benchmark, SWE-EVO exercise and CLI quickstart; the SWE-EVO article links to benchmark methodology, quickstart and skills documentation. The CLI benchmark's own title and search intent remain focused on headless automation and overhead. No claim is made of a site-wide cannibalization audit.

The title, canonical URL and matching share image remain stable during this final keyword pass. No extra keyword repetitions, analytics events, tracking identifiers, experimental results or benchmark scores are introduced. The benchmark return link is a navigation addition, so its publication/modification dates are not refreshed solely for that minor edit.

## Verification and release state

Product head `4dd6cc64829a908952d2b6dd70a6df2a20afadee` was pushed normally at **10:36:32 UTC**, with active hooks passing root/UI lint, backend/UI builds, secrets/dependency checks and all 26 repository gates. Remote head and OPEN PR #6434 were read back. New-head CI `39764390526` and Static Checks `39764390643` are running at this **10:37 UTC checkpoint**; the previous head’s green run does not verify this commit. Current-head review monitoring is scheduled from the first poll at 10:41:32 UTC to the 11:06:32 UTC cap. No new-head CI/review result is inferred. [Focused QA and source hashes](2026-10-22-keyword-pass/qa.md) record a passing website build, 226 SEO/link tests, three-file HTML lint (zero errors / six existing orphan-image warnings), valid anchors, consistent metadata/dates and preservation of measured findings. QA was run before commit against base `0527af498b00d5df33781c41fd4b939f996eb9af`; the report explicitly identifies the checked working-file hashes. The commit changes the same five files and hashes. Local desktop and 375px phone review confirms the updated opening is visible and readable, with no horizontal overflow; the temporary viewport override was reset. The article preview remains available on port 3005.

Read-only integration preflight against sandbox `e26b933688eb35294d0ff44ca69b78bd02c2a4e9` is conflict-free: tree `f921116166cce31a55698021a6c709fb1249db1f`. All eight candidate paths match the article commit byte-for-byte, and the merged signup repair is preserved. The [integration receipt](2026-10-22-keyword-pass/integration.json) records source hashes; it creates no merge commit and supplies no deployed/build-output hash.

No search-ranking, click-through, qualified-traffic or conversion improvement has been measured. PR #6434 still needs its normal merge/release and post-release checks. Do not request recrawl of an unpublished candidate or treat green CI as publication.

## Subsequent verification and Bing recovery

Article head `4dd6cc64829a908952d2b6dd70a6df2a20afadee` passed CI `39764390526` on **attempt 1 at 10:48:02 UTC**: all five UI/four backend shards, both shard gates, website, lint/build and test aggregate passed. Static Checks `39764390643` also passed. No retry or source/gate change was needed. Scope-appropriate E2E/Gherkin workflow gates passed while selected tests were skipped; they are not executed E2E evidence. Current-head review monitoring remains active at this checkpoint; older reviews do not cover the final rewrite.

Research PR #16's initial head `45b1f221dc7b11e294af816b8fdee09ff3344a5a` passed CodeQL `39764637404` at 10:39:35 UTC. That result does not cover this later Bing evidence addition.

[The recovered Bing receipt](2026-10-22-bing-followup.json) preserves exact normal-UI dates, tables and source limits. The 28-day current Search report now loads for 22 September–19 October, with **zero clicks / 109 impressions**. The earlier 25 August–21 September window and the corresponding Compare view explicitly return “Data for the selected range is not available”; they remain unknown, not zero. Independently selected 14-day reports recover **14 → 95 impressions**, with zero reported clicks in both periods. Their totals add to the current 28-day headline. Keywords/pages have smaller totals than headline/daily/device/country tables; the cause remains unverified, and missing or suppressed activity is not reconstructed.

Sitemap details also recovered: apex sitemap 65 discovered URLs, last crawl 20 October; www sitemap 64, last crawl 16 October; both report Success. Their sum accounts for the 129 summary across two sitemap entries. The overlap of their URL sets, distinct canonical/indexed page count and present live sitemap size are not established by that summary. No submission, delete or recrawl was performed.

Bing AI Performance also recovered for exact Custom windows: current 28-day citations **33**, earlier 28-day report **zero** with all 28 daily rows explicitly zero. This source-reported AI zero differs from Search Performance’s unavailable earlier period; sampling/coverage limits still apply. The two 14-day AI windows show **8 → 25 citations**, and their totals reconcile to 33. All available cited-page rows are retained; the current window includes knowledge graph (10) and skills adoption (7). One sampled grounding query reports six citations and a 33.33% share; its denominator is not reconstructed, and it is not a complete accounting. Only Grounding Queries and Pages tabs were observed, not a separate Topics Portfolio view.

Bing uses source-native dates with unverified timezone/finality; keep these separate from Pacific GSC and UTC PostHog. Visibility and sampled AI citation metrics do not establish qualified acquisition or a causal effect of unpublished content. This expands the fixed-date Bing baseline; Search’s earlier 28-day window remains unavailable and the row-total mismatch remains unresolved. The selected skills/knowledge-graph refreshes remain scheduled for Days 7–8, rather than being reported as completed in Days 1–5.

## Adjacent merged work

Signup PR #6442 merged into sandbox at `e26b933688eb35294d0ff44ca69b78bd02c2a4e9` on 22 October at 10:21:31 UTC. Its candidate signup file is byte-identical in that merge. Sandbox deployment run `39762498046` succeeded at 10:24:05 UTC. This is sandbox deployment evidence, not proof of production publication or a successful authentication journey.

Production main `85ca67ac285c9355da6acb941a005b8c50126e57` predates the signup merge and retains the old form in source. Its deployment run `39762334762` succeeded at 10:25:46 UTC. A direct HTTP probe was denied on the probing path, and a search-tool fetch was stale; neither supplies a fresh public signup body/hash. Production promotion and fresh live verification remain outstanding.

## Signup release preparation — 11:13 UTC checkpoint

The [fresh sandbox receipt](2026-10-22-signup-release/sandbox-live.json) verifies HTTP 200 at `https://aictrl-sandbox.web.app/signup`, with all 11,881 bytes equal to the source and built candidate (SHA-256 `1e589deba3cd1c9c41de3f6a776ceb7c4b1a5a4c193fb2f4466864fff6d56cd4`). Browser DOM confirms zero forms/email inputs, the bare app-root email link and its visible `aria-describedby` explanation. No email, provider action or terms acceptance was activated. This is deployed sandbox verification, not production or authentication success.

The [promotion preflight](2026-10-22-signup-release/promotion-preflight.json) is conflict-free against main `85ca67ac285c9355da6acb941a005b8c50126e57` and sandbox `e26b933688eb35294d0ff44ca69b78bd02c2a4e9`: tree `da1ae6fc0c08629550c1bd6eb0197941296c397e`. Only signup differs from main in the proposed merge result. Main-only changes to the open-source review article are preserved; comparing branch tips directly would misleadingly include that article difference.

[Draft production release PR #6446](https://github.com/aictrl-dev/aictrl/pull/6446), created **11:12:32 UTC**, promotes sandbox to main with one changed signup file (seven additions / ten deletions), links #6439 and matches milestone 85. It adds no source commit or deployment. SWE-EVO remains in separate unmerged #6434 and is absent from this release head.

New release-boundary CI `39768849728` and Static Checks `39768849694` are running at this checkpoint. Older sandbox deploy/check results share head `e26b933...` but do not establish these new release-event checks. E2E/Gherkin workflow gates pass with actual selected tests skipped. Review monitoring is scheduled for 11:17:32–11:42:32 UTC; no release-head verdict or green result is inferred. The normal production merge/deploy and exact live verification remain pending.

The full Days 1–5 objective remains incomplete: approved acquisition/consent semantics (#4665), an authorized successful real-provider journey, release/live/index evidence and qualified-traffic measurement remain open. This pass spent USD 0 and installed no MCP, OAuth grant or paid service.
