#!/usr/bin/env npx tsx
/**
 * Coverage-map SCRIPT node (exp-020 coverage-guided directed resampling).
 *
 * Replaces the free-text "look elsewhere" carry-forward (exp-011) with a
 * STRUCTURED coverage map computed deterministically from every prior round's
 * findings + the source. Exposed downstream as {{coverage.context}} so the next
 * round's lens prompts can target the UNEXPLORED cells instead of re-reading the
 * whole file. No model, no AI-node budget.
 *
 * The map has five cells (per the research backlog):
 *   already_found        — file:line — [lens] title  (do NOT re-report)
 *   covered_files        — files that already have at least one finding
 *   covered_bug_classes  — lenses (security/correctness/...) already exercised
 *   unexplored_symbols   — defined functions with NO finding nearby (prioritise)
 *   unexplored_failure_modes — checklist classes not yet exercised
 *
 * CLI (called by the harness): --pr <id> --paths <csv> --pindir <dir> --artefacts <file>
 */
import * as fs from 'node:fs';
import * as path from 'node:path';

const argv = process.argv.slice(2);
const get = (f: string, d = '') => { const i = argv.indexOf(f); return i !== -1 ? argv[i + 1] : d; };
const paths = get('--paths').split(',').map(s => s.trim()).filter(Boolean);
const pinDir = get('--pindir');
const artefactsFile = get('--artefacts');

const SYMBOL_NEAR_TOL = 8;   // a symbol is "covered" if a finding sits within +/-8 lines of its definition
const MAX_FOUND = 40;        // cap the already-found list so the prompt stays compact
const MAX_SYMS = 12;

// Canonical failure-mode checklist (the lens taxonomy). Whatever is NOT yet
// covered becomes an explicit "go check this" instruction for the next round.
const FAILURE_MODES: Record<string, string> = {
  security: 'authz / injection / secret-handling / tenant-scoping defects',
  correctness: 'wrong logic, off-by-one, incorrect conditions, bad return values',
  concurrency: 'races, TOCTOU, unguarded shared state, ordering assumptions',
  validation: 'missing/incorrect input validation, unchecked external data',
  edgecases: 'empty/boundary/duplicate/overflow/time-edge inputs',
  resources: 'leaks, missing cleanup, unbounded growth, unclosed handles',
  errors: 'swallowed exceptions, missing error handling, silent failures',
};

interface Finding { file?: string; line?: number | string; title?: string }

// Extract candidate function/method names + their definition line (best-effort).
function fnDefs(src: string): { name: string; line: number }[] {
  const out: { name: string; line: number }[] = [];
  const seen = new Set<string>();
  const lines = src.split('\n');
  const patterns = [
    /(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_$][\w$]*)/,
    /(?:export\s+)?const\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?\(/,
    /^\s{2,}(?:public |private |protected )?(?:static )?(?:async )?([A-Za-z_$][\w$]*)\s*\(/,
  ];
  const skip = new Set(['if', 'for', 'while', 'switch', 'catch', 'constructor', 'return', 'function']);
  lines.forEach((ln, i) => {
    for (const re of patterns) {
      const m = re.exec(ln);
      if (m && !skip.has(m[1]) && !seen.has(m[1])) { seen.add(m[1]); out.push({ name: m[1], line: i + 1 }); }
    }
  });
  return out;
}

const toLine = (l: number | string | undefined): number | null => {
  if (l == null || l === '') return null;
  const m = String(l).match(/^(\d+)/);
  return m ? parseInt(m[1]) : null;
};

// ── Gather prior findings from the artefacts map, tagged with their lens. ──
const priorByNode: Record<string, { findings?: Finding[] }> =
  artefactsFile && fs.existsSync(artefactsFile) ? JSON.parse(fs.readFileSync(artefactsFile, 'utf8')) : {};

interface Tagged { file: string; line: number | null; title: string; lens: string }
const found: Tagged[] = [];
const coveredClasses = new Set<string>();
for (const [node, art] of Object.entries(priorByNode)) {
  const lens = node.replace(/_(?:r|round)?\d+$/, ''); // security_r1 / security_1 / security_round1 -> security
  for (const f of art?.findings ?? []) {
    if (!f.file) continue;
    found.push({ file: f.file, line: toLine(f.line), title: (f.title ?? '').slice(0, 80), lens });
    if (FAILURE_MODES[lens]) coveredClasses.add(lens);
  }
}

const coveredFiles = new Set(found.map(f => f.file));

// ── Unexplored symbols: defined functions with no finding within +/-TOL lines. ──
const unexplored: string[] = [];
for (const rel of paths) {
  let src = '';
  try { src = fs.readFileSync(path.join(pinDir, rel), 'utf8'); } catch { continue; }
  const findingLines = found.filter(f => f.file === rel && f.line != null).map(f => f.line as number);
  for (const { name, line } of fnDefs(src)) {
    const near = findingLines.some(fl => Math.abs(fl - line) <= SYMBOL_NEAR_TOL);
    if (!near) unexplored.push(`${name} (${rel}:${line})`);
  }
}

const unexploredModes = Object.entries(FAILURE_MODES)
  .filter(([k]) => !coveredClasses.has(k))
  .map(([k, v]) => `${k} — ${v}`);

// ── Emit the structured map (markdown on stdout -> {{coverage.context}}). ──
const fmt = (xs: string[], n: number) =>
  xs.length ? xs.slice(0, n).map(x => `- ${x}`).join('\n') + (xs.length > n ? `\n- ...and ${xs.length - n} more` : '') : '- (none)';

const out: string[] = [
  '## Coverage Map — focus this round ENTIRELY on the UNEXPLORED cells below',
  '',
  '### Already found (KNOWN — do NOT re-report these)',
  found.length
    ? found.slice(0, MAX_FOUND).map(f => `- ${f.file}:${f.line ?? '?'} — [${f.lens}] ${f.title}`).join('\n') +
      (found.length > MAX_FOUND ? `\n- ...and ${found.length - MAX_FOUND} more` : '')
    : '- (nothing found yet)',
  '',
  '### Files already touched',
  fmt([...coveredFiles], 20),
  '',
  '### Bug classes already exercised (de-prioritise)',
  coveredClasses.size ? `- ${[...coveredClasses].join(', ')}` : '- (none)',
  '',
  '### UNEXPLORED symbols — no finding near these yet; PRIORITISE them',
  fmt(unexplored, MAX_SYMS),
  '',
  '### UNEXPLORED failure modes — actively hunt these classes',
  unexploredModes.length ? unexploredModes.map(m => `- ${m}`).join('\n') : '- (all classes exercised — re-scan unexplored symbols above)',
  '',
];
process.stdout.write(out.join('\n') + '\n');
