#!/usr/bin/env npx tsx
/**
 * Run the cr-loop baseline skill against one PR via the aictrl CLI.
 *
 * Pipes the PR's title + body + diff to `aictrl run -m zai-coding-plan/glm-5.1
 * -f skill.md --format json`, captures the NDJSON output, extracts the
 * assistant's text reply, parses the trailing JSON code block for findings.
 *
 * Output: experiments/cr-loop/runs/<pr-number>/<run-id>.json with shape
 *   { prNumber, skillVersion, runId, durationMs, findings: [...], rawText }
 *
 * Run the scorer against this file separately:
 *   npx tsx scripts/score.ts --findings runs/1788/<run-id>.json
 *
 * Usage:
 *   npx tsx experiments/cr-loop/scripts/run-review.ts --pr 1788
 */

import { spawnSync } from 'node:child_process';
import * as fs from 'node:fs';
import * as path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT = path.resolve(__dirname, '..');
const DATA_DIR = path.join(ROOT, 'data');
const SKILL_PATH = path.join(ROOT, 'skill.md');
const RUNS_DIR = path.join(ROOT, 'runs');

const MODEL = process.env.CR_LOOP_MODEL ?? 'zai-coding-plan/glm-5.1';
const TIMEOUT_MS = parseInt(process.env.CR_LOOP_TIMEOUT_MS ?? `${20 * 60 * 1000}`, 10); // default 20 min, override via env

interface EnrichedPr {
  number: number;
  title: string;
  body: string;
  baseRefName: string;
  headRefName: string;
  baseSha: string;
  headSha: string;
  additions: number;
  deletions: number;
  changedFiles: number;
  diff: string;
}

interface SkillFinding {
  file: string;
  line?: number | string | null;
  severity: string;
  rule?: string;
  title?: string;
  description?: string;
}

function parseArgs() {
  const args = process.argv.slice(2);
  const prIdx = args.indexOf('--pr');
  const variantIdx = args.indexOf('--variant');
  const promptIdx = args.indexOf('--prompt');
  if (prIdx === -1) {
    console.error('Usage: run-review.ts --pr <number> [--variant baseline|enriched] [--prompt <path>]');
    process.exit(1);
  }
  return {
    pr: parseInt(args[prIdx + 1], 10),
    variant: variantIdx === -1 ? 'baseline' : args[variantIdx + 1],
    promptFile: promptIdx === -1 ? null : args[promptIdx + 1],
  };
}

function buildPrompt(pr: EnrichedPr): string {
  return [
    `# Pull Request #${pr.number}`,
    '',
    `**Title:** ${pr.title}`,
    `**Branch:** \`${pr.headRefName}\` → \`${pr.baseRefName}\``,
    `**Stats:** +${pr.additions} −${pr.deletions} across ${pr.changedFiles} file${pr.changedFiles !== 1 ? 's' : ''}`,
    '',
    '## Body',
    '',
    pr.body || '_(no body provided)_',
    '',
    '## Diff',
    '',
    '```diff',
    pr.diff,
    '```',
    '',
    'Review the diff above. Emit findings as JSON per the skill\'s output contract.',
  ].join('\n');
}

/**
 * aictrl --format json emits NDJSON event lines on stdout. We need the
 * assistant's final text content. Parse each line, accumulate text from
 * `assistant.message` events. Multiple shapes have appeared across versions;
 * be liberal in what we accept.
 */
/**
 * aictrl 0.3.x emits `{ type: 'text', part: { type: 'text', text: '...' } }`
 * events as the assistant streams text. Older shapes are kept for forward/
 * backward compatibility — the goal is to be liberal in what we accept.
 */
function extractAssistantText(ndjson: string): string {
  const out: string[] = [];
  for (const line of ndjson.split('\n')) {
    if (!line.trim()) continue;
    let evt: unknown;
    try {
      evt = JSON.parse(line);
    } catch {
      continue;
    }
    const e = evt as Record<string, unknown>;

    // aictrl 0.3.x — `text` event with nested `part.text`
    if (e.type === 'text') {
      const part = e.part as Record<string, unknown> | undefined;
      if (part && typeof part.text === 'string') out.push(part.text);
      continue;
    }

    // Older / alternative shapes
    if (e.type === 'assistant' && typeof e.text === 'string') out.push(e.text);
    else if (e.role === 'assistant' && typeof e.content === 'string') out.push(e.content);
    else if (e.role === 'assistant' && Array.isArray(e.content)) {
      for (const block of e.content) {
        const b = block as Record<string, unknown>;
        if (b.type === 'text' && typeof b.text === 'string') out.push(b.text);
      }
    }
  }
  return out.join('\n');
}

