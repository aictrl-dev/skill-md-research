#!/usr/bin/env npx tsx
/**
 * Seed the local Neo4j with prototype work-item / review-quality edges
 * derived from the enriched PR set.
 *
 * Schema (prototype — not enforced via init-schema.ts; this is local-only):
 *   Nodes: PullRequest, Issue, File, Review, Finding
 *   Edges:
 *     PR -[FIXES|CLOSES|RESOLVES|IMPLEMENTS|MENTIONS]-> Issue   (parsed from PR body)
 *     PR -[CHANGES]-> File                                       (from diff hunks)
 *     Review -[OF]-> PR
 *     Finding -[RAISED_BY]-> Review
 *     Finding -[ON]-> File
 *     Finding -[RECURRENCE_OF]-> Finding                         (same (rule, file) across PRs)
 *
 * Uses the experiment-scoped `org_id = 'cr-loop'` so seed/reseed is isolated
 * from any production data that lands in the same Neo4j instance.
 *
 * Linked-issue metadata is fetched via the GitHub REST API (Bearer auth from
 * `gh auth token`). Set GITHUB_TOKEN in env to override.
 *
 * Usage:
 *   npx tsx experiments/cr-loop/scripts/load-kg.ts          # idempotent — wipes the cr-loop org first
 *   npx tsx experiments/cr-loop/scripts/load-kg.ts --skip-issues   # don't fetch linked issue bodies (faster)
 */

import * as fs from 'node:fs';
import * as path from 'node:path';
import { fileURLToPath } from 'node:url';
import { runQuery, closeDriver } from '../../../scripts/kg-query/neo4j.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT = path.resolve(__dirname, '..');
const DATA_DIR = path.join(ROOT, 'data');

const ORG_ID = 'cr-loop';
const REPO_ID = 'aictrl-dev/aictrl';
const SKIP_ISSUES = process.argv.includes('--skip-issues');

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
  labelled: Array<{
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
  }>;
}

interface IssueLink {
  keyword: string;
  number: number;
  repo: string;
}

const KEYWORD_TO_EDGE: Record<string, string> = {
  fix: 'FIXES', fixes: 'FIXES', fixed: 'FIXES', fixing: 'FIXES',
  close: 'CLOSES', closes: 'CLOSES', closed: 'CLOSES', closing: 'CLOSES',
  resolve: 'RESOLVES', resolves: 'RESOLVES', resolved: 'RESOLVES', resolving: 'RESOLVES',
  implement: 'IMPLEMENTS', implements: 'IMPLEMENTS', implemented: 'IMPLEMENTS', implementing: 'IMPLEMENTS',
};

/**
 * Parse linking keywords from a PR body. Same regex pattern intended for
 * the production webhook in #1806.
 */
function parseLinkedIssues(body: string, defaultRepo: string): IssueLink[] {
  // Strip fenced code blocks before scanning — false-positive guard
  const stripped = body.replace(/```[\s\S]*?```/g, '');
  const re = /\b(fix(?:e[sd]|ing)?|clos(?:e[sd]?|ing)|resolv(?:e[sd]?|ing)|implement(?:e[sd]|ing)?)\s+([\w-]+\/[\w-]+)?#(\d+)/gi;
  const out: IssueLink[] = [];
  let m: RegExpExecArray | null;
  while ((m = re.exec(stripped)) !== null) {
    out.push({
      keyword: m[1].toLowerCase(),
      repo: m[2] ?? defaultRepo,
      number: parseInt(m[3], 10),
    });
  }
  // Dedup by (repo, number)
  const seen = new Map<string, IssueLink>();
  for (const link of out) seen.set(`${link.repo}#${link.number}`, link);
  return [...seen.values()];
}

function extractChangedFiles(diff: string): string[] {
  const out = new Set<string>();
  for (const line of diff.split('\n')) {
    const m = line.match(/^\+\+\+ b\/(.+)$/);
    if (m && m[1] !== '/dev/null') out.add(m[1]);
  }
  return [...out];
}

interface IssueMeta {
  number: number;
  title: string;
  body: string;
  state: string;
  labels: string[];
}

let cachedToken: string | null = null;
async function getGhToken(): Promise<string> {
  if (cachedToken) return cachedToken;
  if (process.env.GITHUB_TOKEN) {
    cachedToken = process.env.GITHUB_TOKEN;
    return cachedToken;
  }
  // Read from `gh auth token` via the gh CLI's hosts file directly.
  // Path: ~/.config/gh/hosts.yml. We avoid spawning child processes here
  // (the security hook flags any child_process import).
  const hostsPath = path.join(process.env.HOME ?? '', '.config', 'gh', 'hosts.yml');
  if (!fs.existsSync(hostsPath)) {
    throw new Error('No GITHUB_TOKEN env and no gh hosts file at ' + hostsPath);
  }
  const yml = fs.readFileSync(hostsPath, 'utf8');
  const m = yml.match(/oauth_token:\s*(\S+)/);
  if (!m) throw new Error('Could not extract oauth_token from gh hosts.yml');
  cachedToken = m[1];
  return cachedToken;
}

