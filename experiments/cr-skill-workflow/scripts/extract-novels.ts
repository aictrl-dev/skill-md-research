#!/usr/bin/env npx tsx
/**
 * Extract NOVEL findings from an experiment's results: model findings that match
 * NO answer-key entry (file + line±5). These are the candidates for oracle
 * review — confirm real ones (→ add as TRUE), tag theoretical, mark not-a-bug
 * (→ add as FALSE so future hallucinations get penalised).
 *
 * Pools findings across all reps, dedups on file+line, keeps the highest-
 * confidence variant of each, and groups by PR. Writes JSON + a readable table.
 *
 * Usage: extract-novels.ts --exp <exp-id> [--reps 1,2,3] [--out <path>]
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
const outPath = get('--out', path.join(EXP_DIR, 'results', expId, 'novels.json'));
if (!expId) { console.error('Usage: extract-novels.ts --exp <exp-id>'); process.exit(1); }

const ak: Record<string, any[]> = JSON.parse(fs.readFileSync(path.join(EXP_DIR, 'answer-key.json'), 'utf8'));

interface Finding { file: string; line?: number | string; severity?: string; title?: string; description?: string; confidence?: number }

function parseLine(l: string | number | undefined) {
  if (l == null || l === '') return null;
  const m = String(l).match(/^(\d+)(?:[-–](\d+))?$/);
  if (!m) return null;
  return { start: parseInt(m[1]), end: m[2] ? parseInt(m[2]) : parseInt(m[1]) };
}
function overlap(a: ReturnType<typeof parseLine>, b: ReturnType<typeof parseLine>) {
  // null/unparsable line must NOT match (else a line-less or comma-list finding
  // would match any oracle entry in the file). Require a real overlap.
  if (!a || !b) return false;
  return Math.abs(a.start - b.start) <= LINE_TOL || (a.start <= b.end + LINE_TOL && a.end + LINE_TOL >= b.start);
}
const matchesOracle = (pr: string, f: Finding) =>
  (ak[pr] ?? []).some(lbl => lbl.file === f.file && overlap(parseLine(f.line), parseLine(lbl.line)));

// Pool + dedup findings per PR across reps (keep highest confidence per file:line)
const byPR: Record<string, Finding[]> = {};
for (const rep of reps) {
  for (const sub of ['files', 'modules']) {
    const dir = path.join(EXP_DIR, 'results', expId, `rep-${rep}`, 'treatment', sub);
    if (!fs.existsSync(dir)) continue;
    for (const fn of fs.readdirSync(dir)) {
      if (!/^PR-\d+\.findings\.json$/.test(fn)) continue;
      const data = JSON.parse(fs.readFileSync(path.join(dir, fn), 'utf8')) as { prNumber?: number; findings?: Finding[] };
      const pr = String(data.prNumber ?? fn.match(/PR-(\d+)/)?.[1]);
      (byPR[pr] ??= []);
      for (const sf of (data.findings ?? [])) {
        const ex = byPR[pr].find(e => e.file === sf.file && overlap(parseLine(e.line), parseLine(sf.line)));
        if (!ex) byPR[pr].push(sf);
        else if ((sf.confidence ?? 0) > (ex.confidence ?? 0)) Object.assign(ex, sf);
      }
    }
  }
}

const novelsByPR: Record<string, Finding[]> = {};
let total = 0;
for (const [pr, findings] of Object.entries(byPR)) {
  const novels = findings.filter(f => !matchesOracle(pr, f));
  if (novels.length) { novelsByPR[pr] = novels; total += novels.length; }
}

fs.mkdirSync(path.dirname(outPath), { recursive: true });
fs.writeFileSync(outPath, JSON.stringify({ expId, reps, total, novelsByPR }, null, 2));

console.log(`\n=== ${total} novel findings across ${Object.keys(novelsByPR).length} PRs (exp ${expId}) ===\n`);
for (const [pr, novels] of Object.entries(novelsByPR).sort((a, b) => Number(a[0]) - Number(b[0]))) {
  console.log(`PR-${pr} (${novels.length}):`);
  for (const n of novels.sort((a, b) => (parseLine(a.line)?.start ?? 0) - (parseLine(b.line)?.start ?? 0))) {
    console.log(`  L${n.line} [${n.severity ?? '?'}] ${n.title ?? ''} — ${n.description ?? ''}`);
  }
}
console.log(`\nnovels.json → ${outPath}`);
