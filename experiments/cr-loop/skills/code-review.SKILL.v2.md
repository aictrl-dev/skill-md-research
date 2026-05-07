---
name: code-review
description: Agent-procedure for reviewing a GitHub pull request. Fetches per-file diffs, dispatches parallel Security / Consistency / Bug-Hunter subagents, merges findings, records all data via MCP tools, and posts a PR comment via the executor output handler. Use when reviewing any PR.
tags:
  - code-review
  - quality
  - best-practices
allowedTools:
  - Read
  - Grep
  - Glob
  - Bash
  - Task
  - aictrl_query_context
  - record_review_started
  - record_finding
  - record_review_completed
version: "6.0.0"
metadata:
  stack: "all"
  phase: "review"
---

# Code Review (Agent Procedure)

You are the outer orchestrator for a code review. Follow these steps
exactly. Do not improvise. Do not read the full PR diff as a single blob.

## Output contract

**This skill does NOT produce a Markdown output artifact.**

All findings are written to the data layer via MCP tools
(`record_review_started`, `record_finding`, `record_review_completed`).
The executor output handler posts the GitHub PR comment downstream based
on findings stored in the data layer.

Subagents return JSON internally so the outer can dedup, sort, and cap.
That JSON is a private intermediate format — it MUST NOT appear in any
MCP tool call or final text output.

## Step 0 — Record review start

Before fetching the PR, call `record_review_started` with the known
context. You MUST use the env vars injected by the executor for required
IDs. Capture the returned `reviewId` — every `record_finding` call requires it.

Required env vars (provided by executor):
- `AICTRL_ORG_ID` — organization ID
- `AICTRL_EXECUTION_ID` — task execution ID (pass as `execution_run_id`)
- `AICTRL_SKILL_VERSION` — version string e.g. `code-review@6.0.0`
- `AICTRL_MODEL_FULL_PATH` — model path e.g. `zai-coding-plan/glm-5.1`
- `AICTRL_MODEL_PROVIDER` — provider e.g. `zhipuai`
- `AICTRL_MODEL_NAME` — model name e.g. `glm-5.1`

The `pr`, `sha`, `repository` values come from your Step 1 fetch (below).
Record `started_at` as the current ISO timestamp before any fetching.

```
record_review_started({
  org_id: $AICTRL_ORG_ID,
  execution_run_id: $AICTRL_EXECUTION_ID,
  repository: { full_name: "<owner/repo>", platform: "github" },
  pr: { number: <n>, url: "<pr_url>", title: "<title>",
        base_branch: "<base>", head_branch: "<head>",
        author: { username: "<login>" },
        additions: <additions>, deletions: <deletions>,
        changed_files: <changed_files> },
  sha: "<40-char head sha>",
  bot: "aictrl-dev",
  bot_metadata: { runtime: "platform-executor",
                  subagent_mix: ["Security", "Consistency", "Bug-Hunter"] },
  model: { provider: $AICTRL_MODEL_PROVIDER,
           name: $AICTRL_MODEL_NAME,
           full_path: $AICTRL_MODEL_FULL_PATH },
  skill_version: $AICTRL_SKILL_VERSION,
  review_attempt: 1,
  ingestion_source: "mcp",
  started_at: "<ISO timestamp>",
  idempotency_key: $AICTRL_EXECUTION_ID
})
→ returns { reviewId }
```

**If the MCP call fails, abort immediately** with an error message; do not
continue reviewing without a reviewId.

## Step 1 — Fetch PR metadata and per-file patches

Create a local scratch directory, then fetch metadata and GitHub's
per-file patch objects. Never run `gh pr diff <n>` without `--name-only`;
that command produces a monolithic patch and is forbidden.

```
mkdir -p .cr
gh pr view <n> --repo <owner/repo> --json number,title,body,baseRefName,headRefName,author,headRefOid > .cr/pr-meta.json
gh api "repos/<owner/repo>/pulls/<n>/files" --paginate > .cr/pr-files.json
```

`pulls/:n/files` returns an array where each element has
`{ filename, status, additions, deletions, changes, patch, sha }`.
The `patch` field is the unified diff for that file only. Binary files
come back without `patch`; skip those from review.

Note: if you called record_review_started before the Step 1 fetch you
will have needed to use placeholder values — **update the review call
with real pr/sha/repository data from the Step 1 fetch**. If you called
Step 0 after Step 1 that is fine; pass real values directly.

## Step 2 — Build concern manifests (one pass, no refinement)

Classify each file into three manifests with a single `jq` invocation
per manifest. Do not iterate on the filter — pick a reasonable rule and
commit to it.

