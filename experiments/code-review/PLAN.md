# Code-Review Research Framework — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the connective tissue that turns the one-off `cr-loop` study into a repeatable code-review research practice: an `aggregate.ts` that rolls per-PR scores into one experiment-level Results row, a `sync-sheet.ts` that validates a row and emits MCP-ready cells, plus README/TRACKER docs.

**Architecture:** Reuse `cr-loop`'s exported per-PR `score()` as the trusted inner loop. A shared `schema.ts` owns the Results column order + enums + validation (DRY between aggregate and sync). `aggregate.ts` and `sync-sheet.ts` each expose a pure function + a thin CLI guarded by `import.meta.url`. Sheet writes stay MCP-driven (the scripts produce JSON; the agent appends via the google-sheets MCP).

**Tech Stack:** TypeScript run via `npx tsx` (no build step), `node:test` + `node:assert/strict` for tests (zero extra deps), executed with `npx tsx --test <files>`.

**Repo & branch:** All work happens in the **`skill-md-research`** repo (`/home/bulat/code/skill-md-research`) on the existing branch **`feat/code-review-research-framework`**. Every command below assumes that repo root as cwd. Spec: [`experiments/code-review/DESIGN.md`](./DESIGN.md).

---

## File Structure

```
experiments/code-review/
├── DESIGN.md                       # spec (already committed)
├── PLAN.md                         # this file
├── package.json                    # NEW — npm script aliases + type:module
├── README.md                       # NEW — the loop, conventions, baked-in lessons
├── TRACKER.md                      # NEW — pointer to the Sheet + experiment index
└── scripts/
    ├── schema.ts                   # NEW — RESULTS_COLUMNS, enums, ResultsRow, validate, toCellArray
    ├── schema.test.ts              # NEW
    ├── aggregate.ts                # NEW — aggregate() + CLI
    ├── aggregate.test.ts           # NEW
    ├── sync-sheet.ts               # NEW — validate + emit cells + CLI
    ├── sync-sheet.test.ts          # NEW
    ├── score-path.test.ts          # NEW — locks the score.ts refactor
    └── __fixtures__/               # NEW — deterministic test data
        ├── answer-key.json
        └── findings/
            ├── PR-1.findings.json
            └── PR-2.findings.json
```

**Modified:** `experiments/cr-loop/scripts/score.ts` — one backward-compatible change (optional `answerKeyPath` param + export two interfaces).

---

### Task 1: Refactor `score.ts` to accept an explicit answer-key path

The aggregator must score the **same** findings against **both** answer-key versions in one process. Today `score.ts` locks the answer-key path at module load from `CR_LOOP_ANSWER_KEY`, so two versions can't coexist in one run. Add an optional 3rd parameter (default = existing behaviour) and export the types the aggregator needs. Fully backward compatible — the CLI and env default are untouched.

**Files:**
- Modify: `experiments/cr-loop/scripts/score.ts`
- Create: `experiments/code-review/scripts/__fixtures__/answer-key.json`
- Create: `experiments/code-review/scripts/__fixtures__/findings/PR-1.findings.json`
- Create: `experiments/code-review/scripts/__fixtures__/findings/PR-2.findings.json`
- Test: `experiments/code-review/scripts/score-path.test.ts`

- [ ] **Step 1: Create the fixture answer key**

Create `experiments/code-review/scripts/__fixtures__/answer-key.json`:

```json
{
  "1": [
    { "bot": "x", "severity": "BUG", "file": "a.ts", "line": "10", "description": "real bug, fixed", "verdict": "TRUE", "action": "FIX", "reason": "" },
    { "bot": "x", "severity": "BUG", "file": "b.ts", "line": "20", "description": "real bug, missed", "verdict": "TRUE", "action": "FIX", "reason": "" }
  ],
  "2": [
    { "bot": "x", "severity": "SECURITY", "file": "c.ts", "line": "5", "description": "known false positive", "verdict": "FALSE", "action": "IGNORE", "reason": "" }
  ]
}
```

- [ ] **Step 2: Create the fixture findings files**

Create `experiments/code-review/scripts/__fixtures__/findings/PR-1.findings.json` (1 finding that matches `a.ts:10`; `b.ts:20` is left un-raised → a false negative):

```json
{ "prNumber": 1, "findings": [ { "file": "a.ts", "line": 10, "severity": "BUG", "title": "matches g1" } ] }
```

Create `experiments/code-review/scripts/__fixtures__/findings/PR-2.findings.json` (1 finding matching the FALSE-verdict label → a false positive, plus 1 novel finding with no label):

```json
{ "prNumber": 2, "findings": [ { "file": "c.ts", "line": 5, "severity": "SECURITY", "title": "repeats known FP" }, { "file": "d.ts", "line": 99, "severity": "BUG", "title": "novel" } ] }
```

