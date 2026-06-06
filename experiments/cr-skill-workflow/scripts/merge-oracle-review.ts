#!/usr/bin/env npx tsx
/**
 * Merge the per-PR oracle review (review/PR-*.classified.json) into answer-key.json:
 *  - existingTrue: set impact = real|theoretical on the matching TRUE entry.
 *  - novels: real → TRUE/FIX/real, theoretical → TRUE/IGNORE/theoretical,
 *            not-a-bug → FALSE/IGNORE (so future hallucinations cost precision).
 *
 * Writes through the symlink to the canonical shared oracle. Idempotent-ish:
 * novels are tagged with bot 'panel-review-2026-06-06'; re-running would dup them,
 * so run once. Prints a full before/after summary.
 *
 * Usage: merge-oracle-review.ts --exp <exp-id> [--dry-run]
 */
import * as fs from 'node:fs';
import * as path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const EXP_DIR = path.resolve(HERE, '..');
const argv = process.argv.slice(2);
const get = (f: string, d: string) => { const i = argv.indexOf(f); return i !== -1 ? argv[i + 1] : d; };
const expId = get('--exp', '');
const dryRun = argv.includes('--dry-run');
if (!expId) { console.error('Usage: merge-oracle-review.ts --exp <exp-id> [--dry-run]'); process.exit(1); }

const AK_LINK = path.join(EXP_DIR, 'answer-key.json');
const AK_REAL = fs.realpathSync(AK_LINK); // write through the symlink to the canonical file
const reviewDir = path.join(EXP_DIR, 'results', expId, 'review');
const novels = JSON.parse(fs.readFileSync(path.join(EXP_DIR, 'results', expId, 'novels.json'), 'utf8'));

const ak: Record<string, any[]> = JSON.parse(fs.readFileSync(AK_REAL, 'utf8'));

const before = {
  true: Object.values(ak).flat().filter((e: any) => e.verdict === 'TRUE').length,
  false: Object.values(ak).flat().filter((e: any) => e.verdict === 'FALSE').length,
};

let tagged = 0, tagMiss = 0, addedReal = 0, addedTheo = 0, addedFalse = 0, novelMiss = 0;

for (const f of fs.readdirSync(reviewDir).filter(x => x.endsWith('.classified.json'))) {
  const c = JSON.parse(fs.readFileSync(path.join(reviewDir, f), 'utf8'));
  const pr = String(c.pr);
  ak[pr] ??= [];

  // 1) tag existing TRUE entries by line
  const usedTrue = new Set<number>();
  for (const et of (c.existingTrue ?? [])) {
    const idx = ak[pr].findIndex((e: any, i: number) =>
      !usedTrue.has(i) && e.verdict === 'TRUE' && String(e.line) === String(et.line));
    if (idx === -1) { tagMiss++; continue; }
    usedTrue.add(idx);
    ak[pr][idx].impact = et.impact === 'real' ? 'real' : 'theoretical';
    ak[pr][idx].impactReason = et.reason ?? '';
    tagged++;
  }

  // 2) add novels (look up full data in novels.json by line)
  const prNovels: any[] = novels.novelsByPR?.[pr] ?? [];
  for (const nv of (c.novels ?? [])) {
    const src = prNovels.find((x: any) => String(x.line) === String(nv.line));
    if (!src) { novelMiss++; continue; }
    const base = {
      bot: 'panel-review-2026-06-06',
      severity: src.severity ?? 'MEDIUM',
      file: src.file,
      line: String(src.line),
      description: src.description ?? src.title ?? '',
      reason: nv.reason ?? '',
    };
    if (nv.verdict === 'real') {
      ak[pr].push({ ...base, verdict: 'TRUE', action: 'FIX', impact: 'real' }); addedReal++;
    } else if (nv.verdict === 'theoretical') {
      ak[pr].push({ ...base, verdict: 'TRUE', action: 'IGNORE', impact: 'theoretical' }); addedTheo++;
    } else {
      ak[pr].push({ ...base, verdict: 'FALSE', action: 'IGNORE' }); addedFalse++;
    }
  }
}

// sort each PR: TRUE first, then by line
for (const pr of Object.keys(ak)) {
  ak[pr].sort((a: any, b: any) => {
    if (a.verdict !== b.verdict) return a.verdict === 'TRUE' ? -1 : a.verdict === 'FALSE' && b.verdict === 'UNCERTAIN' ? -1 : 1;
    return parseInt(a.line) - parseInt(b.line);
  });
}

const after = {
  true: Object.values(ak).flat().filter((e: any) => e.verdict === 'TRUE').length,
  false: Object.values(ak).flat().filter((e: any) => e.verdict === 'FALSE').length,
  real: Object.values(ak).flat().filter((e: any) => e.verdict === 'TRUE' && e.impact === 'real').length,
  theo: Object.values(ak).flat().filter((e: any) => e.verdict === 'TRUE' && e.impact === 'theoretical').length,
  untagged: Object.values(ak).flat().filter((e: any) => e.verdict === 'TRUE' && !e.impact).length,
};

console.log('=== oracle review merge ===');
console.log(`tagged existing TRUE: ${tagged} (miss: ${tagMiss})`);
console.log(`added novels: ${addedReal} real, ${addedTheo} theoretical, ${addedFalse} false (novel match miss: ${novelMiss})`);
console.log(`TRUE: ${before.true} → ${after.true}  | FALSE: ${before.false} → ${after.false}`);
console.log(`TRUE by impact: real=${after.real} theoretical=${after.theo} untagged=${after.untagged}`);

if (dryRun) { console.log('\n(dry run — not written)'); process.exit(0); }
fs.writeFileSync(AK_REAL, JSON.stringify(ak, null, 2));
console.log(`\nwrote ${AK_REAL}`);
