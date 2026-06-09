#!/usr/bin/env npx tsx
/**
 * Two empirical curves for the blog, both built by RESAMPLING the pool of
 * individual single-pass gemma reviews (per-lens findings files; baselines and
 * merged-union files excluded).
 *
 *   1. LONG TAIL — per real bug, find-rate = (passes that surfaced it) /
 *      (passes for that PR). Sorted descending. Shows a few bugs are found
 *      almost every pass and a long tail is found by <5% — which is why driving
 *      union-recall to 100% needs exponentially many passes.
 *
 *   2. RECALL / F2 vs NODES — brute-force union estimate. For k = 1..N, sample k
 *      passes per PR (without replacement), union+dedup (file+line±5), score
 *      against the oracle with the SAME matching as score.ts, micro-average over
 *      PRs, average over many resamples. Plus an analytic extrapolation
 *      recall(k) = mean_bug[1-(1-rate)^k] that reaches out to thousands of
 *      passes cheaply and exposes the cost of the last few percent of recall.
 *
 * Output: analysis/curves.json (consumed by the blog charts).
 *
 * NOTE: the pool mixes configurations (temps, framings, directed rounds). Per the
 * leakage note in recurring-fp.ts, that inflates absolute counts roughly
 * uniformly; the SHAPE of both curves is the robust, reported result.
 */
import * as fs from 'node:fs';
import * as path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const EXP_DIR = path.resolve(HERE, '..');
const TOL = 5;
const REPS = 300;                 // resamples per k for the empirical curve
const K_EMPIRICAL = [1, 2, 3, 5, 8, 10, 13, 15, 21, 34, 55, 89, 144];
const K_ANALYTIC = [1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377, 610, 1000, 1597, 2584];
// lens/persona discovery passes only — drop the judge filter node (not a discovery pass)
const EXCLUDE_NODES = new Set(['judge']);
let seed = 0xdecafbad;
const random = () => {
  seed = (seed * 1664525 + 1013904223) >>> 0;
  return seed / 0x100000000;
};

const ak: Record<string, any[]> = JSON.parse(fs.readFileSync(path.join(EXP_DIR, 'answer-key.json'), 'utf8'));
const isReal = (l: any) => l.verdict === 'TRUE' && (l.impact ?? 'real') === 'real';
const parseLine = (l: any) => { if (l == null || l === '') return null; const m = String(l).match(/^(\d+)(?:[-–](\d+))?$/); return m ? { s: +m[1], e: m[2] ? +m[2] : +m[1] } : null; };
const overlap = (a: any, b: any) => !a || !b ? false : (Math.abs(a.s - b.s) <= TOL || (a.s <= b.e + TOL && a.e + TOL >= b.s));

type Finding = { file: string; line: any };
// pool: pr -> array of passes; each pass is the finding list of one per-lens file
const pool: Record<string, Finding[][]> = {};
function walk(d: string) {
  for (const e of fs.readdirSync(d, { withFileTypes: true })) {
    const p = path.join(d, e.name);
    if (e.isDirectory()) walk(p);
    else {
      const m = e.name.match(/^PR-(\d+)\.([a-zA-Z0-9_]+)\.findings\.json$/);   // per-lens only
      if (!m) continue;
      const node = m[2].replace(/_(?:r|round)?\d+$/, '');
      if (EXCLUDE_NODES.has(node)) continue;
      try {
        const fnd = (JSON.parse(fs.readFileSync(p, 'utf8')).findings ?? []).map((f: any) => ({ file: f.file, line: f.line }));
        (pool[m[1]] ??= []).push(fnd);
      } catch { /* skip unparseable */ }
    }
  }
}
const root = path.join(EXP_DIR, 'results');
if (fs.existsSync(root)) walk(root);

// PRs that contain at least one real bug drive recall; keep all PRs for FP/precision.
const realBugs: { pr: string; file: string; line: any; reason: string }[] = [];
for (const [pr, labels] of Object.entries(ak)) for (const l of labels) if (isReal(l))
  realBugs.push({ pr, file: l.file, line: l.line, reason: (l.reason ?? l.title ?? '').replace(/\s+/g, ' ').slice(0, 90) });

// ---------- 1. LONG TAIL: per-bug find-rate over the pool ----------
const passHitsBug = (passes: Finding[][], file: string, lr: any) =>
  passes.filter(pf => pf.some(f => f.file === file && overlap(parseLine(f.line), lr))).length;

const longTail = realBugs.map(b => {
  const passes = pool[b.pr] ?? [];
  const rate = passes.length ? passHitsBug(passes, b.file, parseLine(b.line)) / passes.length : 0;
  return { pr: b.pr, file: b.file.split('/').pop(), line: b.line, rate: +rate.toFixed(4), passes: passes.length, reason: b.reason };
}).sort((a, b) => b.rate - a.rate);

