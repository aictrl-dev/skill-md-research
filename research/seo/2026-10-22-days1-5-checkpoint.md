# Days 1–5 checkpoint — 22 October 2026

The [original plan](2026-10-21-days1-5/2026-10-22-seo-aeo-14-day-plan.md) and [21 October execution record](2026-10-21-days1-5/2026-10-21-days1-5-execution.md) remain the scope. This checkpoint records subsequent work without rewriting the historical evidence snapshot. **The full Days 1–5 objective is not complete.**

## Current acceptance audit

| Requirement | Current evidence | Assessment |
| --- | --- | --- |
| Search and acquisition baseline | Historical Google/Bing/PostHog captures and query-to-page table remain in the original snapshot | Available evidence retained; matching Bing windows and selected-page segment discrepancy remain unresolved |
| Outcome semantics and consent | #4665 remains Open; #6391 remains Draft at `6ccc8fb4af9f512ae72f1f8e6068a95a6ba1f13f`, re-read on 22 October | Diagnosis complete; approved contract and qualified acquisition NSM unavailable |
| Successful controlled product journey | Prior isolated CLI install/startup/schema-rejection receipt; no authorized real-provider/result evidence | Partial; startup and deterministic rejection do not prove execution success or attributable adoption |
| Signup email repair | [PR #6442](https://github.com/aictrl-dev/aictrl/pull/6442), head `3e7f4baae4079317d613b8ddc043d2ce2fc55b2e`, one signup file | Focused QA, actual repository preflight, CI and Static Checks pass; automated review running, release pending |
| SWE-EVO refresh and supporting links | Article PR #6434 head `0527af498b00d5df33781c41fd4b939f996eb9af`; six publishing paths plus the requested blog-writing skill; full CI attempt 3 passed | Implemented, locally checked and CI verified; current-head automated verdict absent and release pending |
| Current review, release and live hashes | Article PR remains Open; six scheduled review polls through 10:10 UTC found only two older reviews and 11 unchanged inline comments | Bounded monitoring complete; no current-head automated verdict, merge, deployment or live-candidate hash proof |
| Canonical/index verification and recrawl | Previous live tests/indexing requests apply to already published agent/benchmark pages | No request for unpublished changed articles; post-release verification remains pending |

## Article changes and evidence

The article now explains model-upgrade prompt maintenance using current vendor guidance, contrasting repository-context research, qualified SWE-EVO results and an explicitly limited tool-overhead experiment. It gives readers an instruction audit, a proposed comparison exercise and a failure-to-control framework. No aictrl SWE-EVO quality score is claimed.

Owner feedback replaced the earlier coloured boxes and arrows with plain Words in Table layouts. [The visual record](2026-10-22-swe-evo-wit/README.md) distinguishes a mechanically passing design from owner acceptance. The experiment eyebrow is now evergreen. Displayed figures use compact numbers and whole percentages; calculations continue to use unrounded source data. The tracked blog-writing skill makes that readability pass a standing requirement. [Numerical QA](2026-10-22-numerical-readability/README.md) preserves the final source hashes and rounding checks.

Local article QA covers website build, 226 focused SEO/link tests, HTML validation, accessible table structure, source/link parity and desktop/phone review. It is not proof of production publication or ranking improvement.

Integration preflight on 22 October: `git merge-tree --write-tree origin/sandbox HEAD` against sandbox `0e6e6b96b27caa7c31e7caa4bb6f9aee4c8c84a7` was conflict-free, yielding tree `2af9a1024f332b2dafb70bb3ab2eaf7908e2413e`. All seven candidate paths matched the article head byte-for-byte in that merged tree. This creates no release commit and is not deployment evidence.

## CI provenance

Article CI run `39757140380`, head `0527af498b00d5df33781c41fd4b939f996eb9af`:

- **Attempt 1:** failed the duplicate-ID diagnostic assertion in `PrExplanationCard.test.tsx`. The component and test blobs are identical to CI base `f2e0e58917203a8eae1e719c157bf98bec3e874d`; neither path is in this PR. Four backend and four other UI shards, website checks, lint/build and Static Checks passed. A later-effect timing race is a hypothesis, not a proven cause.
- **Local reproduction:** the isolated case passed, then the complete file passed 113 tests. No source or test was changed. Passing locally does not erase the CI failure.
- **Attempt 2:** one failed-job retry passed all tests in UI shard 5. Its timing aggregation deliberately rejected mixing workflow attempts, so the overall workflow still failed. Do not present that attempt as green.
- **Attempt 3:** one full-workflow rerun was accepted at **10:01:57 UTC**, to obtain a coherent attempt under the existing provenance gate. At the 10:10 checkpoint, all five UI shards, their timing-provenance check, website and lint/build passed; four backend shards remained live. No further retry is authorized in this verification cycle if this complete attempt fails.

**Final CI result:** attempt 3 completed **SUCCESS at 10:12:55 UTC**, on the unchanged article head. All five UI and four backend shards, both coherent-attempt validation gates, website, lint/build and the final aggregate passed. Static Checks also passed. The PR rollup was **22 successful / nine skipped**, zero pending or failing. PR #6434's stored verification body was updated and read back with that exact head and milestone 85. The original failure remains recorded; its timing-race hypothesis was not repaired by this article change.

The six scheduled article review polls ended at the 30-minute cap. The last response, **10:10:18 UTC**, confirmed the same head, two stale 21 October reviews and 11 unchanged inline comments. No current-head verdict or new/edited finding appeared. The review window ended; the separate CI handle remained active and was still being monitored.

The exact duplicate-ID test failure was not found as an existing issue in the targeted search. #6306/#6119 describe a different initial-anchor case with a similar synchronization concern. A follow-up reliability investigation should check whether the diagnostic assertion waits for the reveal effect, retain the hostile duplicate-ID fixture, and verify the repair under the real shard workload. Do not silently disable the assertion or weaken timing-provenance validation.

## Separate signup deliverable

The static signup page's placeholder email form POSTed to the app homepage without requesting a magic link. The separate repair replaces it with “Continue with email in aictrl” and a next-screen explanation associated through `aria-describedby`. The email link uses the bare existing app root. GitHub/Google destinations are unchanged; unused input styling is removed.

Focused verification: website build and 226 SEO/link tests pass; marketing HTML lint has zero errors and seven existing warnings; the card-scoped accessibility audit has zero violations. Root browser inspection covers desktop and 375px phone width, no horizontal overflow, native keyboard focus and the link/description. No email was entered or submitted. Source SHA-256 is `1e589deba3cd1c9c41de3f6a776ceb7c4b1a5a4c193fb2f4466864fff6d56cd4`. The [focused report and machine receipt](2026-10-22-signup-handoff/README.md) retain the pre-commit base-versus-working-tree distinction.

The new worktree initially lacked generated Husky shims. Normal initial commit/push commands therefore did not run hooks; this was caught before PR creation. Local shims were restored; the actual preflight passed, then a second normal push automatically invoked and passed the hook checks, completing **10:08:39 UTC**. These completed receipts establish root/UI lint, both production builds, secrets/dependency checks and all 26 repository gates, including the explicit AGENTS checklist. Optional local E2E was skipped without the emulator. The initial unhooked commands are not check evidence. HTML has no matching lint-staged rule, so the focused HTML checks are reported separately.

PR #6442 targets sandbox, opens with `Closes #6439`, and carries milestone 85, matching the issue. It changes only `website/public/signup.html` (7 additions / 10 deletions). The stored body, head, source hash and clean worktree were read back. CI `39760912399`, Static Checks `39760912357` and the queued automated review were live at PR creation; no terminal result is inferred from their creation.

At the first scheduled poll, **10:14:14 UTC**, signup CI and Static Checks were both terminal **SUCCESS**, with 10 successful and 14 skipped scope-appropriate checks. Backend/UI-wide CI jobs are skipped for this website-only diff; the local full lint/build/static preflight is separate evidence. The AI Code Review (KG Extract) check was still **IN_PROGRESS**, with no posted review or inline comment. Monitoring continues to the 30-minute cap from PR creation (10:38:59 UTC) unless a verdict arrives sooner. No release is inferred from green CI.

## Keyword and tooling follow-up

[The new keyword study](2026-10-22-keyword-planner-and-skills.md) records real UK/US Keyword Planner ranges, existing GSC intent, proposed opening/heading improvements and assessed SEO skills. The benchmark topic remains the primary intent. Suggestions polluted by automotive “harness” terms are excluded from developer-acquisition conclusions.

A dedicated Keyword Planner MCP could remove recurring UI navigation, but Google's official reporting MCP alone does not expose the planning RPCs. The candidate/community tool inspection is documented; no MCP installation, OAuth grant, API-access application, new cloud service or paid subscription has occurred.

## Remaining external decisions and outcomes

- #4665 still requires the exact Product/Privacy contract and its downstream rollout evidence. Existing sign-in is not analytics consent; no anonymous-history linking or additional collection is enabled here.
- A successful real-provider/result check still needs the intended authorized provider setup. No credentials are inferred from browser sessions or taken from another process.
- Release approval remains outstanding. Prepare and verify the PRs, then follow the normal sandbox-to-main flow once authorized; only afterward record exact live content hashes, canonical status, timestamps and legitimate recrawl receipts.

This continuation spent **USD 0** and made no partner, campaign or subscription commitment. The cumulative budget remains a USD 200 authority limit with unverified historical available balance. Qualified traffic and successful downstream acquisition remain unknown.