- **Security manifest**: paths matching any of
  `auth`, `session`, `crypto`, `middleware`, `route`, `handler`,
  `login`, `token`, `secret`, `sql`, `query`, or yaml/env files that
  could carry secrets.
- **Consistency manifest**: every text file in the diff except
  lockfiles, generated files, snapshots, and binaries.
- **Bug Hunter manifest**: every source-code file (exclude `.md`,
  pure-config, fixtures).

A file may appear in multiple manifests. This is fine.

## Step 3 — Shard the Bug Hunter manifest

Bug Hunter is the long-pole concern. Compute
`S = sum of (additions + deletions)` across bug-hunter files. Pick
shard count `N`:

| S changed lines    | N bug-hunter subagents |
|--------------------|------------------------|
| S <= 1000          | 1                      |
| 1000 < S <= 3000   | 2                      |
| 3000 < S <= 8000   | 3                      |
| S > 8000           | 4                      |

Shard by top-level directory first (keeps related files together). If
a single directory exceeds the shard budget (~3000 lines or ~50 files),
split that directory alphabetically on filename. No file is split
across shards.

Security and Consistency are NOT sharded.

## Step 4 — Dispatch subagents (one turn, all parallel)

Emit `2 + N` `Task` tool calls in a **single assistant turn**. Do not
wait for any to return before launching the others. Subagents run as
leaves — they cannot spawn their own subagents.

Each Task prompt MUST contain, inline:

