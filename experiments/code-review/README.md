# Code-Review Research Framework

The durable, cross-experiment layer for code-review-agent research. The
[`cr-loop`](../cr-loop/) study proved the measurement harness (benchmark PRs →
variant runs → answer-key scoring → novel-triage loop); this framework is the
registry + connective tissue that makes it repeatable. See [`DESIGN.md`](./DESIGN.md)
for the full rationale.

## Source of truth

The **[Google Sheet](https://docs.google.com/spreadsheets/d/1txtt4rYQULxMZQHOgOqn8TcAx5bQBPEjknRsDxIUU4Q/edit)**
is the registry. Tabs: `Hypotheses`, `Metrics`, `Results`, and a `Schema`
data-dictionary describing every field + the allowed levels for categorical
fields. [`TRACKER.md`](./TRACKER.md) is a thin human pointer to it.

## The loop

1. **Author** a `Hypotheses` row + define the variant (a skill file/config under
   the experiment's folder).
2. **Run** the variant over the frozen benchmark; collect per-PR findings into
   the experiment's `results/` (reuse cr-loop's runners).
3. **Aggregate + score** — once per answer-key version:
   ```bash
   npx tsx scripts/aggregate.ts \
     --findings-dir ../cr-loop/results/raw/phase-E \
     --answer-key extended \
     --experiment cr-loop --hypothesis H-003 --variant "Phase E" \
     --skill-version code-review.SKILL.v3.md --model zai-coding-plan/glm-5.1 \
     --tool-config "KG:populated" --baseline-f1 0.369 \
     --out /tmp/row.json --breakdown-out /tmp/breakdown.json
   ```
   (`--kg-state populated` still works — it maps to `--tool-config "KG:populated"`.)
   `--breakdown-out` writes one per-defect-class row for every class the answer
   key labels via `category` (skips only-novel classes; empty for cr-loop, whose
   key predates the taxonomy). SNR (TP/FP) and Significance (ΔF1 vs noise floor)
   are derived automatically.
4. **Sync** — validate + shape the row(s), then append via the google-sheets MCP:
   ```bash
   npx tsx scripts/sync-sheet.ts --in /tmp/row.json \
     --breakdown-in /tmp/breakdown.json --known-hids H-001,H-002,H-003
   ```
   Feed each printed payload (`{ sheet: "Experiments", values }` and
   `{ sheet: "ClassBreakdown", values }`) to the MCP `update_cells` /
   `batch_update_cells` tool (the agent assigns the next `E-ID`).
5. **Triage novels** — adjudicate produced findings with no answer-key match;
   fold confirmed-real ones into `answer-key-extended.json` and re-score.
6. **Conclude** — set the `Hypotheses` Status and one-line Learning.

## Invariants (do not break)

- **AnswerKey version is a scoring dimension, not a variant.** Score every run
  against both `orig` and `extended`; each is its own Results row. (This is what
  hid cr-loop's Phase-E winner against the original key.)
- **Novels are conservative-by-default.** A produced finding with no answer-key
  match is tracked for triage, never auto-scored as a false positive.
- **Micro-average, not mean-of-F1.** Aggregate sums TP/FP/FN across PRs then
  computes P/R/F1, so small PRs don't dominate.
- **Small-sample honesty.** F1 variance is ~0.01 on 10 PRs / single seed — flag
  deltas within noise as inconclusive, not confirmed.

## Files

- `scripts/schema.ts` — `Experiments` (25-col) + `ClassBreakdown` (12-col) row
  contracts, enums, validation, cell ordering.
- `scripts/aggregate.ts` — per-PR scores → one micro-averaged `Experiments` row
  + per-defect-class `ClassBreakdown` rows (derives SNR + Significance).
- `scripts/sync-sheet.ts` — validate rows + emit the MCP append payloads.
- Reuses `../cr-loop/scripts/score.ts` (`score()`) as the per-PR scorer; it now
  also returns `totals.byCategory` for the per-class breakdown.

## Tests

```bash
npm test   # or: npx tsx --test scripts/*.test.ts
```