- [ ] **Step 3: Write the failing test**

Create `experiments/code-review/scripts/score-path.test.ts`:

```ts
import { test } from 'node:test';
import assert from 'node:assert/strict';
import * as path from 'node:path';
import { fileURLToPath } from 'node:url';
import { score } from '../../cr-loop/scripts/score.ts';

const here = path.dirname(fileURLToPath(import.meta.url));
const FIX_AK = path.join(here, '__fixtures__', 'answer-key.json');

test('score() honours an explicit answerKeyPath argument', () => {
  // PR 1: one finding matching a.ts:10 (TRUE/FIX) -> 1 TP; b.ts:20 missed -> 1 FN
  const result = score(1, [{ file: 'a.ts', line: 10, severity: 'BUG' }], FIX_AK);
  assert.equal(result.totals.truePositives, 1);
  assert.equal(result.totals.falseNegatives, 1);
  assert.equal(result.totals.novelFindings, 0);
  assert.equal(result.precision, 1);
});
```

- [ ] **Step 4: Run the test to verify it fails**

Run: `cd /home/bulat/code/skill-md-research && npx tsx --test experiments/code-review/scripts/score-path.test.ts`
Expected: FAIL — `score` accepts only 2 args, so the 3rd argument is ignored and it reads the real cr-loop answer key (`PR 1` there has different labels), OR a type error. Confirm it does not pass.

- [ ] **Step 5: Apply the refactor to `score.ts`**

In `experiments/cr-loop/scripts/score.ts`, export the two interfaces the aggregator imports. Change:

```ts
interface SkillFinding {
```
to:
```ts
export interface SkillFinding {
```

and change:

```ts
interface ScoreResult {
```
to:
```ts
export interface ScoreResult {
```

Then change the function signature and the read line. Replace:

```ts
export function score(prNumber: number, skillFindings: SkillFinding[]): ScoreResult {
  const answerKey = JSON.parse(fs.readFileSync(ANSWER_KEY_PATH, 'utf8')) as Record<string, AnswerKeyEntry[]>;
```
with:
```ts
export function score(
  prNumber: number,
  skillFindings: SkillFinding[],
  answerKeyPath: string = ANSWER_KEY_PATH,
): ScoreResult {
  const answerKey = JSON.parse(fs.readFileSync(answerKeyPath, 'utf8')) as Record<string, AnswerKeyEntry[]>;
```

- [ ] **Step 6: Run the test to verify it passes**

Run: `cd /home/bulat/code/skill-md-research && npx tsx --test experiments/code-review/scripts/score-path.test.ts`
Expected: PASS (`# pass 1`, exit 0).

- [ ] **Step 7: Verify the CLI still works (no regression)**

Run: `cd /home/bulat/code/skill-md-research/experiments/cr-loop && npx tsx scripts/score.ts --findings results/raw/phase-E/PR-1785.findings.json`
Expected: prints a JSON `ScoreResult` with `"prNumber": 1785` (default answer key still used). Exit 0.

- [ ] **Step 8: Commit**

```bash
cd /home/bulat/code/skill-md-research
git add experiments/cr-loop/scripts/score.ts experiments/code-review/scripts/score-path.test.ts experiments/code-review/scripts/__fixtures__
git commit -m "feat(cr-research): score() accepts explicit answer-key path + export types

Backward-compatible: default path and CLI unchanged. Enables scoring the
same findings against both answer-key versions in one process."
```

---

### Task 2: `schema.ts` — Results column contract (enums, validation, cell ordering)

Single source of truth for the Results row shape, shared by `aggregate.ts` and `sync-sheet.ts`. `RESULTS_COLUMNS` must match the Sheet header exactly (drift here silently misaligns every appended row).

**Files:**
- Create: `experiments/code-review/scripts/schema.ts`
- Test: `experiments/code-review/scripts/schema.test.ts`

- [ ] **Step 1: Write the failing test**

Create `experiments/code-review/scripts/schema.test.ts`:

