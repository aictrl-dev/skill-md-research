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
if (!expId) { console.error('Usage: score.ts --exp <exp-id>'); process.exit(1); }

const AK_PATH = path.join(EXP_DIR, 'answer-key.json');
const ak: Record<string, AKEntry[]> = JSON.parse(fs.readFileSync(AK_PATH, 'utf8'));

interface AKEntry { verdict: string; action: string; file: string; line: string; }
interface Finding { file: string; line?: number | string; }

function parseLine(l: string | number | undefined) {
  if (l == null || l === '') return null;
  const m = String(l).match(/^(\d+)(?:[-–](\d+))?$/);
  if (!m) return null;
  return { start: parseInt(m[1]), end: m[2] ? parseInt(m[2]) : parseInt(m[1]) };
}
function overlap(a: ReturnType<typeof parseLine>, b: ReturnType<typeof parseLine>) {
  if (!a || !b) return true;
  return Math.abs(a.start - b.start) <= LINE_TOL ||
    (a.start <= b.end + LINE_TOL && a.end + LINE_TOL >= b.start);
}
interface Agg { tp: number; fp: number; fn: number; novels: number; n: number; }
const blank = (): Agg => ({ tp: 0, fp: 0, fn: 0, novels: 0, n: 0 });
function prf(g: Agg) {
  const p = g.tp + g.fp === 0 ? 0 : g.tp / (g.tp + g.fp);
  const r = g.tp + g.fn === 0 ? 0 : g.tp / (g.tp + g.fn);
  return { p, r, f1: p + r === 0 ? 0 : (2 * p * r) / (p + r) };
}
const r3 = (n: number) => (Math.round(n * 1000) / 1000).toFixed(3);

function scoreFile(fullPath: string, into: Agg) {
  const data = JSON.parse(fs.readFileSync(fullPath, 'utf8')) as { prNumber?: number; findings?: Finding[] };
  const pr = String(data.prNumber ?? fullPath.match(/PR-(\d+)/)?.[1]);
  const findings: Finding[] = data.findings ?? [];
  const labels = ak[pr] ?? [];
  const usedAK = new Set<number>(), usedF = new Set<number>();
  findings.forEach((sf, i) => {
    const sfLine = parseLine(sf.line);
    const idx = labels.findIndex((lbl, j) => !usedAK.has(j) && sf.file === lbl.file && overlap(sfLine, parseLine(lbl.line)));
    if (idx === -1) return;
    usedAK.add(idx); usedF.add(i);
  });
  let tp = 0, fp = 0;
  for (const j of usedAK) {
    const v = labels[j].verdict;
    if (v === 'TRUE') tp += 1; else if (v === 'FALSE') fp += 1; else if (v === 'UNCERTAIN') tp += 0.5;
  }
  let fn = 0;
  for (let j = 0; j < labels.length; j++) {
    if (usedAK.has(j)) continue;
    const lbl = labels[j];
    if (lbl.verdict !== 'TRUE') continue;
    fn += lbl.action === 'FIX' ? 1 : 0.5;
  }
  // novels = findings that matched no answer-key entry at all. They are NOT
  // counted as FP (FP = matched-but-verdict-FALSE only), mirroring
  // score-relaxed.ts so the baseline comparison stays apples-to-apples. We track
  // them so the research loop can spot a prompt that games low FP by
  // hallucinating findings outside the answer-key's line ranges.
  const novels = findings.filter((_, i) => !usedF.has(i)).length;
  into.tp += tp; into.fp += fp; into.fn += fn; into.novels += novels; into.n += 1;
}

function scoreDir(dir: string, into: Agg) {
  if (!fs.existsSync(dir)) return;
  for (const f of fs.readdirSync(dir)) {
    if (/^PR-\d+\.findings\.json$/.test(f)) scoreFile(path.join(dir, f), into);
  }
}

const overall = blank(), byScope: Record<string, Agg> = { file: blank(), module: blank() };
for (const rep of reps) {
  for (const [scope, sub] of [['file','files'],['module','modules']] as const) {
    const dir = path.join(resultsBase, expId, `rep-${rep}`, 'treatment', sub);
    scoreDir(dir, overall);
    scoreDir(dir, byScope[scope]);
  }
}
const o = prf(overall);
console.log(`\n=== ${expId} ===`);
console.log(`  overall: P=${r3(o.p)} R=${r3(o.r)} F1=${r3(o.f1)} | TP=${overall.tp} FP=${overall.fp} FN=${overall.fn} novels=${overall.novels} n=${overall.n}`);
for (const s of ['file','module']) {
  const c = prf(byScope[s]); console.log(`  ${s}: F1=${r3(c.f1)} (n=${byScope[s].n})`);
}

// Write scores.json
const scoresPath = path.join(resultsBase, expId, 'scores.json');
fs.writeFileSync(scoresPath, JSON.stringify({ expId, reps, overall: { ...o, ...overall }, byScope: Object.fromEntries(Object.entries(byScope).map(([k,v])=>[k,{...prf(v),...v}])) }, null, 2));
console.log(`\nscores.json → ${scoresPath}`);
