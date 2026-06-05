import { test } from 'node:test';
import assert from 'node:assert/strict';
import * as fs from 'node:fs';
import * as os from 'node:os';
import * as path from 'node:path';
import { buildPrompt } from './build-prompt.ts';

test('buildPrompt inlines review.md, each path, and file contents', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'cr-bp-'));
  fs.mkdirSync(path.join(dir, 'src'), { recursive: true });
  fs.writeFileSync(path.join(dir, 'src/a.ts'), 'export const a = 1;\n');
  fs.writeFileSync(path.join(dir, 'src/b.ts'), 'export const b = 2;\n');
  const reviewMd = '# REVIEW INSTRUCTIONS MARKER';

  const out = buildPrompt(reviewMd, dir, ['src/a.ts', 'src/b.ts']);

  assert.ok(out.includes('REVIEW INSTRUCTIONS MARKER'), 'includes review.md');
  assert.ok(out.includes('src/a.ts') && out.includes('src/b.ts'), 'names both paths');
  assert.ok(out.includes('export const a = 1;'), 'inlines a.ts contents');
  assert.ok(out.includes('export const b = 2;'), 'inlines b.ts contents');
});

test('buildPrompt throws with the offending path when a file is missing', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'cr-bp-'));
  assert.throws(() => buildPrompt('x', dir, ['nope.ts']), /nope\.ts/);
});