```ts
import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  RESULTS_COLUMNS,
  validateResultsRow,
  toCellArray,
  type ResultsRow,
} from './schema.ts';

const goodRow: ResultsRow = {
  experiment: 'cr-loop',
  hId: 'H-001',
  variant: 'Phase E',
  skillVersion: 'code-review.SKILL.v3.md',
  model: 'zai-coding-plan/glm-5.1',
  kgState: 'populated',
  answerKeyVersion: 'extended',
  nPrs: 10,
  tp: 30, fp: 1, fn: 73.5, novels: 14,
  precision: 0.968, recall: 0.29, f1: 0.446,
  deltaF1: 0.077, cost: '', logLink: 'log/004.md',
};

test('RESULTS_COLUMNS matches the committed Sheet header exactly', () => {
  assert.deepEqual(RESULTS_COLUMNS, [
    'R-ID', 'Experiment', 'H-ID', 'Variant / Phase', 'Skill Version', 'Model',
    'KG State', 'AnswerKey Version', 'N PRs', 'TP', 'FP', 'FN', 'Novels',
    'Precision', 'Recall', 'F1', 'Δ F1 vs Baseline', 'Cost', 'Log Link',
  ]);
});

test('validateResultsRow accepts a well-formed row', () => {
  assert.doesNotThrow(() => validateResultsRow(goodRow));
});

test('validateResultsRow rejects an unknown KG State', () => {
  assert.throws(() => validateResultsRow({ ...goodRow, kgState: 'foo' as never }), /KG State/);
});

test('validateResultsRow rejects an unknown AnswerKey Version', () => {
  assert.throws(() => validateResultsRow({ ...goodRow, answerKeyVersion: 'v2' as never }), /AnswerKey Version/);
});

test('validateResultsRow rejects a malformed H-ID', () => {
  assert.throws(() => validateResultsRow({ ...goodRow, hId: 'HX1' }), /H-ID/);
});

test('validateResultsRow enforces knownHids when provided (no orphan Results)', () => {
  assert.throws(() => validateResultsRow(goodRow, { knownHids: ['H-002'] }), /not found/);
  assert.doesNotThrow(() => validateResultsRow(goodRow, { knownHids: ['H-001'] }));
});

test('toCellArray returns 19 cells in column order with R-ID blank by default', () => {
  const cells = toCellArray(goodRow);
  assert.equal(cells.length, 19);
  assert.equal(cells[0], '');                 // R-ID assigned at write
  assert.equal(cells[1], 'cr-loop');           // Experiment
  assert.equal(cells[7], 'extended');          // AnswerKey Version
  assert.equal(cells[15], 0.446);              // F1
});

test('toCellArray renders null deltaF1 as blank', () => {
  const cells = toCellArray({ ...goodRow, deltaF1: null });
  assert.equal(cells[16], '');
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd /home/bulat/code/skill-md-research && npx tsx --test experiments/code-review/scripts/schema.test.ts`
Expected: FAIL — `Cannot find module './schema.ts'`.

- [ ] **Step 3: Write `schema.ts`**

Create `experiments/code-review/scripts/schema.ts`:

```ts
/**
 * Results-row contract for the code-review research framework.
 * Single source of truth shared by aggregate.ts and sync-sheet.ts.
 * RESULTS_COLUMNS MUST stay identical to the "Results" tab header in the Sheet.
 */

export const RESULTS_COLUMNS = [
  'R-ID', 'Experiment', 'H-ID', 'Variant / Phase', 'Skill Version', 'Model',
  'KG State', 'AnswerKey Version', 'N PRs', 'TP', 'FP', 'FN', 'Novels',
  'Precision', 'Recall', 'F1', 'Δ F1 vs Baseline', 'Cost', 'Log Link',
] as const;

export const KG_STATES = ['empty', 'populated'] as const;
export type KgState = (typeof KG_STATES)[number];

export const ANSWER_KEY_VERSIONS = ['orig', 'extended'] as const;
export type AnswerKeyVersion = (typeof ANSWER_KEY_VERSIONS)[number];

export interface ResultsRow {
  rId?: string; // assigned at MCP write time; blank from the scripts
  experiment: string;
  hId: string;
  variant: string;
  skillVersion: string;
  model: string;
  kgState: KgState;
  answerKeyVersion: AnswerKeyVersion;
  nPrs: number;
  tp: number;
  fp: number;
  fn: number;
  novels: number;
  precision: number;
  recall: number;
  f1: number;
  deltaF1: number | null; // blank when no baseline supplied
  cost: string; // tokens / $ ; blank when no run-meta
  logLink: string;
}

export interface ValidateOpts {
  /** When supplied, the row's hId MUST be a member (prevents orphan Results). */
  knownHids?: string[];
}

const REQUIRED_STRINGS: ReadonlyArray<keyof ResultsRow> = [
  'experiment', 'hId', 'variant', 'skillVersion', 'model',
];
const REQUIRED_NUMBERS: ReadonlyArray<keyof ResultsRow> = [
  'nPrs', 'tp', 'fp', 'fn', 'novels', 'precision', 'recall', 'f1',
];

export function validateResultsRow(row: ResultsRow, opts: ValidateOpts = {}): void {
  for (const k of REQUIRED_STRINGS) {
    if (typeof row[k] !== 'string' || (row[k] as string).trim() === '') {
      throw new Error(`Results row invalid: '${k}' must be a non-empty string`);
    }
  }
  if (!/^H-\d+$/.test(row.hId)) {
    throw new Error(`Results row invalid: H-ID '${row.hId}' must match /^H-\\d+$/`);
  }
  if (!(KG_STATES as readonly string[]).includes(row.kgState)) {
    throw new Error(`Results row invalid: KG State '${row.kgState}' not in ${KG_STATES.join(' | ')}`);
  }
  if (!(ANSWER_KEY_VERSIONS as readonly string[]).includes(row.answerKeyVersion)) {
    throw new Error(`Results row invalid: AnswerKey Version '${row.answerKeyVersion}' not in ${ANSWER_KEY_VERSIONS.join(' | ')}`);
  }
  for (const k of REQUIRED_NUMBERS) {
    if (typeof row[k] !== 'number' || !Number.isFinite(row[k] as number)) {
      throw new Error(`Results row invalid: '${k}' must be a finite number`);
    }
  }
  if (row.deltaF1 !== null && (typeof row.deltaF1 !== 'number' || !Number.isFinite(row.deltaF1))) {
    throw new Error(`Results row invalid: 'deltaF1' must be a finite number or null`);
  }
  if (opts.knownHids && !opts.knownHids.includes(row.hId)) {
    throw new Error(`Results row invalid: H-ID '${row.hId}' not found among known hypotheses [${opts.knownHids.join(', ')}]`);
  }
}

/** Render a row into a 19-cell array in exact RESULTS_COLUMNS order. */
export function toCellArray(row: ResultsRow): (string | number)[] {
  const blankIfNull = (v: number | null): string | number => (v === null ? '' : v);
  return [
    row.rId ?? '',
    row.experiment,
    row.hId,
    row.variant,
    row.skillVersion,
    row.model,
    row.kgState,
    row.answerKeyVersion,
    row.nPrs,
    row.tp,
    row.fp,
    row.fn,
    row.novels,
    row.precision,
    row.recall,
    row.f1,
    blankIfNull(row.deltaF1),
    row.cost,
    row.logLink,
  ];
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd /home/bulat/code/skill-md-research && npx tsx --test experiments/code-review/scripts/schema.test.ts`
Expected: PASS (`# pass 8`, exit 0).

