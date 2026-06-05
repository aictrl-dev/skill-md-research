# `cr-local-kg` — Local-Model Code Review on Current Files, KG A/B

**Date:** 2026-06-05
**Status:** design approved — pending spec review
**Home:** `experiments/cr-local-kg/` (new)
**Depends on:** `experiments/cr-loop/` (scorer + skill variants), `experiments/code-review/` (registry framework)

---

## 1. Purpose & hypothesis

Does giving a **local** reviewer model (`gemma4:12b-96k` via ollama) access to the
aictrl Knowledge Graph (callers, impact, co-changes, prior findings, linked
issues) improve its code review of **current** `aictrl_main` files?

This re-tests cr-loop's central question under two deliberate changes:

1. **Local small model** (`gemma4:12b-96k`) instead of cloud `glm-5.1`.
2. **Current files** instead of historical PR diffs — which removes the
   "time machine" problem: the production KG reflects the *current* state of the
   codebase, so reviewing current code keeps the KG and the thing-under-review in
   sync. Reviewing a historical diff means the KG already contains the PR's
   changes (or code that came after), desynchronising graph and target.

**Primary hypotheses (registered in the Google Sheet):**

- **H-local-1:** Local-model KG availability raises F1 (treatment > control).
- **H-local-2:** The KG effect concentrates on **module** tasks (cross-file
  reasoning) and is near-zero on **single-file** tasks.

## 2. Conditions

Identical model, prompt, tasks, and seeds across both conditions; a single toggle:

| Condition | Tools | Mechanism |
|---|---|---|
| **Control** (−KG) | file read / grep / glob only | opencode, no MCP |
| **Treatment** (+KG) | + 24 aictrl KG tools | opencode + remote `https://aictrl.dev/aictrl/mcp` (Bearer token; KG already populated for the aictrl repo) |

This reuses **kg-ab-test's proven mechanism** — two opencode config files that
differ only in the `mcp` block (see `experiments/kg-ab-test/opencode-control.json`
vs `opencode-treatment.json`) — applied to a *review* task rather than a
*generation* task. No local backend, Firestore emulator, or Neo4j required: the
treatment uses the production MCP.

**Rejected alternatives:**
- cr-loop's local-backend + Neo4j + `aictrl` CLI stack — the CLI is wired to
  `glm-5.1`; retargeting it to ollama is a large lift for no benefit here.
- A custom ollama + MCP client — reinvents opencode's tool-calling loop and MCP
  transport for nothing.

## 3. Tasks — current files & modules

- **Pin `aictrl_main` to a fixed commit** so "current files" is frozen and
  reproducible. The commit MUST be one the production KG has indexed (see §7,
  risk 2), otherwise treatment `query_context: domain=code` calls return empty.
- **Selection (the approved "mix"):** ~**15 single-file tasks** + ~**5 module
  tasks**. A *module* is a small related set of current files (e.g.
  route → service → repo) chosen for KG-visible coupling (callers / impact /
  co-changes), so the treatment has cross-file work to exploit.
  - Single-file tasks act as a near-control: the KG has little to do, so we
    expect ~zero effect there (H-local-2).
- **Review prompt:** a self-contained code-review prompt adapted from cr-loop's
  **Phase-E winner** (`cr-loop/skills/code-review.SKILL.v3.md` — the
  "SHOULD use, no gating" wording that drove the +KG tool usage). The reviewer
  receives the file(s) and emits findings as JSON.

## 4. Ground truth — KG-neutral frozen gold

Build a **frozen answer-key per task, once**, before the sweep:

1. **Claude oracle, MCP off** (`claude` CLI, no KG) proposes candidate findings
   on each task. Claude is independent of the aictrl review stack, giving the
   least-biased gold.
2. **Manual triage** of candidates → TRUE / FALSE / UNCERTAIN, plus any
   **curated real issues** known about those files folded in.
3. The result is `answer-key.json` in cr-loop's answer-key shape.

**Why this is not circular / not KG-biased:** the oracle never touches the KG,
so the gold is neutral to the treatment. Both conditions (gemma ±KG) are scored
against the *same* fixed gold.

**Acknowledged confound:** the oracle (strong) sets a high bar; gemma (small,
local) will score low in **absolute** F1. The experiment's result is the
**+KG vs −KG delta**, not the absolute F1.

## 5. Scoring & registry integration

- Emit gemma findings as JSON in **cr-loop's findings shape**; reuse
  `experiments/cr-loop/scripts/score.ts` (`score()` — fuzzy file + line +
  semantic match → TP / FP / FN / novels / half-credits / precision / recall /
  F1) as the per-task scorer.
