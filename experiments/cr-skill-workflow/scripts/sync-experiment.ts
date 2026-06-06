#!/usr/bin/env npx tsx
/**
 * Append one experiment result row to the research tracker Google Sheet.
 * Reads scores.json produced by score.ts.
 *
 * Usage: sync-experiment.ts --exp <exp-id> [--results-base <path>]
 *
 * Columns (matching existing sheet layout):
 *   exp-id | hypothesis | F1 per-run | F1 file | F1 module | ΔF1 vs baseline | TP | FP | FN | n | notes
 *
 * Baseline (cr-local-kg treatment): per-run F1 = 0.204
 */
import * as fs from 'node:fs';
import * as path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const EXP_DIR = path.resolve(HERE, '..');
const BASELINE_F1 = 0.204;
const SHEET_ID = '1txtt4rYQULxMZQHOgOqn8TcAx5bQBPEjknRsDxIUU4Q';

const argv = process.argv.slice(2);
const get = (flag: string, def: string) => { const i = argv.indexOf(flag); return i !== -1 ? argv[i + 1] : def; };
const expId = get('--exp', '');
const resultsBase = get('--results-base', path.join(EXP_DIR, 'results'));
if (!expId) { console.error('Usage: sync-experiment.ts --exp <exp-id>'); process.exit(1); }

const scoresPath = path.join(resultsBase, expId, 'scores.json');
if (!fs.existsSync(scoresPath)) {
  console.error(`scores.json not found: ${scoresPath}\nRun score.ts first.`);
  process.exit(1);
}
const scores = JSON.parse(fs.readFileSync(scoresPath, 'utf8'));

// Try to read hypothesis from dag.yaml or SKILL.md header
let hypothesis = '';
const dagPath = path.join(EXP_DIR, 'experiments', expId, 'dag.yaml');
const skillPath = path.join(EXP_DIR, 'experiments', expId, 'skills', 'code-review', 'SKILL.md');
if (fs.existsSync(dagPath)) {
  const m = fs.readFileSync(dagPath, 'utf8').match(/hypothesis:\s*"(.+?)"/);
  if (m) hypothesis = m[1];
} else if (fs.existsSync(skillPath)) {
  const m = fs.readFileSync(skillPath, 'utf8').match(/description:\s*(.+)/);
  if (m) hypothesis = m[1].trim();
}

// scores.json now carries both full-set and real-set aggregates. The REAL set
// (user-impacting bugs only) is the headline metric; full-set is recorded too.
const realF1 = (scores.overall.real.f1 as number).toFixed(3);
const fullF1 = (scores.overall.full.f1 as number).toFixed(3);
const deltaReal = (scores.overall.real.f1 - BASELINE_F1).toFixed(3);
const unionRealF1 = (scores.union?.real?.f1 ?? 0).toFixed(3);

const row = [
  expId,
  hypothesis,
  realF1,         // headline: per-run real-set F1
  fullF1,         // per-run full-set F1
  unionRealF1,    // union-of-reps real-set F1
  deltaReal,      // ΔF1 vs 0.204 baseline (real-set)
  String(scores.overall.real.tp ?? ''),
  String(scores.overall.real.fp ?? ''),
  String(scores.overall.real.fn ?? ''),
  String(scores.overall.real.n ?? ''),
  '',
];

console.log('\nRow to append to Google Sheet:');
console.log(row.join('\t'));
console.log(`\nSheet: https://docs.google.com/spreadsheets/d/${SHEET_ID}`);
console.log('\nTo append via MCP, run this script inside a Claude session with Google Sheets MCP enabled.');
console.log('The row values above can be pasted manually if MCP is unavailable.');

// Emit MCP-ready format for use inside a Claude Code session
console.log('\n--- MCP PAYLOAD ---');
console.log(JSON.stringify({ spreadsheetId: SHEET_ID, range: 'Sheet1!A:K', values: [row] }, null, 2));