/**
 * Find the LAST fenced JSON code block in the assistant's text and parse it
 * as { findings: SkillFinding[] }. Tolerant of leading reasoning prose.
 */
function extractFindings(text: string): { findings: SkillFinding[]; raw: string | null } {
  const blocks = [...text.matchAll(/```json\s*\n([\s\S]*?)\n```/g)];
  if (blocks.length === 0) return { findings: [], raw: null };
  const raw = blocks[blocks.length - 1][1];
  try {
    const parsed = JSON.parse(raw) as { findings?: SkillFinding[] };
    return { findings: parsed.findings ?? [], raw };
  } catch (err) {
    console.warn(`  [parse] could not parse final JSON block: ${(err as Error).message}`);
    return { findings: [], raw };
  }
}

function ensureDir(p: string) {
  fs.mkdirSync(p, { recursive: true });
}

function main() {
  const { pr, variant, promptFile } = parseArgs();
  const dataPath = path.join(DATA_DIR, `pr-${pr}.json`);
  if (!fs.existsSync(dataPath)) {
    console.error(`No enriched data for PR #${pr}; run enrich-pr-set.ts first`);
    process.exit(1);
  }
  if (!fs.existsSync(SKILL_PATH)) {
    console.error(`No skill.md at ${SKILL_PATH}`);
    process.exit(1);
  }

  // If --prompt is given, use that file directly. Otherwise fall back to the
  // built-in baseline-style prompt construction. The build-enriched-prompt.ts
  // script writes both variants to prompts/<pr>/{baseline,enriched}.md.
  const enriched = JSON.parse(fs.readFileSync(dataPath, 'utf8')) as EnrichedPr;
  const prompt = promptFile
    ? fs.readFileSync(promptFile, 'utf8')
    : buildPrompt(enriched);

  const runId = `${new Date().toISOString().replace(/[:.]/g, '-')}-${variant}-${process.pid}`;
  const runDir = path.join(RUNS_DIR, String(pr));
  ensureDir(runDir);
  const runPath = path.join(runDir, `${runId}.json`);
  const ndjsonPath = path.join(runDir, `${runId}.ndjson`);
  const promptPath = path.join(runDir, `${runId}.prompt.md`);
  fs.writeFileSync(promptPath, prompt);

  console.log(`  [run] PR #${pr} via ${MODEL}, prompt size: ${prompt.length.toLocaleString()} chars`);
  const start = Date.now();
  const result = spawnSync(
    'aictrl',
    ['run', '--model', MODEL, '--format', 'json', '-f', SKILL_PATH, '--dir', ROOT],
    {
      input: prompt,
      encoding: 'utf8',
      maxBuffer: 100 * 1024 * 1024,
      timeout: TIMEOUT_MS,
    },
  );
  const durationMs = Date.now() - start;

  if (result.error) {
    console.error(`  [run] aictrl error: ${result.error.message}`);
    process.exit(1);
  }
  if (result.status !== 0) {
    console.warn(`  [run] aictrl exit ${result.status}, stderr (first 500):\n${(result.stderr ?? '').slice(0, 500)}`);
  }

  const ndjson = result.stdout ?? '';
  fs.writeFileSync(ndjsonPath, ndjson);

  const text = extractAssistantText(ndjson);
  const { findings, raw } = extractFindings(text);

  const output = {
    prNumber: pr,
    skillVersion: '0.1.0',
    variant,
    promptSource: promptFile ?? '<built-in>',
    promptSize: prompt.length,
    model: MODEL,
    runId,
    durationMs,
    findings,
    rawJsonBlock: raw,
    assistantText: text,
    stderr: (result.stderr ?? '').slice(0, 4000),
  };
  fs.writeFileSync(runPath, JSON.stringify(output, null, 2));

  console.log(
    `  [run] PR #${pr} done in ${(durationMs / 1000).toFixed(1)}s — ${findings.length} findings extracted`,
  );
  console.log(`  [run] Saved: ${runPath}`);

  // Helpful next-step hint
  console.log(`\n  Score with: npx tsx experiments/cr-loop/scripts/score.ts --findings ${runPath}`);
}

main();
