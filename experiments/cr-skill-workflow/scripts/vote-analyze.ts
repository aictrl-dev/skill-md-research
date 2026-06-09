#!/usr/bin/env npx tsx
/**
 * Offline consensus-vote analysis (zero GPU). Reads an experiment's PERSISTED
 * per-node findings (PR-<id>.<node>.findings.json) — written by the harness for
 * every run — recomputes the vote-merge retroactively, and answers the core
 * exp-021 hypothesis: does vote-count (how many decorrelated resamples surfaced a
 * finding) correlate with correctness?
 *
 * For each PR it clusters findings across node files (file + line +/-5), counts
 * votes (# distinct nodes) and nLenses (# distinct lenses = node minus _r<round>),
 * classifies each cluster against the oracle as realTP / theoTP / FP(matched a
 * FALSE entry) / novel, and prints the vote distribution + precision-by-threshold.
 * For strict precision, novel clusters count as FP unless they are independently
 * validated and merged into answer-key.json.
 *
 * Usage: vote-analyze.ts --exp <exp-id> [--reps 1,2,3] [--tasks 105,201,...]
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
const reps = get('--reps', '1').split(',').map(s => s.trim());
const resultsBase = get('--results-base', path.join(EXP_DIR, 'results'));
const taskFilter = new Set(get('--tasks', '').split(',').map(s => s.trim()).filter(Boolean));
if (!expId) { console.error('Usage: vote-analyze.ts --exp <exp-id>'); process.exit(1); }

interface AKEntry { verdict: string; action: string; file: string; line: string; impact?: string }
const ak: Record<string, AKEntry[]> = JSON.parse(fs.readFileSync(path.join(EXP_DIR, 'answer-key.json'), 'utf8'));
const isRealTrue = (l: AKEntry) => l.verdict === 'TRUE' && (l.impact ?? 'real') === 'real';

interface Finding { file?: string; line?: number | string; confidence?: number; title?: string }
const ln = (l: number | string | undefined): number | null => {
  if (l == null || l === '') return null;
  const m = String(l).match(/^(\d+)/); return m ? parseInt(m[1]) : null;
};
function parseRange(l: string | number | undefined) {
  if (l == null || l === '') return null;
  const m = String(l).match(/^(\d+)(?:[-–](\d+))?$/);
  return m ? { start: parseInt(m[1]), end: m[2] ? parseInt(m[2]) : parseInt(m[1]) } : null;
}
function overlap(a: { start: number; end: number } | null, b: { start: number; end: number } | null) {
  if (!a || !b) return false;
  return Math.abs(a.start - b.start) <= LINE_TOL || (a.start <= b.end + LINE_TOL && a.end + LINE_TOL >= b.start);
}

interface Cluster { file: string; line: number | null; votes: Set<string>; lenses: Set<string> }

// vote-merge one PR's per-node files into clusters
function clustersFor(dir: string, pr: string): Cluster[] {
  const clusters: Cluster[] = [];
  const re = new RegExp(`^PR-${pr}\\.([a-zA-Z_0-9]+)\\.findings\\.json$`);
  for (const f of fs.readdirSync(dir)) {
    const m = f.match(re);
    if (!m) continue;
    const node = m[1];
    const lens = node.replace(/_(?:r|round)?\d+$/, '');
    const data = JSON.parse(fs.readFileSync(path.join(dir, f), 'utf8')) as { findings?: Finding[] };
    for (const x of data.findings ?? []) {
      if (!x.file) continue;
      const xl = ln(x.line);
      let c = clusters.find(c => c.file === x.file && (c.line == null) === (xl == null) && (c.line == null || Math.abs(c.line - xl!) <= LINE_TOL));
      if (!c) { c = { file: x.file, line: xl, votes: new Set(), lenses: new Set() }; clusters.push(c); }
      c.votes.add(node); c.lenses.add(lens);
      if (xl != null && c.line == null) c.line = xl;
    }
  }
  return clusters;
}

type Klass = 'realTP' | 'theoTP' | 'FP' | 'novel';
function classify(pr: string, c: Cluster): Klass {
  const labels = ak[pr] ?? [];
  const cl = c.line == null ? null : { start: c.line, end: c.line };
  const hit = labels.find(lbl => lbl.file === c.file && overlap(cl, parseRange(lbl.line)));
  if (!hit) return 'novel';
  if (hit.verdict === 'FALSE') return 'FP';
  if (hit.verdict === 'TRUE') return isRealTrue(hit) ? 'realTP' : 'theoTP';
  return 'novel';
}

// ── Collect all clusters across PRs/reps. ──
const all: { pr: string; votes: number; nLenses: number; k: Klass }[] = [];
let maxVotes = 0;
for (const rep of reps) {
  for (const sub of ['files', 'modules']) {
    const dir = path.join(resultsBase, expId, `rep-${rep}`, 'treatment', sub);
    if (!fs.existsSync(dir)) continue;
    const prs = new Set<string>();
    for (const f of fs.readdirSync(dir)) { const m = f.match(/^PR-(\d+)\./); if (m) prs.add(m[1]); }
    for (const pr of prs) {
      if (taskFilter.size && !taskFilter.has(pr)) continue;
      for (const c of clustersFor(dir, pr)) {
        const votes = c.votes.size; maxVotes = Math.max(maxVotes, votes);
        all.push({ pr, votes, nLenses: c.lenses.size, k: classify(pr, c) });
      }
    }
  }
}
if (!all.length) { console.error(`No per-node findings under ${path.join(resultsBase, expId)} (run with per-node persistence).`); process.exit(1); }

const r3 = (n: number) => (Math.round(n * 1000) / 1000).toFixed(3);
const prsSeen = [...new Set(all.map(a => a.pr))].sort((a, b) => +a - +b);
console.log(`\n=== vote-analyze: ${expId} (reps ${reps.join(',')}, ${prsSeen.length} PRs, ${all.length} findings, max ${maxVotes} voters) ===`);

// Distribution: at EXACTLY v votes, how do findings break down?
console.log(`\n  votes | realTP theoTP  FP  novel | strict precision (realTP / (realTP+FP+novel))`);
for (let v = 1; v <= maxVotes; v++) {
  const at = all.filter(a => a.votes === v);
  if (!at.length) continue;
  const c = (k: Klass) => at.filter(a => a.k === k).length;
  const rtp = c('realTP'), ttp = c('theoTP'), fp = c('FP'), nov = c('novel');
  const good = rtp + fp + nov === 0 ? NaN : rtp / (rtp + fp + nov);
  console.log(`   =${v}  |  ${String(rtp).padStart(4)}  ${String(ttp).padStart(5)} ${String(fp).padStart(4)} ${String(nov).padStart(5)}  |  ${isNaN(good) ? '  -  ' : r3(good)}`);
}

// Threshold view: at votes>=v, REAL precision (vs FALSE-trap FPs) and recall retained.
const totalRealTP = all.filter(a => a.k === 'realTP').length;
console.log(`\n  votes>=v | realTP  FP  novel | strict precision* | realTP retained`);
for (let v = 1; v <= maxVotes; v++) {
  const at = all.filter(a => a.votes >= v);
  const rtp = at.filter(a => a.k === 'realTP').length;
  const fp = at.filter(a => a.k === 'FP').length;
  const nov = at.filter(a => a.k === 'novel').length;
  const prec = rtp + fp + nov === 0 ? NaN : rtp / (rtp + fp + nov);
  console.log(`   >=${v}     |  ${String(rtp).padStart(4)} ${String(fp).padStart(4)} ${String(nov).padStart(6)}  |     ${isNaN(prec) ? '  -  ' : r3(prec)}      |  ${r3(rtp / (totalRealTP || 1))} (${rtp}/${totalRealTP})`);
}
console.log(`\n  *precision here = realTP / (realTP + FALSE-trap FP + novel); theoretical excluded.`);
console.log(`  Hypothesis holds if strict precision rises with votes and high-v retains most realTP.`);
