#!/usr/bin/env npx tsx
/**
 * Build the ENRICHED variant of a review prompt — same as the baseline but
 * with a "Prior context (from local KG)" block prepended. The block contains:
 *
 *   - Linked issues (with title + body excerpt) via PR -[FIXES|CLOSES|...]-> Issue
 *   - Prior findings on files this PR changes, INCLUDING THEIR VERDICTS, via
 *     Finding -[:ON]-> File <-[:CHANGES]- (other PRs)
 *
 * The verdicts are the recurrence-check signal: when the model sees that the
 * same finding was raised before and marked FALSE/IGNORE, it should suppress
 * the duplicate. When it was TRUE/FIX, the model should raise it again with
 * higher confidence.
 *
 * This isolates the "does context help" signal cleanly: the only difference
 * between baseline and enriched runs is this prepended block.
 *
 * Usage:
 *   npx tsx experiments/cr-loop/scripts/build-enriched-prompt.ts --pr 1788
 *
 * Writes: experiments/cr-loop/prompts/<pr>/enriched.md
 *         experiments/cr-loop/prompts/<pr>/baseline.md  (mirrors run-review's prompt)
 */

import * as fs from 'node:fs';
import * as path from 'node:path';
import { fileURLToPath } from 'node:url';
import { runQuery, closeDriver } from '../../../scripts/kg-query/neo4j.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT = path.resolve(__dirname, '..');
const DATA_DIR = path.join(ROOT, 'data');
const PROMPTS_DIR = path.join(ROOT, 'prompts');

const ORG_ID = 'cr-loop';

interface EnrichedPr {
  number: number;
  title: string;
  body: string;
  baseRefName: string;
  headRefName: string;
  additions: number;
  deletions: number;
  changedFiles: number;
  diff: string;
}

function parseArgs() {
  const args = process.argv.slice(2);
  const prIdx = args.indexOf('--pr');
  if (prIdx === -1) { console.error('Usage: build-enriched-prompt.ts --pr <number>'); process.exit(1); }
  return { pr: parseInt(args[prIdx + 1], 10) };
}

