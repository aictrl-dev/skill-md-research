#!/usr/bin/env npx tsx
/**
 * Never-found analysis: across EVERY finding ever produced (all experiments, all
 * reps, all per-node + merged + direct-CLI result files), which real-bug oracle
 * entries were NEVER matched by any finding? That set is the floor of the approach.
 *
 * Aggregating all findings is contamination-robust for THIS question: extra/leaked
 * findings only make "ever found" more generous, so a real bug missed even here is
 * robustly unreachable by anything we tried.
 *
 * Match = same file + line ±5 (the scorer's relaxed rule). Real bug = TRUE with
 * impact real (untagged TRUE counts as real).
 *
 * Usage: never-found.ts
 */
import * as fs from 'node:fs';
import * as path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const EXP_DIR = path.resolve(HERE, '..');
const TOL = 5;
const ak: Record<string, any[]> = JSON.parse(fs.readFileSync(path.join(EXP_DIR, 'answer-key.json'), 'utf8'));
const isReal = (l: any) => l.verdict === 'TRUE' && (l.impact ?? 'real') === 'real';

function rng(l: any) { if (l == null || l === '') return null; const m = String(l).match(/^(\d+)(?:[-–](\d+))?$/); return m ? { s: +m[1], e: m[2] ? +m[2] : +m[1] } : null; }
function hit(a: any, b: any) { if (!a || !b) return false; return Math.abs(a.s - b.s) <= TOL || (a.s <= b.e + TOL && a.e + TOL >= b.s); }

// Collect ALL findings ever produced, keyed by PR → list of {file, line}
const byPR: Record<string, { file: string; line: any }[]> = {};
let fileCount = 0;
const resultsRoot = path.join(EXP_DIR, 'results');
function walk(dir: string) {
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) walk(p);
    else if (/\.findings\.json$/.test(e.name)) {
      fileCount++;
      try {
        const d = JSON.parse(fs.readFileSync(p, 'utf8'));
        const pr = String(d.prNumber ?? e.name.match(/PR-(\d+)/)?.[1]);
        (byPR[pr] ??= []);
        for (const f of d.findings ?? []) if (f.file) byPR[pr].push({ file: f.file, line: f.line });
      } catch {}
    }
  }
}
if (fs.existsSync(resultsRoot)) walk(resultsRoot);

// For each real-bug entry, was it ever matched?
let total = 0, found = 0;
const never: { pr: string; file: string; line: any; action: string; reason: string }[] = [];
for (const [pr, labels] of Object.entries(ak)) {
  for (const lbl of labels) {
    if (!isReal(lbl)) continue;
    total++;
    const lr = rng(lbl.line);
    const everHit = (byPR[pr] ?? []).some(f => f.file === lbl.file && hit(rng(f.line), lr));
    if (everHit) found++;
    else never.push({ pr, file: lbl.file, line: lbl.line, action: lbl.action ?? '-', reason: (lbl.reason ?? lbl.title ?? '').slice(0, 140) });
  }
}

console.log(`\n=== NEVER-FOUND ANALYSIS (across ${fileCount} findings files, all experiments) ===`);
console.log(`real-bug oracle entries: ${total}`);
console.log(`ever found by SOMETHING:  ${found} (${(100*found/total).toFixed(0)}%)`);
console.log(`NEVER found by anything:  ${never.length} (${(100*never.length/total).toFixed(0)}%)\n`);
console.log(`--- the never-found set ---`);
for (const n of never) console.log(`  PR-${n.pr}  ${n.file}:${n.line}  [${n.action}]\n      ${n.reason}`);
// group by file/PR for a quick shape
const byPr2: Record<string, number> = {};
for (const n of never) byPr2[n.pr] = (byPr2[n.pr] ?? 0) + 1;
console.log(`\n--- never-found by PR ---`);
for (const [pr, c] of Object.entries(byPr2).sort((a,b)=>b[1]-a[1])) console.log(`  PR-${pr}: ${c}`);
