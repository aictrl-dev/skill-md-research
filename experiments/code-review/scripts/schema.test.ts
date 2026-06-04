import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  EXPERIMENTS_COLUMNS,
  CLASS_BREAKDOWN_COLUMNS,
  validateExperimentRow,
  validateClassBreakdownRow,
  toExperimentCellArray,
  toClassBreakdownCellArray,
  type ExperimentRow,
  type ClassBreakdownRow,
} from './schema.ts';

const goodRow: ExperimentRow = {
  experiment: 'cr-loop',
  hId: 'H-001',
  variant: 'Phase E',
  skillVersion: 'code-review.SKILL.v3.md',
  model: 'zai-coding-plan/glm-5.1',
  toolContextConfig: 'KG:populated',
  answerKeyVersion: 'extended',
  nPrs: 10,
  tp: 30, fp: 1, fn: 73.5, novels: 14,
  precision: 0.968, recall: 0.29, f1: 0.446,
  deltaF1: 0.077, cost: '', logLink: 'log/004.md',
  snr: 30, latency: '', tokensPerPr: null, annotationCoverage: '', seed: '',
  significance: 'inconclusive',
};

const goodCb: ClassBreakdownRow = {
  experiment: 'csharp-review', hId: 'H-006', answerKeyVersion: 'extended',
  defectClass: 'null-safety', tp: 1, fp: 0, fn: 1,
  precision: 1, recall: 0.5, f1: 0.667, notes: '',
};

test('EXPERIMENTS_COLUMNS matches the committed Sheet header exactly', () => {
  assert.deepEqual(EXPERIMENTS_COLUMNS, [
    'E-ID', 'Experiment', 'H-ID', 'Variant / Phase', 'Skill Version', 'Model',
    'Tool/Context Config', 'AnswerKey Version', 'N PRs', 'TP', 'FP', 'FN', 'Novels',
    'Precision', 'Recall', 'F1', 'Δ F1 vs Baseline', 'Cost', 'Log Link',
    'SNR', 'Latency (p50/p95 ms)', 'Tokens/PR', 'Annotation Coverage', 'Seed',
    'Significance',
  ]);
});

test('CLASS_BREAKDOWN_COLUMNS matches the committed Sheet header exactly', () => {
  assert.deepEqual(CLASS_BREAKDOWN_COLUMNS, [
    'E-ID', 'Experiment', 'H-ID', 'AnswerKey Version', 'Defect Class',
    'TP', 'FP', 'FN', 'Precision', 'Recall', 'F1', 'Notes',
  ]);
});

test('validateExperimentRow accepts a well-formed row', () => {
  assert.doesNotThrow(() => validateExperimentRow(goodRow));
});

test('validateExperimentRow rejects an unknown AnswerKey Version', () => {
  assert.throws(() => validateExperimentRow({ ...goodRow, answerKeyVersion: 'v2' as never }), /AnswerKey Version/);
});

test('validateExperimentRow rejects a malformed H-ID', () => {
  assert.throws(() => validateExperimentRow({ ...goodRow, hId: 'HX1' }), /H-ID/);
});

test('validateExperimentRow rejects an unknown Annotation Coverage', () => {
  assert.throws(() => validateExperimentRow({ ...goodRow, annotationCoverage: 'lots' as never }), /Annotation Coverage/);
});

test('validateExperimentRow rejects an unknown Significance', () => {
  assert.throws(() => validateExperimentRow({ ...goodRow, significance: 'proven' as never }), /Significance/);
});

test('validateExperimentRow accepts null snr / tokensPerPr and blank coverage', () => {
  assert.doesNotThrow(() => validateExperimentRow({ ...goodRow, snr: null, tokensPerPr: null, annotationCoverage: '', significance: '' }));
});

test('validateExperimentRow enforces knownHids when provided (no orphan rows)', () => {
  assert.throws(() => validateExperimentRow(goodRow, { knownHids: ['H-002'] }), /not found/);
  assert.doesNotThrow(() => validateExperimentRow(goodRow, { knownHids: ['H-001'] }));
});

test('toExperimentCellArray returns 25 cells in column order with E-ID blank by default', () => {
  const cells = toExperimentCellArray(goodRow);
  assert.equal(cells.length, 25);
  assert.equal(cells[0], '');          // E-ID
  assert.equal(cells[1], 'cr-loop');   // Experiment
  assert.equal(cells[7], 'extended');  // AnswerKey Version
  assert.equal(cells[15], 0.446);      // F1
  assert.equal(cells[19], 30);         // SNR
});

test('toExperimentCellArray renders null deltaF1 / snr / tokensPerPr as blank', () => {
  const cells = toExperimentCellArray({ ...goodRow, deltaF1: null, snr: null, tokensPerPr: null });
  assert.equal(cells[16], ''); // Δ F1
  assert.equal(cells[19], ''); // SNR
  assert.equal(cells[21], ''); // Tokens/PR
});

test('validateClassBreakdownRow accepts a well-formed row', () => {
  assert.doesNotThrow(() => validateClassBreakdownRow(goodCb));
});

test('validateClassBreakdownRow rejects an unknown Defect Class', () => {
  assert.throws(() => validateClassBreakdownRow({ ...goodCb, defectClass: 'typos' as never }), /Defect Class/);
});

test('toClassBreakdownCellArray returns 12 cells in column order', () => {
  const cells = toClassBreakdownCellArray(goodCb);
  assert.equal(cells.length, 12);
  assert.equal(cells[0], '');             // E-ID
  assert.equal(cells[4], 'null-safety');  // Defect Class
  assert.equal(cells[10], 0.667);         // F1
});
