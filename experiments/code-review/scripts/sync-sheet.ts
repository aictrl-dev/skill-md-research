#!/usr/bin/env npx tsx
/**
 * Validate row(s) and emit MCP-ready append payloads for the Sheet.
 *
 * The actual write is performed by the agent via the google-sheets MCP
 * (update_cells / batch_update_cells) — this script only validates + shapes.
 * The agent assigns the next E-ID(s) on write.
 *
 * Usage:
 *   npx tsx sync-sheet.ts --in row.json [--breakdown-in breakdown.json] \
 *     [--known-hids H-001,H-002]
 * Prints one payload per provided input:
 *   { "sheet": "Experiments",    "values": [[ ...25 cells... ]] }
 *   { "sheet": "ClassBreakdown", "values": [[ ...12 cells... ], ...] }
 */
import * as fs from 'node:fs';
import {
  validateExperimentRow,
  validateClassBreakdownRow,
  toExperimentCellArray,
  toClassBreakdownCellArray,
  type ExperimentRow,
  type ClassBreakdownRow,
} from './schema.ts';

export interface SyncPayload {
  sheet: 'Experiments';
  values: (string | number)[][];
}

export interface ClassBreakdownPayload {
  sheet: 'ClassBreakdown';
  values: (string | number)[][];
}

export function buildSyncPayload(row: ExperimentRow, knownHids?: string[]): SyncPayload {
  validateExperimentRow(row, knownHids ? { knownHids } : {});
  return { sheet: 'Experiments', values: [toExperimentCellArray(row)] };
}

export function buildClassBreakdownPayload(
  rows: ClassBreakdownRow[],
  knownHids?: string[],
): ClassBreakdownPayload {
  rows.forEach((r) => validateClassBreakdownRow(r, knownHids ? { knownHids } : {}));
  return { sheet: 'ClassBreakdown', values: rows.map(toClassBreakdownCellArray) };
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

function readJson<T>(file: string, label: string): T {
  try {
    return JSON.parse(fs.readFileSync(file, 'utf8')) as T;
  } catch (err) {
    const msg = (err as NodeJS.ErrnoException).code === 'ENOENT'
      ? `sync-sheet: file not found: ${file}`
      : `sync-sheet: failed to parse JSON from ${file}: ${(err as Error).message}`;
    console.error(`${msg} (${label})`);
    process.exit(1);
  }
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const a = argMap(process.argv.slice(2));
  if (!a.in && !a['breakdown-in']) {
    console.error('sync-sheet: --in <row.json> and/or --breakdown-in <breakdown.json> is required');
    process.exit(1);
  }
  const knownHids = a['known-hids'] ? a['known-hids'].split(',').map((s) => s.trim()) : undefined;
  if (a.in) {
    const row = readJson<ExperimentRow>(a.in, 'experiment row');
    console.log(JSON.stringify(buildSyncPayload(row, knownHids), null, 2));
  }
  if (a['breakdown-in']) {
    const rows = readJson<ClassBreakdownRow[]>(a['breakdown-in'], 'class breakdown');
    console.log(JSON.stringify(buildClassBreakdownPayload(rows, knownHids), null, 2));
  }
}