function buildBasePrompt(pr: EnrichedPr): string {
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

interface LinkedIssue {
  number: number;
  title: string;
  body: string;
  state: string;
  edgeType: string;
}

interface PriorFinding {
  prNumber: number;
  file: string;
  line: string | null;
  severity: string;
  description: string;
  verdict: string;
  action: string;
  reason: string;
}

async function fetchLinkedIssues(prFqid: string): Promise<LinkedIssue[]> {
  const rows = await runQuery<{
    number: number; title: string; body: string; state: string; edge: string;
  }>(
    `MATCH (pr:PullRequest {org_id: $orgId, fqid: $fqid})-[r]->(i:Issue)
     WHERE type(r) IN ['FIXES','CLOSES','RESOLVES','IMPLEMENTS','MENTIONS']
     RETURN i.number AS number, i.title AS title, i.body AS body, i.state AS state, type(r) AS edge`,
    { orgId: ORG_ID, fqid: prFqid },
  );
  return rows.map((r) => ({
    number: r.number,
    title: r.title,
    body: r.body,
    state: r.state,
    edgeType: r.edge,
  }));
}

async function fetchPriorFindingsOnChangedFiles(prFqid: string, currentPrNumber: number): Promise<PriorFinding[]> {
  // Files this PR changes
  const rows = await runQuery<PriorFinding>(
    `MATCH (current:PullRequest {org_id: $orgId, fqid: $fqid})-[:CHANGES]->(file:File)
     MATCH (other:PullRequest {org_id: $orgId})-[:CHANGES]->(file)
     WHERE other.number <> $currentNumber
     MATCH (f:Finding {org_id: $orgId})-[:ON]->(file)
     MATCH (f)-[:RAISED_BY]->(:Review)-[:OF]->(other)
     RETURN other.number AS prNumber, file.path AS file, f.line AS line,
            f.severity AS severity, f.description AS description,
            f.verdict AS verdict, f.action AS action, f.reason AS reason
     ORDER BY other.number DESC, file.path`,
    { orgId: ORG_ID, fqid: prFqid, currentNumber: currentPrNumber },
  );
  return rows;
}

function formatContextBlock(linked: LinkedIssue[], prior: PriorFinding[]): string {
  const lines: string[] = [
    '## Prior context (from local KG — use this to inform your review)',
    '',
  ];

  // --- Linked issues ---
  lines.push('### Linked issues');
  if (linked.length === 0) {
    lines.push('_(none — this PR does not declare a fixes/closes/implements relationship to any issue)_');
  } else {
    for (const i of linked) {
      lines.push('');
      lines.push(`**${i.edgeType}** issue #${i.number} (${i.state}) — *${i.title}*`);
      lines.push('');
      lines.push('> ' + (i.body || '_(no body)_').split('\n').slice(0, 8).join('\n> ').slice(0, 1200));
    }
  }
  lines.push('');

  // --- Prior findings on changed files ---
  lines.push('### Prior findings on the same files (cross-PR history)');
  lines.push('');
  if (prior.length === 0) {
    lines.push('_(none — no recorded findings on the files this PR changes)_');
  } else {
    lines.push('Each row is a finding raised on a previous PR for a file ALSO touched by this PR. **The `verdict` column tells you whether human reviewers confirmed it (TRUE) or rejected it as a false positive (FALSE).** When considering a similar finding for this PR, raise the bar if the same/similar issue was previously marked FALSE/IGNORE.');
    lines.push('');
    lines.push('| PR | file:line | severity | verdict | action | description |');
    lines.push('|---|---|---|---|---|---|');
    for (const p of prior.slice(0, 40)) { // cap to keep prompt size sane
      const desc = p.description.replace(/\|/g, '\\|').slice(0, 110);
      lines.push(`| #${p.prNumber} | \`${p.file}:${p.line ?? '-'}\` | ${p.severity} | **${p.verdict}** | ${p.action} | ${desc} |`);
    }
    if (prior.length > 40) lines.push('| ... | ... | ... | ... | ... | _(${prior.length - 40} more truncated)_ |');
  }
  lines.push('');
  return lines.join('\n');
}

async function main() {
  const { pr: prNumber } = parseArgs();

  const dataPath = path.join(DATA_DIR, `pr-${prNumber}.json`);
  if (!fs.existsSync(dataPath)) {
    console.error(`No enriched data for PR #${prNumber}; run enrich-pr-set.ts first`);
    process.exit(1);
  }
  const enriched = JSON.parse(fs.readFileSync(dataPath, 'utf8')) as EnrichedPr;

  const prFqid = `gh:aictrl-dev/aictrl#${prNumber}`;
  const linked = await fetchLinkedIssues(prFqid);
  const prior = await fetchPriorFindingsOnChangedFiles(prFqid, prNumber);

  const base = buildBasePrompt(enriched);
  const context = formatContextBlock(linked, prior);
  const enrichedPrompt = `${context}\n---\n\n${base}`;

  const promptDir = path.join(PROMPTS_DIR, String(prNumber));
  fs.mkdirSync(promptDir, { recursive: true });
  fs.writeFileSync(path.join(promptDir, 'baseline.md'), base);
  fs.writeFileSync(path.join(promptDir, 'enriched.md'), enrichedPrompt);

  console.log(`PR #${prNumber}`);
  console.log(`  Linked issues:  ${linked.length}`);
  console.log(`  Prior findings: ${prior.length} (on files this PR changes)`);
  console.log(`  Baseline prompt: ${base.length.toLocaleString()} chars`);
  console.log(`  Enriched prompt: ${enrichedPrompt.length.toLocaleString()} chars (+${(enrichedPrompt.length - base.length).toLocaleString()})`);
  console.log(`  Wrote: ${path.join(promptDir, 'baseline.md')}`);
  console.log(`  Wrote: ${path.join(promptDir, 'enriched.md')}`);

  await closeDriver();
}

main().catch((err) => { console.error(err); process.exit(1); });