- [ ] **Step 5: Commit**

```bash
cd /home/bulat/code/skill-md-research
git add experiments/code-review/scripts/schema.ts experiments/code-review/scripts/schema.test.ts
git commit -m "feat(cr-research): add schema.ts — Results column contract + validation"
```

---

### Task 3: `aggregate.ts` — roll per-PR scores into one Results row

**Files:**
- Create: `experiments/code-review/scripts/aggregate.ts`
- Test: `experiments/code-review/scripts/aggregate.test.ts`

- [ ] **Step 1: Write the failing test**

Create `experiments/code-review/scripts/aggregate.test.ts`. Uses the Task 1 fixtures. Hand-computed expectation: PR-1 → TP 1, FN 1; PR-2 → FP 1 (matches FALSE label), Novel 1. Micro: TP 1, FP 1, FN 1, Novels 1, N 2 → precision 0.5, recall 0.5, f1 0.5.

```ts
import { test } from 'node:test';
import assert from 'node:assert/strict';
import * as path from 'node:path';
import { fileURLToPath } from 'node:url';
import { aggregate } from './aggregate.ts';

const here = path.dirname(fileURLToPath(import.meta.url));
const FIX_AK = path.join(here, '__fixtures__', 'answer-key.json');
const FIX_FINDINGS = path.join(here, '__fixtures__', 'findings');

const meta = {
  experiment: 'fixture',
  hId: 'H-001',
  variant: 'unit-test',
  skillVersion: 'fix.md',
  model: 'test',
  kgState: 'empty' as const,
};

test('aggregate micro-averages per-PR scores into one row', () => {
  const row = aggregate(FIX_FINDINGS, FIX_AK, 'orig', meta);
  assert.equal(row.nPrs, 2);
  assert.equal(row.tp, 1);
  assert.equal(row.fp, 1);
  assert.equal(row.fn, 1);
  assert.equal(row.novels, 1);
  assert.equal(row.precision, 0.5);
  assert.equal(row.recall, 0.5);
  assert.equal(row.f1, 0.5);
  assert.equal(row.answerKeyVersion, 'orig');
  assert.equal(row.deltaF1, null); // no baseline supplied
});

test('aggregate computes deltaF1 against a supplied baseline', () => {
  const row = aggregate(FIX_FINDINGS, FIX_AK, 'orig', { ...meta, baselineF1: 0.4 });
  assert.equal(row.deltaF1, 0.1); // 0.5 - 0.4
});

test('aggregate throws on an empty findings directory', () => {
  assert.throws(() => aggregate(here, FIX_AK, 'orig', meta), /no PR-.*findings/i);
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd /home/bulat/code/skill-md-research && npx tsx --test experiments/code-review/scripts/aggregate.test.ts`
Expected: FAIL — `Cannot find module './aggregate.ts'`.

