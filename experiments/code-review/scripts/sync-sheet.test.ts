import { test } from 'node:test';
import assert from 'node:assert/strict';
import { buildSyncPayload, buildClassBreakdownPayload } from './sync-sheet.ts';
import type { ExperimentRow, ClassBreakdownRow } from './schema.ts';

const row: ExperimentRow = {
  experiment: 'cr-loop', hId: 'H-001', variant: 'Phase E',
  skillVersion: 'v3.md', model: 'glm-5.1', toolContextConfig: 'KG:populated',
  answerKeyVersion: 'extended', nPrs: 10, tp: 30, fp: 1, fn: 73.5, novels: 14,
  precision: 0.968, recall: 0.29, f1: 0.446, deltaF1: 0.077, cost: '', logLink: '',
  snr: 30, latency: '', tokensPerPr: null, annotationCoverage: '', seed: '',
  significance: 'inconclusive',
};

const cb: ClassBreakdownRow = {
  experiment: 'csharp-review', hId: 'H-006', answerKeyVersion: 'extended',
  defectClass: 'memory-lifecycle', tp: 0, fp: 0, fn: 4,
  precision: 0, recall: 0, f1: 0, notes: '',
};

test('buildSyncPayload returns an Experiments-targeted single-row payload', () => {
  const payload = buildSyncPayload(row);
  assert.equal(payload.sheet, 'Experiments');
  assert.equal(payload.values.length, 1);
  assert.equal(payload.values[0].length, 25);
  assert.equal(payload.values[0][2], 'H-001');
});

test('buildSyncPayload enforces knownHids (no orphan rows)', () => {
  assert.throws(() => buildSyncPayload(row, ['H-999']), /not found/);
  assert.doesNotThrow(() => buildSyncPayload(row, ['H-001']));
});

test('buildSyncPayload rejects an invalid row before emitting', () => {
  assert.throws(() => buildSyncPayload({ ...row, significance: 'bad' as never }), /Significance/);
});

test('buildClassBreakdownPayload returns a ClassBreakdown payload', () => {
  const payload = buildClassBreakdownPayload([cb]);
  assert.equal(payload.sheet, 'ClassBreakdown');
  assert.equal(payload.values.length, 1);
  assert.equal(payload.values[0].length, 12);
  assert.equal(payload.values[0][4], 'memory-lifecycle');
});

test('buildClassBreakdownPayload validates rows + enforces knownHids', () => {
  assert.throws(() => buildClassBreakdownPayload([{ ...cb, defectClass: 'nope' as never }]), /Defect Class/);
  assert.throws(() => buildClassBreakdownPayload([cb], ['H-001']), /not found/);
  assert.doesNotThrow(() => buildClassBreakdownPayload([cb], ['H-006']));
});