- Roll up via the **`experiments/code-review` framework**: `aggregate.ts`
  (micro-averaged Results row per condition) → `sync-sheet.ts` → Google Sheet
  registry.
- This experiment is a **new registry entry**: new `Hypotheses` rows (H-local-1,
  H-local-2) + `Results` rows per **condition × seed** (and, for H-local-2,
  per **task-class** = single-file vs module).
- **Invariant inherited from cr-loop:** novels (gemma findings with no gold
  match) are routed to triage, **never auto-scored as FP**. Confirmed-real
  novels may extend the gold (bumping its version), recorded as a scoring
  dimension, not a variant.

## 6. Scale & build sequence

**Target: Medium, 3 seeds** — ~20 tasks × 2 conditions × 3 seeds ≈ **120 local
gemma runs** (free but slow) + ~20 Claude oracle runs (gold, once). Built
incrementally so gold is never curated against broken plumbing:

1. **Smoke (1 seed, 2 files + 1 module):** confirm opencode → ollama runs;
   gemma actually *calls* KG tools in treatment; findings parse; `score.ts`
   produces sane F1.
2. **Gold build:** Claude oracle + triage across all ~20 tasks → frozen
   `answer-key.json`.
3. **Full sweep:** 3 seeds × 2 conditions; `aggregate.ts`; sync to sheet;
   triage novels; conclude with one-line Learning per hypothesis.

## 7. Risks / open questions

1. **gemma tool-calling quality (the core bet).** A 12B local model may
   under-use 24 KG tools. If treatment barely calls them, there is no effect to
   measure. The smoke step (§6.1) checks tool-call counts; if weak, adjust the
   prompt (cr-loop showed wording is the dominant lever — 2.6× swing) or record
   "local model too small to exploit KG" as the finding itself.
2. **KG / code sync.** The production KG must have indexed the pinned commit
   (the milder, current-code form of the time-machine concern). Prerequisite:
   confirm `query_context: domain=code` returns real results for the selected
   files at the pinned commit; otherwise re-index or move the pin.
3. **96k context vs KG tool output.** Module reviews plus graph results may
   strain even the 96k window; watch for context truncation silently dropping
   either the code or the tool results.
4. **opencode ollama provider** is not yet configured locally (no `ollama`
   block in `~/.config/opencode/`). Small addition: point an openai-compatible
   provider at `localhost:11434`. Verified in smoke step.

## 8. What already exists (reused as-is)

| Asset | Role |
|---|---|
| `experiments/kg-ab-test/opencode-{control,treatment}.json` | the −KG / +KG config toggle pattern |
| `experiments/cr-loop/skills/code-review.SKILL.v3.md` | the proven +KG review prompt (Phase-E winner) |
| `experiments/cr-loop/scripts/score.ts` | per-task fuzzy scorer → F1 |
| `experiments/code-review/scripts/{aggregate,sync-sheet,schema}.ts` | registry roll-up + Google Sheet append |
| `claude` CLI | KG-off gold oracle |
| ollama `gemma4:12b-96k` | the reviewer model under test |

## 9. What is new (the build)

```
experiments/cr-local-kg/
├── README.md                       # this experiment's how-to
├── opencode-control.json           # −KG (no mcp)
├── opencode-treatment.json         # +KG (aictrl.dev mcp)
├── tasks/
│   ├── files/*.json                # ~15 single-file task specs (pinned commit + path)
│   └── modules/*.json              # ~5 module task specs (file sets)
├── prompts/review.md               # self-contained reviewer prompt (from SKILL.v3)
├── answer-key.json                 # frozen KG-neutral gold (oracle + triage)
├── scripts/
│   ├── build-gold.sh               # claude oracle (MCP off) over tasks → candidates
│   ├── run-condition.sh            # opencode + ollama over tasks for one condition/seed
│   └── score-sweep.ts              # per-task score.ts → aggregate.ts → results-row.json
└── results/
    ├── gold-candidates/            # raw oracle output pre-triage
    └── raw/seed-{1,2,3}/{control,treatment}/<task>.findings.json
```

## 10. Out of scope

- Generalising beyond `gemma4:12b-96k` / one repo / TypeScript (note as caveat).
- Local KG population / Neo4j (treatment uses prod MCP).
- Auto-orchestration of the reviewer across tasks beyond `run-condition.sh`.
- Production skill changes — this is measurement, not a product change.