- [ ] **Step 3: Write `aggregate.ts`**

Create `experiments/code-review/scripts/aggregate.ts`:

```ts
#!/usr/bin/env npx tsx
/**
 * Aggregate per-PR cr-loop scores for one variant into a single Results row.
 *
 * Reuses cr-loop's trusted score() per PR, then micro-averages: sum TP/FP/FN
 * across PRs and compute precision/recall/F1 from the sums (NOT a mean of
 * per-PR F1s, which would over-weight small PRs).
 *
 * Usage:
 *   npx tsx aggregate.ts --findings-dir <dir> --answer-key <orig|extended> \
 *     --experiment cr-loop --hypothesis H-003 --variant "Phase E" \
 *     --skill-version code-review.SKILL.v3.md --model zai-coding-plan/glm-5.1 \
 *     --kg-state populated [--baseline-f1 0.369] [--cost "46M tok"] \
 *     [--log-link log/004.md] [--out results-row.json]
 *
 * --answer-key orig|extended resolves to cr-loop/answer-key.json or
 * answer-key-extended.json. For tests, pass --answer-key-path + --answer-key-version.
 */
import * as fs from 'node:fs';
import * as path from 'node:path';
import { fileURLToPath } from 'node:url';
import { score, type SkillFinding } from '../../cr-loop/scripts/score.ts';
import {
  type ResultsRow,
  type KgState,
  type AnswerKeyVersion,
  KG_STATES,
  ANSWER_KEY_VERSIONS,
} from './schema.ts';

const round3 = (n: number): number => Math.round(n * 1000) / 1000;

export interface AggregateMeta {
  experiment: string;
  hId: string;
  variant: string;
  skillVersion: string;
  model: string;
  kgState: KgState;
  baselineF1?: number | null;
  cost?: string;
  logLink?: string;
}

export function aggregate(
  findingsDir: string,
  answerKeyPath: string,
  answerKeyVersion: AnswerKeyVersion,
  meta: AggregateMeta,
): ResultsRow {
  if (!fs.existsSync(findingsDir) || !fs.statSync(findingsDir).isDirectory()) {
    throw new Error(`aggregate: findings dir not found: ${findingsDir}`);
  }
  const files = fs
    .readdirSync(findingsDir)
    .filter((f) => /^PR-\d+\.findings\.json$/.test(f))
    .sort();
  if (files.length === 0) {
    throw new Error(`aggregate: no PR-*.findings.json files in ${findingsDir}`);
  }

  let tp = 0, fp = 0, fn = 0, novels = 0;
  for (const file of files) {
    const full = path.join(findingsDir, file);
    const data = JSON.parse(fs.readFileSync(full, 'utf8')) as {
      prNumber?: number;
      findings?: SkillFinding[];
    };
    if (!Array.isArray(data.findings)) {
      throw new Error(`aggregate: '${file}' has no 'findings' array`);
    }
    const prNumber = data.prNumber ?? Number(file.match(/^PR-(\d+)\./)?.[1]);
    if (!prNumber) {
      throw new Error(`aggregate: cannot determine PR number for '${file}'`);
    }
    const r = score(prNumber, data.findings, answerKeyPath);
    tp += r.totals.truePositives;
    fp += r.totals.falsePositives;
    fn += r.totals.falseNegatives;
    novels += r.totals.novelFindings;
  }

  const precision = tp + fp === 0 ? 0 : tp / (tp + fp);
  const recall = tp + fn === 0 ? 0 : tp / (tp + fn);
  const f1 = precision + recall === 0 ? 0 : (2 * precision * recall) / (precision + recall);
  const baseline = meta.baselineF1 ?? null;

  return {
    experiment: meta.experiment,
    hId: meta.hId,
    variant: meta.variant,
    skillVersion: meta.skillVersion,
    model: meta.model,
    kgState: meta.kgState,
    answerKeyVersion,
    nPrs: files.length,
    tp: round3(tp),
    fp: round3(fp),
    fn: round3(fn),
    novels,
    precision: round3(precision),
    recall: round3(recall),
    f1: round3(f1),
    deltaF1: baseline === null ? null : round3(f1 - baseline),
    cost: meta.cost ?? '',
    logLink: meta.logLink ?? '',
  };
}

// ---- CLI ----
function argMap(argv: string[]): Record<string, string> {
  const out: Record<string, string> = {};
  for (let i = 0; i < argv.length; i += 1) {
    if (argv[i].startsWith('--')) {
      out[argv[i].slice(2)] = argv[i + 1] ?? '';
      i += 1;
    }
  }
  return out;
}

function resolveAnswerKey(a: Record<string, string>): { path: string; version: AnswerKeyVersion } {
  const here = path.dirname(fileURLToPath(import.meta.url));
  if (a['answer-key-path']) {
    const version = a['answer-key-version'] as AnswerKeyVersion;
    if (!(ANSWER_KEY_VERSIONS as readonly string[]).includes(version)) {
      throw new Error(`--answer-key-version must be one of ${ANSWER_KEY_VERSIONS.join(' | ')}`);
    }
    return { path: a['answer-key-path'], version };
  }
  const version = a['answer-key'] as AnswerKeyVersion;
  if (!(ANSWER_KEY_VERSIONS as readonly string[]).includes(version)) {
    throw new Error(`--answer-key must be one of ${ANSWER_KEY_VERSIONS.join(' | ')}`);
  }
  const file = version === 'orig' ? 'answer-key.json' : 'answer-key-extended.json';
  return { path: path.resolve(here, '../../cr-loop', file), version };
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const a = argMap(process.argv.slice(2));
  if (!a['findings-dir']) {
    console.error('aggregate: --findings-dir is required');
    process.exit(1);
  }
  if (!(KG_STATES as readonly string[]).includes(a['kg-state'])) {
    console.error(`aggregate: --kg-state must be one of ${KG_STATES.join(' | ')}`);
    process.exit(1);
  }
  const ak = resolveAnswerKey(a);
  const row = aggregate(a['findings-dir'], ak.path, ak.version, {
    experiment: a.experiment,
    hId: a.hypothesis,
    variant: a.variant,
    skillVersion: a['skill-version'],
    model: a.model,
    kgState: a['kg-state'] as KgState,
    baselineF1: a['baseline-f1'] ? Number(a['baseline-f1']) : null,
    cost: a.cost,
    logLink: a['log-link'],
  });
  const json = JSON.stringify(row, null, 2);
  if (a.out) {
    fs.writeFileSync(a.out, json);
    console.error(`aggregate: wrote ${a.out}`);
  } else {
    console.log(json);
  }
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd /home/bulat/code/skill-md-research && npx tsx --test experiments/code-review/scripts/aggregate.test.ts`
Expected: PASS (`# pass 3`, exit 0).

