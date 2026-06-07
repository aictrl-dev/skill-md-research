#!/usr/bin/env npx tsx
/**
 * F2-calibrated consensus ranker (exp-021 precision layer).
 *
 * The negative result from the precision phase was that gemma's self-reported
 * confidence is uncalibrated and every model-side judge deletes recall. This
 * ranker uses ONLY the LOCAL, model-free consensus features attached by the
 * `output: vote` merge — `votes` (# decorrelated resamples agreeing) and
 * `nLenses` (# distinct lenses agreeing) — and calibrates a threshold for F2.
 *
 * To avoid overfitting 20 tasks, it SPLITS tasks into train/test, picks the
 * (minVotes, minLenses) cut that maximises REAL-set F2 on TRAIN, and reports the
 * held-out TEST F2 at that cut vs the votes>=1 (keep-all) baseline. A real lift on
 * held-out test is the bar; a lift only on train is overfitting.
 *
 * Matching mirrors score.ts exactly: file + line +/-5, REAL set (impact:real TRUE).
 *
 * Usage: rank-f2.ts --exp <exp-id> [--reps 1,2,3] [--split odd-even|half]
 *                   [--max-votes 7] [--tasks 105,201,...]
 */
import * as fs from 'node:fs';
import * as path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const EXP_DIR = path.resolve(HERE, '..');
const LINE_TOL = 5;

const argv = process.argv.slice(2);
const get = (f: string, d: string) => { const i = argv.indexOf(f); return i !== -1 ? argv[i + 1] : d; };
const expId = get('--exp', '');
const reps = get('--reps', '1,2,3').split(',').map(s => s.trim());
const resultsBase = get('--results-base', path.join(EXP_DIR, 'results'));
const splitMode = get('--split', 'odd-even'); // odd-even | half
const maxVotes = Number(get('--max-votes', '7'));
const taskFilter = new Set(get('--tasks', '').split(',').map(s => s.trim()).filter(Boolean));
if (!expId) { console.error('Usage: rank-f2.ts --exp <exp-id>'); process.exit(1); }

interface AKEntry { verdict: string; action: string; file: string; line: string; impact?: string }
const ak: Record<string, AKEntry[]> = JSON.parse(fs.readFileSync(path.join(EXP_DIR, 'answer-key.json'), 'utf8'));
const isRealTrue = (l: AKEntry) => l.verdict === 'TRUE' && (l.impact ?? 'real') === 'real';

interface Finding { file: string; line?: number | string; votes?: number; nLenses?: number }
function parseLine(l: string | number | undefined) {
  if (l == null || l === '') return null;
  const m = String(l).match(/^(\d+)(?:[-–](\d+))?$/);
  return m ? { start: parseInt(m[1]), end: m[2] ? parseInt(m[2]) : parseInt(m[1]) } : null;
}
function overlap(a: ReturnType<typeof parseLine>, b: ReturnType<typeof parseLine>) {
  // null/unparsable line must NOT match (else a line-less or comma-list finding
  // would match any oracle entry in the file). Require a real overlap.
  if (!a || !b) return false;
  return Math.abs(a.start - b.start) <= LINE_TOL || (a.start <= b.end + LINE_TOL && a.end + LINE_TOL >= b.start);
}

// ── Load findings per PR (pooled across reps, like the union scorer). ──
const byPR: Record<string, Finding[]> = {};
for (const rep of reps) {
  for (const sub of ['files', 'modules']) {
    const dir = path.join(resultsBase, expId, `rep-${rep}`, 'treatment', sub);
    if (!fs.existsSync(dir)) continue;
    for (const f of fs.readdirSync(dir)) {
      const m = f.match(/^PR-(\d+)\.findings\.json$/);
      if (!m) continue;
      const pr = m[1];
      if (taskFilter.size && !taskFilter.has(pr)) continue;
      const data = JSON.parse(fs.readFileSync(path.join(dir, f), 'utf8')) as { findings?: Finding[] };
      (byPR[pr] ??= []).push(...(data.findings ?? []));
    }
  }
}
const prs = Object.keys(byPR).sort((a, b) => +a - +b);
if (!prs.length) { console.error(`No findings under ${path.join(resultsBase, expId)} — has it run?`); process.exit(1); }

