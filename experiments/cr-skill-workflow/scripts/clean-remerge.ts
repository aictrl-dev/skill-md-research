#!/usr/bin/env npx tsx
/**
 * Clean re-merge — recover correct results after the shared-scratch contamination
 * bug (the union/vote merge globbed leftover findings-*.json from OTHER experiments).
 *
 * The fix needs no re-run: the harness persisted EACH node's findings separately
 * as PR-<id>.<node>.findings.json, and a node file was written fresh by THIS
 * experiment (overwriting any same-named stale file at its run time). So we just
 * re-merge ONLY the experiment's legit nodes (from its dag.yaml), ignoring the
 * stale-named per-node files the persist-loop also copied in, and overwrite the
 * final PR-<id>.findings.json.
 *
 * Usage: clean-remerge.ts --exp <exp-id> [--reps 1,2,3] [--write]
 *   (without --write it reports how many stale files it would drop, no changes)
 */
import * as fs from 'node:fs';
import * as path from 'node:path';
import { fileURLToPath } from 'node:url';
import * as yaml from 'js-yaml';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const EXP_DIR = path.resolve(HERE, '..');
const TOL = 5;
const argv = process.argv.slice(2);
const get = (f: string, d: string) => { const i = argv.indexOf(f); return i !== -1 ? argv[i + 1] : d; };
const expId = get('--exp', '');
const reps = get('--reps', '1,2,3').split(',').map(s => s.trim());
const write = argv.includes('--write');
if (!expId) { console.error('Usage: clean-remerge.ts --exp <exp-id>'); process.exit(1); }

const dag = yaml.load(fs.readFileSync(path.join(EXP_DIR, 'experiments', expId, 'dag.yaml'), 'utf8')) as any;
const legit = new Set(Object.keys(dag.nodes).filter(k => dag.nodes[k].type !== 'script'));
const output: string = dag.output;
const ln = (l: any): number | null => { if (l == null || l === '') return null; const m = String(l).match(/^(\d+)/); return m ? parseInt(m[1]) : null; };

interface F { file?: string; line?: number | string; confidence?: number; [k: string]: any }

function voteMerge(byNode: Record<string, F[]>): F[] {
  const clusters: { file: string; line: number | null; votes: Set<string>; lenses: Set<string>; rep: F; repConf: number }[] = [];
  for (const [node, fs_] of Object.entries(byNode)) {
    const lens = node.replace(/_(?:r|round)?\d+$/, '');
    for (const x of fs_) {
      if (!x.file) continue;
      const xl = ln(x.line);
      let c = clusters.find(c => c.file === x.file && (c.line == null) === (xl == null) && (c.line == null || Math.abs(c.line - xl!) <= TOL));
      if (!c) { c = { file: x.file, line: xl, votes: new Set(), lenses: new Set(), rep: x, repConf: x.confidence ?? 0 }; clusters.push(c); }
      c.votes.add(node); c.lenses.add(lens);
      if ((xl != null && c.line == null) || (x.confidence ?? 0) > c.repConf) { c.rep = x; c.repConf = x.confidence ?? 0; if (c.line == null) c.line = xl; }
    }
  }
  return clusters.map(c => ({ ...c.rep, votes: c.votes.size, nLenses: c.lenses.size }))
    .sort((a, b) => (b.votes! - a.votes!) || ((b.confidence ?? 0) - (a.confidence ?? 0)));
}
function unionMerge(byNode: Record<string, F[]>): F[] {
  const seen = new Set<string>(); const all: F[] = [];
  for (const fs_ of Object.values(byNode)) for (const x of fs_) { const k = `${x.file}:${x.line}`; if (!seen.has(k)) { seen.add(k); all.push(x); } }
  return all;
}

let prs = 0, droppedFiles = 0;
for (const rep of reps) {
  for (const sub of ['files', 'modules']) {
    const dir = path.join(EXP_DIR, 'results', expId, `rep-${rep}`, 'treatment', sub);
    if (!fs.existsSync(dir)) continue;
    const ids = new Set<string>();
    for (const f of fs.readdirSync(dir)) { const m = f.match(/^PR-(\d+)\.[a-zA-Z_0-9]+\.findings\.json$/); if (m) ids.add(m[1]); }
    for (const id of ids) {
      const byNode: Record<string, F[]> = {};
      for (const f of fs.readdirSync(dir)) {
        const m = f.match(new RegExp(`^PR-${id}\\.([a-zA-Z_0-9]+)\\.findings\\.json$`));
        if (!m) continue;
        if (!legit.has(m[1])) { droppedFiles++; continue; }   // skip stale/other-experiment nodes
        byNode[m[1]] = JSON.parse(fs.readFileSync(path.join(dir, f), 'utf8')).findings ?? [];
      }
      if (!Object.keys(byNode).length) continue;
      const merged = output === 'vote' ? voteMerge(byNode) : output === 'union' ? unionMerge(byNode) : (byNode[output] ?? []);
      prs++;
      if (write) fs.writeFileSync(path.join(dir, `PR-${id}.findings.json`), JSON.stringify({ prNumber: parseInt(id), findings: merged }, null, 2));
    }
  }
}
console.log(`${expId}: ${write ? 'REWROTE' : 'would rewrite'} ${prs} PR result(s) from ${legit.size} legit nodes (output=${output}); dropped ${droppedFiles} stale per-node files.${write ? '' : '  [dry-run; pass --write to apply]'}`);