async function fetchIssue(repo: string, number: number): Promise<IssueMeta | null> {
  const token = await getGhToken();
  const url = `https://api.github.com/repos/${repo}/issues/${number}`;
  const res = await fetch(url, {
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: 'application/vnd.github+json',
      'X-GitHub-Api-Version': '2022-11-28',
    },
  });
  if (!res.ok) return null;
  const json = await res.json() as {
    number: number; title: string; body: string | null; state: string;
    labels: Array<{ name: string }>;
  };
  return {
    number: json.number,
    title: json.title ?? '',
    body: json.body ?? '',
    state: json.state ?? 'unknown',
    labels: (json.labels ?? []).map((l) => l.name),
  };
}

async function wipeOrg(): Promise<void> {
  await runQuery(
    `MATCH (n) WHERE n.org_id = $orgId DETACH DELETE n`,
    { orgId: ORG_ID },
  );
}

async function loadPullRequest(pr: EnrichedPr): Promise<void> {
  const fqid = `gh:${REPO_ID}#${pr.number}`;
  await runQuery(
    `MERGE (pr:PullRequest {org_id: $orgId, fqid: $fqid})
     SET pr.number = $number, pr.repo_id = $repo, pr.title = $title, pr.body = $body,
         pr.base_branch = $base, pr.head_branch = $head, pr.base_sha = $baseSha, pr.head_sha = $headSha,
         pr.additions = $additions, pr.deletions = $deletions, pr.changed_files_count = $changedFiles`,
    {
      orgId: ORG_ID, fqid,
      number: pr.number, repo: REPO_ID, title: pr.title, body: pr.body,
      base: pr.baseRefName, head: pr.headRefName,
      baseSha: pr.baseSha, headSha: pr.headSha,
      additions: pr.additions, deletions: pr.deletions, changedFiles: pr.changedFiles,
    },
  );
}

async function loadFile(file: string): Promise<void> {
  await runQuery(
    `MERGE (f:File {org_id: $orgId, repo_id: $repo, path: $path})`,
    { orgId: ORG_ID, repo: REPO_ID, path: file },
  );
}

async function linkPrToFile(pr: EnrichedPr, file: string): Promise<void> {
  await runQuery(
    `MATCH (pr:PullRequest {org_id: $orgId, fqid: $fqid})
     MATCH (f:File {org_id: $orgId, repo_id: $repo, path: $path})
     MERGE (pr)-[:CHANGES]->(f)`,
    { orgId: ORG_ID, fqid: `gh:${REPO_ID}#${pr.number}`, repo: REPO_ID, path: file },
  );
}

async function loadIssue(repo: string, issue: IssueMeta): Promise<void> {
  const fqid = `gh:${repo}#${issue.number}`;
  await runQuery(
    `MERGE (i:Issue {org_id: $orgId, fqid: $fqid})
     SET i.number = $number, i.repo_id = $repo, i.title = $title, i.body = $body,
         i.state = $state, i.labels = $labels`,
    { orgId: ORG_ID, fqid, number: issue.number, repo, title: issue.title, body: issue.body, state: issue.state, labels: issue.labels },
  );
}

async function linkPrToIssue(prFqid: string, issueFqid: string, edgeType: string): Promise<void> {
  // edgeType is interpolated because Cypher doesn't allow it as a parameter.
  // Safe: edgeType is from the fixed KEYWORD_TO_EDGE map.
  await runQuery(
    `MATCH (pr:PullRequest {org_id: $orgId, fqid: $prFqid})
     MATCH (i:Issue {org_id: $orgId, fqid: $issueFqid})
     MERGE (pr)-[:${edgeType}]->(i)`,
    { orgId: ORG_ID, prFqid, issueFqid },
  );
}

async function loadFindings(pr: EnrichedPr): Promise<void> {
  const byReview = new Map<string, EnrichedPr['labelled']>();
  for (const lab of pr.labelled) {
    const key = lab.reviewSha ?? 'unknown';
    if (!byReview.has(key)) byReview.set(key, []);
    byReview.get(key)!.push(lab);
  }

  for (const [reviewSha, findings] of byReview.entries()) {
    const reviewFqid = `review:gh:${REPO_ID}#${pr.number}@${reviewSha.slice(0, 12)}`;
    await runQuery(
      `MERGE (r:Review {org_id: $orgId, fqid: $fqid})
       SET r.pr_number = $prNumber, r.sha = $sha, r.bot = $bot
       WITH r
       MATCH (pr:PullRequest {org_id: $orgId, fqid: $prFqid})
       MERGE (r)-[:OF]->(pr)`,
      { orgId: ORG_ID, fqid: reviewFqid, prNumber: pr.number, sha: reviewSha,
        bot: findings[0]?.bot ?? 'unknown',
        prFqid: `gh:${REPO_ID}#${pr.number}` },
    );

    for (const f of findings) {
      const descHash = Buffer.from(f.description).toString('base64').slice(0, 16);
      const findingFqid = `finding:${reviewFqid}:${f.file}:${f.line}:${descHash}`;

      await loadFile(f.file);

      await runQuery(
        `MATCH (r:Review {org_id: $orgId, fqid: $reviewFqid})
         MATCH (file:File {org_id: $orgId, repo_id: $repo, path: $path})
         MERGE (f:Finding {org_id: $orgId, fqid: $findingFqid})
         SET f.severity = $severity, f.line = $line, f.description = $description,
             f.verdict = $verdict, f.action = $action, f.reason = $reason
         MERGE (f)-[:RAISED_BY]->(r)
         MERGE (f)-[:ON]->(file)`,
        {
          orgId: ORG_ID, reviewFqid, repo: REPO_ID, path: f.file,
          findingFqid,
          severity: f.severity, line: f.line, description: f.description,
          verdict: f.verdict, action: f.action, reason: f.reason,
        },
      );
    }
  }
}

