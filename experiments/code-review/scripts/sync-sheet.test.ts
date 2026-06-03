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
  assert.equal(payload.values[0][2], 'H-001');
});

test('buildSyncPayload enforces knownHids (no orphan Results)', () => {
  assert.throws(() => buildSyncPayload(row, ['H-999']), /not found/);
  assert.doesNotThrow(() => buildSyncPayload(row, ['H-001']));
});

test('buildSyncPayload rejects an invalid row before emitting', () => {
  assert.throws(() => buildSyncPayload({ ...row, kgState: 'bad' as never }), /KG State/);
});
