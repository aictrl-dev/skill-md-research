# Production release and remaining boundaries — 22 October 2026

Release [#6446](https://github.com/aictrl-dev/aictrl/pull/6446) **merged at 15:06:30 UTC**, merge `7000314ba863d4e356bb8d4b3763a42be4099ed1`, final source `6eb7dbfe6f369ddfb7bb15f7dc3c31d2073e9eeb`. Final scope was **36 paths, 815 additions / 1,472 deletions**, including #6452. Earlier open-release, pending-service and mixed-sandbox records remain dated history, not current production state. **The full Days 1–5 goal is still incomplete.**

## Source and terminal deployment evidence

The [production manifest](production-manifest.json) verifies all nine publication files unchanged from reviewed c051 and preserves main's separate open-source-review article. The [terminal deployment receipt](deployments.json) has SHA-256 `8220ba50de4d05e01f67470c082468e28e0efaf9e8763f8075097a2ab9a6e015`; all six known production handles are terminal: **five SUCCESS / one CANCELLED**, zero pending or failing.

| Exact-merge handle | Outcome |
| --- | --- |
| [Cloud Run 39801702353](https://github.com/aictrl-dev/aictrl/actions/runs/39801702353) | SUCCESS |
| [Cloud Run 39801694793](https://github.com/aictrl-dev/aictrl/actions/runs/39801694793) | SUCCESS |
| [Static Content 39801702435](https://github.com/aictrl-dev/aictrl/actions/runs/39801702435) | SUCCESS |
| [Static Content 39801695372](https://github.com/aictrl-dev/aictrl/actions/runs/39801695372) | SUCCESS, with purge failure retained below |
| [Static Checks 39801702512](https://github.com/aictrl-dev/aictrl/actions/runs/39801702512) | SUCCESS; secret scan ran, repository checks/aggregate skipped |
| [Static Checks 39801695031](https://github.com/aictrl-dev/aictrl/actions/runs/39801695031) | CANCELLED; not a pass |

Latest ready production service revision is **`session-control-00638-z2f` at 100% traffic**. Its pinned platform-image digest matches the build provenance; both service deployments passed their health checks. The DBOS step reports SUCCESS but the worker pool is disabled, so its image update was a no-op. Executor image/job updates and Firebase Hosting rewrite steps were scoped out; static publication occurred through the separate static-content workflows. Do not turn those skipped/no-op boundaries into executed deployment claims.

Fresh final-source CI and actual E2E/Gherkin runs passed before merge, as recorded in the receipt. Those are source-head results; no new full suite against the merge was launched by this archival work. The duplicate workflow/event cause is unproven, and no archive operation started, retried or cancelled a production workflow.

## Public content and the unresolved edge image

The [15:11:47 UTC public receipt](production-live.json) reports **nine HTTP 200 responses / eight exact source-byte matches**. Article canonical, description, modified/category metadata and both neutral WiT tables match; root visually checked the desktop article as readable. The ninth response is the OG image: its edge bytes are stale. The receipt deliberately retains `all_checks_pass: false`; there is no nine-exact-edge claim.

The [image-cache receipt](image-cache.json) verifies the origin OG image exactly equals source, while the public edge still served an older **HIT** at **15:29:47 UTC**. Both workflow purge attempts failed with **error 7003**, despite green workflow conclusions. Existing [issue #6436](https://github.com/aictrl-dev/aictrl/issues/6436) tracks this defect; no new issue, purge or cache/config change was performed. Cloudflare's browser was signed out; a sign-in question and handoff tab remain pending.

Python's default HTTP client received Cloudflare 1010/403 on the probing path; ordinary curl/Chrome and Google's live fetch worked. This does not establish that Google is blocked.

## Indexing and custom-domain routing

The [Google inspection receipt](google-inspection.json) distinguishes the existing indexed page (last crawl displayed **16 October**, timezone unlabelled) from the new live fetch. The live test passed and its tested HTML showed the current article title. **One recrawl request was accepted at 15:22:49 UTC**. Queue acceptance does not establish indexing of the revised content, ranking changes or qualified traffic.

The [apex routing receipt](apex-routing.json) shows `https://aictrl.dev/?wizard=bind-repos` still returns the marketing page without an SPA root, while the direct Cloud Run URL returns the expected SPA root. The reviewed Worker publication remains pending. These were inert unauthenticated reads, without a callback, binding, sign-in or repository action. Production service deployment does not itself publish the apex Worker.

## Updated requirement audit

| Requirement | Current state |
| --- | --- |
| Day 1 baseline | Available capture complete; Bing prior-window/row-total limits and other documented unknowns remain unchanged |
| Day 2 successful journey | Unproven; selected Gemini 3.8 Flash test remains unexecuted with secure configuration-reference question pending, zero provider requests / USD 0 spend |
| Day 3 repairs and measurement | Functional changes published; issue #4665 remains OPEN and draft #6391 unapproved, so acquisition/consent instrumentation remains gated |
| Day 4 content | Reviewed publication source complete; production HTML/discovery content verified, with the stale edge OG image explicitly unresolved |
| Day 5 release and live checks | Approval/merge and production-service gates closed; edge cache, reviewed apex Worker publication and complete route/journey verification remain pending |

No revised-index, ranking, qualified-acquisition, successful authentication/provider-result or policy-approval outcome is inferred. All earlier research and the original 44-file archive are preserved. This archival update makes no source, tracking, provider, deployment, purchase, Worker or cache mutation.

## Cloudflare follow-up — 16:00 UTC

The [new rollout receipts](cloudflare-followup/README.md) supersede the current Worker/image-blocker status above without rewriting those original observations. Reviewed Worker version `fe280117-d3b2-479d-8622-6153dba6d701` is published at 100%; inert setup-root routing now serves the SPA, while marketing/article/explore behavior is preserved. The canonical article OG image now matches release source after a purge of only its origin-fetch cache key. The pre-purge mismatch remains in the new routing receipt; automated purge issue #6436 is still open.

The owner reports updating the GitHub App Setup URL; its endpoint was independently reachable, while the saved private setting and a real install remain unverified. Provider/journey, policy and qualified-outcome requirements remain open. This resolves the observed public routing/image defects, **not the full Days 1–5 goal**.

## Partner discovery follow-up

The [partner priorities note](../2026-10-22-partner-discovery-priorities.md) records native Glama/skills.sh listing observations and public-source registry/plugin readiness, separating live placements from pending applications and platform counters from qualified referrals. Optional provider-specific CLI testing is activation work and does not block independent SEO delivery or free partner research. The original qualified-visitor NSM and existing consent, measurement, paid-placement and cumulative-budget gates remain intact; this pass made no new submission, external message, reservation or spend.

## Authorized partner actions — 18:01 UTC checkpoint

The [execution record](../2026-10-22-partner-actions.md) archives one authorized factual follow-up on the existing closed OpenCode submission, plus a fresh isolated 1.2.0 installer check that passed clean install/repeat/uninstall for 17 skills without OAuth or model use. No duplicate PR, accepted listing or qualified-acquisition result is inferred. The Console editorial pitch remains unsent pending the intended business sender/prior-contact check; MCP.so's USD 39 offer was assessed, not bought. Smithery's announced 31 October shutdown concerns its proxy/managed identity, not proof that its entire directory is closing.

The founder confirmed all four partnership streams. **Issue #4665 governs new analytics collection; it does not block partnerships, listings, authorized outreach or assessment.** These activities proceed independently while qualification measurements remain unknown. No new spend, reservation or commitment was made, and the original cumulative USD 200 authority and qualified-visitor NSM remain unchanged. This is actual bounded partner execution, not full Days 1–5 completion.

## Live skills catalog improvement

The [partner execution record](../2026-10-22-partner-actions.md#existing-skillssh-catalog-improvement--live) now includes merged skills PR #88 and the verified public skills.sh page with five task groups. One documented isolated maintainer install refreshed the metadata; it is internal maintenance, not organic acquisition. Catalog inclusion remains 13 skills; new spend remains USD 0.