- [ ] **Step 5: Smoke-test the CLI against real cr-loop Phase-E data**

Run:
```bash
cd /home/bulat/code/skill-md-research
npx tsx experiments/code-review/scripts/aggregate.ts \
  --findings-dir experiments/cr-loop/results/raw/phase-E \
  --answer-key extended --experiment cr-loop --hypothesis H-003 \
  --variant "Phase E — SHOULD use, no gating" \
  --skill-version code-review.SKILL.v3.md --model zai-coding-plan/glm-5.1 \
  --kg-state populated --baseline-f1 0.369 --log-link experiments/cr-loop/log/004-full-research-flow.md
```
Expected: a JSON `ResultsRow` printed to stdout with `"nPrs": 10`, `"answerKeyVersion": "extended"`, and a non-zero `f1`. (Sanity only — not asserted in a test, since the real answer key may evolve.)

- [ ] **Step 6: Commit**

```bash
cd /home/bulat/code/skill-md-research
git add experiments/code-review/scripts/aggregate.ts experiments/code-review/scripts/aggregate.test.ts
git commit -m "feat(cr-research): add aggregate.ts — micro-averaged Results row from per-PR scores"
```

---

### Task 4: `sync-sheet.ts` — validate a row and emit MCP-ready cells

Produces the exact payload the agent feeds to the google-sheets MCP (`update_cells` / `batch_update_cells`). Enforces the row contract and (optionally) the no-orphan-Results rule. Does **not** call the Sheets API.

**Files:**
- Create: `experiments/code-review/scripts/sync-sheet.ts`
- Test: `experiments/code-review/scripts/sync-sheet.test.ts`

- [ ] **Step 1: Write the failing test**

Create `experiments/code-review/scripts/sync-sheet.test.ts`:

```ts
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { buildSyncPayload } from './sync-sheet.ts';
import type { ResultsRow } from './schema.ts';

const row: ResultsRow = {
  experiment: 'cr-loop', hId: 'H-001', variant: 'Phase E',
  skillVersion: 'v3.md', model: 'glm-5.1', kgState: 'populated',
  answerKeyVersion: 'extended', nPrs: 10, tp: 30, fp: 1, fn: 73.5, novels: 14,
  precision: 0.968, recall: 0.29, f1: 0.446, deltaF1: 0.077, cost: '', logLink: '',
};

test('buildSyncPayload returns a Results-targeted single-row payload', () => {
  const payload = buildSyncPayload(row);
  assert.equal(payload.sheet, 'Results');
  assert.equal(payload.values.length, 1);
  assert.equal(payload.values[0].length, 19);
  assert.equal(payload.values[0][2], 'H-001'); // H-ID column
});

test('buildSyncPayload enforces knownHids (no orphan Results)', () => {
  assert.throws(() => buildSyncPayload(row, ['H-999']), /not found/);
  assert.doesNotThrow(() => buildSyncPayload(row, ['H-001']));
});

test('buildSyncPayload rejects an invalid row before emitting', () => {
  assert.throws(() => buildSyncPayload({ ...row, kgState: 'bad' as never }), /KG State/);
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd /home/bulat/code/skill-md-research && npx tsx --test experiments/code-review/scripts/sync-sheet.test.ts`
Expected: FAIL — `Cannot find module './sync-sheet.ts'`.

