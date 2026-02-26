---
name: commit-style
description: Write commit messages following team conventions including gitmoji, structured body sections, DCO sign-off, and JIRA ticket references.
---

# Team Commit Style Guide

Write commit messages following the team conventions. Every commit message must be structured, concise, and informative. This guide extends Conventional Commits v1.0.0 with opinionated team rules including gitmoji, mandatory body sections, DCO sign-off, and JIRA ticket references.

## Core Structure

A commit message has three parts:

```
<type>(<scope>)[!]: <gitmoji> <description>

Why:
<motivation paragraph>

What:
<changes paragraph>

<footers>
```

## Type Prefixes

Use exactly one of these type prefixes. The type must match what the change actually does:

| Type | When to Use |
|------|-------------|
| `feat` | A new feature or capability for the user |
| `fix` | A bug fix |
| `docs` | Documentation-only changes |
| `style` | Formatting, whitespace, semicolons (no logic change) |
| `refactor` | Code restructuring without behavior change |
| `perf` | Performance improvement |
| `test` | Adding or updating tests only |
| `build` | Build system or dependency changes |
| `ci` | CI/CD configuration changes |
| `chore` | Maintenance tasks (deps, tooling) |
| `revert` | Reverting a previous commit |

## Scope Rules

Scope is REQUIRED and must come from the project's allowed vocabulary:
- Allowed scopes are defined per-project (e.g., `auth`, `api`, `db`, `ui`, `core`)
- Must be lowercase kebab-case
- Wrap in parentheses after the type: `feat(auth): ...`

Good: `feat(api)`, `fix(db)`, `docs(core)`
Bad: `feat(API)`, `fix(User Service)`, `feat` (missing scope)

## Gitmoji Convention

Every commit description starts with a gitmoji shortcode matching the type. The mapping is:

| Type | Gitmoji |
|------|---------|
| `feat` | `:sparkles:` |
| `fix` | `:bug:` |
| `docs` | `:memo:` |
| `style` | `:art:` |
| `refactor` | `:recycle:` |
| `perf` | `:zap:` |
| `test` | `:white_check_mark:` |
| `build` | `:hammer:` |
| `ci` | `:construction_worker:` |
| `chore` | `:wrench:` |
| `revert` | `:rewind:` |

Example: `fix(db): :bug: handle null record in findById`

## Breaking Change Indicator

For breaking changes, add `!` after the scope, before the colon:
```
feat(auth)!: :sparkles: replace jwt lib
```

A `BREAKING CHANGE:` footer is also required (see Footers section).

## Subject Line Rules

The subject line is `<type>(<scope>)[!]: <gitmoji> <description>`. Follow these rules:

1. **Total length**: Keep the full subject line at 50 characters or fewer
2. **Imperative mood**: Write as a command — "add feature" not "added feature" or "adding feature" or "adds feature"
3. **No trailing period**: Do not end the description with `.`
4. **Lowercase start**: Begin the description (after gitmoji) with a lowercase letter — `:sparkles: add rate limiting` not `:sparkles: Add rate limiting`

### Imperative Mood Guide

Imagine completing the sentence: "If applied, this commit will ___"

Good: "fix null pointer in findById", "add rate limiting middleware"
Bad: "fixed the bug", "adding new feature", "adds validation", "updated tests"

Words to avoid at the start of the description:
- Past tense: added, fixed, removed, updated, changed, refactored
- Gerund (-ing): adding, fixing, removing, updating, changing
- Third person: adds, fixes, removes, updates, changes

## Body Rules

### Always Required

The body is always required. It must contain exactly two section headers:

- `Why:` — explains the motivation or problem being solved
- `What:` — explains the technical changes made

### Formatting Rules

- Separate from subject with exactly one blank line
- Body must be 30-150 words total (configurable per project)
- Wrap lines at 72 characters (URLs are exempt from wrapping)

### Good Body Example

```
Why:
UserService.findById() throws a null pointer exception when
querying for a user ID that does not exist in the database.
This crashes the request handler silently.

What:
Add null check after database query and return a proper 404
response with descriptive error message instead of crashing.
```

## Footers

Footers go after the body (separated by a blank line). All footers use git-trailer `Key: value` format.

### Required Footers

Every commit must include:

1. **Ticket reference** (JIRA-style, NOT GitHub `#123`):
   ```
   Ticket: PROJ-247
   ```

2. **DCO sign-off**:
   ```
   Signed-off-by: Full Name <email>
   ```

### Conditional Footers

When the commit introduces a breaking change, include a `BREAKING CHANGE:` footer with a description of at least 10 characters:
```
BREAKING CHANGE: JWT tokens signed with jsonwebtoken are
incompatible with jose. All active sessions will be invalidated.
Users must log in again after deployment.
```

The `BREAKING CHANGE:` footer is required in addition to the `!` indicator in the subject.

## Complete Examples

### Simple Bug Fix

```
fix(db): :bug: handle null record in findById

Why:
UserService.findById() throws a null pointer exception when
querying for a user ID that does not exist in the database.
This crashes the request handler silently.

What:
Add null check after database query and return a proper 404
response with descriptive error message instead of crashing.

Ticket: PROJ-247
Signed-off-by: Alice Developer <alice@example.com>
```

### Feature with Body

```
feat(api): :sparkles: add per-IP rate limiting

Why:
The API has no protection against abuse. A single client can
make unlimited requests, potentially causing service degradation
for all users.

What:
Implement sliding window rate limiter backed by Redis. Default
config allows 100 requests per 15-minute window. Returns 429
with Retry-After header when the limit is exceeded.

Ticket: PROJ-312
Signed-off-by: Alice Developer <alice@example.com>
```

### Breaking Change

```
feat(auth)!: :sparkles: replace jwt lib

Why:
The jsonwebtoken library has known CVEs and lacks native
TypeScript types. jose is standards-compliant and provides
full TS support with zero native dependencies.

What:
Migrate all token signing from jwt.sign() to jose SignJWT
builder pattern. Verification now uses jwtVerify() with
explicit algorithm allowlist.

BREAKING CHANGE: JWT tokens signed with jsonwebtoken are
incompatible with jose. All active sessions will be
invalidated. Users must log in again after deployment.

Ticket: PROJ-189
Signed-off-by: Alice Developer <alice@example.com>
```

## Quick Checklist

Before submitting, verify:
1. Valid type prefix
2. Correct separator `: `
3. Imperative mood
4. No trailing period
5. Lowercase start (after gitmoji)
6. Scope from allowed vocabulary
7. Gitmoji after type matching the commit type
8. Body has `Why:` and `What:` sections
9. Body is 30-150 words
10. All footers use `Key: value` format
11. `Signed-off-by` footer present
12. `BREAKING CHANGE` footer (when applicable)
13. `Ticket` footer with JIRA-style reference
14. Subject line is 50 characters or fewer