1. The concern name (`Security`, `Consistency`, or `Bug Hunter shard k/N`).
2. PR metadata from step 1.
3. The subagent's assigned file list with `{ filename, status,
   additions, deletions, patch }` inlined per file (pulled from
   `.cr/pr-files.json`). Do NOT pass the path to a shared patch file.
4. The concern-specific checklist (copy the relevant bullets from
   below — do not tell the subagent to read a file).
5. The subagent output contract (JSON, used internally by the outer):

   ```
   Return ONLY a JSON array. Each element:
   {
     "file": "<path in the repository>",
     "line": <integer, line number in the HEAD file>,
     "end_line": <integer, optional end line>,
     "language": "<language, e.g. 'typescript'>",
     "severity": "BLOCKER" | "MAJOR" | "MINOR" | "NIT",
     "rule_slug": "bug" | "security" | "performance" | "consistency" | "style" | "docs" | "enhancement" | "other",
     "rule_sub_slug": "<optional narrower tag>",
     "summary": "<≤60-char dashboard title>",
     "description": "<one or two sentences: what is wrong and why it matters, max 2000 chars>",
     "suggested_fix": "<concrete suggestion: code direction or replacement, optional>",
     "citation_code": "<optional: the offending line(s), ≤6 lines, no leading +/->"
   }
   If you find nothing, return [].
   ```

6. The tool rules block, verbatim:

   ```
   Tool rules:
   - You already have every patch you need inline. DO NOT run
     `gh pr diff`. DO NOT Read any file under
     `/home/executor/.local/share/aictrl/tool-output/` or
     `~/.local/share/aictrl/tool-output/`. If such a path appears,
     use Grep against it, never Read with offsets.
   - You MUST use `aictrl_query_context` to verify every finding
     before including it in the JSON array. Reach for graph actions
     FIRST, fall back to file reads only when the graph cannot answer:
       * `callers` (function blast radius) — required before flagging
         a bug on any function. If the function has 0 callers, the bug
         doesn't matter; drop or downgrade the finding.
       * `impact` (file blast radius) — required before recommending
         a rename, signature change, or removal. If many dependants,
         raise severity or DEFER as out-of-scope.
       * `co_changes` (historical coupling) — required on each changed
         file. If a tightly-coupled neighbour (test, fixture, migration)
         is not in the PR, raise a "missing update" finding.
       * `domain=issues, action=context` on each changed file — check
         whether the same finding has been raised before. If a prior
         finding with verdict FALSE/IGNORE matches your candidate,
         suppress it. If verdict TRUE/FIX matches, raise with higher
         confidence.
       * `read` / `context` / `search` only when the four graph actions
         above did not answer the question.
   - Budget: at most 25 tool calls (the 4 required graph actions per
     finding don't count against you), at most 10 minutes.
   - Return ONLY the JSON array. No prose.
   ```

### Security checklist (Security subagent prompt)

- Input validation at every trust boundary.
- Parameterized queries only; no string-concatenated SQL.
- Authn/authz checks on every new endpoint or protected handler.
- No secrets in source, logs, error messages, or test fixtures.
- Safe HTML handling: check for unsafe DOM sinks and dynamic code
  evaluation patterns.
- Redirect and CORS changes reviewed.
- Secret comparison uses constant-time helpers, not `===` / `!==`.

### Consistency checklist (Consistency subagent prompt)

- New code matches surrounding file and module conventions.
- Imports, naming, and file placement follow existing patterns.
- No dead code, no TODOs without an issue reference.
- Public API changes have matching type/OpenAPI/SDK updates.
- Error handling style matches neighbours (throw vs return).
- Functions used across files are moved to a shared module, not
  duplicated.

### Bug and breaking-change checklist (each Bug Hunter shard)

- Null/undefined safety on new code paths; optional chaining covers
  every property on the chain, not just the root.
- Off-by-one, boundary conditions, empty-input handling.
- Race conditions, idempotency, double-execution safety.
- N+1 queries, unbounded cross-tenant scans, missing pagination.
- Breaking changes: public function signatures, stored schema, wire
  formats, persisted fields, env vars.
- Migrations are forward- and backward-compatible across rollout.
- File deletions: verify no dynamic imports or string path references
  remain.

## Step 5 — Merge findings and record to data layer

After all subagents return:

1. Parse each subagent's JSON array.
2. Deduplicate findings by `(file, line, rule_slug, description)`. On a
   duplicate, keep the entry with the highest severity, and prefer the
   longer `suggested_fix` text.
3. Sort by severity descending (`BLOCKER > MAJOR > MINOR > NIT`), then
   by file, then by line ascending.
4. If more than 40 findings remain, drop `NIT` first, then `MINOR`,
   until the list is at most 40. Record the dropped count.
5. For each surviving finding, call `record_finding` once. Pass the
   `reviewId` from Step 0. Use the subagent label as `subagent` field
   (e.g. `"Security"`, `"Consistency"`, `"Bug-Hunter-1/2"`).

```
record_finding({
  review_id: <reviewId>,
  org_id: $AICTRL_ORG_ID,
  repository: { full_name: "<owner/repo>", platform: "github" },
  pr: { number: <n>, url: "<pr_url>" },
  sha: "<40-char sha>",
  bot: "aictrl-dev",
  model: { provider: $AICTRL_MODEL_PROVIDER,
           name: $AICTRL_MODEL_NAME,
           full_path: $AICTRL_MODEL_FULL_PATH },
  skill_version: $AICTRL_SKILL_VERSION,
  review_attempt: 1,
  subagent: "<Security|Consistency|Bug-Hunter-k/N>",
  file: "<repo-relative path>",
  line: <line number or omit for file-level>,
  end_line: <optional>,
  language: "<optional>",
  rule_slug: "<bug|security|performance|consistency|style|docs|enhancement|other>",
  rule_sub_slug: "<optional>",
  severity: "<BLOCKER|MAJOR|MINOR|NIT>",
  summary: "<≤60-char title>",
  description: "<what + why>",
  suggested_fix: "<optional>",
  citation_code: "<optional snippet>",
  ingestion_source: "mcp"
})
```

All `record_finding` calls may be issued in parallel (single assistant
turn). Do not wait for one to complete before issuing the next.

## Step 6 — Finalize review

Once all `record_finding` calls have completed, call
`record_review_completed` with the final metrics. Compute `duration_ms`
as the elapsed time from the `started_at` value used in Step 0.

```
record_review_completed({
  org_id: $AICTRL_ORG_ID,
  review_id: <reviewId>,
  finding_count: <total findings recorded>,
  duration_ms: <elapsed ms>
})
```

After `record_review_completed` returns, your work is done. Do not emit
any further output. The executor handles GitHub comment posting
downstream based on the data written to the data layer.

## Anti-patterns (do not do these)

- Do NOT run `gh pr diff <n>` without `--name-only`.
- Do NOT Read files under `~/.local/share/aictrl/tool-output/` — those
  are overflow spills from other tools; they are a paging trap.
- Do NOT pass a tool-output overflow path to a subagent.
- Do NOT dispatch subagents sequentially or across multiple turns.
- Do NOT refine manifest filters iteratively — commit to one rule per
  manifest.
- Do NOT let a subagent exceed 20 tool calls.
- Do NOT emit the final PR comment as a Markdown artifact. The data layer
  drives all downstream comment posting.
- Do NOT include praise, scope-expansion suggestions, or stylistic nits
  that a linter would catch (see `references/FEEDBACK.md`).
- Do NOT continue if `record_review_started` fails — abort with an error.

## Reference files

- `references/CHECKLISTS.md` — detailed review checklists by PR type
  (feature, bugfix, refactor, security, performance). Only consult
  when building subagent prompts; do not read at runtime.
- `references/FEEDBACK.md` — phrasing guidance for finding fields.