// ── REAL-set F2 over a set of PRs at a given (minVotes, minLenses) cut. ──
function f2Real(prSet: string[], minVotes: number, minLenses: number) {
  let tp = 0, fp = 0, fn = 0;
  for (const pr of prSet) {
    const findings = (byPR[pr] ?? []).filter(x => (x.votes ?? Infinity) >= minVotes && (x.nLenses ?? Infinity) >= minLenses);
    const labels = ak[pr] ?? [];
    const usedAK = new Set<number>();
    for (const sf of findings) {
      const sfLine = parseLine(sf.line);
      const idx = labels.findIndex((lbl, j) => !usedAK.has(j) && sf.file === lbl.file && overlap(sfLine, parseLine(lbl.line)));
      if (idx !== -1) usedAK.add(idx);
    }
    for (const j of usedAK) {
      const lbl = labels[j];
      if (lbl.verdict === 'TRUE') { if (isRealTrue(lbl)) tp += 1; }
      else if (lbl.verdict === 'FALSE') fp += 1;
    }
    for (let j = 0; j < labels.length; j++) {
      if (usedAK.has(j)) continue;
      const lbl = labels[j];
      if (isRealTrue(lbl)) fn += lbl.action === 'FIX' ? 1 : 0.5;
    }
  }
  const p = tp + fp === 0 ? 0 : tp / (tp + fp);
  const r = tp + fn === 0 ? 0 : tp / (tp + fn);
  const f2 = 4 * p + r === 0 ? 0 : (5 * p * r) / (4 * p + r);
  return { p, r, f2, tp, fp, fn };
}

// ── Train/test split. ──
const train: string[] = [], test: string[] = [];
prs.forEach((pr, i) => {
  const toTest = splitMode === 'half' ? i >= Math.ceil(prs.length / 2) : (+pr % 2 === 0);
  (toTest ? test : train).push(pr);
});

// ── Calibrate (minVotes, minLenses) on TRAIN, evaluate on TEST. ──
let best = { v: 1, l: 1, f2: -1 };
for (let v = 1; v <= maxVotes; v++) {
  for (let l = 1; l <= 5; l++) {
    const s = f2Real(train, v, l);
    if (s.f2 > best.f2) best = { v, l, f2: s.f2 };
  }
}
const r3 = (n: number) => (Math.round(n * 1000) / 1000).toFixed(3);
const baseTrain = f2Real(train, 1, 1), baseTest = f2Real(test, 1, 1);
const calTrain = f2Real(train, best.v, best.l), calTest = f2Real(test, best.v, best.l);

console.log(`\n=== rank-f2: ${expId} (split=${splitMode}) ===`);
console.log(`  tasks: ${prs.length}  train=${train.length} [${train.join(',')}]  test=${test.length} [${test.join(',')}]`);
console.log(`  calibrated cut: minVotes>=${best.v}, minLenses>=${best.l}`);
console.log(`  REAL F2 — keep-all baseline:  train=${r3(baseTrain.f2)}  test=${r3(baseTest.f2)}`);
console.log(`  REAL F2 — calibrated cut:     train=${r3(calTrain.f2)}  test=${r3(calTest.f2)}`);
console.log(`  TEST detail @cut: P=${r3(calTest.p)} R=${r3(calTest.r)} F2=${r3(calTest.f2)} (tp=${calTest.tp} fp=${calTest.fp} fn=${calTest.fn})`);
console.log(`  held-out lift vs keep-all: ${r3(calTest.f2 - baseTest.f2)} ${calTest.f2 > baseTest.f2 ? '(REAL lift)' : '(no lift — consensus cut does not generalise)'}`);

// Full vote-threshold curve on ALL tasks (for the response-curve graph).
console.log(`  vote-threshold curve (all tasks, minLenses>=1):`);
for (let v = 1; v <= maxVotes; v++) {
  const s = f2Real(prs, v, 1);
  console.log(`    votes>=${v}: P=${r3(s.p)} R=${r3(s.r)} F2=${r3(s.f2)} (tp=${s.tp} fp=${s.fp} fn=${s.fn})`);
}
