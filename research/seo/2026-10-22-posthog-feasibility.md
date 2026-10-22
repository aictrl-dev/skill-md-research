# Existing EU PostHog: technical feasibility check

**22 October 2026. Read-only; no approval, capture, setting or deletion change.**

EU hosting is settled by founder confirmation: use the existing `eu.posthog.com` instance. The founder does not need to choose hosting again. The checked project is 88595. [Filtered technical receipt](2026-10-22-posthog-feasibility.json).

## Findings that change the next action

| Draft assumption | Current evidence | Required correction |
| --- | --- | --- |
| Ninety-day raw-event deletion can be promised after setting retention | Current [PostHog event-retention documentation](https://posthog.com/docs/data/events-retention), retrieved through the instance MCP, says plan windows are one year free/seven years paid; they cannot be shortened on request. It explicitly distinguishes retention from deletion. | The 90-day deletion commitment is not technically established. Engineering must provide a verified deletion mechanism or present a supported alternative period for the final decision. Do not present the draft target as configured or feasible. The follow-up billing read confirms a paid plan and lists a seven-year Product Analytics retention feature; this remains distinct from physical deletion. |
| A 30-day project setting proves event retention | The read-only project response returns `session_recording_retention_period: 30d`, with no raw-event retention field. | This is recording retention only. It cannot validate the raw-event promise. |
| Deletion by distinct ID establishes erasure for events without profiles | The current `persons-bulk-delete` MCP schema accepts distinct IDs but describes deletion of associated persons and optionally their events; it returns 202 Accepted. The operation was not called. | This schema does not prove coverage for events without person profiles, completed deletion within seven days, or safe later consent under the same identity. Keep those engineering checks unresolved rather than ask the founder to certify them. |
| Existing project defaults already match the proposed contract | Current response shows `anonymize_ips: false` and `session_recording_opt_in: false`. | Verify producer/ingestion behavior separately before any rollout. These settings alone establish neither approved fields nor universal absence of recording. No settings were changed. |

The deletion reference is [PostHog's data-storage documentation](https://posthog.com/docs/privacy/data-storage#data-deletion). Community answers and old source issues returned by search were excluded from capability evidence. A successful deletion request would not, by itself, prove removal; this pass executed no deletion and created no test events.

## Provider workflow follow-up — 22:06 UTC

The active MCP project was independently confirmed as 88595. Its read-only billing overview reports an active paid subscription and a seven-year `product_analytics_data_retention` feature. Only these plan facts are retained; financial amounts, payment details and customer IDs are excluded. This resolves the earlier unknown plan tier and supplies the existing plan window; it does not establish a shorter deletion mechanism.

Direct reading of the official deletion page supplied details absent from the MCP search excerpts:

- A bulk-deletion response reports matched/queued persons and any `deletion_errors`. HTTP202 is acceptance, not completed event erasure.
- `GET /api/projects/:project_id/persons/deletion_status` exposes pending/completed operations and `delete_verified_at`. Engineering can use this to verify actual completion for the matched person, rather than report success when a request queues.
- Event erasure is asynchronous. The page establishes no seven-day guarantee.
- The documented deleted-ID reset allows future events to create a person profile. It cannot be assumed compatible with the draft's no-profile capture rule. Deletion of events without profiles and safe later re-grant remain unproved.

The concrete next engineering check belongs with existing [#4671](https://github.com/aictrl-dev/aictrl/issues/4671): demonstrate matched-event erasure and completion verification for the proposed identity strategy in an isolated test environment, including later re-grant. Do not use unrelated production identities or treat an empty person match as erasure. This read-only pass created no events, called no deletion/reset/status API, and made no account or policy change.

## What should come back to the founder

[PR #6391](https://github.com/aictrl-dev/aictrl/pull/6391), inspected at `6ccc8fb4af9f512ae72f1f8e6068a95a6ba1f13f`, remains a supporting draft. Its previously chosen separate website/account cohorts stay intact. Before requesting final sign-off, engineering should supply an implementable event/field phase, verified retention/deletion behavior and matching short public consent copy. EU hosting needs no renewed choice. No proposal or public policy copy was silently changed by this research record.

The current record supports no claim that 90-day physical deletion or seven-day erasure is available, configured or demonstrated. It also does not establish that those mechanisms are impossible; the missing provider evidence remains explicit.

## SEO boundary

These findings concern new analytics enablement. Existing read-only reporting, content, listings, partner outreach and placement assessment continue independently. Qualified conversion attribution stays unknown where the existing evidence cannot establish it. The optional Gemini provider test is separate activation work and adds no SEO publication prerequisite. Console outreach is already sent from bulat@aictrl.dev per founder confirmation; do not send a duplicate.

This check cost USD 0 and performed no project settings, SDK, identity, capture, consent, deletion, billing or access mutation. The receipt excludes the API token and user/event rows.
