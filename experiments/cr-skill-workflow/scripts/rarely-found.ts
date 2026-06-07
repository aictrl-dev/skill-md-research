#!/usr/bin/env npx tsx
/**
 * Rarely-found analysis. Since no real bug is NEVER found, the real ceiling is
 * FREQUENCY: for each real bug, what fraction of individual review passes (per-node
 * findings files = one model call each) surfaced it? The low-hit-rate tail is what
 * caps single-run recall and dictates how much resampling you need.
 *
 * Restricted to per-node files (PR-<id>.<node>.findings.json) so each counted unit
 * is one model pass. Cross-experiment leakage inflates numerator and denominator
 * together, so hit-RATE stays roughly interpretable (treat as approximate).
 */
import * as fs from 'node:fs';
import * as path from 'node:path';
import { fileURLToPath } from 'node:url';
const HERE = path.dirname(fileURLToPath(import.meta.url));
const EXP_DIR = path.resolve(HERE, '..');
const TOL = 5;
const ak: Record<string, any[]> = JSON.parse(fs.readFileSync(path.join(EXP_DIR, 'answer-key.json'), 'utf8'));
const isReal = (l: any) => l.verdict === 'TRUE' && (l.impact ?? 'real') === 'real';
const rng = (l: any) => { if (l == null || l === '') return null; const m = String(l).match(/^(\d+)(?:[-–](\d+))?$/); return m ? { s: +m[1], e: m[2] ? +m[2] : +m[1] } : null; };
const hit = (a: any, b: any) => !a || !b ? false : (Math.abs(a.s - b.s) <= TOL || (a.s <= b.e + TOL && a.e + TOL >= b.s));

// per-node pass files only: PR-<id>.<node>.findings.json (node segment present)
const passesByPR: Record<string, { file: string; line: any }[][]> = {};
function walk(d: string) {
  for (const e of fs.readdirSync(d, { withFileTypes: true })) {
    const p = path.join(d, e.name);
    if (e.isDirectory()) walk(p);
    else { const m = e.name.match(/^PR-(\d+)\.[a-zA-Z0-9_]+\.findings\.json$/); if (!m) continue;
      try { const fnd = (JSON.parse(fs.readFileSync(p, 'utf8')).findings ?? []).map((f: any) => ({ file: f.file, line: f.line }));
        (passesByPR[m[1]] ??= []).push(fnd); } catch {} }
  }
}
// --exp <id> restricts the analysis to one experiment's passes (e.g. measure a new
// lens's hit-rate); default walks ALL results.
const expArg = (() => { const i = process.argv.indexOf('--exp'); return i !== -1 ? process.argv[i + 1] : ''; })();
const root = expArg ? path.join(EXP_DIR, 'results', expArg) : path.join(EXP_DIR, 'results');
if (fs.existsSync(root)) walk(root);
if (expArg) console.log(`(scoped to experiment: ${expArg})`);

const rows: { pr: string; file: string; line: any; hits: number; passes: number; rate: number; reason: string }[] = [];
for (const [pr, labels] of Object.entries(ak)) {
  const passes = passesByPR[pr] ?? [];
  for (const lbl of labels) {
    if (!isReal(lbl)) continue;
    const lr = rng(lbl.line);
    const hits = passes.filter(pf => pf.some(f => f.file === lbl.file && hit(rng(f.line), lr))).length;
    rows.push({ pr, file: lbl.file.split('/').pop()!, line: lbl.line, hits, passes: passes.length, rate: passes.length ? hits / passes.length : 0, reason: (lbl.reason ?? lbl.title ?? '').slice(0, 90) });
  }
}
rows.sort((a, b) => a.rate - b.rate);
const r3 = (n: number) => (Math.round(n * 1000) / 10).toFixed(1);
console.log(`\n=== RARELY-FOUND (hit-rate across individual model passes) ===`);
const buckets = [[0, 0.02], [0.02, 0.05], [0.05, 0.10], [0.10, 0.25], [0.25, 1.01]];
const names = ['<2% (very fragile)', '2-5%', '5-10%', '10-25%', '>25% (easy)'];
buckets.forEach((b, i) => console.log(`  ${names[i].padEnd(20)}: ${rows.filter(r => r.rate >= b[0] && r.rate < b[1]).length} bugs`));
console.log(`\n--- hardest 12 real bugs (lowest hit-rate) ---`);
for (const r of rows.slice(0, 12)) console.log(`  ${r3(r.rate)}%  (${r.hits}/${r.passes})  PR-${r.pr} ${r.file}:${r.line}\n      ${r.reason}`);
