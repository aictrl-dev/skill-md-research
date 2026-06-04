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
  toolContextConfig: 'KG:empty',
};

test('aggregate micro-averages per-PR scores into one row', () => {
  const { row } = aggregate(FIX_FINDINGS, FIX_AK, 'orig', meta);
  assert.equal(row.nPrs, 2);
  assert.equal(row.tp, 1);
  assert.equal(row.fp, 1);
  assert.equal(row.fn, 1);
  assert.equal(row.novels, 1);
  assert.equal(row.precision, 0.5);
  assert.equal(row.recall, 0.5);
  assert.equal(row.f1, 0.5);
  assert.equal(row.answerKeyVersion, 'orig');
  assert.equal(row.deltaF1, null);
  assert.equal(row.snr, 1);          // TP/FP = 1/1
  assert.equal(row.significance, ''); // no baseline → no verdict
});

test('aggregate computes deltaF1 + significance against a supplied baseline', () => {
  const { row } = aggregate(FIX_FINDINGS, FIX_AK, 'orig', { ...meta, baselineF1: 0.4 });
  assert.equal(row.deltaF1, 0.1);
  assert.equal(row.significance, 'inconclusive'); // 0.1 > noise floor, single seed
});

test('aggregate flags a within-noise delta as noise', () => {
  const { row } = aggregate(FIX_FINDINGS, FIX_AK, 'orig', { ...meta, baselineF1: 0.495 });
  assert.equal(row.deltaF1, 0.005);
  assert.equal(row.significance, 'noise');
});

test('aggregate emits per-defect-class breakdown rows (skips only-novel classes)', () => {
  const { breakdown } = aggregate(FIX_FINDINGS, FIX_AK, 'extended', meta);
  // null-safety (tp+fn) and security (fp) are scored; performance is novel-only → skipped.
  assert.equal(breakdown.length, 2);
  const ns = breakdown.find((b) => b.defectClass === 'null-safety');
  assert.ok(ns);
  assert.equal(ns.tp, 1);
  assert.equal(ns.fn, 1);
  assert.equal(ns.recall, 0.5);
  assert.equal(ns.f1, 0.667);
  const sec = breakdown.find((b) => b.defectClass === 'security');
  assert.ok(sec);
  assert.equal(sec.fp, 1);
  assert.equal(sec.precision, 0);
  assert.equal(breakdown.find((b) => b.defectClass === 'performance'), undefined);
  // breakdown carries the scoring dimension through
  assert.equal(ns.answerKeyVersion, 'extended');
});

test('aggregate throws on an empty findings directory', () => {
  assert.throws(() => aggregate(here, FIX_AK, 'orig', meta), /no PR-.*findings/i);
});
