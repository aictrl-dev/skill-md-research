---
name: explore-context
description: Explore codebase structure, read source files, search code, traverse the dependency graph, and understand architecture. LOAD THIS SKILL FIRST before reading or reviewing any code — it provides the query_context tool for accessing the full repository.
tags:
  - context
  - code-access
  - mcp
allowedTools:
  - aictrl_query_context
version: "2.0.0"
---

# Explore Context

You have `query_context`, a graph-aware tool for exploring the project. It does more than `cat` and `grep`: it walks a knowledge graph that knows **who calls what, what depends on what, what historically moves together, and which findings have been raised on each file before**. If you only use it as a smarter `read`, you are wasting it.

**Default mental model: every code-touching question becomes a graph query first, a file read last.**

## Required: Pre-Recording Verification Protocol

If you are reviewing code and about to record a finding, claim a bug, or recommend a change — **run these queries first** and incorporate the results into your reasoning:

1. **Blast radius** — `query_context(domain=code, action=callers, query=<function>)` and/or `query_context(domain=code, action=impact, query=<file or entity>)`.
   - If `callers` returns 0 results on a function you're about to flag → the function is unused; the bug doesn't matter (or the finding is wrong).
   - If `impact` returns dozens of dependants on a file you're suggesting to change → escalate severity, suggest an incremental migration, or DEFER if scope explodes.

2. **Historical coupling** — `query_context(domain=code, action=co_changes, query=<file>)`.
   - If a test file always moves with the source file you're editing and the PR doesn't touch it → flag the missing test update.
   - If the file co-changes with config / migration files and the PR is "code only" → ask why.

3. **Cross-PR finding history** — `query_context(domain=issues, action=context, query=<file path>)` (or whatever your platform calls it).
   - If the same finding has been raised before on this file with verdict FALSE/IGNORE → suppress the duplicate or raise the bar.
   - If it was raised TRUE/FIX before and the same pattern is back → flag it with **higher** confidence.

You are not done with verification until at least one of (1)–(3) returns a substantive result OR you can explicitly state why none applies. Recording a finding without any graph context is a precision failure.

## Workflow patterns (use these as templates)

### Reviewing a PR — the canonical loop

```
For each changed file F:
  1. context(F)              # what does this file do?
  2. impact(F)               # what depends on it? (blast radius)
  3. co_changes(F)           # what tests/fixtures usually move with it?

For each changed function G:
  4. callers(G)              # who depends on this signature?

Before recording finding X on file F:
  5. query domain=issues for prior findings on F   # cross-PR history
  6. read(F, start_line, end_line) ONLY if 1-5 left an open question
```

### Refactoring a function

1. `callers` on the function → know who calls it
2. `impact` on the containing file → know the broader blast radius
3. `co_changes` on the file → spot tests/fixtures that always move with it
4. `skeleton` on the candidate edit set → confirm signatures
5. `read` only the lines you need to change

### Scoping unfamiliar code

1. `search` for the entry symbol
2. `deps` outgoing to see what it pulls in
3. `impact` to see what depends on it
4. `traverse` with `IMPLEMENTS` / `EXTENDS` for inheritance shape

## Code-domain actions — quick reference

| Situation | Action | When to reach for it |
|-----------|--------|---------------------|
| Function blast radius | **`callers`** | Every PR review, before recording any finding on a function |
| File blast radius | **`impact`** | Every PR review, before recording any finding on a file |
| Tests/fixtures coupling | **`co_changes`** | Every PR review, to flag missing test updates |
| Multi-hop graph walk | **`traverse`** | Inheritance shape, custom edge filters |
| Outgoing dependencies | **`deps`** | Refactor scoping, "what does this need" |
| File summary | `context` | Before reading a file in full |
| Signatures only | `skeleton` | Confirming surface before refactor |
| Find by name | `search` | Last-resort symbol lookup |
| Raw source | `read` | Only after graph queries narrowed the scope |

The bold rows are the ones you should reach for **first** on any review or refactor task. The non-bold rows are narrowing helpers.

### callers — who calls this function

```json
{ "domain": "code", "action": "callers", "query": "launchExecution" }
```

Find all callers of a function via CALLS edges. Accepts a bare name or qualified id (`server/services/task-executor.ts::launchExecution`).
**Use this every time you are about to record a bug-class finding on a function** — it tells you the blast radius before you commit the claim. If the function has zero callers, the bug doesn't matter.

If the graph has no direct edges yet (e.g. extractor coverage gap), the response falls back to file-level reverse imports — treat that as a hint, not a complete list.

### impact — what depends on this entity

```json
{ "domain": "code", "action": "impact", "query": "server/state/interface.ts" }
```

