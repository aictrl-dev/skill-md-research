# Combined release checkpoint — 22 October 2026

Recorded after the fresh **11:55:09 UTC** sandbox verification, using the verified receipts and check states supplied at this checkpoint. This supersedes the current-scope statements in the [earlier signup-only checkpoint](../2026-10-22-keyword-implementation.md#signup-release-preparation--1113-utc-checkpoint); its original receipts and timestamps remain historical evidence. **Days 1–5 is not complete.**

## Current source and release state

[Article PR #6434](https://github.com/aictrl-dev/aictrl/pull/6434) merged to sandbox at **11:26:33 UTC**, squash `4c1a61f2d96af9fdb016bfb21c393f71b80c668a`, tree `f921116166cce31a55698021a6c709fb1249db1f`. The signup repair was already in sandbox. This source merge is not production publication.

The owner then merged the separate CI-policy [PR #6445](https://github.com/aictrl-dev/aictrl/pull/6445) at **11:41:05 UTC**, advancing sandbox/release head to `ac7ef62e58a21984e32d719b05cc294a7de21e3e`. [Release PR #6446](https://github.com/aictrl-dev/aictrl/pull/6446) remains **OPEN and ready for required review**, with **12 paths**: the original article/discovery/link/image/writing-skill/signup changes, plus `scripts/ci/test-impact-policy.mjs`, `scripts/ci/test-impact-policy.d.mts` and `test/ci-test-impact.test.ts`. The CI-policy change did not originate in this SEO research update. Production remains unmerged.

The original [nine-path promotion receipt](promotion-preflight.json) applies to `4c1a61f2...` and tree `399adbea774c3b94d9994d9b23bf2172169f6589`. Its source scope was 330 additions / 912 deletions. The [12-path promotion receipt](promotion-preflight-ac7.json) applies to `ac7ef62e...` and tree `3d91f02d0965900689948de90d50f3c0a537e36d`. Both use main `85ca67ac285c9355da6acb941a005b8c50126e57`, are conflict-free and preserve all candidate paths plus main's separate `open-source-review-ai-era.html` change. Neither creates a merge commit, deployment or live-body proof.

## Connected metadata follow-up

[Source PR #6451](https://github.com/aictrl-dev/aictrl/pull/6451) is **OPEN and unmerged**, at `57c596052c8f1180584e39ae1a73778110e7e21b`. It was pushed normally at **11:50:28 UTC** and created at **11:51:19 UTC**. Active hooks passed root/UI lint, backend/UI builds, secrets/production-dependency checks and all 26 repository gates; optional local E2E was skipped without its emulator.

Its four-file patch aligns category/filter labels, connected modification metadata and the llms.txt title. The [focused QA report](connected-metadata-qa.md) and [machine receipt](results.json) retain all four final hashes, the pre-commit `4c1a61f2...` baseline and final-head readback. Website build, 226 focused SEO/link tests, HTML validation and the real existing category-filter behavior passed. Embedded CSS and both WiT tables remain byte-identical to the baseline; no fresh browser, assistive-technology or axe result is claimed. Absolute worktree/temporary-runner details are omitted from the human report; its findings and limits remain intact.

These follow-up hashes do not replace the original candidate/source/deployment baselines, and the unmerged patch is not yet part of release head `ac7ef62e...`. The release description explicitly treats merging #6451 as a production-promotion prerequisite.

## Review evidence and persistence limits

The owner's linked [deterministic review](https://github.com/aictrl-dev/aictrl/pull/6446#issuecomment-6339805536) contained six fresh findings; an earlier signup NIT was also checked. The [full response](https://github.com/aictrl-dev/aictrl/pull/6446#issuecomment-6340057599) was posted and read back with a valid seven-row JSON sidecar: **four FIX** decisions (three metadata findings and the PR-description correction), and **three IGNORE** decisions (ARIA removal FALSE; CSS/email informational findings TRUE). The explicit table roles are retained because the mobile block layout needs them.

Verdict persistence reported **matched 3, written 3, verified 3, failed 4, unrecorded 0**. Four inline-comment joins had null IDs and were not guessed. The structured sidecar records those decisions, but complete finding-store persistence is not established. No private raw MCP response or organization inventory is included here. This response is not release approval or proof that the source follow-up merged.

## Head-specific checks and pending handles

| Head / boundary | Receipt | State at checkpoint |
| --- | --- | --- |
| Original combined `4c1a61f2...` | [CI 39770616746](https://github.com/aictrl-dev/aictrl/actions/runs/39770616746) | SUCCESS, attempt 1, **11:38:45 UTC**; five UI/four backend shards, both gates, UI/backend coverage, website/lint-build and container sidecar/smoke/preflight passed |
| Original combined `4c1a61f2...` | [Static Checks 39770616922](https://github.com/aictrl-dev/aictrl/actions/runs/39770616922) | SUCCESS, **11:32:17 UTC**; website job in CI passed **11:29:29 UTC** |
| Original combined `4c1a61f2...` | AI quality check | SUCCESS, **11:38:10 UTC**, generic output; use the actual review/response above rather than infer detailed approval |
| Expanded release `ac7ef62e...` | [CI 39772445468](https://github.com/aictrl-dev/aictrl/actions/runs/39772445468) | Still active at latest verified read; the earlier green source head does not establish this run's result |
| Expanded release `ac7ef62e...` | [Static Checks 39772445343](https://github.com/aictrl-dev/aictrl/actions/runs/39772445343) | Passed |
| Original sandbox deployment `4c1a61f2...` | [Deploy 39770611449](https://github.com/aictrl-dev/aictrl/actions/runs/39770611449), [terminal receipt](deploy-terminal.json) | Overall FAILED at **11:53:04 UTC**: at **11:52:42.767 UTC**, the fence timed out draining **one active repository integration run**. Fence-release cleanup passed at **11:52:44.638 UTC**. Cloud Run, DBOS worker and deployment-health verification were skipped |
| Unmerged source follow-up `57c59605...` | [CI 39773730388](https://github.com/aictrl-dev/aictrl/actions/runs/39773730388), [Static Checks 39773730272](https://github.com/aictrl-dev/aictrl/actions/runs/39773730272) | CI SUCCESS on attempt 1 at **11:54:12 UTC**; Static Checks SUCCESS at **11:55:26 UTC**. The **11:55:38 UTC** review read verified the same head, base `ac7ef62e...` and four-file scope, with zero posted reviews/inline comments and the quality check still IN_PROGRESS. Review cap **12:20:28 UTC**; no automated approval is claimed |

Selected E2E/Gherkin execution remained skipped in the earlier green workflow; passing gates do not establish those tests ran. No rerun, cancellation or lock change is claimed. Existing [signup sandbox receipt](../2026-10-22-signup-release/sandbox-live.json) covers only that earlier signup candidate.

## Partial Hosting publication and fresh sandbox proof

The failed overall run nevertheless completed **Deploy Firebase Hosting**, step 12, successfully from **11:29:39 to 11:29:47 UTC**, before reaching the integration fence. The [fresh eight-artifact sandbox receipt](sandbox-live.json), captured **11:55:09 UTC**, verifies HTTP 200 and exact source bytes/hashes for all eight public candidate artifacts from `4c1a61f2...`, including the article, connected pages, discovery files, share image and signup. The SWE canonical and description match the intended source.

The article refresh is therefore verified live on **sandbox Hosting**. Full backend/worker deployment failed, and the unmerged metadata follow-up #6451 is not represented by these baseline hashes. This evidence establishes neither production publication, authentication/provider success, index inclusion nor acquisition outcomes. Keep partial static publication separate from the failed overall deployment.

## Remaining requirements

Keep current review/merge/deployment checks attached to their exact heads. Production promotion, exact post-release live hashes/canonicals/timestamps and legitimate changed-page indexing checks remain outstanding, as do approved acquisition/consent semantics under product issue #4665, an authorized successful real-provider/result journey and qualified acquisition measurement. No policy approval, completed authentication, provider execution, traffic gain or partner spend is inferred.

The original 44-file archive and [Bing baseline](../2026-10-22-bing-followup.json) remain unchanged, including missing-window, sampling, timezone and row-total limitations. This research update spends USD 0 and performs no product mutation.
