# Referral and Search research engine

This is the ongoing research ledger for aictrl acquisition. The objective is relevant engineering traffic that can turn into useful product adoption. Listings, backlinks, directory installs and clicks are intermediate signals; none establishes qualified traffic by itself.

**Start with [the referral plan](referral-plan.md), [the Search plan](search-marketing-plan.md) and [the landing-page briefs](landing-page-briefs.md).** The research snapshot is 22 October 2026. Prices and platform rules need rechecking before execution.

## Canonical data

[store.json](store.json) is the source of truth. It contains 48 distribution sources, evidence, seven demand clusters, existing landing assets, 28 keyword seeds, advertised offers, next actions, outcome fields and paused ad drafts. [store.schema.json](store.schema.json) defines the contract. Generated CSVs are convenient spreadsheet imports, not a second independently edited database.

The register includes 26 opportunities to prepare, three existing surfaces to maintain, eight applications/conversations to monitor, ten holds and one rejected paid offering. These are 48 researched surfaces, not 48 new partners, accepted listings or independent backlinks. Sources under the same operator and syndicated registry records remain related.

Existing application states come from the earlier dated research and founder confirmation. They are not new actions in this pass. An unverified listing or price stays unknown. The ledger currently contains no newly incurred spend, outcomes or serving campaigns.

## Commands

Use Python 3.11 or later. The only dependency is the JSON Schema validator, isolated to this folder:

```bash
cd research/seo/acquisition
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python engine.py validate
.venv/bin/python engine.py report
.venv/bin/python engine.py queue --as-of 2026-10-23 --limit 15
.venv/bin/python engine.py export
.venv/bin/python -m unittest discover -s tests -v
```

`queue` is a research/preparation queue. It does not submit or publish anything. Holds are hidden unless `--include-holds` is supplied. Dates are explicit review targets in Europe/London, not platform promises. The CSV queue is generated through the snapshot's `meta.as_of`; the command can show later review dates without altering history.

After an actual externally verified status change, record its receipt locally:

```bash
.venv/bin/python engine.py record SOURCE_ID \
  --status submitted \
  --url https://example.com/actual-receipt \
  --note 'What was submitted, by whom, and what the receipt establishes' \
  --on YYYY-MM-DD
.venv/bin/python engine.py export
```

Replace the placeholders with real evidence. For a private receipt, link a sanitized research record rather than a token-bearing URL or an email inbox. Do not put account identifiers, reviewer credentials or signed URLs in this public repository. A `live` entry needs its actual public page URL. Validation checks structure and references; it does not independently authenticate a receipt or establish that a website is live.

`record` appends the status event and evidence in the same validated JSON snapshot and replaces the file atomically. There is one writer: avoid simultaneous edits; Git review resolves collaboration. Other research changes, offers and outcome observations are edited in JSON, validated, then exported. This deliberately avoids building a service or a two-way spreadsheet synchronization system.

## Evidence and outcomes

- Record the claim, observation date, URL and limitation. A platform's audience claim is not aictrl traffic. A founder-confirmed working client is not an approved marketplace listing.
- Add a source-specific outcome only with its period and evidence ID. Unknown visitors, qualified visitors and spend are `null`, not zero. Qualification requires a verified signup, demo request or successful installation/connection plus relevant use-case intent in the rolling 28-day window. Relevant-page visits and CTA/install clicks alone are insufficient. Report unknown when permitted evidence or deduplication is unavailable; no anonymous/account joining is introduced.
- Keep GSC property, search type, date window and timezone attached to observations. Existing baseline dates are Pacific daily dates. Planner uses separate US/GB requests, English and Google Search only.
- Do not sum close-variant volume ranges, infer CPC from advertiser competition, or pool directory reach into a visitor forecast.
- Use the existing EU PostHog instance for permitted aggregate referral/outcome checks when accessible. No new collection, identity joins or tracking parameters are required to continue research, improve content or prepare listings. Issue #4665 concerns new analytics enablement only.

## Budget accounting

The partner ceiling is **$200 cumulative**. Search advertising has no separately assigned budget. The current ledger records zero new spend; historical liabilities have not been fully reconciled, so available balance is unknown.

`budget_entries` contains current liabilities and settled charges. A committed entry becomes `spent` when settled; do not append the same charge a second time. Link each entry to its source and receipt. The validator rejects totals above the ceiling. Quotes and advertised offers never become commitments automatically. Recurring plans and unknown all-in charges cannot be treated as affordable one-off placements.

There is no purchase or outreach automation. Current work is research and preparation. Before execution, recheck eligibility, prior applications, actual all-in terms, the remaining cumulative balance and the final item to publish or buy.

## Working cadence

On each research run, validate the store, inspect due actions, and work on at most three listing packages plus two substantive editorial/integration artifacts. Update the same IDs instead of creating duplicates. Review pending applications at their actual queue windows; do not continually resubmit. Regenerate CSVs after changes.

At seven and 28 days after an actual placement goes live, compare referral visits and qualified outcomes where observable. Use the placement date, not a planned launch date. Retain failures and rejected hypotheses. Keep paid offers on hold when price or relevance remains unsupported.

Generated imports: [sources](generated/sources.csv), [offers](generated/offers.csv), [keywords](generated/keywords.csv), [due actions](generated/queue.csv). Prefix protection prevents common spreadsheet formula injection when importing external strings.
