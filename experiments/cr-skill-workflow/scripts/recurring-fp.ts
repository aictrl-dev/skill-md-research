#!/usr/bin/env npx tsx
/**
 * Recurring false-positive analysis. Across every individual model pass (per-node
 * findings files), cluster findings by file + line (±5), count how many passes
 * produce each cluster, and classify each against the oracle:
 *   realTP / theoretical / FALSE(trap) / novel(no oracle entry).
 * The high-frequency FALSE + novel clusters are the recurring FPs — the precision
 * drain. If a few clusters dominate FP volume, they're worth a code-fix or a
 * deterministic known-FP suppression list.
 *
 * (Cross-experiment leakage inflates counts ~uniformly; "what recurs" is robust.)
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

// classify a (file,line) against the oracle
function classify(pr: string, file: string, line: any): { cls: string; reason: string } {
  const lr = rng(line);
  for (const lbl of (ak[pr] ?? [])) {
    if (lbl.file !== file) continue;
    if (hit(rng(lbl.line), lr)) {
      const cls = lbl.verdict === 'FALSE' ? 'FALSE' : lbl.verdict === 'UNCERTAIN' ? 'UNCERTAIN' : isReal(lbl) ? 'realTP' : 'theoretical';
      return { cls, reason: (lbl.reason ?? lbl.title ?? '').replace(/\s+/g, ' ').slice(0, 90) };
    }
  }
  return { cls: 'novel', reason: '' };
}

// cluster across per-node passes: key = pr|file|line-bucket(rounded to nearest TOL)
const clusters: Record<string, { pr: string; file: string; line: any; passes: number; titles: Set<string> }> = {};
function walk(d: string) {
  for (const e of fs.readdirSync(d, { withFileTypes: true })) {
    const p = path.join(d, e.name);
    if (e.isDirectory()) walk(p);
    else { const m = e.name.match(/^PR-(\d+)\.[a-zA-Z0-9_]+\.findings\.json$/); if (!m) continue;
      try {
        const seen = new Set<string>();
        for (const f of (JSON.parse(fs.readFileSync(p, 'utf8')).findings ?? [])) {
          if (!f.file) continue;
          const ln = rng(f.line); const bucket = ln ? Math.round(ln.s / TOL) * TOL : 'na';
          const key = `${m[1]}|${f.file}|${bucket}`;
          if (seen.has(key)) continue; seen.add(key); // count once per pass
          (clusters[key] ??= { pr: m[1], file: f.file, line: f.line, passes: 0, titles: new Set() });
          clusters[key].passes++; if (f.title) clusters[key].titles.add(String(f.title).slice(0, 50));
        }
      } catch {}
    }
  }
}
const root = path.join(EXP_DIR, 'results'); if (fs.existsSync(root)) walk(root);

const all = Object.values(clusters).map(c => ({ ...c, ...classify(c.pr, c.file, c.line) }));
const fp = all.filter(c => c.cls === 'FALSE' || c.cls === 'novel');
const totalFpVol = fp.reduce((s, c) => s + c.passes, 0);
const sorted = fp.sort((a, b) => b.passes - a.passes);
const r0 = (n: number) => (Math.round(n * 10) / 10);

console.log(`\n=== RECURRING FALSE-POSITIVE ANALYSIS ===`);
console.log(`distinct FP clusters (FALSE-trap or novel): ${fp.length}`);
console.log(`total FP volume (pass-hits on FP clusters): ${totalFpVol}`);
const top = sorted.slice(0, 20);
console.log(`top-20 clusters = ${r0(100 * top.reduce((s,c)=>s+c.passes,0) / totalFpVol)}% of all FP volume\n`);
console.log(`--- top 20 recurring FPs (passes | class | PR file:line) ---`);
for (const c of top) console.log(`  ${String(c.passes).padStart(4)}  ${c.cls.padEnd(6)}  PR-${c.pr} ${c.file.split('/').pop()}:${c.line}\n        ${c.cls === 'FALSE' ? c.reason : '[' + [...c.titles].slice(0,2).join(' | ') + ']'}`);
// FALSE vs novel split of FP volume
const falseVol = fp.filter(c=>c.cls==='FALSE').reduce((s,c)=>s+c.passes,0);
console.log(`\nFP volume split: FALSE-trap (known oracle FPs)=${falseVol} (${r0(100*falseVol/totalFpVol)}%) | novel (unlabeled)=${totalFpVol-falseVol} (${r0(100*(totalFpVol-falseVol)/totalFpVol)}%)`);
