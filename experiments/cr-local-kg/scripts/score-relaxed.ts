#!/usr/bin/env npx tsx
/**
 * Relaxed identity, strict precision: file + line±5 match only, NO severity
 * requirement; unmatched/novel findings count as FP and are also reported.
 * Scores both gemma4 (results/raw) and GLM-4.7 (results/raw-glm47).
 * Prints per-condition per-scope breakdown.
 */
import * as fs from 'node:fs';
import * as path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const EXP = path.resolve(HERE, '..');
const AK_PATH = path.join(EXP, 'answer-key.json');
const LINE_TOL = 5;

const ak: Record<string, AKEntry[]> = JSON.parse(fs.readFileSync(AK_PATH, 'utf8'));

interface AKEntry { verdict: string; action: string; file: string; line: string; }
interface Finding { file: string; line?: number | string; severity?: string; }

function parseLine(l: string | number | undefined) {
  if (l === undefined || l === null || l === '') return null;
  const m = String(l).match(/^(\d+)(?:[-–](\d+))?$/);
  if (!m) return null;
  return { start: parseInt(m[1]), end: m[2] ? parseInt(m[2]) : parseInt(m[1]) };
}

function overlap(a: ReturnType<typeof parseLine>, b: ReturnType<typeof parseLine>) {
  if (!a || !b) return false;
  return Math.abs(a.start - b.start) <= LINE_TOL ||
    (a.start <= b.end + LINE_TOL && a.end + LINE_TOL >= b.start);
}

interface Agg { tp: number; fp: number; fn: number; novels: number; n: number; }
const blank = (): Agg => ({ tp: 0, fp: 0, fn: 0, novels: 0, n: 0 });
function prf(g: Agg) {
  const p = g.tp + g.fp === 0 ? 0 : g.tp / (g.tp + g.fp);
  const r = g.tp + g.fn === 0 ? 0 : g.tp / (g.tp + g.fn);
  const f1 = p + r === 0 ? 0 : (2 * p * r) / (p + r);
  const f2 = 4 * p + r === 0 ? 0 : (5 * p * r) / (4 * p + r);
  return { p, r, f1, f2 };
}
const r3 = (n: number) => (Math.round(n * 1000) / 1000).toFixed(3);

function scoreFile(fullPath: string, into: Agg): void {
  const data = JSON.parse(fs.readFileSync(fullPath, 'utf8')) as { prNumber?: number; findings?: Finding[] };
  const pr = String(data.prNumber ?? fullPath.match(/PR-(\d+)/)?.[1]);
  const findings: Finding[] = data.findings ?? [];
  const labels = ak[pr] ?? [];

  const usedAK = new Set<number>();
  const usedSkill = new Set<number>();

  findings.forEach((sf, i) => {
    const sfLine = parseLine(sf.line);
    const idx = labels.findIndex((lbl, j) => {
      if (usedAK.has(j)) return false;
      if (sf.file !== lbl.file) return false;
      return overlap(sfLine, parseLine(lbl.line));
    });
    if (idx === -1) return;
    usedAK.add(idx);
    usedSkill.add(i);
  });

  let tp = 0, fp = 0;
  for (const idx of usedAK) {
    const lbl = labels[idx];
    if (lbl.verdict === 'TRUE') tp += 1;
    else if (lbl.verdict === 'FALSE') fp += 1;
    else if (lbl.verdict === 'UNCERTAIN') tp += 0.5;
  }

  let fn = 0;
  for (let j = 0; j < labels.length; j++) {
    if (usedAK.has(j)) continue;
    const lbl = labels[j];
    if (lbl.verdict !== 'TRUE') continue;
    fn += lbl.action === 'FIX' ? 1 : 0.5;
  }

  const novels = findings.filter((_, i) => !usedSkill.has(i)).length;
  fp += novels;

  into.tp += tp; into.fp += fp; into.fn += fn; into.novels += novels; into.n += 1;
}

function scoreDir(dir: string, into: Agg): void {
  if (!fs.existsSync(dir)) return;
  for (const f of fs.readdirSync(dir)) {
    if (/^PR-\d+\.findings\.json$/.test(f))
      scoreFile(path.join(dir, f), into);
  }
}

const REPS = ['1', '2', '3'];
const CONDS = ['control', 'treatment'] as const;

