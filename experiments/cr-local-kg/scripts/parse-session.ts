#!/usr/bin/env npx tsx
// Parse an `aictrl run --format json` (or opencode) session dump: extract the
// assistant's text parts, then pull findings JSON out of them.
import * as fs from 'node:fs';
import { extractFindings } from './parse-findings.ts';

/** Concatenate every string `text`/`content` field found anywhere in the dump. */
function assistantText(raw: string): string {
  const texts: string[] = [];
  const walk = (node: unknown): void => {
    if (Array.isArray(node)) { node.forEach(walk); return; }
    if (node && typeof node === 'object') {
      const o = node as Record<string, unknown>;
      if (typeof o.text === 'string') texts.push(o.text);
      else if (typeof o.content === 'string') texts.push(o.content);
      Object.values(o).forEach(walk);
    }
  };
  // dump may be one JSON object or newline-delimited JSON events
  try { walk(JSON.parse(raw)); }
  catch { raw.split('\n').forEach((l) => { try { walk(JSON.parse(l)); } catch { /* skip */ } }); }
  return texts.join('\n');
}

// CLI: parse-session.ts --session <dump> --pr <id> --out <findings.json>
const a: Record<string, string> = {};
const argv = process.argv.slice(2);
for (let i = 0; i < argv.length; i += 1) {
  if (argv[i].startsWith('--')) { a[argv[i].slice(2)] = argv[i + 1] ?? ''; i += 1; }
}
const raw = fs.readFileSync(a.session, 'utf8');
const findings = extractFindings(assistantText(raw));
fs.writeFileSync(a.out, JSON.stringify({ prNumber: Number(a.pr), findings }, null, 2));
console.error(`parse-session: ${findings.length} findings → ${a.out}`);