// ---------- 2a. EMPIRICAL recall / precision / F2 vs k (union of k sampled passes) ----------
// real-set scoring mirrors score.ts's strict precision policy: TP = real-bug
// match, FP = FALSE-trap match plus every unmatched novel finding. If a novel is
// later independently validated, merge it into answer-key.json and it becomes TP.
const falseTraps: Record<string, { file: string; line: any }[]> = {};
const realByPR: Record<string, { file: string; line: any }[]> = {};
const labelsByPR: Record<string, { verdict: string; file: string; line: any }[]> = {};
for (const [pr, labels] of Object.entries(ak)) {
  for (const l of labels) {
    (labelsByPR[pr] ??= []).push({ verdict: l.verdict, file: l.file, line: l.line });
    if (l.verdict === 'FALSE') (falseTraps[pr] ??= []).push({ file: l.file, line: l.line });
    if (isReal(l)) (realByPR[pr] ??= []).push({ file: l.file, line: l.line });
  }
}
const PRS = Object.keys(pool);
const sampleK = (arr: Finding[][], k: number): Finding[][] => {
  if (k >= arr.length) return arr;
  const idx = arr.map((_, i) => i);
  for (let i = idx.length - 1; i > 0; i--) { const j = Math.floor(random() * (i + 1)); [idx[i], idx[j]] = [idx[j], idx[i]]; }
  return idx.slice(0, k).map(i => arr[i]);
};
const dedup = (passes: Finding[][]): Finding[] => {
  const out: Finding[] = [];
  for (const pf of passes) for (const f of pf) {
    if (!f.file) continue;
    if (!out.some(e => e.file === f.file && overlap(parseLine(e.line), parseLine(f.line)))) out.push(f);
  }
  return out;
};
function scoreUnion(unionByPR: Record<string, Finding[]>) {
  let tp = 0, fp = 0, fn = 0;
  for (const pr of new Set([...Object.keys(realByPR), ...Object.keys(falseTraps), ...Object.keys(unionByPR)])) {
    const fnd = unionByPR[pr] ?? [];
    for (const rb of (realByPR[pr] ?? [])) {
      if (fnd.some(f => f.file === rb.file && overlap(parseLine(f.line), parseLine(rb.line)))) tp++; else fn++;
    }
    for (const ft of (falseTraps[pr] ?? [])) {
      if (fnd.some(f => f.file === ft.file && overlap(parseLine(f.line), parseLine(ft.line)))) fp++;
    }
    for (const f of fnd) {
      const labels = labelsByPR[pr] ?? [];
      const matched = labels.some(lbl => f.file === lbl.file && overlap(parseLine(f.line), parseLine(lbl.line)));
      if (!matched) fp++;
    }
  }
  const p = tp + fp === 0 ? 0 : tp / (tp + fp);
  const r = tp + fn === 0 ? 0 : tp / (tp + fn);
  const f2 = 4 * p + r === 0 ? 0 : (5 * p * r) / (4 * p + r);
  return { p, r, f2 };
}
const maxPool = Math.min(...PRS.filter(pr => realByPR[pr]).map(pr => pool[pr].length));
const pct = (sorted: number[], q: number) => sorted[Math.min(sorted.length - 1, Math.max(0, Math.round(q * (sorted.length - 1))))];
const mean = (a: number[]) => a.reduce((s, x) => s + x, 0) / a.length;
// For each k, resample REPS times and keep the full distribution → mean + 80% and 95% bands.
const empirical = K_EMPIRICAL.filter(k => k <= maxPool).map(k => {
  const rs: number[] = [], fs2: number[] = [], ps: number[] = [];
  for (let rep = 0; rep < REPS; rep++) {
    const u: Record<string, Finding[]> = {};
    for (const pr of PRS) u[pr] = dedup(sampleK(pool[pr], k));
    const s = scoreUnion(u); rs.push(s.r); fs2.push(s.f2); ps.push(s.p);
  }
  rs.sort((a, b) => a - b); fs2.sort((a, b) => a - b); ps.sort((a, b) => a - b);
  const r4 = (x: number) => +x.toFixed(4);
  return {
    k,
    recall: r4(mean(rs)), precision: r4(mean(ps)), f2: r4(mean(fs2)),
    recall_p025: r4(pct(rs, 0.025)), recall_p975: r4(pct(rs, 0.975)),
    recall_p10: r4(pct(rs, 0.10)), recall_p90: r4(pct(rs, 0.90)),
    f2_p025: r4(pct(fs2, 0.025)), f2_p975: r4(pct(fs2, 0.975)),
    f2_p10: r4(pct(fs2, 0.10)), f2_p90: r4(pct(fs2, 0.90)),
  };
});

