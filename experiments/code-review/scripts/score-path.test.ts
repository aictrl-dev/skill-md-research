import { test } from 'node:test';
import assert from 'node:assert/strict';
import * as path from 'node:path';
import { fileURLToPath } from 'node:url';
import { score } from '../../cr-loop/scripts/score.ts';

const here = path.dirname(fileURLToPath(import.meta.url));
const FIX_AK = path.join(here, '__fixtures__', 'answer-key.json');

test('score() honours an explicit answerKeyPath argument', () => {
  const result = score(1, [{ file: 'a.ts', line: 10, severity: 'BUG' }], FIX_AK);
  assert.equal(result.totals.truePositives, 1);
  assert.equal(result.totals.falseNegatives, 1);
  assert.equal(result.totals.novelFindings, 0);
  assert.equal(result.precision, 1);
  assert.equal(result.recall, 0.5);
});
