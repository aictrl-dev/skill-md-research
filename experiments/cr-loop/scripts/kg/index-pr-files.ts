#!/usr/bin/env npx tsx
/**
 * Focused KG indexer for the cr-loop experiment.
 *
 * Walks .cr/pr-files.json across the 10 staged PR workspaces, collects the
 * union of changed files, then expands that set with sibling files in the
 * same directory (so the agent has a bit of context, not just the changed
 * line). Runs extractIncremental on this targeted set and inserts into Neo4j
 * with org_id='cr-loop'.
 *
 * Avoids the full-tree discoverFiles bug that walks .claude/worktrees and
 * blows up to 75k+ files.
 *
 * Usage: node --stack-size=8000 --import tsx experiments/cr-loop/scripts/index-pr-files.ts
 */
import * as fs from 'node:fs';
import * as path from 'node:path';
import neo4j from 'neo4j-driver';
import { extractIncremental, insertAll } from '../../../scripts/kg-query/graph-builder.js';
import { DEFAULT_STACK_LAYERS } from '../../../server/state/types.js';

const REPO_ROOT = path.resolve(import.meta.dirname, '..', '..', '..');
const ORG_ID = 'cr-loop';
const REPO_ID = 'aictrl-dev/aictrl';

const NEO4J_URI = process.env.NEO4J_URI ?? 'bolt://localhost:7687';
const NEO4J_USER = process.env.NEO4J_USER ?? 'neo4j';
const NEO4J_PASS = process.env.NEO4J_PASS ?? 'knowledge-graph-experiment';

interface PrFile {
  filename: string;
  status: string;
  additions: number;
  deletions: number;
  changes: number;
  patch?: string;
}

function collectChangedFiles(): Set<string> {
  const set = new Set<string>();
  const workspacesDir = path.join(REPO_ROOT, 'experiments/cr-loop/workspaces');
  for (const dir of fs.readdirSync(workspacesDir)) {
    const filesPath = path.join(workspacesDir, dir, '.cr/pr-files.json');
    if (!fs.existsSync(filesPath)) continue;
    const arr = JSON.parse(fs.readFileSync(filesPath, 'utf8')) as PrFile[];
    for (const f of arr) set.add(f.filename);
  }
  return set;
}

/**
 * Add sibling files in the same directory as each changed file. Caps siblings
 * per directory to keep the index focused and small.
 */
function expandWithSiblings(files: Set<string>, capPerDir = 30): string[] {
  const dirs = new Set<string>();
  for (const f of files) dirs.add(path.dirname(f));

  const out = new Set<string>(files);
  for (const dir of dirs) {
    const abs = path.join(REPO_ROOT, dir);
    if (!fs.existsSync(abs)) continue;
    let added = 0;
    for (const entry of fs.readdirSync(abs, { withFileTypes: true })) {
      if (added >= capPerDir) break;
      if (!entry.isFile()) continue;
      if (!/\.(ts|tsx|mts|cts)$/.test(entry.name)) continue;
      if (entry.name.endsWith('.d.ts')) continue;
      const rel = path.join(dir, entry.name);
      out.add(rel);
      added++;
    }
  }
  return [...out];
}

async function main() {
  const changed = collectChangedFiles();
  console.log(`Changed files across 10 PRs: ${changed.size}`);

  const files = expandWithSiblings(changed, 25)
    .filter((p) => /\.(ts|tsx|mts|cts|css)$/.test(p))
    .filter((p) => !p.endsWith('.d.ts'));
  console.log(`Files to index (with siblings): ${files.length}`);

  console.log('Extracting…');
  const result = extractIncremental(REPO_ROOT, files);
  console.log(
    `  extracted: files=${result.files.length} functions=${result.functions.length} ` +
    `classes=${result.classes.length} interfaces=${result.interfaces.length} ` +
    `edges=${result.edges.length}`,
  );

  console.log('Inserting into Neo4j…');
  const driver = neo4j.driver(NEO4J_URI, neo4j.auth.basic(NEO4J_USER, NEO4J_PASS));
  const session = driver.session();
  try {
    const stackLayers = DEFAULT_STACK_LAYERS.map((l) => ({
      id: l.id,
      name: l.name,
      order: l.order,
      pathPatterns: l.pathPatterns,
      categoryMapping: l.categoryMapping,
    }));
    const stats = await insertAll(
      session,
      result,
      ORG_ID,
      REPO_ID,
      undefined,
      REPO_ROOT,
      stackLayers,
      { fullName: REPO_ID, defaultBranch: 'main', provider: 'github' },
      (msg, step, total) => console.log(`  [${step}/${total}] ${msg}`),
      driver,
    );
    console.log(`Done: ${JSON.stringify(stats.totals ?? stats, null, 2)}`);
  } finally {
    await session.close();
    await driver.close();
  }
}

main().catch((err) => {
  console.error('Fatal:', err);
  process.exit(1);
});
