# Code-Review Research Framework — Design

**Date:** 2026-06-03
**Status:** implemented (see [`PLAN.md`](./PLAN.md), [`README.md`](./README.md))
**Repo:** `aictrl-dev/skill-md-research`
**Home:** `experiments/code-review/`

---

## 1. Purpose

A durable framework for running, scoring, and **tracking** code-review-agent
experiments, with a Google Sheet as the cross-experiment registry of
hypotheses, metrics, and results.

The optimisation target is **review quality (precision / recall / F1) first**,
with **cost / latency** and **coverage breadth** recorded on every experiment so
a quality win that regresses another axis is visible rather than silent.

This framework does **not** invent a measurement harness. The
[`cr-loop`](../cr-loop/) experiment already proved one end-to-end
(benchmark PRs → variant runs → answer-key scoring → novel-triage feedback
loop). The framework is the **connective tissue and registry** that turns that
one-off study into a repeatable practice.

## 2. Problem being solved

Today every code-review experiment's hypotheses and results live inside that
experiment's own markdown logs and an HTML summary (e.g.
`cr-loop/log/004-full-research-flow.md`, `cr-loop/cr-loop-research-summary.html`).
There is **no registry that spans experiments**: no single place that answers
"what code-review hypotheses have we tested, what's their status, and how do the
variants compare on a common scoreboard?"

