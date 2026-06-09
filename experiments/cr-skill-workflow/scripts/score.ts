#!/usr/bin/env npx tsx
/**
 * Score an experiment's results against answer-key.json.
 * Relaxed matching: file + line±5, no severity requirement.
 * Writes results/<exp-id>/scores.json and prints F1 table.
 *
 * Usage: score.ts --exp <exp-id> [--results-base <path>] [--reps 1,2,3]
 *   --exp          experiment id (e.g. exp-001-multistep-prompt)
 *   --results-base base results directory (default: ../results)
 *   --reps         comma-separated rep numbers (default: 1,2,3)
 */
import * as fs from 'node:fs';
import * as path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const EXP_DIR = path.resolve(HERE, '..');
const LINE_TOL = 5;

// ── CLI args ──
const argv = process.argv.slice(2);
const get = (flag: string, def: string) => {
  const i = argv.indexOf(flag);
  return i !== -1 ? argv[i + 1] : def;
};
const expId = get('--exp', '');
const resultsBase = get('--results-base', path.join(EXP_DIR, 'results'));
const reps = get('--reps', '1,2,3').split(',').map(s => s.trim());
// --min-confidence N drops findings with confidence < N before scoring. A
// finding with no confidence field is kept (treated as 10) so absence never
// silently filters it. Lets us precision-tune verbose panels for free.
const minConf = Number(get('--min-confidence', '0'));
// --min-votes N drops consensus-vote findings (exp-020/021) with votes < N. A
// finding with no `votes` field is kept (treated as Infinity) so this never
// filters non-vote experiments. votes = # of decorrelated resamples that
// surfaced the finding — statistical agreement, the first LOCAL precision signal.
const minVotes = Number(get('--min-votes', '0'));
// --tasks 105,201,... restricts scoring to those PR ids (for probe-subset reads).
const taskFilter = new Set(get('--tasks', '').split(',').map(s => s.trim()).filter(Boolean));
const prAllowed = (pr: string) => taskFilter.size === 0 || taskFilter.has(pr);
// --node <name> scores per-node files PR-<id>.<node>.findings.json (ablation);
// default scores the final result PR-<id>.findings.json.
const nodeName = get('--node', '');
// --novel-policy fp|ignore controls unmatched findings. The default is fp
// because precision should degrade when a workflow generates unadjudicated noise.
// Use "ignore" only to reproduce older oracle-only numbers.
const novelPolicy = get('--novel-policy', 'fp');
if (!['fp', 'ignore'].includes(novelPolicy)) {
  console.error('--novel-policy must be fp or ignore');
  process.exit(1);
}
const countNovelsAsFp = novelPolicy === 'fp';
const escapeRegExp = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
const fileRe = nodeName
  ? new RegExp(`^PR-(\\d+)\\.${escapeRegExp(nodeName)}\\.findings\\.json$`)
  : /^PR-(\d+)\.findings\.json$/;
if (!expId) { console.error('Usage: score.ts --exp <exp-id>'); process.exit(1); }

const AK_PATH = path.join(EXP_DIR, 'answer-key.json');
const ak: Record<string, AKEntry[]> = JSON.parse(fs.readFileSync(AK_PATH, 'utf8'));

interface AKEntry { verdict: string; action: string; file: string; line: string; impact?: string }
// A TRUE entry counts toward the REAL set unless explicitly tagged theoretical.
// (Untagged TRUE defaults to real, so real-set == full-set until tagging lands.)
const isRealTrue = (lbl: AKEntry) => lbl.verdict === 'TRUE' && (lbl.impact ?? 'real') === 'real';
interface Finding { file: string; line?: number | string; confidence?: number; votes?: number }

/** Apply the --min-confidence and --min-votes gates. Missing field ⇒ kept. */
function passesConf(f: Finding): boolean {
  return (f.confidence ?? 10) >= minConf && (f.votes ?? Infinity) >= minVotes;
}