// ---------- 2c. BASELINES (frontier reference) — real-set F2 on the SAME oracle ----------
// Single-pass cloud models: score their merged findings per PR with scoreUnion.
const COST_PER_CALL = 0.0024;                       // Vertex Flash-class $/gemma call (exec-summary basis)
const BASELINE_COST: Record<string, number> = { haiku: 0.0052, glm47: 0.0067, opus: 0.0975 };
function scoreBaseline(dir: string) {
  const u: Record<string, Finding[]> = {};
  if (!fs.existsSync(dir)) return null;
  const walkB = (d: string) => {
    for (const e of fs.readdirSync(d, { withFileTypes: true })) {
      const p = path.join(d, e.name);
      if (e.isDirectory()) { walkB(p); continue; }
      const m = e.name.match(/^PR-(\d+)\.findings\.json$/);            // merged single pass
      if (!m) continue;
      try { (u[m[1]] ??= []).push(...(JSON.parse(fs.readFileSync(p, 'utf8')).findings ?? []).map((f: any) => ({ file: f.file, line: f.line }))); } catch {}
    }
  };
  walkB(dir);
  return scoreUnion(u);
}
const baselines = [
  { name: 'Haiku 4.5', cost: BASELINE_COST.haiku, s: scoreBaseline(path.join(root, 'haiku-baseline')) },
  { name: 'GLM 4.7', cost: BASELINE_COST.glm47, s: scoreBaseline(path.join(root, 'glm47-baseline')) },
  { name: 'Opus 4.8 (circular P)', cost: BASELINE_COST.opus, s: scoreBaseline(path.join(root, 'opus-baseline')) },
].filter(b => b.s).map(b => ({ name: b.name, cost: b.cost, f2: +b.s!.f2.toFixed(3), recall: +b.s!.r.toFixed(3), precision: +b.s!.p.toFixed(3) }));

// Frontier = the same bootstrap, x mapped to cost = k * COST_PER_CALL, with the F2 band.
const FRONTIER_K = [1, 3, 5, 10, 15];
const frontierGemma = FRONTIER_K.map(k => {
  const e = empirical.find(x => x.k === k);
  return e ? { k, cost: +(k * COST_PER_CALL).toFixed(4), f2: e.f2, f2_p10: e.f2_p10, f2_p90: e.f2_p90 } : null;
}).filter(Boolean);

// ---------- 2b. ANALYTIC recall & F2 extrapolation ----------
// recall(k)=mean_bug[1-(1-p)^k]; precision(k) from the SAME independence model
// applied to FALSE-trap and novel-cluster find-rates: expected TPs =
// sum_bug[1-(1-p)^k] (one per real bug), expected FPs =
// sum_fp[1-(1-q)^k]. F2 = 5PR/(4P+R).
const rates = longTail.map(b => b.rate);
// per-FALSE-trap find-rate across the same pool (mirror of the real-bug long tail)
const trapRates: number[] = [];
for (const [pr, traps] of Object.entries(falseTraps)) {
  const passes = pool[pr] ?? [];
  if (!passes.length) continue;
  for (const t of traps) trapRates.push(passHitsBug(passes, t.file, parseLine(t.line)) / passes.length);
}
const novelClusters: Record<string, Finding[]> = {};
for (const [pr, passes] of Object.entries(pool)) {
  for (const pf of passes) for (const f of pf) {
    if (!f.file) continue;
    const labels = labelsByPR[pr] ?? [];
    const matched = labels.some(lbl => f.file === lbl.file && overlap(parseLine(f.line), parseLine(lbl.line)));
    if (matched) continue;
    const clusters = (novelClusters[pr] ??= []);
    if (!clusters.some(c => c.file === f.file && overlap(parseLine(c.line), parseLine(f.line)))) clusters.push(f);
  }
}
const novelRates: number[] = [];
for (const [pr, clusters] of Object.entries(novelClusters)) {
  const passes = pool[pr] ?? [];
  if (!passes.length) continue;
  for (const c of clusters) novelRates.push(passHitsBug(passes, c.file, parseLine(c.line)) / passes.length);
}
const fpRates = [...trapRates, ...novelRates];
const analytic = K_ANALYTIC.map(k => {
  const expTP = rates.reduce((s, p) => s + (1 - Math.pow(1 - p, k)), 0);
  const expFP = fpRates.reduce((s, q) => s + (1 - Math.pow(1 - q, k)), 0);
  const recall = expTP / rates.length;
  const prec = expTP + expFP === 0 ? 0 : expTP / (expTP + expFP);
  const f2 = 4 * prec + recall === 0 ? 0 : (5 * prec * recall) / (4 * prec + recall);
  return { k, recall: +recall.toFixed(4), precision: +prec.toFixed(4), f2: +f2.toFixed(4) };
});
// how many independent passes to expect a given mean recall, and to 95%-catch the rarest bug
const recallToK = (target: number) => {
  for (let k = 1; k <= 100000; k++) {
    if (rates.reduce((s, p) => s + (1 - Math.pow(1 - p, k)), 0) / rates.length >= target) return k;
  }
  return Infinity;
};
const rarest = longTail[longTail.length - 1];
const k95rarest = rarest.rate > 0 ? Math.ceil(Math.log(0.05) / Math.log(1 - rarest.rate)) : Infinity;

