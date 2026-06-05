#!/usr/bin/env npx tsx
/**
 * Unit tests for the cr-local-kg pipeline. Run with:
 *   npx tsx --test scripts/pipeline.test.ts
 *
 * All fixtures are synthetic and written to an OS tmp dir — results/raw is
 * never touched.
 */
import { test } from 'node:test';
import assert from 'node:assert/strict';
import * as fs from 'node:fs';
import * as os from 'node:os';
import * as path from 'node:path';

import { aggregate, parseSession } from './pipeline.ts';

// ---------------------------------------------------------------------------
// Fixture helpers
// ---------------------------------------------------------------------------
function mkTmp(): string {
  return fs.mkdtempSync(path.join(os.tmpdir(), 'crlkg-test-'));
}

function writeFindings(dir: string, pr: number, findings: unknown[]): void {
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(path.join(dir, `PR-${pr}.findings.json`), JSON.stringify({ prNumber: pr, findings }));
}

function writeRaw(dir: string, pr: number, name: string, contents: string): void {
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(path.join(dir, `PR-${pr}.${name}`), contents);
}

/** A step_finish JSONL event carrying token usage at part.tokens. */
function stepFinish(total: number, input: number, output: number, reasoning: number): string {
  return JSON.stringify({
    type: 'step_finish',
    part: { type: 'step-finish', tokens: { total, input, output, reasoning, cache: { read: 0, write: 0 } } },
  });
}

/** A message_complete JSONL event — duplicates the step's tokens; must NOT be double-counted. */
function messageComplete(total: number, input: number, output: number, reasoning: number): string {
  return JSON.stringify({
    type: 'message_complete',
    tokens: { total, input, output, reasoning, cache: { read: 0, write: 0 } },
  });
}

/** A tool_use JSONL event for a KG query_context call with the given action. */
function kgToolUse(action: string): string {
  return JSON.stringify({
    type: 'tool_use',
    part: { tool: 'aictrl_query_context', state: { status: 'completed', input: { action, domain: 'code', query: 'x' } } },
  });
}

/**
 * A tiny answer key. cr-loop's matcher needs (file, severity-family, line ±5).
 * PR 1 (file class): two TRUE/FIX entries -> hard recall targets.
 * PR 2 (module class): one TRUE/FIX entry.
 */
function writeAnswerKey(p: string): void {
  const ak = {
    '1': [
      {
        bot: 'x',
        severity: 'HIGH',
        file: 'a.ts',
        line: '10',
        description: 'real bug A',
        verdict: 'TRUE',
        action: 'FIX',
        reason: '',
      },
      {
        bot: 'x',
        severity: 'MEDIUM',
        file: 'b.ts',
        line: '20',
        description: 'real bug B',
        verdict: 'TRUE',
        action: 'FIX',
        reason: '',
      },
    ],
    '2': [
      {
        bot: 'x',
        severity: 'HIGH',
        file: 'm.ts',
        line: '5',
        description: 'real module bug',
        verdict: 'TRUE',
        action: 'FIX',
        reason: '',
      },
    ],
  };
  fs.writeFileSync(p, JSON.stringify(ak));
}

// ---------------------------------------------------------------------------
// 1. micro-average math
// ---------------------------------------------------------------------------
test('micro-average math: hand-computed TP/FP/FN and F1', () => {
  const base = mkTmp();
  const akPath = path.join(base, 'ak.json');
  writeAnswerKey(akPath);

  const filesDir = path.join(base, 'rep-1', 'control', 'files');
  // PR 1: catches bug A (TP), misses bug B (FN), raises one extra (novel).
  writeFindings(filesDir, 1, [
    { file: 'a.ts', line: 11, severity: 'HIGH', title: 'caught A' }, // matches AK#0 (TRUE/FIX -> TP)
    { file: 'z.ts', line: 99, severity: 'LOW', title: 'novel' }, // no AK match -> novel
  ]);
  const modulesDir = path.join(base, 'rep-1', 'control', 'modules');
  // PR 2: catches the module bug (TP).
  writeFindings(modulesDir, 2, [{ file: 'm.ts', line: 5, severity: 'HIGH', title: 'caught M' }]);

  const s = aggregate({ reps: [1], answerKeyPath: akPath, baseDir: base });
  const o = s.conditions.control.overall;

  // Hand-computed: TP=2 (A + M), FP=0, FN=1 (B missed, TRUE/FIX), novels=1.
  assert.equal(o.truePositives, 2);
  assert.equal(o.falsePositives, 0);
  assert.equal(o.falseNegatives, 1);
  assert.equal(o.novelFindings, 1);
  assert.equal(o.n, 2);

  // precision = 2/2 = 1, recall = 2/3 = 0.667, F1 = 2*1*0.667/(1+0.667) = 0.8.
  assert.equal(o.precision, 1);
  assert.equal(o.recall, 0.667);
  assert.equal(o.f1, 0.8);
});