function parseLine(l: string | number | undefined) {
  if (l == null || l === '') return null;
  const m = String(l).match(/^(\d+)(?:[-–](\d+))?$/);
  if (!m) return null;
  return { start: parseInt(m[1]), end: m[2] ? parseInt(m[2]) : parseInt(m[1]) };
}
function overlap(a: ReturnType<typeof parseLine>, b: ReturnType<typeof parseLine>) {
  // A null/unparsable line (e.g. a finding with no line, or a comma-list like
  // "51, 106, 142") must NOT match — otherwise such a finding would be awarded
  // a TP/FP against ANY oracle entry in the same file. Require a real overlap.
  if (!a || !b) return false;
  return Math.abs(a.start - b.start) <= LINE_TOL ||
    (a.start <= b.end + LINE_TOL && a.end + LINE_TOL >= b.start);
}
interface Agg { tp: number; fp: number; fn: number; novels: number; n: number; }
const blank = (): Agg => ({ tp: 0, fp: 0, fn: 0, novels: 0, n: 0 });
// Each scored unit yields two aggregates: full (all TRUE) and real (impact:real only).
interface Pair { full: Agg; real: Agg }
const blankPair = (): Pair => ({ full: blank(), real: blank() });
function prf(g: Agg) {
  const p = g.tp + g.fp === 0 ? 0 : g.tp / (g.tp + g.fp);
  const r = g.tp + g.fn === 0 ? 0 : g.tp / (g.tp + g.fn);
  const f1 = p + r === 0 ? 0 : (2 * p * r) / (p + r);
  // F2 weights recall 2× precision (β=2) — for code review a missed real bug
  // usually costs more than a false positive, so F2 is the decision metric.
  const f2 = (4 * p + r) === 0 ? 0 : (5 * p * r) / (4 * p + r);
  return { p, r, f1, f2 };
}
const r3 = (n: number) => (Math.round(n * 1000) / 1000).toFixed(3);

// Score one findings file against the oracle, updating BOTH aggregates.
// full set: TRUE→TP, FALSE→FP, UNCERTAIN→0.5TP; missed TRUE→FN.
// real set: only impact:real TRUE count (TP / FN); FALSE still →FP; matches to
//   theoretical/UNCERTAIN entries are excluded entirely (don't-care).
function scoreInto(prRaw: string, rawFindings: Finding[], into: Pair) {
  const pr = prRaw;
  const findings: Finding[] = rawFindings.filter(passesConf);
  const labels = ak[pr] ?? [];
  const usedAK = new Set<number>(), usedF = new Set<number>();
  findings.forEach((sf, i) => {
    const sfLine = parseLine(sf.line);
    const idx = labels.findIndex((lbl, j) => !usedAK.has(j) && sf.file === lbl.file && overlap(sfLine, parseLine(lbl.line)));
    if (idx === -1) return;
    usedAK.add(idx); usedF.add(i);
  });
  // matched entries
  for (const j of usedAK) {
    const lbl = labels[j];
    if (lbl.verdict === 'TRUE') { into.full.tp += 1; if (isRealTrue(lbl)) into.real.tp += 1; }
    else if (lbl.verdict === 'FALSE') { into.full.fp += 1; into.real.fp += 1; }
    else if (lbl.verdict === 'UNCERTAIN') { into.full.tp += 0.5; /* excluded from real */ }
  }
  // missed TRUE entries → FN
  for (let j = 0; j < labels.length; j++) {
    if (usedAK.has(j)) continue;
    const lbl = labels[j];
    if (lbl.verdict !== 'TRUE') continue;
    const w = lbl.action === 'FIX' ? 1 : 0.5;
    into.full.fn += w;
    if (isRealTrue(lbl)) into.real.fn += w;
  }
  // novels = findings matching nothing (same for both sets). In the default
  // strict-precision policy they count as FP; the raw count is still reported so
  // independently adjudicated novel TPs can later be merged into the oracle.
  const novels = findings.filter((_, i) => !usedF.has(i)).length;
  if (countNovelsAsFp) { into.full.fp += novels; into.real.fp += novels; }
  into.full.novels += novels; into.real.novels += novels;
  into.full.n += 1; into.real.n += 1;
}

function scoreFileInto(fullPath: string, into: Pair) {
  const data = JSON.parse(fs.readFileSync(fullPath, 'utf8')) as { prNumber?: number; findings?: Finding[] };
  const pr = String(data.prNumber ?? fullPath.match(/PR-(\d+)/)?.[1]);
  scoreInto(pr, data.findings ?? [], into);
}

function scoreDir(dir: string, into: Pair) {
  if (!fs.existsSync(dir)) return;
  for (const f of fs.readdirSync(dir)) {
    const m = f.match(fileRe);
    if (m && prAllowed(m[1])) scoreFileInto(path.join(dir, f), into);
  }
}

