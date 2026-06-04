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
  assert.equal(cells[0], '');
  assert.equal(cells[1], 'cr-loop');
  assert.equal(cells[7], 'extended');
  assert.equal(cells[15], 0.446);
});

test('toCellArray renders null deltaF1 as blank', () => {
  const cells = toCellArray({ ...goodRow, deltaF1: null });
  assert.equal(cells[16], '');
});
