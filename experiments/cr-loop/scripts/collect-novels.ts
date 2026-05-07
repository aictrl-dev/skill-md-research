#!/usr/bin/env npx tsx
/**
 * Walk findings.json across phases A/B/D/E, find findings that don't match
 * any entry in answer-key.json (the "novels"), deduplicate by
 * (file, normalized-description), and dump them as a single triage list.
 *
 * Output: experiments/cr-loop/novels-to-triage.json
 *   [
 *     { id, file, line, severity, title, description, foundIn: ['A','B','E'] }
 *   ]
 *
 * Usage: npx tsx experiments/cr-loop/scripts/collect-novels.ts
 */
import * as fs from 'node:fs';
import * as path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT = path.resolve(__dirname, '..');

const PHASES: Array<{ id: string; dir: string }> = [
  { id: 'A', dir: 'runs-prod' },
  { id: 'B', dir: 'runs-prod-b' },
  { id: 'D', dir: 'runs-prod-d' },
  { id: 'E', dir: 'runs-prod-e' },
];

interface AKEntry {
  bot: string;
  severity: string;
  file: string;
  line: string;
  description: string;
  verdict: string;
  action: string;
  reason: string;
}

interface Finding {
  file: string;
  line?: number | string | null;
  severity: string;
  title?: string;
  description?: string;
}

interface FindingsFile {
  prNumber: number;
  findings: Finding[];
}

const AK_PATH = path.join(ROOT, 'answer-key.json');
const ak = JSON.parse(fs.readFileSync(AK_PATH, 'utf8')) as Record<string, AKEntry[]>;

function normalize(s: string): string {
  return s.toLowerCase().replace(/[^a-z0-9]+/g, ' ').replace(/\s+/g, ' ').trim();
}

function sharedTokens(a: string, b: string): number {
  const setA = new Set(normalize(a).split(' ').filter((w) => w.length > 3));
  const setB = new Set(normalize(b).split(' ').filter((w) => w.length > 3));
  let n = 0;
  for (const w of setA) if (setB.has(w)) n++;
  return n;
}

function matchesAK(pr: number, f: Finding, akEntries: AKEntry[]): boolean {
  if (!akEntries) return false;
  const fLine = f.line == null ? null : (typeof f.line === 'number' ? f.line : parseInt(f.line as string, 10));
  for (const ak of akEntries) {
    if (ak.file !== f.file) continue;
    const akLine = ak.line ? parseInt(ak.line, 10) : null;
    const lineMatch = akLine == null || fLine == null || Math.abs(fLine - akLine) <= 5;
    if (!lineMatch) continue;
    const desc = (f.description || f.title || '');
    const tokens = sharedTokens(desc, ak.description);
    if (tokens >= 2) return true;
  }
  return false;
}

interface Novel {
  id: string;
  prNumber: number;
  file: string;
  line: string | null;
  severity: string;
  title: string;
  description: string;
  foundIn: Set<string>;
}

const novels = new Map<string, Novel>();

for (const phase of PHASES) {
  const dir = path.join(ROOT, phase.dir);
  if (!fs.existsSync(dir)) continue;
  for (const prDir of fs.readdirSync(dir)) {
    const ff = fs.readdirSync(path.join(dir, prDir)).find((n) => n.endsWith('.findings.json'));
    if (!ff) continue;
    const data = JSON.parse(fs.readFileSync(path.join(dir, prDir, ff), 'utf8')) as FindingsFile;
    const prNum = data.prNumber;
    const akEntries = ak[String(prNum)] ?? [];
    for (const f of data.findings) {
      if (matchesAK(prNum, f, akEntries)) continue;
      const desc = f.description || f.title || '';
      const sig = `${prNum}:${f.file}:${normalize(desc).slice(0, 60)}`;
      const existing = novels.get(sig);
      if (existing) {
        existing.foundIn.add(phase.id);
      } else {
        novels.set(sig, {
          id: sig,
          prNumber: prNum,
          file: f.file,
          line: f.line == null ? null : String(f.line),
          severity: f.severity,
          title: f.title || '',
          description: desc,
          foundIn: new Set([phase.id]),
        });
      }
    }
  }
}

const out = [...novels.values()]
  .map((n) => ({ ...n, foundIn: [...n.foundIn].sort() }))
  .sort((a, b) => {
    if (a.prNumber !== b.prNumber) return a.prNumber - b.prNumber;
    if (a.file !== b.file) return a.file.localeCompare(b.file);
    return 0;
  });

const outPath = path.join(ROOT, 'novels-to-triage.json');
fs.writeFileSync(outPath, JSON.stringify(out, null, 2));

console.log(`Wrote ${out.length} unique novel findings to ${outPath}`);

// Per-PR breakdown
const byPr = new Map<number, number>();
for (const n of out) byPr.set(n.prNumber, (byPr.get(n.prNumber) ?? 0) + 1);
console.log('\nPer-PR breakdown:');
for (const [pr, n] of [...byPr.entries()].sort((a, b) => a[0] - b[0])) {
  console.log(`  PR #${pr}: ${n} novels`);
}

// Phase coverage breakdown
const phaseCount: Record<string, number> = {};
for (const n of out) {
  const key = n.foundIn.join('+');
  phaseCount[key] = (phaseCount[key] ?? 0) + 1;
}
console.log('\nFound in phases:');
for (const [k, v] of Object.entries(phaseCount).sort((a, b) => b[1] - a[1])) {
  console.log(`  ${k}: ${v}`);
}
