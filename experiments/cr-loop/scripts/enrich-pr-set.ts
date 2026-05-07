#!/usr/bin/env npx tsx
/**
 * Enrich pr-set.json with diff + bot findings + verdict labels.
 *
 * Reads experiments/cr-loop/pr-set.json (10 PR numbers). For each PR, fetches
 * via the GitHub API:
 *   - body, base/head SHA, additions, deletions, changedFiles
 *   - the diff (`gh pr diff`)
 *   - all bot reviews (github-actions[bot] + aictrl-dev[bot] structured comments)
 *   - all our /reply-to-code-review verdict comments (with JSON sidecars)
 *
 * Parses the verdict sidecars into a per-finding answer key:
 *   { (file, line, rule) → { verdict: TRUE|FALSE|UNCERTAIN, action: FIX|DEFER|IGNORE } }
 *
 * Writes enriched data to experiments/cr-loop/data/pr-<N>.json (one file per
 * PR — easier to inspect and version-control selectively) plus an aggregated
 * answer-key.json.
 *
 * Usage:
 *   npx tsx experiments/cr-loop/scripts/enrich-pr-set.ts
 *
 * Idempotent: skips PRs whose data file already exists unless --refresh.
 */

import { execFileSync } from 'node:child_process';
import * as fs from 'node:fs';
import * as path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT = path.resolve(__dirname, '..');
const DATA_DIR = path.join(ROOT, 'data');
const PR_SET_PATH = path.join(ROOT, 'pr-set.json');
const ANSWER_KEY_PATH = path.join(ROOT, 'answer-key.json');

const REFRESH = process.argv.includes('--refresh');

interface PrSpec {
  number: number;
  category: string;
  title: string;
  rationale: string;
}

interface VerdictFinding {
  bot: string;
  severity: string;
  file: string;
  line: string;
  description: string;
  reviewSha?: string;
  reviewCreated?: string;
  verdict: 'TRUE' | 'FALSE' | 'UNCERTAIN';
  action: 'FIX' | 'DEFER' | 'IGNORE';
  reason: string;
}

interface VerdictSidecar {
  sourcePR: number;
  analyzedAt: string;
  findings: VerdictFinding[];
}

interface BotComment {
  id: number;
  user: string;
  createdAt: string;
  body: string;
}

interface EnrichedPr {
  number: number;
  category: string;
  title: string;
  rationale: string;
  body: string;
  baseRefName: string;
  headRefName: string;
  baseSha: string;
  headSha: string;
  additions: number;
  deletions: number;
  changedFiles: number;
  diff: string;
  botReviews: BotComment[];
  verdicts: VerdictSidecar[];
  /** Flat answer-key for this PR — one entry per labelled finding. */
  labelled: VerdictFinding[];
}

/**
 * Run a command with execFile (no shell) — safe for unvalidated args. Used
 * for `gh` invocations where PR numbers come from a JSON file we control.
 */
function gh(args: string[]): string {
  return execFileSync('gh', args, {
    encoding: 'utf8',
    maxBuffer: 50 * 1024 * 1024,
  }).trim();
}

function fetchPrMeta(num: number) {
  const json = gh([
    'pr', 'view', String(num),
    '--repo', 'aictrl-dev/aictrl',
    '--json', 'number,title,body,baseRefName,headRefName,baseRefOid,headRefOid,additions,deletions,changedFiles,state,mergedAt',
  ]);
  return JSON.parse(json);
}

function fetchPrDiff(num: number): string {
  return gh(['pr', 'diff', String(num), '--repo', 'aictrl-dev/aictrl']);
}

/**
 * Fetch every comment on a PR — bot reviews AND human verdict responses.
 * The /reply-to-code-review skill posts verdicts as the authenticated user
 * (typically `byapparov`), so we can't filter to bots-only. The downstream
 * `isStructuredReview` and `isVerdictResponse` filters partition by body
 * shape, not author.
 */
function fetchAllComments(num: number): BotComment[] {
  const raw = gh([
    'api',
    `repos/aictrl-dev/aictrl/issues/${num}/comments`,
    '--paginate',
    '--jq',
    '[.[] | {id, user: .user.login, createdAt: .created_at, body}]',
  ]);
  return JSON.parse(raw) as BotComment[];
}

/**
 * Extract all `<!-- review-verdicts ... -->` JSON sidecars from a comment
 * body. A single comment may carry exactly one sidecar (today's format), but
 * the regex tolerates multiple in case the format evolves.
 */