for (const [label, rawDir] of [['gemma4', 'raw'], ['GLM-4.7', 'raw-glm47']] as const) {
  console.log(`\n=== ${label} ===`);
  for (const cond of CONDS) {
    const overall = blank();
    const byClass: Record<string, Agg> = { file: blank(), module: blank() };
    for (const rep of REPS) {
      for (const [cls, sub] of [['file', 'files'], ['module', 'modules']] as const) {
        const dir = path.join(EXP, `results/${rawDir}`, `rep-${rep}`, cond, sub);
        scoreDir(dir, overall);
        scoreDir(dir, byClass[cls]);
      }
    }
    const o = prf(overall);
    console.log(`  ${cond}: P=${r3(o.p)} R=${r3(o.r)} F1=${r3(o.f1)} F2=${r3(o.f2)} | TP=${overall.tp} FP=${overall.fp} FN=${overall.fn} novels=${overall.novels} n=${overall.n}`);
    for (const cls of ['file', 'module']) {
      const c = prf(byClass[cls]);
      console.log(`    ${cls}: F1=${r3(c.f1)} F2=${r3(c.f2)} (P=${r3(c.p)} R=${r3(c.r)} n=${byClass[cls].n})`);
    }
  }
  // Delta
  const ctrl = blank(), trt = blank();
  for (const rep of REPS) {
    for (const [, sub] of [['file', 'files'], ['module', 'modules']] as const) {
      scoreDir(path.join(EXP, `results/${rawDir}`, `rep-${rep}`, 'control', sub), ctrl);
      scoreDir(path.join(EXP, `results/${rawDir}`, `rep-${rep}`, 'treatment', sub), trt);
    }
  }
  // Delta per scope
  console.log(`  ΔF1 overall: ${(prf(trt).f1 - prf(ctrl).f1).toFixed(3)}`);
  console.log(`  ΔF2 overall: ${(prf(trt).f2 - prf(ctrl).f2).toFixed(3)}`);
  const ctrlF = blank(), trtF = blank(), ctrlM = blank(), trtM = blank();
  for (const rep of REPS) {
    scoreDir(path.join(EXP, `results/${rawDir}`, `rep-${rep}`, 'control', 'files'), ctrlF);
    scoreDir(path.join(EXP, `results/${rawDir}`, `rep-${rep}`, 'treatment', 'files'), trtF);
    scoreDir(path.join(EXP, `results/${rawDir}`, `rep-${rep}`, 'control', 'modules'), ctrlM);
    scoreDir(path.join(EXP, `results/${rawDir}`, `rep-${rep}`, 'treatment', 'modules'), trtM);
  }
  console.log(`  ΔF1 file scope:   ${(prf(trtF).f1 - prf(ctrlF).f1).toFixed(3)}`);
  console.log(`  ΔF2 file scope:   ${(prf(trtF).f2 - prf(ctrlF).f2).toFixed(3)}`);
  console.log(`  ΔF1 module scope: ${(prf(trtM).f1 - prf(ctrlM).f1).toFixed(3)}`);
  console.log(`  ΔF2 module scope: ${(prf(trtM).f2 - prf(ctrlM).f2).toFixed(3)}`);
}

// Union-of-3-reps (deduplicate across reps, score once per PR)
console.log('\n=== Union of 3 reps F1 (relaxed) ===');
for (const [label, rawDir] of [['gemma4', 'raw'], ['GLM-4.7', 'raw-glm47']] as const) {
  for (const cond of CONDS) {
    // Collect all findings per PR, deduplicate file+line±5
    const byPR: Record<string, Finding[]> = {};
    for (const rep of REPS) {
      for (const sub of ['files', 'modules']) {
        const dir = path.join(EXP, `results/${rawDir}`, `rep-${rep}`, cond, sub);
        if (!fs.existsSync(dir)) continue;
        for (const f of fs.readdirSync(dir)) {
          if (!/^PR-\d+\.findings\.json$/.test(f)) continue;
          const data = JSON.parse(fs.readFileSync(path.join(dir, f), 'utf8')) as { prNumber?: number; findings?: Finding[] };
          const pr = String(data.prNumber ?? f.match(/PR-(\d+)/)?.[1]);
          if (!byPR[pr]) byPR[pr] = [];
          for (const sf of (data.findings ?? [])) {
            const sfLine = parseLine(sf.line);
            const dup = byPR[pr].some(ex => ex.file === sf.file && overlap(parseLine(ex.line), sfLine));
            if (!dup) byPR[pr].push(sf);
          }
        }
      }
    }
    // Score union findings
    const agg = blank();
    for (const [pr, findings] of Object.entries(byPR)) {
      const labels = ak[pr] ?? [];
      const usedAK = new Set<number>();
      const usedSkill = new Set<number>();
      findings.forEach((sf, i) => {
        const sfLine = parseLine(sf.line);
        const idx = labels.findIndex((lbl, j) => {
          if (usedAK.has(j)) return false;
          if (sf.file !== lbl.file) return false;
          return overlap(sfLine, parseLine(lbl.line));
        });
        if (idx === -1) return;
        usedAK.add(idx); usedSkill.add(i);
      });
      let tp = 0, fp = 0;
      for (const idx of usedAK) {
        const lbl = labels[idx];
        if (lbl.verdict === 'TRUE') tp += 1;
        else if (lbl.verdict === 'FALSE') fp += 1;
        else if (lbl.verdict === 'UNCERTAIN') tp += 0.5;
      }
      let fn = 0;
      for (let j = 0; j < labels.length; j++) {
        if (usedAK.has(j)) continue;
        const lbl = labels[j];
        if (lbl.verdict !== 'TRUE') continue;
        fn += lbl.action === 'FIX' ? 1 : 0.5;
      }
      const novels = findings.filter((_, i) => !usedSkill.has(i)).length;
      fp += novels;
      agg.tp += tp; agg.fp += fp; agg.fn += fn;
      agg.novels += novels;
      agg.n += 1;
    }
    const o = prf(agg);
    console.log(`  ${label} ${cond}: F1=${r3(o.f1)} F2=${r3(o.f2)} P=${r3(o.p)} R=${r3(o.r)} | TP=${agg.tp} FP=${agg.fp} FN=${agg.fn} novels=${agg.novels}`);
  }
}