Reverse-dependency / blast-radius query. Accepts a file path or entity name (`IStateManager`). Walks transitively up to `params.depth` (default 2, max 4).
**Use this when scoping a refactor or removing dead code** — `impact` answers *"what breaks if I change this?"* directly. A finding that recommends "rename X" without an `impact` query is incomplete.

### co_changes — historical coupling

```json
{ "domain": "code", "action": "co_changes", "query": "server/services/task-executor.ts" }
```

Files that historically change together with this one (commit-level coupling). Adds a temporal dimension that grep cannot reach: a file may not import another but may always be edited alongside it.
**Use this on every PR review** to catch tests / fixtures that always travel with the code under review. If `co_changes` shows a strong neighbour the PR doesn't touch, that's a missing-update finding.

### traverse — custom graph walk

```json
{
  "domain": "code",
  "action": "traverse",
  "query": "IStateManager",
  "params": {
    "direction": "incoming",
    "edge_types": ["IMPLEMENTS"],
    "max_hops": 1
  }
}
```

Arbitrary multi-hop traversal filtered by `edge_types`, `node_types`, `direction` (`outgoing` / `incoming` / `both`), and `max_hops` (1–4). Replaces chaining `impact` + `callers` + `deps` for flexible exploration. Available edges include `IMPORTS`, `CALLS`, `EXTENDS`, `IMPLEMENTS`, `CONTAINS`, `CO_CHANGES`. Reach for `traverse` when the canned actions don't fit — e.g. "all classes implementing interfaces with 'Manager' in the name".

### deps — what does this file import

```json
{ "domain": "code", "action": "deps", "query": "server/mcp/tools/features.ts" }
```

Full dependency tree for a file. `params.direction` accepts `imports` (default), `importedBy`, or `both`. `params.depth` controls hops (default 2, max 4). Use this to understand a module's surface before refactoring.

### context — file summary

```json
{ "domain": "code", "action": "context", "query": "server/api/skills-routes.ts" }
```

Returns a file's imports, exports, and definitions. Use this to understand a file's role without reading every line. For PR review: cheaper than `read`, denser than `search`.

### skeleton — signatures only

```json
{ "domain": "code", "action": "skeleton", "query": "server/services/task-executor.ts" }
```

Token-efficient overview of file structure (~85–90% fewer tokens than full content). Pass an array via `params.files` to skeleton up to 10 files in one call.

### read — full source (last resort)

```json
{ "domain": "code", "action": "read", "query": "server/state/types.ts" }
```

Returns full file contents. Use `params.start_line` / `params.end_line` for ranges.
**`read` is the most expensive action.** Prefer `context` or `skeleton` first. Only `read` when the graph queries above have narrowed the question to specific lines.

### search — find by name (last resort)

```json
{ "domain": "code", "action": "search", "query": "TaskExecutor" }
```

Case-insensitive substring match across files, functions, classes, interfaces, type aliases. Use `params.type` to filter (`file`, `function`, `class`, `interface`, `type`).
**`search` is a last-resort lookup**, not a workflow tool. If you find yourself reaching for `search` repeatedly, you are using `query_context` as a grep — pivot to `callers` / `impact` instead.

### batch_context — many files at once

```json
{ "domain": "code", "action": "batch_context", "params": { "files": ["a.ts", "b.ts", "c.ts"] } }
```

Compact summary per file plus inter-file connections. Designed for the post-`plan` workflow — ~65–75% fewer tokens than calling `context` repeatedly and avoids round-trips.

### plan — task → candidate files

```json
{ "domain": "code", "action": "plan", "query": "add rate limiting to MCP tool execution" }
```

Given a task description, queries the graph and returns candidate files to modify. Useful as a starting point on unfamiliar code, then narrow with `skeleton` / `context`.

## Cross-PR finding history (`domain=issues`)

The graph also stores findings raised on prior PRs and their human verdicts (TRUE/FIX, FALSE/IGNORE, etc.). **Before recording a finding, check whether the same pattern has been raised before on the same file.**

```json
{ "domain": "issues", "action": "context", "query": "ui/src/utils/formatDuration.ts" }
```

If the response includes a finding with the same shape and **verdict=FALSE/IGNORE**, suppress your duplicate. The bar to raise a finding that has been previously rejected is higher than the bar to raise a fresh one.

If the response includes the same shape with **verdict=TRUE/FIX**, raise it again with higher confidence — recurrence is itself a signal.

## Budget guidance

Graph queries are cheap; full file reads are not. A reasonable session budget on a single review:

- **Minimum 2 graph queries per finding** (one blast-radius, one cross-PR check) before recording it
- ~10–15 `callers` / `impact` / `co_changes` / `context` queries per PR
- ~3–5 `read` calls, scoped with `start_line` / `end_line` where possible

If you find yourself reaching for `read` or `search` before you've run a single `callers` / `impact` / `co_changes` query on the changed entity, **stop**. Pick the right graph action first.
