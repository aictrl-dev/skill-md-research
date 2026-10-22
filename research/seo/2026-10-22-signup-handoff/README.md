# Signup email handoff validation

Issue [#6439](https://github.com/aictrl-dev/aictrl/issues/6439), extracted from the original Days 1–5 batch. Candidate product commit: `3e7f4baae4079317d613b8ddc043d2ce2fc55b2e`.

- [Focused QA report](qa.md): commands, findings, unchanged-provider check and root browser observations.
- [Source/DOM and scoped accessibility receipt](source-and-axe-results.json).

The receipt was captured **before commit**, with base HEAD `0e6e6b96b27caa7c31e7caa4bb6f9aee4c8c84a7` and the signup edit in the working tree. Its source SHA-256 matches the committed candidate. The `head` field identifies the then-current base, not an assertion that the unmodified base already implemented the repair.

The scoped axe audit excludes contrast under jsdom. Browser review checks desktop and phone rendering and keyboard focus, without submitting email or completing authentication. No complete signup/delivery/provider result, live rollout or qualified-traffic improvement is established.

Repository hook and CI publication status is recorded in the [current Days 1–5 checkpoint](../2026-10-22-days1-5-checkpoint.md). These artifacts preserve focused validation; they do not replace that later provenance.
