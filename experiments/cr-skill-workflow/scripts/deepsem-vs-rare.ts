#!/usr/bin/env npx tsx
/**
 * Does the new deep-semantic prompt find the bugs that are RARE in our stats?
 * For each real bug, compute hit-rate among GENERIC passes (all per-node files
 * EXCEPT exp-032) vs the DEEP-SEMANTIC passes (exp-032 only). Focus on the rare
 * tail (generic hit-rate < 5%) and show whether the new prompt lifts them.
 */
import * as fs from 'node:fs';
import * as path from 'node:path';
import { fileURLToPath } from 'node:url';
const HERE = path.dirname(fileURLToPath(import.meta.url));
const EXP_DIR = path.resolve(HERE, '..');
const TOL = 5;
const ak: Record<string, any[]> = JSON.parse(fs.readFileSync(path.join(EXP_DIR, 'answer-key.json'), 'utf8'));
const isReal = (l: any) => l.verdict === 'TRUE' && (l.impact ?? 'real') === 'real';
const rng = (s: any) => { if (s == null || s === '') return null; const m = String(s).match(/^(\d+)(?:[-–](\d+))?$/); return m ? { s: +m[1], e: m[2] ? +m[2] : +m[1] } : null; };
const hit = (a: any, b: any) => !a || !b ? false : (Math.abs(a.s - b.s) <= TOL || (a.s <= b.e + TOL && a.e + TOL >= b.s));

// per-PR pass lists, split by deep-semantic vs generic
const gen: Record<string, { file: string; line: any }[][]> = {};
const deep: Record<string, { file: string; line: any }[][]> = {};
function walk(d: string, isDeep: boolean) {
  for (const e of fs.readdirSync(d, { withFileTypes: true })) {
    const p = path.join(d, e.name);
    if (e.isDirectory()) walk(p, isDeep || e.name === 'exp-032-deepsemantic');
    else { const m = e.name.match(/^PR-(\d+)\.[a-zA-Z0-9_]+\.findings\.json$/); if (!m) continue;
      try { const fnd = (JSON.parse(fs.readFileSync(p, 'utf8')).findings ?? []).map((f: any) => ({ file: f.file, line: f.line }));
        (isDeep ? deep : gen)[m[1]] ??= []; (isDeep ? deep : gen)[m[1]].push(fnd); } catch {} }
  }
}
const root = path.join(EXP_DIR, 'results'); if (fs.existsSync(root)) walk(root, false);

const rate = (passes: { file: string; line: any }[][], file: string, lr: any) =>
  !passes?.length ? null : passes.filter(pf => pf.some(f => f.file === file && hit(rng(f.line), lr))).length / passes.length;

const rows: any[] = [];
for (const [pr, labels] of Object.entries(ak)) for (const l of labels) {
  if (!isReal(l)) continue;
  const lr = rng(l.line);
  rows.push({ pr, f: l.file.split('/').pop(), line: l.line, g: rate(gen[pr], l.file, lr), d: rate(deep[pr], l.file, lr), reason: (l.reason || l.title || '').replace(/\s+/g, ' ').slice(0, 70) });
}
const pct = (x: any) => x == null ? ' n/a ' : (Math.round(x * 1000) / 10).toFixed(1) + '%';
const RARE = 0.05;
const rare = rows.filter(r => (r.g ?? 0) < RARE).sort((a, b) => (b.d ?? 0) - (a.d ?? 0));
console.log(`\n=== Deep-semantic prompt vs the RARE tail (generic hit-rate < ${RARE*100}%) ===`);
console.log(`generic passes/PR ≈ ${Math.round(Object.values(gen).reduce((s,a)=>s+a.length,0)/Math.max(1,Object.keys(gen).length))}, deep-semantic passes/PR = ${Math.round(Object.values(deep).reduce((s,a)=>s+a.length,0)/Math.max(1,Object.keys(deep).length||1))}`);
console.log(`\n  generic | deepsem | PR file:line`);
let lifted = 0, caught = 0;
for (const r of rare) {
  if ((r.d ?? 0) > 0) caught++;
  if ((r.d ?? 0) > (r.g ?? 0)) lifted++;
  console.log(`  ${pct(r.g).padStart(6)} | ${pct(r.d).padStart(6)}  | PR-${r.pr} ${r.f}:${r.line}  ${(r.d ?? 0) > (r.g ?? 0) ? '↑' : ''}`);
}
console.log(`\n  rare bugs: ${rare.length} | deep-semantic catches (>0%): ${caught} | deep-semantic hit-rate > generic: ${lifted}`);
const meanG = rare.reduce((s,r)=>s+(r.g??0),0)/rare.length, meanD = rare.reduce((s,r)=>s+(r.d??0),0)/rare.length;
console.log(`  mean hit-rate on rare tail — generic ${pct(meanG)} vs deep-semantic ${pct(meanD)}`);