The Google Sheet
([1txtt4rYQULxMZQHOgOqn8TcAx5bQBPEjknRsDxIUU4Q](https://docs.google.com/spreadsheets/d/1txtt4rYQULxMZQHOgOqn8TcAx5bQBPEjknRsDxIUU4Q/edit))
becomes that registry. cr-loop is back-filled as **experiment #1**; future
code-review experiments adopt the same shape.

## 3. Scope

**In scope:** code-review experiments only (cr-loop + future CR studies).

**Out of scope:**
- Generalising the registry to non-CR experiments (`kg-ab-test`,
  `tool-latency`) — their metrics (answer-key, novels, F1) differ enough that a
  shared schema would over-generalise. They keep their own logs.
- Rebuilding the scorer, benchmark, or runners — `cr-loop` owns those.
- Auto-orchestrating the reviewer agent across PRs (the "one-click experiment").
  That is a later, separable concern; this framework scores runs that already
  happened.
- A Google service-account / CI write path. Sheet writes are MCP-driven and
  in-session for now (see §7).

## 4. What already exists (reused as-is)

From [`experiments/cr-loop/`](../cr-loop/):

| Asset | Role in the framework |
|---|---|
| `pr-set.json` | The frozen benchmark PR set (10 PRs, categorised) |
| `answer-key.json` | Gold labels built from prior bot reviews + `/reply-to-code-review` verdict sidecars (83 entries) |
| `answer-key-extended.json` | Gold labels after manual novel triage (143 entries) |
| `scripts/score.ts` | **Per-PR** scorer → `ScoreResult` (TP/FP/FN/novels/half-credits, precision, recall, F1, missed[], novels[]); answer-key selected via `CR_LOOP_ANSWER_KEY` |
| `scripts/collect-novels.ts`, `extend-answer-key.ts` | The novel-triage feedback loop that improves the gold set |
| `scripts/run-prod-skill.sh`, `run-all-prod.sh`, `read-firestore-findings.sh` | Variant runners |
| `skills/code-review.SKILL.v{2,3}.md` | Variant skill definitions under test |
| `results/raw/phase-*/` | Per-PR findings JSON for completed phases |

**Key invariants inherited from cr-loop (the framework must preserve these):**

1. **Answer-key version is a scoring dimension, not a variant.** The same run
   scored against `answer-key.json` vs `answer-key-extended.json` yields two
   different F1s. cr-loop's Phase-E winner was *hidden* by the original
   answer-key and only surfaced against the extended one. The registry records
   answer-key version as a **column**, so this can never be silently conflated.
2. **Novel findings are conservative-by-default.** A produced finding with no
   answer-key match is **not** scored as FP automatically — it is tracked as a
   novel for human triage. Confirmed-real novels are folded into the extended
   answer-key (bumping its effective version). Without this loop, every variant
   that adds context *appears* to regress.
3. **F1 variance is ~0.01 on a single seed × 10 PRs.** Headline deltas are
   suggestive, not proven. The registry records sample size and flags small
   deltas as inconclusive rather than confirmed.

## 5. What is new (the build)

Only connective tissue. New tree under `experiments/code-review/`:

```
experiments/code-review/
├── README.md          # the framework: hypothesis → variant → run → score → sheet loop + conventions
├── DESIGN.md          # this document
├── TRACKER.md         # thin human pointer; the Sheet is the source of truth
└── scripts/
    ├── aggregate.ts   # roll up N per-PR ScoreResults (one variant) → one experiment-level Results row
    └── sync-sheet.ts  # emit results-row.json for MCP-driven append (see §7)
```

`cr-loop/` is **not moved** (moving it breaks `scripts/kg/*.ts` relative imports
of `../../../scripts/kg-query/`). It is referenced as experiment #1.

### 5.1 `aggregate.ts`

- **Input:** a directory of per-PR findings for one variant (e.g.
  `cr-loop/results/raw/phase-E/`) + an answer-key selection.
- **Behaviour:** invoke the cr-loop scoring logic per PR, then aggregate:
  - `TP`, `FP`, `FN`, `novels`, `halfCredits` summed across PRs.
  - Aggregate `precision = ΣTP / (ΣTP+ΣFP)`, `recall = ΣTP / (ΣTP+ΣFN)`,
    `F1 = 2PR/(P+R)` — computed from the summed counts (micro-average), not a
    mean of per-PR F1s (which would over-weight small PRs).
  - Pass through experiment metadata: experiment id, variant/phase, skill
    version, model, KG state, answer-key version, N PRs.
  - Cost/latency: if a `run-meta.json` (tokens / `cost_usd` / `duration_ms`) is
    present alongside the findings, roll it up; otherwise emit `null` (recorded
    as blank, never fabricated).
- **Output:** a single `results-row.json` matching the Results tab schema (§6.3).
- **Fail-fast (per aictrl conventions):** throw with the offending PR/file id on
  missing findings, malformed JSON, or an answer-key version that does not match
  the requested one. A measurement, never a gate — but it must never score
  partial data silently.

### 5.2 `sync-sheet.ts`

- Validates a `results-row.json` against the Results schema and the referenced
  `H-ID` (which must already exist in the Hypotheses tab — no orphan Results).
- Emits the row in append-ready form (ordered cell array) for the **google-sheets
  MCP** to write. The actual append is performed in-session via MCP
  (`update_cells` / `batch_update_cells`), not by this script directly.

## 6. The Google Sheet

Three tabs (the existing `Merics` tab is renamed `Metrics`).

### 6.1 Hypotheses (human-authored)

| Column | Meaning |
|---|---|
| H-ID | `H-001`, `H-002`, … |
| Experiment | e.g. `cr-loop` |
| Date | proposed date |
| Hypothesis | "We believe ⟨variant change⟩ will ⟨move metric⟩ because ⟨reason⟩" |
| Knob | prompt / model / subagents / thresholds / prompt-structure / KG |
| Predicted effect | e.g. `+recall, neutral cost` |
| Status | proposed → running → scored → confirmed / refuted / abandoned |
| Result R-IDs | comma-separated links to Results rows |
| Learning | one-line outcome once scored |

### 6.2 Metrics (dictionary + live baseline)

| Column | Meaning |
|---|---|
| Metric | Precision, Recall, F1, Novel-rate, Half-credit rule, Cost (tokens/$), p50/p95 latency, Coverage-by-category |
| Definition | plain-language |
| Formula | e.g. `F1 = 2PR/(P+R)`, micro-averaged across PRs |
| Source | `gold-benchmark` (this framework) or `BigQuery-live` (prod dashboard, for drift context) |
| Direction | ↑ better / ↓ better |
| Baseline value | current prod-equivalent config (cr-loop Phase A/B: F1 ≈ 0.23–0.30) |

The Metrics tab reuses the existing aictrl code-review vocabulary
(precision/recall/F1, verdict TRUE/FALSE/UNCERTAIN, severity, novels) rather
than inventing parallel terms.

### 6.3 Results (one row per variant × answer-key run; MCP-written)

| Column | Source |
|---|---|
| R-ID | assigned on write (`R-001`…) |
| Experiment | metadata |
| H-ID | links to Hypotheses |
| Variant / Phase | e.g. `Phase E — SHOULD use, no gating` |
| Skill version | e.g. `code-review.SKILL.v3.md` |
| Model | e.g. `zai-coding-plan/glm-5.1` |
| KG state | empty / populated |
| AnswerKey version | `orig` / `extended` (**dimension, not variant** — §4.1) |
| N PRs | sample size |
| TP, FP, FN, Novels | aggregated counts |
| Precision, Recall, F1 | micro-averaged |
| Δ F1 vs baseline | vs the experiment's declared baseline variant |
| Cost | tokens / `$` (blank if no run-meta) |
| Log link | path to the phase log / findings dir |

### 6.4 Seed / back-fill (first action after build)

- **Results:** cr-loop's **5 phases (A, B, C-failed, D, E) × 2 answer-keys** as
  the opening rows, taken from the README's published table and `results/raw/`.
- **Hypotheses:** cr-loop's three findings as Hypotheses with terminal status:
  - H: "KG availability raises F1" → B vs A (+0.04) → **confirmed (weak)**.
  - H: "MUST-verify-before-record raises precision" → Phase D → **refuted**
    (recall collapse, −0.15 F1).
  - H: "SHOULD-use, no gating is the right lever" → Phase E → **confirmed**
    (+0.088 F1 vs B on extended AK).
- **Metrics:** seed the dictionary + Phase A/B baseline values.

This makes the framework immediately real and demonstrates the schema, instead
of shipping an empty sheet.

## 7. Sheet-write mechanism

**MCP-driven, in-session** (chosen over a service-account script):
`aggregate.ts` → `results-row.json`; `sync-sheet.ts` validates it; the row is
appended via the connected **google-sheets MCP**. Zero new credentials; works
today. A `googleapis` + service-account path can be added later if unattended /
CI writes are wanted — the row shape is identical, so nothing is thrown away.

## 8. The experiment loop (conventions, documented in README.md)

1. **Author** a Hypotheses row + define the variant (a skill file / config under
   the experiment's folder).
2. **Run** the variant over the frozen benchmark; collect per-PR findings into
   the experiment's `results/` (reusing cr-loop's runners).
3. **Aggregate + score:** `aggregate.ts` → `results-row.json` (per answer-key
   version).
4. **Sync:** append the Results row(s) via MCP; set the Hypothesis status.
5. **Triage novels:** adjudicate unmatched produced findings; fold confirmed-real
   ones into the extended answer-key (bump version); re-score if needed.
6. **Conclude:** mark the Hypothesis confirmed / refuted / inconclusive, with the
   one-line Learning.

## 9. Discipline baked in

- **Baseline first:** score the prod-equivalent variant to fill the Metrics
  baseline before comparing anything.
- **Version-gated comparison:** only compare Results rows sharing an answer-key
  version; `aggregate.ts` throws on mismatch.
- **Small-sample honesty:** record N; flag deltas within F1 noise (~0.01 on
  10 PRs / single seed) as inconclusive, never confirmed. Encourage 3-seed
  averaging for headline claims.
- **Conservative novels:** never auto-score an unmatched finding as FP; route it
  to triage.
- **Fail-fast:** missing fields, version mismatch, or unknown H-ID → throw with
  the offending id; no orphan Results, no silent partial scoring.

## 10. Testing

- **`aggregate.ts`:** unit tests on the micro-average rollup (known per-PR
  counts → known aggregate P/R/F1); answer-key-mismatch throws; missing
  run-meta → null cost, not a crash.
- **`sync-sheet.ts`:** schema validation rejects a row with an unknown H-ID or
  missing required column; emitted cell order matches the Results header.
- Reuse cr-loop's existing per-PR scoring behaviour as the trusted inner loop
  (not re-tested here).

## 11. Open questions / future work

- 3-seed averaging to tighten F1 bars (cr-loop caveat).
- Optional `BigQuery-live` columns in Metrics to track real-world drift against
  the controlled benchmark.
- Auto-orchestration (Approach B) if manual variant runs become the bottleneck.
- A service-account write path for unattended/CI runs.