// ---------------------------------------------------------------------------
// 2. token summing
// ---------------------------------------------------------------------------
test('token summing: 3 step_finish events, message_complete not double-counted', () => {
  const raw = [
    stepFinish(100, 90, 10, 0),
    messageComplete(100, 90, 10, 0), // duplicate — ignored
    messageComplete(100, 90, 10, 0), // duplicate — ignored
    stepFinish(250, 220, 30, 0),
    messageComplete(250, 220, 30, 0),
    stepFinish(500, 450, 50, 0),
    messageComplete(500, 450, 50, 0),
    'not json at all', // malformed line — skipped
  ].join('\n');

  const s = parseSession(raw);
  assert.equal(s.modelSteps, 3); // only step_finish counted
  assert.equal(s.outputTokens, 10 + 30 + 50); // 90
  assert.equal(s.reasoningTokens, 0);
  assert.equal(s.inputTokensCumulative, 90 + 220 + 450); // 760
});

// ---------------------------------------------------------------------------
// 3. KG-action parsing
// ---------------------------------------------------------------------------
test('KG-action parsing: histogram of callers + impact + repeat', () => {
  const raw = [kgToolUse('callers'), kgToolUse('impact'), kgToolUse('callers')].join('\n');
  const s = parseSession(raw);
  assert.equal(s.kgCalls, 3);
  assert.deepEqual(s.kgActions, { callers: 2, impact: 1 });
});

// ---------------------------------------------------------------------------
// 4. class split
// ---------------------------------------------------------------------------
test('class split: files -> file bucket, modules -> module bucket', () => {
  const base = mkTmp();
  const akPath = path.join(base, 'ak.json');
  writeAnswerKey(akPath);

  // file-class review under files/, module-class review under modules/
  writeFindings(path.join(base, 'rep-1', 'treatment', 'files'), 1, [
    { file: 'a.ts', line: 10, severity: 'HIGH', title: 'A' },
  ]);
  writeFindings(path.join(base, 'rep-1', 'treatment', 'modules'), 2, [
    { file: 'm.ts', line: 5, severity: 'HIGH', title: 'M' },
  ]);

  const s = aggregate({ reps: [1], answerKeyPath: akPath, baseDir: base });
  const t = s.conditions.treatment;
  assert.equal(t.byClass.file.n, 1);
  assert.equal(t.byClass.file.truePositives, 1);
  assert.equal(t.byClass.module.n, 1);
  assert.equal(t.byClass.module.truePositives, 1);
  assert.equal(t.overall.n, 2);
});

// ---------------------------------------------------------------------------
// 5. fail-soft
// ---------------------------------------------------------------------------
test('fail-soft: malformed findings.json is skipped + counted, not thrown', () => {
  const base = mkTmp();
  const akPath = path.join(base, 'ak.json');
  writeAnswerKey(akPath);

  const dir = path.join(base, 'rep-1', 'control', 'files');
  // one good review, one corrupt file
  writeFindings(dir, 1, [{ file: 'a.ts', line: 10, severity: 'HIGH', title: 'A' }]);
  writeRaw(dir, 2, 'findings.json', '{ this is not valid json ]');

  let s: ReturnType<typeof aggregate> | undefined;
  assert.doesNotThrow(() => {
    s = aggregate({ reps: [1], answerKeyPath: akPath, baseDir: base });
  });
  const o = s!.conditions.control.overall;
  assert.equal(o.n, 1); // only the good one scored
  assert.equal(o.skipped, 1); // the corrupt one counted
  assert.equal(o.truePositives, 1);
});

// ---------------------------------------------------------------------------
// 6. partial sweep / missing dirs don't crash
// ---------------------------------------------------------------------------
test('partial sweep: requesting a missing rep yields empty cells, no throw', () => {
  const base = mkTmp();
  const akPath = path.join(base, 'ak.json');
  writeAnswerKey(akPath);
  writeFindings(path.join(base, 'rep-1', 'control', 'files'), 1, [
    { file: 'a.ts', line: 10, severity: 'HIGH', title: 'A' },
  ]);

  // rep-2 + rep-3 don't exist on disk.
  let s: ReturnType<typeof aggregate> | undefined;
  assert.doesNotThrow(() => {
    s = aggregate({ reps: [1, 2, 3], answerKeyPath: akPath, baseDir: base });
  });
  assert.equal(s!.conditions.control.overall.n, 1);
  assert.equal(s!.conditions.treatment.overall.n, 0); // no treatment data at all
});
