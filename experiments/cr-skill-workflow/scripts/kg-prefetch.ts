#!/usr/bin/env npx tsx
/**
 * KG-prefetch SCRIPT node. Deterministically pulls graph context for the task's
 * source file(s) — file impact (dependents), co-changes, and per-function caller
 * counts — and prints a compact markdown block on stdout. Injected downstream as
 * {{kg_prefetch.context}}. No model, no AI-node budget.
 *
 * Caller counts are the precision signal: a finding on a 0-caller function rarely
 * matters; many callers means a real blast radius / raise severity.
 *
 * CLI (called by the harness): --pr <id> --paths <csv> --pindir <dir> [--artefacts <file>]
 */
import * as fs from 'node:fs';
import * as path from 'node:path';
import { queryContext, closeClient } from './kg-query.ts';

const argv = process.argv.slice(2);
const get = (f: string, d = '') => { const i = argv.indexOf(f); return i !== -1 ? argv[i + 1] : d; };
const paths = get('--paths').split(',').map(s => s.trim()).filter(Boolean);
const pinDir = get('--pindir');
const MAX_FNS_PER_FILE = 6;

// Extract candidate function/method names from source (best-effort, dedup, order-preserving).
function fnNames(src: string): string[] {
  const names = new Set<string>();
  const patterns = [
    /(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_$][\w$]*)/g,
    /(?:export\s+)?const\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?\(/g,
    /^\s{2,}(?:public |private |protected )?(?:async )?([A-Za-z_$][\w$]*)\s*\(/gm,
  ];
  for (const re of patterns) { let m; while ((m = re.exec(src))) names.add(m[1]); }
  ['if', 'for', 'while', 'switch', 'catch', 'constructor', 'return'].forEach(n => names.delete(n));
  return [...names];
}

const fmtList = (xs: string[], n = 8) =>
  xs.length ? xs.slice(0, n).join(', ') + (xs.length > n ? `, and ${xs.length - n} more` : '') : 'none';

(async () => {
  const out: string[] = ['## Knowledge Graph Context (pre-computed — use it to judge REAL impact)', ''];
  let calls = 0;
  for (const p of paths) {
    const abs = path.join(pinDir, p);
    if (!fs.existsSync(abs)) continue;
    const src = fs.readFileSync(abs, 'utf8');
    out.push(`### ${p}`);

    try {
      const impact: any = await queryContext('code', 'impact', p); calls++;
      const deps = (impact?.result?.directDependents ?? impact?.directDependents ?? []).map((d: any) => d.path ?? d);
      out.push(`- Dependents (blast radius): ${fmtList(deps)} — ${deps.length} file(s).`);
    } catch { out.push('- Dependents: (unavailable)'); }

    try {
      const co: any = await queryContext('code', 'co_changes', p); calls++;
      const cc = (co?.result?.coChanges ?? co?.coChanges ?? co?.result ?? []);
      const ccPaths = Array.isArray(cc) ? cc.map((x: any) => x.path ?? x.file ?? x) : [];
      out.push(`- Historically co-changes with: ${fmtList(ccPaths)} (flag if this change should touch these but does not).`);
    } catch { out.push('- Co-changes: (unavailable)'); }

    const fns = fnNames(src).slice(0, MAX_FNS_PER_FILE);
    out.push('- Function caller counts (0 callers means unused, a bug there rarely matters; many means real blast radius):');
    for (const fn of fns) {
      try {
        const c: any = await queryContext('code', 'callers', fn); calls++;
        const callers = (c?.result?.callers ?? c?.callers ?? []);
        const n = Array.isArray(callers) ? callers.length : 0;
        const where = Array.isArray(callers) ? fmtList(callers.map((x: any) => x.name ?? x.file ?? x.path ?? x.id ?? String(x)), 4) : '';
        out.push(`  - ${fn}: ${n} caller(s)${n ? ` [${where}]` : ' — UNUSED'}`);
      } catch { out.push(`  - ${fn}: (unavailable)`); }
    }
    out.push('');
  }
  out.push(`_(${calls} graph queries, deterministic.)_`);
  process.stdout.write(out.join('\n') + '\n');
  await closeClient();
})().catch(e => { process.stdout.write(`## Knowledge Graph Context\n(unavailable: ${e.message})\n`); process.exit(0); });