function extractVerdictSidecars(body: string): VerdictSidecar[] {
  const re = /<!--\s*review-verdicts\s*\n([\s\S]*?)\n-->/g;
  const out: VerdictSidecar[] = [];
  let m: RegExpExecArray | null;
  while ((m = re.exec(body)) !== null) {
    try {
      out.push(JSON.parse(m[1]) as VerdictSidecar);
    } catch (err) {
      console.warn(`  [verdict] could not parse sidecar: ${(err as Error).message}`);
    }
  }
  return out;
}

/**
 * Filter bot comments down to ones that are STRUCTURED reviews (vs. raw
 * thinking output). Heuristic: starts with `## Code Review` and contains
 * either a finding table (`| # |`) or a severity heading (`### MAJOR` etc).
 *
 * Raw-thinking comments (which start with "Now let me dispatch...", "I'll
 * follow the code review skill procedure...", etc.) are dropped.
 */
function isStructuredReview(c: BotComment): boolean {
  const head = c.body.slice(0, 200);
  if (!head.includes('## Code Review')) return false;
  return c.body.includes('| # |') || /### (BLOCKER|MAJOR|MINOR|NIT|SECURITY|CONSISTENCY|BUG)/.test(c.body);
}

/**
 * Filter bot comments down to verdict responses we wrote via
 * /reply-to-code-review. Identified by the `## Review response` heading.
 */
function isVerdictResponse(c: BotComment): boolean {
  return c.body.startsWith('## Review response');
}

function enrichPr(spec: PrSpec): EnrichedPr {
  const meta = fetchPrMeta(spec.number);
  const diff = fetchPrDiff(spec.number);
  const allComments = fetchAllComments(spec.number);

  const botReviews = allComments.filter(isStructuredReview);
  const verdictComments = allComments.filter(isVerdictResponse);
  const verdicts = verdictComments.flatMap((c) => extractVerdictSidecars(c.body));
  const labelled = verdicts.flatMap((v) => v.findings);

  return {
    number: spec.number,
    category: spec.category,
    title: spec.title,
    rationale: spec.rationale,
    body: meta.body ?? '',
    baseRefName: meta.baseRefName,
    headRefName: meta.headRefName,
    baseSha: meta.baseRefOid,
    headSha: meta.headRefOid,
    additions: meta.additions,
    deletions: meta.deletions,
    changedFiles: meta.changedFiles,
    diff,
    botReviews,
    verdicts,
    labelled,
  };
}

function main() {
  fs.mkdirSync(DATA_DIR, { recursive: true });
  const prSet = JSON.parse(fs.readFileSync(PR_SET_PATH, 'utf8')) as { prs: PrSpec[] };

  const summary: Array<{ number: number; category: string; reviews: number; labelled: number }> = [];
  const fullAnswerKey: Record<number, VerdictFinding[]> = {};

  for (const spec of prSet.prs) {
    const dataPath = path.join(DATA_DIR, `pr-${spec.number}.json`);
    if (fs.existsSync(dataPath) && !REFRESH) {
      const cached = JSON.parse(fs.readFileSync(dataPath, 'utf8')) as EnrichedPr;
      summary.push({
        number: spec.number,
        category: spec.category,
        reviews: cached.botReviews.length,
        labelled: cached.labelled.length,
      });
      fullAnswerKey[spec.number] = cached.labelled;
      console.log(`  [cache] PR #${spec.number} (${spec.category}) — ${cached.botReviews.length} reviews, ${cached.labelled.length} labelled findings`);
      continue;
    }

    console.log(`  [fetch] PR #${spec.number} (${spec.category}) — ${spec.title.slice(0, 60)}...`);
    const enriched = enrichPr(spec);
    fs.writeFileSync(dataPath, JSON.stringify(enriched, null, 2));
    summary.push({
      number: spec.number,
      category: spec.category,
      reviews: enriched.botReviews.length,
      labelled: enriched.labelled.length,
    });
    fullAnswerKey[spec.number] = enriched.labelled;
    console.log(`    → ${enriched.botReviews.length} structured reviews, ${enriched.labelled.length} labelled findings`);
  }

  fs.writeFileSync(ANSWER_KEY_PATH, JSON.stringify(fullAnswerKey, null, 2));

  console.log('\n=== Summary ===');
  console.log(summary.map((s) => `  PR #${s.number} [${s.category}]: ${s.reviews} reviews, ${s.labelled} labelled findings`).join('\n'));
  console.log(`\n  Total labelled findings (answer key): ${Object.values(fullAnswerKey).flat().length}`);
  console.log(`  Wrote: ${ANSWER_KEY_PATH}`);
}

main();
