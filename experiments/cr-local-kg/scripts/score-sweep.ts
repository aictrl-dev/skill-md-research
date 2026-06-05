#!/usr/bin/env npx tsx
/**
 * Score the cr-local-kg sweep: micro-average precision/recall/F1 per condition
 * (and per task-class) against the frozen gold answer-key, reusing cr-loop's
 * score(). Also surfaces KG-usage + time-per-review from results/timing.csv.
 *
 * Usage: score-sweep.ts [--reps 1,2,3]
 */
import * as fs from 'node:fs';
import * as path from 'node:path';
import { fileURLToPath } from 'node:url';
import { score, type SkillFinding } from '../../cr-loop/scripts/score.ts';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const EXP = path.resolve(HERE, '..');
const AK = path.join(EXP, 'answer-key.json');

const a: Record<string, string> = {};
const argv = process.argv.slice(2);
for (let i = 0; i < argv.length; i += 1) if (argv[i].startsWith('--')) { a[argv[i].slice(2)] = argv[i + 1] ?? ''; i += 1; }
const reps = (a.reps ?? '1,2,3').split(',');

interface Agg { tp: number; fp: number; fn: number; novels: number; n: number; }
const blank = (): Agg => ({ tp: 0, fp: 0, fn: 0, novels: 0, n: 0 });
function prf(g: Agg) {
  const p = g.tp + g.fp === 0 ? 0 : g.tp / (g.tp + g.fp);
  const r = g.tp + g.fn === 0 ? 0 : g.tp / (g.tp + g.fn);
  const f1 = p + r === 0 ? 0 : (2 * p * r) / (p + r);
  return { p, r, f1 };
}
const r3 = (n: number) => Math.round(n * 1000) / 1000;

function scoreDir(dir: string, into: Agg): void {
  if (!fs.existsSync(dir)) return;
  for (const f of fs.readdirSync(dir).filter((x) => /^PR-\d+\.findings\.json$/.test(x))) {
    const data = JSON.parse(fs.readFileSync(path.join(dir, f), 'utf8')) as { prNumber?: number; findings?: SkillFinding[] };
    const pr = data.prNumber ?? Number(f.match(/^PR-(\d+)\./)?.[1]);
    const res = score(pr, data.findings ?? [], AK);
    into.tp += res.totals.truePositives; into.fp += res.totals.falsePositives;
    into.fn += res.totals.falseNegatives; into.novels += res.totals.novelFindings; into.n += 1;
  }
}

// timing.csv → per-condition KG usage + avg seconds
const timing = fs.existsSync(path.join(EXP, 'results/timing.csv'))
  ? fs.readFileSync(path.join(EXP, 'results/timing.csv'), 'utf8').trim().split('\n').slice(1)
      .map((l) => l.split(',')).filter((r) => r.length === 7) : [];

console.log(`\nReps scored: ${reps.join(',')}  |  answer-key: ${path.basename(AK)}\n`);
for (const cond of ['control', 'treatment']) {
  const overall = blank();
  const byClass: Record<string, Agg> = { file: blank(), module: blank() };
  for (const rep of reps) {
    for (const [cls, sub] of [['file', 'files'], ['module', 'modules']] as const) {
      const dir = path.join(EXP, 'results/raw', `rep-${rep}`, cond, sub);
      scoreDir(dir, overall); scoreDir(dir, byClass[cls]);
    }
  }
  const o = prf(overall);
  const t = timing.filter((r) => r[2] === cond);
  const secs = t.map((r) => Number(r[6]));
  const kg = t.map((r) => Number(r[5]));
  const avg = (v: number[]) => (v.length ? v.reduce((x, y) => x + y, 0) / v.length : 0);
  console.log(`== ${cond.toUpperCase()} ==  (n=${overall.n} reviews)`);
  console.log(`   P=${r3(o.p)} R=${r3(o.r)} F1=${r3(o.f1)}  | TP=${overall.tp} FP=${overall.fp} FN=${overall.fn} novels=${overall.novels}`);
  for (const cls of ['file', 'module']) {
    const c = prf(byClass[cls]);
    console.log(`   ${cls}: F1=${r3(c.f1)} (P=${r3(c.p)} R=${r3(c.r)}, n=${byClass[cls].n})`);
  }
  if (t.length) console.log(`   time/review: avg ${avg(secs).toFixed(0)}s | KG: used ${kg.filter((x) => x > 0).length}/${t.length} reviews, avg ${avg(kg).toFixed(1)} calls`);
  console.log('');
}
