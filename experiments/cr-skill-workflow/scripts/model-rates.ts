#!/usr/bin/env npx tsx
/**
 * Per-bug and per-FP find-rates for gemma and GLM-4.7, for analytic response
 * curves recall(k)=mean_i[1-(1-p_i)^k] and strict F2. FP rates include FALSE
 * oracle traps and unmatched novel clusters. If a novel is independently
 * validated, merge it into answer-key.json and it becomes a TP rate.
 *   gemma pool: cr-skill-workflow per-lens passes (~thousands).
 *   GLM pool  : cr-local-kg raw-glm47 (6/PR) + glm47-baseline (1/PR) = 7/PR.
 * Output: analysis/model-rates.json
 */
import * as fs from 'node:fs';
import * as path from 'node:path';
import { fileURLToPath } from 'node:url';
const HERE = path.dirname(fileURLToPath(import.meta.url));
const EXP = path.resolve(HERE, '..');
const EXPS = path.resolve(EXP, '..');
const TOL = 5;
const ak: Record<string, any[]> = JSON.parse(fs.readFileSync(path.join(EXP, 'answer-key.json'), 'utf8'));
const isReal = (l: any) => l.verdict === 'TRUE' && (l.impact ?? 'real') === 'real';
const rng = (s: any) => { if (s == null || s === '') return null; const m = String(s).match(/^(\d+)(?:[-–](\d+))?$/); return m ? { s: +m[1], e: m[2] ? +m[2] : +m[1] } : null; };
const ov = (a: any, b: any) => !a || !b ? false : (Math.abs(a.s - b.s) <= TOL || (a.s <= b.e + TOL && a.e + TOL >= b.s));

type F = { file: string; line: any };
function gemmaPool(): Record<string, F[][]> {
  const pool: Record<string, F[][]> = {};
  (function w(d: string) {
    for (const e of fs.readdirSync(d, { withFileTypes: true })) {
      const p = path.join(d, e.name);
      if (e.isDirectory()) { w(p); continue; }
      const m = e.name.match(/^PR-(\d+)\.([a-zA-Z0-9_]+)\.findings\.json$/);
      if (!m || m[2].replace(/_(?:r|round)?\d+$/, '') === 'judge') continue;
      try { (pool[m[1]] ??= []).push((JSON.parse(fs.readFileSync(p, 'utf8')).findings ?? []).map((f: any) => ({ file: f.file, line: f.line }))); } catch {}
    }
  })(path.join(EXP, 'results'));
  return pool;
}
function glmPool(): Record<string, F[][]> {
  const pool: Record<string, F[][]> = {};
  const add = (root: string) => { if (!fs.existsSync(root)) return; (function w(d: string) {
    for (const e of fs.readdirSync(d, { withFileTypes: true })) {
      const p = path.join(d, e.name);
      if (e.isDirectory()) { w(p); continue; }
      const m = e.name.match(/^PR-(\d+)\.findings\.json$/);
      if (!m) continue;
      try { (pool[m[1]] ??= []).push((JSON.parse(fs.readFileSync(p, 'utf8')).findings ?? []).map((f: any) => ({ file: f.file, line: f.line }))); } catch {}
    }
  })(root); };
  add(path.join(EXPS, 'cr-local-kg', 'results', 'raw-glm47'));
  add(path.join(EXP, 'results', 'glm47-baseline'));
  return pool;
}
function rates(pool: Record<string, F[][]>) {
  const bug: number[] = [], trap: number[] = [], novel: number[] = [];
  const novelClusters: Record<string, F[]> = {};
  for (const [pr, labels] of Object.entries(ak)) {
    const passes = pool[pr] ?? []; if (!passes.length) continue;
    for (const l of labels) {
      const lr = rng(l.line);
      const r = passes.filter(pf => pf.some(f => f.file === l.file && ov(rng(f.line), lr))).length / passes.length;
      if (isReal(l)) bug.push(r);
      else if (l.verdict === 'FALSE') trap.push(r);
    }
  }
  for (const [pr, passes] of Object.entries(pool)) {
    const labels = ak[pr] ?? [];
    for (const pf of passes) for (const f of pf) {
      if (!f.file) continue;
      const matched = labels.some(l => f.file === l.file && ov(rng(f.line), rng(l.line)));
      if (matched) continue;
      const clusters = (novelClusters[pr] ??= []);
      if (!clusters.some(c => c.file === f.file && ov(rng(c.line), rng(f.line)))) clusters.push(f);
    }
  }
  for (const [pr, clusters] of Object.entries(novelClusters)) {
    const passes = pool[pr] ?? []; if (!passes.length) continue;
    for (const c of clusters) {
      const r = passes.filter(pf => pf.some(f => f.file === c.file && ov(rng(f.line), rng(c.line)))).length / passes.length;
      novel.push(r);
    }
  }
  return { bug, trap, novel, passesPerPR: Object.fromEntries(Object.keys(pool).map(pr => [pr, pool[pr].length])) };
}
const gemma = rates(gemmaPool());
const glm = rates(glmPool());
const out = {
  // per-pass cost to review 1,000 LoC (from measured token models)
  costPerPass1kLoC: { gemma: 0.00112, glm: 0.00918 },
  gemma: { nBugs: gemma.bug.length, nTraps: gemma.trap.length, nNovelClusters: gemma.novel.length, bugRates: gemma.bug, trapRates: gemma.trap, novelRates: gemma.novel, minPasses: Math.min(...Object.values(gemma.passesPerPR)) },
  glm: { nBugs: glm.bug.length, nTraps: glm.trap.length, nNovelClusters: glm.novel.length, bugRates: glm.bug, trapRates: glm.trap, novelRates: glm.novel, minPasses: Math.min(...Object.values(glm.passesPerPR)) },
};
fs.writeFileSync(path.join(EXP, 'analysis', 'model-rates.json'), JSON.stringify(out, null, 2));
const r2 = (a: number[]) => (a.reduce((s, x) => s + x, 0) / a.length).toFixed(3);
console.log(`gemma: ${gemma.bug.length} bugs, ${gemma.trap.length} traps, ${gemma.novel.length} novel FP clusters, min passes/PR=${out.gemma.minPasses}, mean bug-rate=${r2(gemma.bug)}, ceiling(>0)=${(gemma.bug.filter(x=>x>0).length/gemma.bug.length).toFixed(3)}`);
console.log(`GLM  : ${glm.bug.length} bugs, ${glm.trap.length} traps, ${glm.novel.length} novel FP clusters, min passes/PR=${out.glm.minPasses}, mean bug-rate=${r2(glm.bug)}, ceiling(>0)=${(glm.bug.filter(x=>x>0).length/glm.bug.length).toFixed(3)}`);
console.log('wrote analysis/model-rates.json');