- [ ] **Step 3: Write `sync-sheet.ts`**

Create `experiments/code-review/scripts/sync-sheet.ts`:

```ts
#!/usr/bin/env npx tsx
/**
 * Validate a Results row and emit an MCP-ready append payload.
 *
 * The actual Sheet write is performed by the agent via the google-sheets MCP
 * (update_cells / batch_update_cells) — this script only validates + shapes.
 *
 * Usage:
 *   npx tsx sync-sheet.ts --in results-row.json [--known-hids H-001,H-002]
 * Prints: { "sheet": "Results", "values": [[ ...19 cells... ]] }
 */
import * as fs from 'node:fs';
import { validateResultsRow, toCellArray, type ResultsRow } from './schema.ts';

export interface SyncPayload {
  sheet: 'Results';
  values: (string | number)[][];
}

export function buildSyncPayload(row: ResultsRow, knownHids?: string[]): SyncPayload {
  validateResultsRow(row, knownHids ? { knownHids } : {});
  return { sheet: 'Results', values: [toCellArray(row)] };
}

// ---- CLI ----
function argMap(argv: string[]): Record<string, string> {
  const out: Record<string, string> = {};
  for (let i = 0; i < argv.length; i += 1) {
    if (argv[i].startsWith('--')) {
      out[argv[i].slice(2)] = argv[i + 1] ?? '';
      i += 1;
    }
  }
  return out;
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const a = argMap(process.argv.slice(2));
  if (!a.in) {
    console.error('sync-sheet: --in <results-row.json> is required');
    process.exit(1);
  }
  const row = JSON.parse(fs.readFileSync(a.in, 'utf8')) as ResultsRow;
  const knownHids = a['known-hids'] ? a['known-hids'].split(',').map((s) => s.trim()) : undefined;
  const payload = buildSyncPayload(row, knownHids);
  console.log(JSON.stringify(payload, null, 2));
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd /home/bulat/code/skill-md-research && npx tsx --test experiments/code-review/scripts/sync-sheet.test.ts`
Expected: PASS (`# pass 3`, exit 0).

- [ ] **Step 5: Commit**

```bash
cd /home/bulat/code/skill-md-research
git add experiments/code-review/scripts/sync-sheet.ts experiments/code-review/scripts/sync-sheet.test.ts
git commit -m "feat(cr-research): add sync-sheet.ts — validate row + emit MCP-ready cells"
```

---

### Task 5: `package.json`, `README.md`, `TRACKER.md`

**Files:**
- Create: `experiments/code-review/package.json`
- Create: `experiments/code-review/README.md`
- Create: `experiments/code-review/TRACKER.md`

- [ ] **Step 1: Create `package.json`**

Create `experiments/code-review/package.json`:

```json
{
  "name": "code-review-research",
  "private": true,
  "type": "module",
  "description": "Hypothesis/metrics/results framework for code-review-agent experiments",
  "scripts": {
    "test": "npx tsx --test scripts/schema.test.ts scripts/aggregate.test.ts scripts/sync-sheet.test.ts scripts/score-path.test.ts",
    "aggregate": "npx tsx scripts/aggregate.ts",
    "sync": "npx tsx scripts/sync-sheet.ts"
  }
}
```

- [ ] **Step 2: Verify the test script runs the whole suite**

Run: `cd /home/bulat/code/skill-md-research/experiments/code-review && npm test`
Expected: all suites pass (`# fail 0`, exit 0).

- [ ] **Step 3: Create `README.md`**

Create `experiments/code-review/README.md`:

````markdown
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
     --kg-state populated --baseline-f1 0.369 --out /tmp/row.json
   ```
4. **Sync** — validate + shape the row, then append it via the google-sheets MCP:
   ```bash
   npx tsx scripts/sync-sheet.ts --in /tmp/row.json --known-hids H-001,H-002,H-003
   ```
   Feed the printed `{ sheet, values }` to the MCP `update_cells` /
   `batch_update_cells` tool (the agent assigns the next `R-ID`).
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

- `scripts/schema.ts` — Results column contract, enums, validation, cell ordering.
- `scripts/aggregate.ts` — per-PR scores → one micro-averaged Results row.
- `scripts/sync-sheet.ts` — validate a row + emit the MCP append payload.
- Reuses `../cr-loop/scripts/score.ts` (`score()`) as the per-PR scorer.

## Tests

```bash
npm test   # or: npx tsx --test scripts/*.test.ts
```
````

- [ ] **Step 4: Create `TRACKER.md`**

Create `experiments/code-review/TRACKER.md`:

```markdown
# Code-Review Research Tracker

