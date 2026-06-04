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
  assert.equal(row.deltaF1, null);
});

test('aggregate computes deltaF1 against a supplied baseline', () => {
  const row = aggregate(FIX_FINDINGS, FIX_AK, 'orig', { ...meta, baselineF1: 0.4 });
  assert.equal(row.deltaF1, 0.1);
});

test('aggregate throws on an empty findings directory', () => {
  assert.throws(() => aggregate(here, FIX_AK, 'orig', meta), /no PR-.*findings/i);
});
