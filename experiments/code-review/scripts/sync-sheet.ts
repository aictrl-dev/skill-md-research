#!/usr/bin/env npx tsx
/**
 * Validate a Results row and emit an MCP-ready append payload.
 *
 * The actual Sheet write is performed by the agent via the google-sheets MCP
 * (update_cells / batch_update_cells) — this script only validates + shapes.
 *
 * Usage:
 *   npx tsx sync-sheet.ts --in results-row.json [--known-hids H-001,H-002]
 * Prints: { "sheet": "Results", "values": [[ ...19 cells... ]] }
 */
import * as fs from 'node:fs';
import { validateResultsRow, toCellArray, type ResultsRow } from './schema.ts';

export interface SyncPayload {
  sheet: 'Results';
  values: (string | number)[][];
}

export function buildSyncPayload(row: ResultsRow, knownHids?: string[]): SyncPayload {
  validateResultsRow(row, knownHids ? { knownHids } : {});
  return { sheet: 'Results', values: [toCellArray(row)] };
}

// ---- CLI ----
function argMap(argv: string[]): Record<string, string> {
  const out: Record<string, string> = {};
  for (let i = 0; i < argv.length; i += 1) {
    if (argv[i].startsWith('--')) {
      out[argv[i].slice(2)] = argv[i + 1] ?? '';
      i += 1;
    }
  }
  return out;
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const a = argMap(process.argv.slice(2));
  if (!a.in) {
    console.error('sync-sheet: --in <results-row.json> is required');
    process.exit(1);
  }
  let row: ResultsRow;
  try {
    row = JSON.parse(fs.readFileSync(a.in, 'utf8')) as ResultsRow;
  } catch (err) {
    const msg = (err as NodeJS.ErrnoException).code === 'ENOENT'
      ? `sync-sheet: file not found: ${a.in}`
      : `sync-sheet: failed to parse JSON from ${a.in}: ${(err as Error).message}`;
    console.error(msg);
    process.exit(1);
  }
  const knownHids = a['known-hids'] ? a['known-hids'].split(',').map((s) => s.trim()) : undefined;
  const payload = buildSyncPayload(row, knownHids);
  console.log(JSON.stringify(payload, null, 2));
}
