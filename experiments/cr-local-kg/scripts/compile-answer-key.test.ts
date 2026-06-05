import { test } from 'node:test';
import assert from 'node:assert/strict';
import * as fs from 'node:fs';
import * as os from 'node:os';
import * as path from 'node:path';
import { compileAnswerKey } from './compile-answer-key.ts';

function tmpTriaged(files: Record<string, unknown[]>): string {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'cr-ak-'));
  for (const [id, arr] of Object.entries(files)) {
    fs.writeFileSync(path.join(dir, `${id}.json`), JSON.stringify(arr));
  }
  return dir;
}

test('groups triaged entries by task id into Record<id, entries>', () => {
  const entry = { bot: 'claude-oracle', severity: 'HIGH', file: 'a.ts', line: '1',
    description: 'd', verdict: 'TRUE', action: 'FIX', reason: 'r' };
  const dir = tmpTriaged({ '101': [entry], '202': [entry, entry] });
  const key = compileAnswerKey(dir);
  assert.equal(key['101'].length, 1);
  assert.equal(key['202'].length, 2);
});

test('throws with the offending id when verdict/action missing', () => {
  const bad = { bot: 'x', severity: 'HIGH', file: 'a.ts', line: '1', description: 'd' };
  const dir = tmpTriaged({ '101': [bad] });
  assert.throws(() => compileAnswerKey(dir), /101/);
});

test('coerces a numeric line to string', () => {
  const entry = { bot: 'claude-oracle', severity: 'LOW', file: 'a.ts', line: 42,
    description: 'd', verdict: 'FALSE', action: 'IGNORE', reason: 'r' };
  const dir = tmpTriaged({ '300': [entry] });
  const key = compileAnswerKey(dir);
  assert.equal(key['300'][0].line, '42');
});