> The **[Google Sheet](https://docs.google.com/spreadsheets/d/1txtt4rYQULxMZQHOgOqn8TcAx5bQBPEjknRsDxIUU4Q/edit)**
> is the source of truth (tabs: Hypotheses · Metrics · Results · Schema).
> This file is a human-readable index only.

## Experiments

| # | Experiment | Folder | Status | Headline |
|---|-----------|--------|--------|----------|
| 1 | KG-augmented code review | [`../cr-loop`](../cr-loop/) | complete (single-seed pilot) | +29% F1 (0.300→0.388, ext AK) from a one-paragraph subagent-prompt change (Phase E) |

## How to add an experiment

See [`README.md`](./README.md). Each experiment is its own folder with a frozen
benchmark + answer key; this framework's scripts aggregate its runs into the
shared `Results` tab.
```

- [ ] **Step 5: Commit**

```bash
cd /home/bulat/code/skill-md-research
git add experiments/code-review/package.json experiments/code-review/README.md experiments/code-review/TRACKER.md
git commit -m "docs(cr-research): add package.json, README, and TRACKER"
```

---

### Task 6: Full-suite verification & push

**Files:** none (verification only)

- [ ] **Step 1: Run the complete test suite**

Run: `cd /home/bulat/code/skill-md-research/experiments/code-review && npm test`
Expected: every suite passes, `# fail 0`, exit 0. If any fail, fix before proceeding.

- [ ] **Step 2: Confirm cr-loop's scorer CLI still works (regression guard)**

Run: `cd /home/bulat/code/skill-md-research/experiments/cr-loop && npx tsx scripts/score.ts --findings results/raw/phase-B/PR-1790.findings.json`
Expected: valid JSON `ScoreResult`, exit 0.

- [ ] **Step 3: Review the diff, then push and open a PR**

```bash
cd /home/bulat/code/skill-md-research
git log --oneline main..HEAD
git push -u origin feat/code-review-research-framework
gh pr create --repo aictrl-dev/skill-md-research --base main \
  --title "Code-review research framework" \
  --body "Adds the cross-experiment hypothesis/metrics/results framework on top of the existing cr-loop harness. See experiments/code-review/DESIGN.md. Reuses cr-loop's per-PR score() (one backward-compatible refactor); adds schema/aggregate/sync-sheet with tests, README, TRACKER. Sheet writes are MCP-driven. cr-loop is referenced as experiment #1."
```
Expected: branch pushed, PR URL printed.

---

## Self-Review

**Spec coverage** (against `DESIGN.md`):
- §5 file tree (README, TRACKER, scripts/aggregate, scripts/sync-sheet) → Tasks 3, 4, 5. ✓
- §5.1 aggregate behaviour (micro-average, run-meta→null cost, fail-fast) → Task 3 (`aggregate()`, `cost` blank default, throws on empty dir / missing findings array). ✓
- §5.2 sync-sheet (validate + H-ID existence + ordered cells, no direct API) → Task 4 + schema `validateResultsRow`/`toCellArray`. ✓
- §4 invariant "answer-key version is a column not a variant" → Task 1 refactor enables dual scoring; `answerKeyVersion` is a Results field + Schema enum. ✓
- §4 "novels conservative" → inherited from `score()` (novels counted separately, never FP); documented in README. ✓
- §6.3 Results columns → `RESULTS_COLUMNS` locked to the committed header via a schema test. ✓
- §6.4 seed/back-fill → intentionally **out of this plan** (you scoped the Sheet to headers + Schema only); the aggregate CLI + smoke step produce the numbers when you choose to back-fill. Noted, not a gap.
- §7 MCP-driven writes → sync-sheet emits payload only; README step 4 documents the MCP hand-off. ✓
- §9 discipline (baseline, version-gated, small-sample, fail-fast) → `--baseline-f1`/`deltaF1`, README invariants, `validateResultsRow` throws. Version-gating of Δ is enforced by convention (README: compare same AnswerKey Version) — acceptable for a research tool.

**Placeholder scan:** none — every code/doc step contains full content.

**Type consistency:** `ResultsRow`, `KgState`, `AnswerKeyVersion`, `SkillFinding`, `ScoreResult` defined once and imported consistently; `score(prNumber, findings, answerKeyPath?)` signature matches all call sites (Task 1 def, Task 3 use); `RESULTS_COLUMNS` (19) matches `toCellArray` (19 cells) matches the Sheet header.