const overall = blankPair(), byScope: Record<string, Pair> = { file: blankPair(), module: blankPair() };
for (const rep of reps) {
  for (const [scope, sub] of [['file','files'],['module','modules']] as const) {
    const dir = path.join(resultsBase, expId, `rep-${rep}`, 'treatment', sub);
    scoreDir(dir, overall);
    scoreDir(dir, byScope[scope]);
  }
}
const oFull = prf(overall.full), oReal = prf(overall.real);
console.log(`\n=== ${expId} ===`);
console.log(`  novel policy: ${novelPolicy === 'fp' ? 'count as FP' : 'ignore in precision'}`);
console.log(`  FULL  per-run: P=${r3(oFull.p)} R=${r3(oFull.r)} F1=${r3(oFull.f1)} F2=${r3(oFull.f2)} | TP=${overall.full.tp} FP=${overall.full.fp} FN=${overall.full.fn} novels=${overall.full.novels} n=${overall.full.n}`);
console.log(`  REAL  per-run: P=${r3(oReal.p)} R=${r3(oReal.r)} F1=${r3(oReal.f1)} F2=${r3(oReal.f2)} | TP=${overall.real.tp} FP=${overall.real.fp} FN=${overall.real.fn}`);
for (const s of ['file','module']) {
  console.log(`  ${s}: full F1=${r3(prf(byScope[s].full).f1)}  real F1=${r3(prf(byScope[s].real).f1)} (n=${byScope[s].full.n})`);
}

// ── Union-of-reps F1 ──
// For each PR, pool findings across ALL reps, dedup on file+line overlap, score
// once. Apples-to-apples comparison against the 0.355 union-of-3 baseline.
function unionScore(): Pair {
  const byPR: Record<string, Finding[]> = {};
  for (const rep of reps) {
    for (const sub of ['files', 'modules']) {
      const dir = path.join(resultsBase, expId, `rep-${rep}`, 'treatment', sub);
      if (!fs.existsSync(dir)) continue;
      for (const f of fs.readdirSync(dir)) {
        if (!/^PR-\d+\.findings\.json$/.test(f)) continue;
        const data = JSON.parse(fs.readFileSync(path.join(dir, f), 'utf8')) as { prNumber?: number; findings?: Finding[] };
        const pr = String(data.prNumber ?? f.match(/PR-(\d+)/)?.[1]);
        if (!prAllowed(pr)) continue;
        (byPR[pr] ??= []);
        for (const sf of (data.findings ?? []).filter(passesConf)) {
          const dup = byPR[pr].some(ex => ex.file === sf.file && overlap(parseLine(ex.line), parseLine(sf.line)));
          if (!dup) byPR[pr].push(sf);
        }
      }
    }
  }
  const agg = blankPair();
  for (const [pr, findings] of Object.entries(byPR)) scoreInto(pr, findings, agg);
  return agg;
}
const u = unionScore();
const uFull = prf(u.full), uReal = prf(u.real);
console.log(`  FULL  union-of-${reps.length}: P=${r3(uFull.p)} R=${r3(uFull.r)} F1=${r3(uFull.f1)} F2=${r3(uFull.f2)} | TP=${u.full.tp} FP=${u.full.fp} FN=${u.full.fn}`);
console.log(`  REAL  union-of-${reps.length}: P=${r3(uReal.p)} R=${r3(uReal.r)} F1=${r3(uReal.f1)} F2=${r3(uReal.f2)} | TP=${u.real.tp} FP=${u.real.fp} FN=${u.real.fn}`);

// Write scores.json
const withPrf = (g: Agg) => ({ ...prf(g), ...g });
const scoresPath = path.join(resultsBase, expId, 'scores.json');
fs.writeFileSync(scoresPath, JSON.stringify({
  expId, reps, novelPolicy,
  overall: { full: withPrf(overall.full), real: withPrf(overall.real) },
  byScope: Object.fromEntries(Object.entries(byScope).map(([k,v])=>[k,{ full: withPrf(v.full), real: withPrf(v.real) }])),
  union: { full: withPrf(u.full), real: withPrf(u.real) },
}, null, 2));
console.log(`\nscores.json → ${scoresPath}`);
