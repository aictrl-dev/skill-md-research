#!/usr/bin/env npx tsx
/**
 * Render a prompt template: replace {{node.artefact}} placeholders with
 * JSON-serialised values from an artefacts map.
 *
 * CLI: render-template.ts --template <path> --artefacts '{"node":{"key":val}}'
 * Writes rendered text to stdout.
 *
 * Also exported as renderTemplate() for use in tests and the type-2 harness.
 */
import * as fs from 'node:fs';

export function renderTemplate(
  template: string,
  artefacts: Record<string, Record<string, unknown>>,
): string {
  return template.replace(/\{\{\s*(\w+)\.(\w+)\s*\}\}/g, (match, node, key) => {
    const val = artefacts[node]?.[key];
    if (val === undefined) return match; // leave unresolved placeholder intact
    return typeof val === 'string' ? val : JSON.stringify(val, null, 2);
  });
}

// CLI entrypoint
if (process.argv[1] === new URL(import.meta.url).pathname ||
    process.argv[1]?.endsWith('render-template.ts')) {
  const a: Record<string, string> = {};
  const argv = process.argv.slice(2);
  for (let i = 0; i < argv.length; i += 1) {
    if (argv[i].startsWith('--')) { a[argv[i].slice(2)] = argv[i + 1] ?? ''; i += 1; }
  }
  if (!a.template || !a.artefacts) {
    console.error('Usage: render-template.ts --template <path> --artefacts <json>');
    process.exit(1);
  }
  const template = fs.readFileSync(a.template, 'utf8');
  const artefacts: Record<string, Record<string, unknown>> = JSON.parse(a.artefacts);
  process.stdout.write(renderTemplate(template, artefacts));
}
