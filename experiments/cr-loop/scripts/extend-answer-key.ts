#!/usr/bin/env npx tsx
/**
 * Take novels-to-triage.json + my classifier verdicts and write
 * answer-key-extended.json that includes the original AK plus the
 * new TRUE entries from triage.
 *
 * Verdicts are encoded inline below — based on manual file verification.
 * Anything classified FALSE is dropped (we don't score the agent down
 * for novels we manually rejected).
 *
 * Usage: npx tsx experiments/cr-loop/scripts/extend-answer-key.ts
 */
import * as fs from 'node:fs';
import * as path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT = path.resolve(__dirname, '..');

interface Novel {
  id: string;
  prNumber: number;
  file: string;
  line: string | null;
  severity: string;
  title: string;
  description: string;
  foundIn: string[];
}

interface AKEntry {
  bot: string;
  severity: string;
  file: string;
  line: string;
  description: string;
  verdict: 'TRUE' | 'FALSE' | 'UNCERTAIN';
  action: 'FIX' | 'DEFER' | 'IGNORE';
  reason: string;
}

// Manual classification: by id substring, mark as FALSE/dropped.
// Default for everything not listed: TRUE/DEFER (most novels are real
// stylistic/refactor findings the prod skill caught).
//
// FIX-priority TRUE findings (real bugs, not stylistic):
const FIX_PATTERNS = [
  // PR 1788
  '36h ',                                           // formatDuration multi-day truncation
  'whitespace-only',                                // skills.ts trim bug (PR 1782)
  'enum values mismatch',                           // hasFindingsMin enum (PR 1790)
  'silently dead-lettered',                         // publish bypass (PR 1790)
  'breaking wire-format',                           // attribute rename (PR 1790)
  'null for REQUIRED',                              // pr.id null (PR 1790)
];

// FALSE patterns (verified against current code, claims don't hold):
const FALSE_PATTERNS = [
  '1803:server/services/code-review-publisher.ts:the payload field skill version', // skill_version mapping (skill_id is what's actually written)
  '1803:server/services/code-review-publisher.ts:model default model',              // DEFAULT_MODEL doesn't exist in file
  'silently exclude migrated docs',                 // 1785 redundant orgId is intentional defense-in-depth (line comments)
];

function isFalse(novel: Novel): boolean {
  return FALSE_PATTERNS.some((p) => novel.id.includes(p) || novel.description.includes(p));
}

function isFix(novel: Novel): boolean {
  return FIX_PATTERNS.some((p) => novel.description.toLowerCase().includes(p.toLowerCase()));
}

const novels = JSON.parse(
  fs.readFileSync(path.join(ROOT, 'novels-to-triage.json'), 'utf8'),
) as Novel[];

const ak = JSON.parse(
  fs.readFileSync(path.join(ROOT, 'answer-key.json'), 'utf8'),
) as Record<string, AKEntry[]>;

// Deep-copy AK
const extended: Record<string, AKEntry[]> = {};
for (const [k, v] of Object.entries(ak)) extended[k] = [...v];

let added = 0;
let droppedFalse = 0;
let firedFix = 0;

for (const n of novels) {
  if (isFalse(n)) {
    droppedFalse++;
    continue;
  }
  const action = isFix(n) ? 'FIX' : 'DEFER';
  if (action === 'FIX') firedFix++;
  const entry: AKEntry = {
    bot: 'manual-triage',
    severity: n.severity.toUpperCase() === 'HIGH' ? 'BUG' :
              n.severity.toUpperCase() === 'CRITICAL' ? 'BUG' :
              n.severity.toUpperCase() === 'MEDIUM' ? 'CONSISTENCY' :
              n.severity.toUpperCase() === 'LOW' ? 'CONSISTENCY' :
              'CONSISTENCY',
    file: n.file,
    line: n.line ?? '',
    description: n.title || n.description.slice(0, 200),
    verdict: 'TRUE',
    action,
    reason: `manual triage from cr-loop novels (foundIn=${n.foundIn.join(',')})`,
  };
  const key = String(n.prNumber);
  if (!extended[key]) extended[key] = [];
  extended[key].push(entry);
  added++;
}

const outPath = path.join(ROOT, 'answer-key-extended.json');
fs.writeFileSync(outPath, JSON.stringify(extended, null, 2));

console.log(`Wrote ${outPath}`);
console.log(`  Original AK entries: ${Object.values(ak).reduce((s, v) => s + v.length, 0)}`);
console.log(`  Novels added (TRUE): ${added}`);
console.log(`    of which FIX action: ${firedFix}`);
console.log(`  Novels dropped (FALSE): ${droppedFalse}`);
console.log(`  New AK total: ${Object.values(extended).reduce((s, v) => s + v.length, 0)}`);

// Per-PR breakdown
console.log('\nPer-PR AK size before/after:');
for (const pr of Object.keys(ak).sort()) {
  const before = ak[pr].length;
  const after = extended[pr].length;
  const delta = after - before;
  if (delta > 0) console.log(`  PR #${pr}: ${before} → ${after} (+${delta})`);
}