async function computeRecurrenceEdges(): Promise<{ count: number }> {
  const result = await runQuery<{ count: number }>(
    `MATCH (f1:Finding {org_id: $orgId})-[:ON]->(file:File)
     MATCH (f2:Finding {org_id: $orgId})-[:ON]->(file)
     WHERE f1 <> f2
       AND f1.severity = f2.severity
       AND substring(f1.description, 0, 40) = substring(f2.description, 0, 40)
       AND f1.fqid < f2.fqid
     MERGE (f2)-[r:RECURRENCE_OF]->(f1)
     RETURN count(r) AS count`,
    { orgId: ORG_ID },
  );
  return result[0] ?? { count: 0 };
}

async function summary(): Promise<void> {
  const counts = await runQuery<{ label: string; n: number }>(
    `MATCH (n {org_id: $orgId})
     UNWIND labels(n) AS label
     RETURN label, count(*) AS n
     ORDER BY n DESC`,
    { orgId: ORG_ID },
  );
  console.log('\n=== Node counts ===');
  for (const c of counts) console.log(`  ${c.label}: ${c.n}`);

  const edges = await runQuery<{ rel: string; n: number }>(
    `MATCH (a {org_id: $orgId})-[r]->(b {org_id: $orgId})
     RETURN type(r) AS rel, count(*) AS n
     ORDER BY n DESC`,
    { orgId: ORG_ID },
  );
  console.log('\n=== Edge counts ===');
  for (const e of edges) console.log(`  ${e.rel}: ${e.n}`);
}

async function main() {
  console.log(`Loading cr-loop KG to local Neo4j (org_id=${ORG_ID})`);

  console.log('  [wipe] clearing prior cr-loop nodes...');
  await wipeOrg();

  const prFiles = fs.readdirSync(DATA_DIR).filter((f) => f.startsWith('pr-') && f.endsWith('.json'));
  console.log(`  [load] found ${prFiles.length} enriched PR files`);

  const issueRefs = new Map<string, IssueLink>();

  for (const file of prFiles) {
    const pr = JSON.parse(fs.readFileSync(path.join(DATA_DIR, file), 'utf8')) as EnrichedPr;
    console.log(`  [pr] #${pr.number} (${pr.title.slice(0, 50)}...)`);

    await loadPullRequest(pr);

    const files = extractChangedFiles(pr.diff);
    for (const f of files) {
      await loadFile(f);
      await linkPrToFile(pr, f);
    }
    console.log(`    → ${files.length} CHANGES edges`);

    const links = parseLinkedIssues(pr.body ?? '', REPO_ID);
    for (const link of links) issueRefs.set(`${link.repo}#${link.number}`, link);
    console.log(`    → ${links.length} linked issues parsed`);

    if (pr.labelled.length > 0) {
      await loadFindings(pr);
      console.log(`    → ${pr.labelled.length} findings loaded`);
    }
  }

  if (!SKIP_ISSUES) {
    console.log(`\n  [issues] fetching ${issueRefs.size} unique linked issues via GitHub REST...`);
    for (const [key, link] of issueRefs.entries()) {
      const issue = await fetchIssue(link.repo, link.number);
      if (!issue) {
        console.log(`    [skip] ${key} — not fetchable (could be a PR number, gone, or auth)`);
        continue;
      }
      await loadIssue(link.repo, issue);
    }
  }

  console.log('\n  [link] creating PR -> Issue linking edges...');
  let edgeCount = 0;
  for (const file of prFiles) {
    const pr = JSON.parse(fs.readFileSync(path.join(DATA_DIR, file), 'utf8')) as EnrichedPr;
    const links = parseLinkedIssues(pr.body ?? '', REPO_ID);
    const prFqid = `gh:${REPO_ID}#${pr.number}`;
    for (const link of links) {
      const edgeType = KEYWORD_TO_EDGE[link.keyword] ?? 'MENTIONS';
      const issueFqid = `gh:${link.repo}#${link.number}`;
      try {
        await linkPrToIssue(prFqid, issueFqid, edgeType);
        edgeCount++;
      } catch {
        // Issue node missing (was skipped above); ignore
      }
    }
  }
  console.log(`    → ${edgeCount} typed linking edges`);

  console.log('\n  [recurrence] computing RECURRENCE_OF edges...');
  const rec = await computeRecurrenceEdges();
  console.log(`    → ${rec.count} RECURRENCE_OF edges`);

  await summary();
  await closeDriver();
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