const out = {
  generated: 'bootstrap-curves.ts',
  poolPassesTotal: Object.values(pool).reduce((s, a) => s + a.length, 0),
  poolPerPR: Object.fromEntries(PRS.map(pr => [pr, pool[pr].length])),
  realBugCount: realBugs.length,
  strictPrecision: {
    novelPolicy: 'unmatched findings count as FP until independently validated and merged into answer-key.json',
    falseTrapCount: trapRates.length,
    novelClusterCount: novelRates.length,
  },
  maxPoolForEmpirical: maxPool,
  longTail,
  empirical,
  analytic,
  baselines,
  frontier: { costPerCall: COST_PER_CALL, gemma: frontierGemma, baselines },
  bootstrapReps: REPS,
  summary: {
    rarestBug: { pr: rarest.pr, file: rarest.file, line: rarest.line, rate: rarest.rate, reason: rarest.reason },
    k95_catch_rarest: k95rarest,
    k_for_recall_90: recallToK(0.90),
    k_for_recall_95: recallToK(0.95),
    k_for_recall_99: recallToK(0.99),
    k_for_recall_100: recallToK(0.999),
    bugsBelow5pct: longTail.filter(b => b.rate < 0.05).length,
    bugsAbove50pct: longTail.filter(b => b.rate >= 0.5).length,
  },
};
fs.mkdirSync(path.join(EXP_DIR, 'analysis'), { recursive: true });
fs.writeFileSync(path.join(EXP_DIR, 'analysis', 'curves.json'), JSON.stringify(out, null, 2));

// ---- console summary ----
console.log(`\npool: ${out.poolPassesTotal} single-pass reviews across ${PRS.length} PRs (${out.realBugCount} real bugs)`);
console.log(`empirical k capped at min pool = ${maxPool}\n`);
console.log(`bands = p2.5..p97.5 over ${REPS} resamples`);
console.log('k     recall [p025-p975]      F2 [p025-p975]');
for (const e of empirical) console.log(`${String(e.k).padStart(3)}   ${e.recall.toFixed(3)} [${e.recall_p025.toFixed(3)}-${e.recall_p975.toFixed(3)}]   ${e.f2.toFixed(3)} [${e.f2_p025.toFixed(3)}-${e.f2_p975.toFixed(3)}]`);
console.log('\nbaselines (real-set, full oracle):');
for (const b of baselines) console.log(`  ${b.name.padEnd(22)} F2=${b.f2.toFixed(3)} R=${b.recall.toFixed(3)} P=${b.precision.toFixed(3)} @ $${b.cost}/review`);
console.log('\nfrontier gemma (F2 vs cost, with band):');
for (const g of frontierGemma) console.log(`  N=${String(g!.k).padStart(2)} $${g!.cost.toFixed(4)}  F2=${g!.f2.toFixed(3)} [${g!.f2_p10.toFixed(3)}-${g!.f2_p90.toFixed(3)}]`);
console.log('\nanalytic extrapolation (recall / prec / F2) — compare F2 to empirical above:');
for (const a of analytic) console.log(`  k=${String(a.k).padStart(4)}  recall=${a.recall.toFixed(3)}  prec=${a.precision.toFixed(3)}  F2=${a.f2.toFixed(3)}`);
console.log(`\nrarest bug: PR-${rarest.pr} ${rarest.file}:${rarest.line} @ ${(rarest.rate*100).toFixed(1)}% find-rate`);
console.log(`  → 95% chance to catch it needs ~${k95rarest} independent passes`);
console.log(`mean recall: 90% @ k≈${out.summary.k_for_recall_90}, 95% @ k≈${out.summary.k_for_recall_95}, 99% @ k≈${out.summary.k_for_recall_99}, ~100% @ k≈${out.summary.k_for_recall_100}`);
console.log(`bugs found by <5% of passes: ${out.summary.bugsBelow5pct}/${out.realBugCount}; by ≥50%: ${out.summary.bugsAbove50pct}/${out.realBugCount}`);
console.log(`\nwrote analysis/curves.json`);
