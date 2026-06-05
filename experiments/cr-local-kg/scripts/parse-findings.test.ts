import { test } from 'node:test';
import assert from 'node:assert/strict';
import { extractFindings } from './parse-findings.ts';

test('extracts a fenced json array from prose', () => {
  const txt = 'Here are my findings:\n```json\n[{"file":"a.ts","line":3,"severity":"HIGH","title":"t","description":"d"}]\n```\nDone.';
  const f = extractFindings(txt);
  assert.equal(f.length, 1);
  assert.equal(f[0].file, 'a.ts');
  assert.equal(f[0].severity, 'HIGH');
});

test('picks the LAST json array when several are present', () => {
  const txt = '```json\n[]\n```\nactually:\n```json\n[{"file":"b.ts","line":1,"severity":"LOW","title":"x","description":"y"}]\n```';
  const f = extractFindings(txt);
  assert.equal(f.length, 1);
  assert.equal(f[0].file, 'b.ts');
});

test('returns [] when there is no parseable array', () => {
  assert.deepEqual(extractFindings('no findings, looks good'), []);
});

test('drops entries missing file or severity (tolerant)', () => {
  const txt = '```json\n[{"line":1},{"file":"c.ts","severity":"MEDIUM","title":"t","description":"d"}]\n```';
  const f = extractFindings(txt);
  assert.equal(f.length, 1);
  assert.equal(f[0].file, 'c.ts');
});
