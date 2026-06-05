# cr-local-kg Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Measure whether the local model `gemma4:12b-96k` (via ollama) reviews current `aictrl_main` files better **with** the aictrl Knowledge-Graph MCP than **without** it, scored as F1 against a frozen, KG-neutral gold answer key.

**Architecture:** Reuse kg-ab-test's opencode config toggle (control = no MCP, treatment = remote `aictrl.dev` MCP) as the only difference between conditions. The reviewer prompt, model, tasks, and reps are held constant. Findings are emitted as JSON, scored per task by cr-loop's `score()`, and rolled up into Google-Sheet Results rows by the `experiments/code-review` framework's `aggregate.ts`/`sync-sheet.ts`. Gold labels come once from a Claude oracle run with MCP **off**, plus manual triage.

**Tech Stack:** ollama (`gemma4:12b-96k`), opencode (1.14.x) headless `run --format json`, TypeScript via `npx tsx`, `claude` CLI (oracle), `gh`/`git` worktree, google-sheets MCP (in-session).

---

## File Structure

All new files live under `experiments/cr-local-kg/` unless noted.

| Path | Responsibility |
|---|---|
| `README.md` | how-to for this experiment |
| `opencode-control.json` | ollama provider, **no** `mcp` block |
| `opencode-treatment.json` | identical + `mcp.aictrl` (aictrl.dev, Bearer) |
| `prompts/review.md` | self-contained reviewer prompt + findings-JSON contract |
| `tasks/tasks.json` | task registry: `{id, class, title, paths[]}` + pinned commit |
| `scripts/build-prompt.ts` | task → full prompt string (review.md + inlined file contents) |
| `scripts/parse-findings.ts` | opencode JSON output → `{prNumber, findings[]}` (TDD) |
| `scripts/run-condition.sh` | run opencode over tasks for one condition×rep → findings files |
| `scripts/oracle-candidates.sh` | `claude` (no MCP) over tasks → `gold/candidates/<id>.json` |
| `scripts/compile-answer-key.ts` | triaged candidates → `answer-key.json` (TDD) |
| `scripts/score-sweep.sh` | call framework `aggregate.ts` per class×condition×rep |
| `gold/candidates/<id>.json` | raw oracle findings (pre-triage) |
| `gold/triaged/<id>.json` | candidates + human `verdict`/`action`/`reason` |
| `answer-key.json` | frozen compiled gold |
| `results/raw/rep-{1,2,3}/{control,treatment}/{files,modules}/PR-<id>.findings.json` | per-task findings |
| `analysis/report.md` | final write-up |

Reused as-is (not modified): `experiments/cr-loop/scripts/score.ts`, `experiments/code-review/scripts/{aggregate,sync-sheet,schema}.ts`, `experiments/kg-ab-test/opencode-treatment.json` (token source).

**Naming contract (load-bearing — keep identical across all tasks):**
- Task id: integer. Single-file tasks `101..`, module tasks `201..`.
- Findings file: `PR-<id>.findings.json`, content `{ "prNumber": <id>, "findings": [...] }`.
- Finding object: `{ file, line, severity, title, description }`, `severity ∈ {CRITICAL,HIGH,MEDIUM,LOW}`.
- Answer key: `answer-key.json` = `{ "<id>": AnswerKeyEntry[] }`, `AnswerKeyEntry = { bot, severity, file, line, description, verdict, action, reason }`, `verdict ∈ {TRUE,FALSE,UNCERTAIN}`, `action ∈ {FIX,DEFER,IGNORE}`.

---

## Task 1: Scaffold + pin aictrl_main

**Files:**
- Create: `experiments/cr-local-kg/.gitignore`
- Create: `experiments/cr-local-kg/tasks/tasks.json` (pin only, tasks added in Task 9)

- [ ] **Step 1: Create the experiment tree**

```bash
cd /home/bulat/code/skill-md-research
mkdir -p experiments/cr-local-kg/{prompts,tasks,scripts,gold/candidates,gold/triaged,analysis}
mkdir -p experiments/cr-local-kg/results/raw
```

- [ ] **Step 2: Pin aictrl_main at its current commit via a worktree**

The user's `../aictrl_main` is on a detached HEAD; freeze that exact commit into an isolated worktree so runs never disturb their checkout.

```bash
PIN=$(git -C ../aictrl_main rev-parse HEAD)
echo "pin=$PIN"
git -C ../aictrl_main worktree add -d ../aictrl_main-cr-pin "$PIN"
ls ../aictrl_main-cr-pin/package.json   # sanity: the repo is there
```
Expected: prints a 40-char commit and lists `package.json`.

- [ ] **Step 3: Record the pin + ignore heavy/secret artifacts**

```bash
cat > experiments/cr-local-kg/tasks/tasks.json <<EOF
{
  "repo": "aictrl-dev/aictrl",
  "pinCommit": "$PIN",
  "pinDir": "../aictrl_main-cr-pin",
  "tasks": []
}
EOF

cat > experiments/cr-local-kg/.gitignore <<'EOF'
results/raw/**/*.jsonl
EOF
```

- [ ] **Step 4: Commit**

```bash
git add experiments/cr-local-kg/.gitignore experiments/cr-local-kg/tasks/tasks.json
git commit -m "feat(cr-local-kg): scaffold experiment + pin aictrl_main commit"
```

---

## Task 2: opencode → ollama provider, both condition configs

**Files:**
- Create: `experiments/cr-local-kg/opencode-control.json`
- Create: `experiments/cr-local-kg/opencode-treatment.json`

- [ ] **Step 1: Write the control config (ollama provider, no MCP)**

```json
{
  "$schema": "https://opencode.ai/config.json",
  "provider": {
    "ollama": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "Ollama (local)",
      "options": { "baseURL": "http://localhost:11434/v1" },
      "models": {
        "gemma4:12b-96k": {
          "name": "Gemma4 12B 96k",
          "options": { "temperature": 0.7 }
        }
      }
    }
  },
  "mcp": {}
}
```

- [ ] **Step 2: Write the treatment config (same provider + aictrl MCP)**

Copy the control config and add the `mcp` block (token reused from `experiments/kg-ab-test/opencode-treatment.json`):

```json
{
  "$schema": "https://opencode.ai/config.json",
  "provider": {
    "ollama": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "Ollama (local)",
      "options": { "baseURL": "http://localhost:11434/v1" },
      "models": {
        "gemma4:12b-96k": {
          "name": "Gemma4 12B 96k",
          "options": { "temperature": 0.7 }
        }
      }
    }
  },
  "mcp": {
    "aictrl": {
      "type": "remote",
      "url": "https://aictrl.dev/aictrl/mcp",
      "enabled": true,
      "timeout": 10000,
      "headers": {
        "Authorization": "Bearer 4b3bd42f7b664e5918292d38d47911203412344a4f9859fbc630aeaadb2f00e3"
      }
    }
  }
}
```

- [ ] **Step 3: Smoke — opencode can drive ollama (control)**

```bash
cd experiments/cr-local-kg
OPENCODE_CONFIG="$PWD/opencode-control.json" \
  opencode run --format json --model ollama/gemma4:12b-96k \
  --title cr-smoke "Reply with exactly the word: OK" | tee /tmp/cr-smoke.json
```
Expected: valid JSON session output containing an assistant message with `OK`.
**If the provider syntax is rejected** by opencode 1.14.50, adjust the `provider` block to the version's documented ollama/openai-compatible shape (`opencode --help`, `~/.config/opencode/opencode.json` for reference) until this prints `OK`, then update both config files identically.

- [ ] **Step 4: Commit**

```bash
git add experiments/cr-local-kg/opencode-control.json experiments/cr-local-kg/opencode-treatment.json
git commit -m "feat(cr-local-kg): opencode ollama provider + control/treatment configs"
```

---

## Task 3: Smoke the treatment MCP path (the core-bet gate)

This is risk #1 from the spec: a 12B local model may not call MCP tools. Prove it does **before** building anything else.

**Files:** none (verification only)

- [ ] **Step 1: Confirm opencode exposes the aictrl MCP tools to the model**

```bash
cd experiments/cr-local-kg
OPENCODE_CONFIG="$PWD/opencode-treatment.json" \
  opencode run --format json --model ollama/gemma4:12b-96k --dir ../../../aictrl_main-cr-pin \
  --title cr-mcp-smoke \
  "List the MCP tools you have available, then call query_context to search the code for 'OrgService' and summarise one result." \
  > /tmp/cr-mcp-smoke.json 2>&1
```

- [ ] **Step 2: Verify a tool call actually happened**

```bash
grep -o 'query_context\|aictrl' /tmp/cr-mcp-smoke.json | sort | uniq -c
grep -c '"tool"\|tool_call\|toolInvocation' /tmp/cr-mcp-smoke.json
```
Expected: at least one tool invocation referencing the aictrl MCP, and a non-empty `query_context` result summarised in the final message.

- [ ] **Step 3: Decision gate (record outcome in `analysis/report.md` under "Feasibility")**

- **Tools called + real results** → proceed to Task 4.
- **Model ignores tools** → before proceeding, strengthen `prompts/review.md` tool wording (cr-loop showed prompt wording is the dominant lever) and re-run Steps 1–2. If still no tool use after a focused attempt, **stop and report**: the headline finding may be "gemma4:12b is too small to exploit the KG via opencode/ollama tool-calling." Capture the evidence either way.

```bash
mkdir -p experiments/cr-local-kg/analysis
# create analysis/report.md with a "## Feasibility" section recording the smoke outcome
git add experiments/cr-local-kg/analysis/report.md
git commit -m "docs(cr-local-kg): record MCP tool-calling feasibility smoke result"
```

---

## Task 4: Reviewer prompt + prompt builder (TDD)

**Files:**
- Create: `experiments/cr-local-kg/prompts/review.md`
- Create: `experiments/cr-local-kg/scripts/build-prompt.ts`
- Test: `experiments/cr-local-kg/scripts/build-prompt.test.ts`

- [ ] **Step 1: Write `prompts/review.md` (one prompt, used by both conditions)**

```markdown
You are a senior code reviewer. Review the code below for **real, specific**
defects: correctness bugs, security issues, data-loss/races, and clear
maintainability problems. Do NOT report style nits or speculative concerns.

You SHOULD use any available context tools (e.g. `query_context` for callers,
impact, co-changes, search, prior findings, linked issues) to check how the
code is used elsewhere before deciding whether something is a real defect.
If no such tools are available, review from the code shown alone.

For every issue, give the file, the line (a single number or `start-end`), a
severity, a short title, and a one-sentence description.

Output ONLY your findings as a single fenced JSON block, nothing else:

```json
[
  { "file": "src/x.ts", "line": 42, "severity": "HIGH",
    "title": "…", "description": "…" }
]
```

`severity` must be one of: CRITICAL, HIGH, MEDIUM, LOW.
If you find no defects, output `[]`.
```

- [ ] **Step 2: Write the failing test for `build-prompt.ts`**

```typescript
// experiments/cr-local-kg/scripts/build-prompt.test.ts
import { test } from 'node:test';
import assert from 'node:assert/strict';
import * as fs from 'node:fs';
import * as os from 'node:os';
import * as path from 'node:path';
import { buildPrompt } from './build-prompt.ts';

test('buildPrompt inlines review.md, each path, and file contents', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'cr-bp-'));
  fs.mkdirSync(path.join(dir, 'src'), { recursive: true });
  fs.writeFileSync(path.join(dir, 'src/a.ts'), 'export const a = 1;\n');
  fs.writeFileSync(path.join(dir, 'src/b.ts'), 'export const b = 2;\n');
  const reviewMd = '# REVIEW INSTRUCTIONS MARKER';

  const out = buildPrompt(reviewMd, dir, ['src/a.ts', 'src/b.ts']);

  assert.ok(out.includes('REVIEW INSTRUCTIONS MARKER'), 'includes review.md');
  assert.ok(out.includes('src/a.ts') && out.includes('src/b.ts'), 'names both paths');
  assert.ok(out.includes('export const a = 1;'), 'inlines a.ts contents');
  assert.ok(out.includes('export const b = 2;'), 'inlines b.ts contents');
});

test('buildPrompt throws with the offending path when a file is missing', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'cr-bp-'));
  assert.throws(() => buildPrompt('x', dir, ['nope.ts']), /nope\.ts/);
});
```

- [ ] **Step 3: Run the test, verify it fails**

Run: `cd experiments/cr-local-kg && npx tsx --test scripts/build-prompt.test.ts`
Expected: FAIL — `Cannot find module './build-prompt.ts'`.

- [ ] **Step 4: Implement `build-prompt.ts`**

```typescript
// experiments/cr-local-kg/scripts/build-prompt.ts
import * as fs from 'node:fs';
import * as path from 'node:path';

/** Build the full reviewer prompt for a task: instructions + each file inlined. */
export function buildPrompt(reviewMd: string, repoDir: string, paths: string[]): string {
  const blocks = paths.map((p) => {
    const full = path.join(repoDir, p);
    if (!fs.existsSync(full)) {
      throw new Error(`build-prompt: file not found in repo: ${p}`);
    }
    const content = fs.readFileSync(full, 'utf8');
    return `\n--- FILE: ${p} ---\n\`\`\`\n${content}\n\`\`\`\n`;
  });
  return `${reviewMd}\n\n# CODE UNDER REVIEW\n${blocks.join('\n')}`;
}

// CLI: build-prompt.ts --repo <dir> --paths a.ts,b.ts [--review prompts/review.md]
if (import.meta.url === `file://${process.argv[1]}`) {
  const a: Record<string, string> = {};
  const argv = process.argv.slice(2);
  for (let i = 0; i < argv.length; i += 1) {
    if (argv[i].startsWith('--')) { a[argv[i].slice(2)] = argv[i + 1] ?? ''; i += 1; }
  }
  const reviewPath = a.review ?? new URL('../prompts/review.md', import.meta.url).pathname;
  const reviewMd = fs.readFileSync(reviewPath, 'utf8');
  process.stdout.write(buildPrompt(reviewMd, a.repo, a.paths.split(',')));
}
```

- [ ] **Step 5: Run the test, verify it passes**

Run: `cd experiments/cr-local-kg && npx tsx --test scripts/build-prompt.test.ts`
Expected: PASS (2 tests).

- [ ] **Step 6: Commit**

```bash
git add experiments/cr-local-kg/prompts/review.md experiments/cr-local-kg/scripts/build-prompt.ts experiments/cr-local-kg/scripts/build-prompt.test.ts
git commit -m "feat(cr-local-kg): reviewer prompt + build-prompt builder (TDD)"
```

---

## Task 5: Findings parser (TDD)

`opencode run --format json` emits a session object; we need the assistant's
final text, then the findings JSON inside it. Small local models emit messy
output, so the parser is tolerant: it scans for the **last** JSON array (in a
fence or bare) and falls back to `[]`.

**Files:**
- Create: `experiments/cr-local-kg/scripts/parse-findings.ts`
- Test: `experiments/cr-local-kg/scripts/parse-findings.test.ts`

- [ ] **Step 1: Write the failing test**

```typescript
// experiments/cr-local-kg/scripts/parse-findings.test.ts
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { extractFindings } from './parse-findings.ts';

test('extracts a fenced json array from prose', () => {
  const txt = 'Here are my findings:\n```json\n[{"file":"a.ts","line":3,"severity":"HIGH","title":"t","description":"d"}]\n```\nDone.';
  const f = extractFindings(txt);
  assert.equal(f.length, 1);
  assert.equal(f[0].file, 'a.ts');
  assert.equal(f[0].severity, 'HIGH');
});

test('picks the LAST json array when several are present', () => {
  const txt = '```json\n[]\n```\nactually:\n```json\n[{"file":"b.ts","line":1,"severity":"LOW","title":"x","description":"y"}]\n```';
  const f = extractFindings(txt);
  assert.equal(f.length, 1);
  assert.equal(f[0].file, 'b.ts');
});

test('returns [] when there is no parseable array', () => {
  assert.deepEqual(extractFindings('no findings, looks good'), []);
});

test('drops entries missing file or severity (tolerant)', () => {
  const txt = '```json\n[{"line":1},{"file":"c.ts","severity":"MEDIUM","title":"t","description":"d"}]\n```';
  const f = extractFindings(txt);
  assert.equal(f.length, 1);
  assert.equal(f[0].file, 'c.ts');
});
```

- [ ] **Step 2: Run the test, verify it fails**

Run: `cd experiments/cr-local-kg && npx tsx --test scripts/parse-findings.test.ts`
Expected: FAIL — `Cannot find module './parse-findings.ts'`.

- [ ] **Step 3: Implement `parse-findings.ts`**

```typescript
// experiments/cr-local-kg/scripts/parse-findings.ts
import * as fs from 'node:fs';
import type { SkillFinding } from '../../cr-loop/scripts/score.ts';

/** Find every top-level JSON array substring in `text`, last first. */
function candidateArrays(text: string): string[] {
  const out: string[] = [];
  for (let i = 0; i < text.length; i += 1) {
    if (text[i] !== '[') continue;
    let depth = 0;
    for (let j = i; j < text.length; j += 1) {
      if (text[j] === '[') depth += 1;
      else if (text[j] === ']') {
        depth -= 1;
        if (depth === 0) { out.push(text.slice(i, j + 1)); break; }
      }
    }
  }
  return out.reverse(); // last array first
}

function isFinding(x: unknown): x is SkillFinding {
  return !!x && typeof x === 'object'
    && typeof (x as Record<string, unknown>).file === 'string'
    && typeof (x as Record<string, unknown>).severity === 'string';
}

/** Tolerantly extract a findings array from a model's free-text answer. */
export function extractFindings(text: string): SkillFinding[] {
  for (const chunk of candidateArrays(text)) {
    try {
      const parsed = JSON.parse(chunk);
      if (Array.isArray(parsed)) {
        const findings = parsed.filter(isFinding);
        // accept this array if it parsed (even if empty after filtering)
        if (parsed.length === 0 || findings.length > 0) return findings;
      }
    } catch { /* not valid JSON, keep scanning */ }
  }
  return [];
}

/** Pull the assistant's final text out of an opencode --format json session. */
export function finalAssistantText(sessionJson: string): string {
  let data: unknown;
  try { data = JSON.parse(sessionJson); } catch { return sessionJson; }
  // opencode shapes vary by version; collect any string 'text'/'content' fields
  // from assistant messages and return the concatenation (last wins for parsing).
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
  walk(data);
  return texts.join('\n');
}

// CLI: parse-findings.ts --session <opencode.json> --pr <id> --out <findings.json>
if (import.meta.url === `file://${process.argv[1]}`) {
  const a: Record<string, string> = {};
  const argv = process.argv.slice(2);
  for (let i = 0; i < argv.length; i += 1) {
    if (argv[i].startsWith('--')) { a[argv[i].slice(2)] = argv[i + 1] ?? ''; i += 1; }
  }
  const raw = fs.readFileSync(a.session, 'utf8');
  const findings = extractFindings(finalAssistantText(raw));
  const payload = { prNumber: Number(a.pr), findings };
  fs.writeFileSync(a.out, JSON.stringify(payload, null, 2));
  console.error(`parse-findings: ${findings.length} findings → ${a.out}`);
}
```

- [ ] **Step 4: Run the test, verify it passes**

Run: `cd experiments/cr-local-kg && npx tsx --test scripts/parse-findings.test.ts`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add experiments/cr-local-kg/scripts/parse-findings.ts experiments/cr-local-kg/scripts/parse-findings.test.ts
git commit -m "feat(cr-local-kg): tolerant opencode-output findings parser (TDD)"
```

---

## Task 6: Condition runner

**Files:**
- Create: `experiments/cr-local-kg/scripts/run-condition.sh`

- [ ] **Step 1: Write `run-condition.sh`**

```bash
#!/usr/bin/env bash
set -euo pipefail
# Run gemma over every task for ONE condition × ONE rep, emit per-task findings.
# Usage: run-condition.sh --condition control|treatment --rep 1
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXP_DIR="$(dirname "$SCRIPT_DIR")"
MODEL="ollama/gemma4:12b-96k"

COND=""; REP=""
while [[ $# -gt 0 ]]; do case $1 in
  --condition) COND="$2"; shift 2;;
  --rep) REP="$2"; shift 2;;
  *) echo "unknown arg $1"; exit 1;;
esac; done
[[ -n "$COND" && -n "$REP" ]] || { echo "need --condition and --rep"; exit 1; }

CONFIG="$EXP_DIR/opencode-${COND}.json"
PIN_DIR="$(npx tsx -e 'console.log(JSON.parse(require("fs").readFileSync(process.argv[1])).pinDir)' "$EXP_DIR/tasks/tasks.json")"
PIN_DIR="$(cd "$EXP_DIR" && cd "$PIN_DIR" && pwd)"

# Iterate tasks via tsx (reads tasks.json, prints "id<TAB>class<TAB>paths,csv")
npx tsx -e '
  const t = JSON.parse(require("fs").readFileSync(process.argv[1]));
  for (const x of t.tasks) console.log([x.id, x.class, x.paths.join(",")].join("\t"));
' "$EXP_DIR/tasks/tasks.json" | while IFS=$'\t' read -r ID CLASS PATHS; do
  OUT_DIR="$EXP_DIR/results/raw/rep-${REP}/${COND}/${CLASS}s"
  mkdir -p "$OUT_DIR"
  echo "[$(date +%H:%M:%S)] task=$ID class=$CLASS cond=$COND rep=$REP"
  PROMPT="$(npx tsx "$SCRIPT_DIR/build-prompt.ts" --repo "$PIN_DIR" --paths "$PATHS")"
  OPENCODE_CONFIG="$CONFIG" opencode run --format json --model "$MODEL" \
    --dir "$PIN_DIR" --title "cr-${COND}-${REP}-${ID}" "$PROMPT" \
    > "$OUT_DIR/PR-${ID}.session.json" 2>&1 || true
  npx tsx "$SCRIPT_DIR/parse-findings.ts" \
    --session "$OUT_DIR/PR-${ID}.session.json" --pr "$ID" \
    --out "$OUT_DIR/PR-${ID}.findings.json"
  # hygiene: reviewer must not mutate the pinned tree
  git -C "$PIN_DIR" checkout -- . 2>/dev/null || true
  git -C "$PIN_DIR" clean -fdq 2>/dev/null || true
done
echo "done: $COND rep $REP"
```

- [ ] **Step 2: Make it executable + commit**

```bash
chmod +x experiments/cr-local-kg/scripts/run-condition.sh
git add experiments/cr-local-kg/scripts/run-condition.sh
git commit -m "feat(cr-local-kg): condition runner (opencode → findings per task)"
```

---

## Task 7: End-to-end smoke (2 files + 1 module, 1 rep)

Prove the whole chain works on a tiny set **before** curating gold or running the full sweep.

**Files:**
- Temporarily edit: `experiments/cr-local-kg/tasks/tasks.json` (3 smoke tasks)

- [ ] **Step 1: Add 3 smoke tasks**

Pick 2 small real files + 1 tiny 2-file module from `../aictrl_main-cr-pin` (use `git -C ../aictrl_main-cr-pin ls-files 'src/**/*.ts' | head`). Set `tasks` in `tasks/tasks.json`, e.g.:

```json
"tasks": [
  { "id": 101, "class": "file",   "title": "smoke file A", "paths": ["src/<realA>.ts"] },
  { "id": 102, "class": "file",   "title": "smoke file B", "paths": ["src/<realB>.ts"] },
  { "id": 201, "class": "module", "title": "smoke module",  "paths": ["src/<svc>.ts","src/<repo>.ts"] }
]
```

- [ ] **Step 2: Run both conditions for rep 1**

```bash
cd experiments/cr-local-kg
./scripts/run-condition.sh --condition control --rep 1
./scripts/run-condition.sh --condition treatment --rep 1
```
Expected: `PR-101/102.findings.json` under `results/raw/rep-1/control/files/`, `PR-201.findings.json` under `…/control/modules/`, and the same under `treatment/`.

- [ ] **Step 3: Verify findings parse and are well-formed**

```bash
for f in results/raw/rep-1/*/*/PR-*.findings.json; do
  echo "$f"; npx tsx -e 'const d=require(process.argv[1]); if(typeof d.prNumber!=="number"||!Array.isArray(d.findings)) throw new Error("bad shape: "+process.argv[1]); console.log("  prNumber",d.prNumber,"findings",d.findings.length)' "$PWD/$f";
done
```
Expected: every file has a numeric `prNumber` and a `findings` array (possibly empty); no throws.

- [ ] **Step 4: Verify scorer runs against a throwaway key**

```bash
echo '{"101":[]}' > /tmp/cr-smoke-key.json
CR_LOOP_ANSWER_KEY=/tmp/cr-smoke-key.json \
  npx tsx ../cr-loop/scripts/score.ts --findings results/raw/rep-1/control/files/PR-101.findings.json --pr 101
```
Expected: a `ScoreResult` JSON prints (F1 = 0 against the empty key is fine — we're proving the pipe, not the score).

- [ ] **Step 5: Reset smoke tasks (don't commit smoke ids)**

Revert `tasks/tasks.json` `tasks` back to `[]` (real tasks land in Task 9). Delete smoke outputs:

```bash
rm -rf experiments/cr-local-kg/results/raw/rep-1
git checkout -- experiments/cr-local-kg/tasks/tasks.json 2>/dev/null || true
```

- [ ] **Step 6: Commit the smoke confirmation (note in report)**

Append an "E2E smoke: PASS" line under `analysis/report.md` "Feasibility" and commit.

```bash
git add experiments/cr-local-kg/analysis/report.md
git commit -m "docs(cr-local-kg): e2e smoke passed (runner → parser → scorer)"
```

---

## Task 8: Select the real task set

**Files:**
- Modify: `experiments/cr-local-kg/tasks/tasks.json`

- [ ] **Step 1: Choose ~15 single files + ~5 modules**

Selection rules (record the rationale per task in its `title`):
- **Single files (`class:"file"`, ids 101–115):** real `.ts` files of moderate size (~50–300 lines) spanning services, repos, route handlers, utils.
- **Modules (`class:"module"`, ids 201–205):** small related sets (route→service→repo, or a feature folder) chosen for **KG-visible coupling** — files whose callers/impact/co-changes live in *other* files, so treatment has cross-file work. Confirm coupling exists:

```bash
# example: does this file have callers the graph would know about?
grep -rl "FunctionExportedFromTaskFile" ../aictrl_main-cr-pin/src | head
```

- [ ] **Step 2: Write all tasks into `tasks.json`** (keep `repo`/`pinCommit`/`pinDir`)

- [ ] **Step 3: Validate the task file shape**

```bash
cd experiments/cr-local-kg
npx tsx -e '
  const t=JSON.parse(require("fs").readFileSync("tasks/tasks.json"));
  const ids=new Set(); let files=0,mods=0;
  for(const x of t.tasks){
    if(ids.has(x.id)) throw new Error("dup id "+x.id); ids.add(x.id);
    if(!["file","module"].includes(x.class)) throw new Error("bad class "+x.id);
    if(!Array.isArray(x.paths)||!x.paths.length) throw new Error("no paths "+x.id);
    for(const p of x.paths) if(!require("fs").existsSync(t.pinDir+"/"+p)) throw new Error("missing "+p);
    x.class==="file"?files++:mods++;
  }
  console.log("ok",t.tasks.length,"tasks:",files,"files,",mods,"modules");
'
```
Expected: `ok 20 tasks: 15 files, 5 modules` (counts may vary slightly).

- [ ] **Step 4: Commit**

```bash
git add experiments/cr-local-kg/tasks/tasks.json
git commit -m "feat(cr-local-kg): select 15 file + 5 module review tasks (pinned)"
```

---

## Task 9: Oracle candidate generation (KG-off)

**Files:**
- Create: `experiments/cr-local-kg/scripts/oracle-candidates.sh`

- [ ] **Step 1: Write `oracle-candidates.sh`**

Runs the `claude` CLI with **no MCP** (KG-neutral) over each task, reusing the same `build-prompt.ts` so the oracle sees exactly what the reviewer sees.

```bash
#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXP_DIR="$(dirname "$SCRIPT_DIR")"
PIN_DIR="$(cd "$EXP_DIR" && cd "$(npx tsx -e 'console.log(JSON.parse(require("fs").readFileSync(process.argv[1])).pinDir)' "$EXP_DIR/tasks/tasks.json")" && pwd)"
mkdir -p "$EXP_DIR/gold/candidates"

npx tsx -e '
  const t=JSON.parse(require("fs").readFileSync(process.argv[1]));
  for(const x of t.tasks) console.log([x.id,x.paths.join(",")].join("\t"));
' "$EXP_DIR/tasks/tasks.json" | while IFS=$'\t' read -r ID PATHS; do
  echo "[oracle] task $ID"
  PROMPT="$(npx tsx "$SCRIPT_DIR/build-prompt.ts" --repo "$PIN_DIR" --paths "$PATHS")"
  # claude CLI, no MCP, non-interactive single-shot
  printf '%s' "$PROMPT" | claude -p --output-format text \
    > "$EXP_DIR/gold/candidates/${ID}.txt" 2>&1 || true
  # reuse the tolerant parser to normalise the oracle's findings JSON
  npx tsx "$SCRIPT_DIR/parse-findings.ts" \
    --session "$EXP_DIR/gold/candidates/${ID}.txt" --pr "$ID" \
    --out "$EXP_DIR/gold/candidates/${ID}.json"
done
echo "oracle candidates done → gold/candidates/"
```

- [ ] **Step 2: Run it**

```bash
chmod +x experiments/cr-local-kg/scripts/oracle-candidates.sh
cd experiments/cr-local-kg && ./scripts/oracle-candidates.sh
```
Expected: one `gold/candidates/<id>.json` per task, each `{prNumber, findings[]}`.
(`parse-findings` runs on raw text here; `finalAssistantText` returns the text unchanged when it isn't JSON, then `extractFindings` pulls the fenced array.)

- [ ] **Step 3: Commit candidates**

```bash
git add experiments/cr-local-kg/scripts/oracle-candidates.sh experiments/cr-local-kg/gold/candidates
git commit -m "feat(cr-local-kg): oracle (claude, KG-off) candidate findings"
```

---

## Task 10: Triage → compile frozen answer key (TDD)

**Files:**
- Create: `experiments/cr-local-kg/scripts/compile-answer-key.ts`
- Test: `experiments/cr-local-kg/scripts/compile-answer-key.test.ts`
- Create (by hand during triage): `experiments/cr-local-kg/gold/triaged/<id>.json`

- [ ] **Step 1: Human triage (manual)**

For each `gold/candidates/<id>.json`, create `gold/triaged/<id>.json`: an array where every entry is a candidate finding **plus** your judgement, and any **curated real issues** you know about are added. Entry shape:

```json
{ "bot": "claude-oracle", "severity": "HIGH", "file": "src/x.ts", "line": "42",
  "description": "…", "verdict": "TRUE", "action": "FIX", "reason": "confirmed against callers" }
```
`verdict ∈ {TRUE,FALSE,UNCERTAIN}`, `action ∈ {FIX,DEFER,IGNORE}`. Drop nothing — record FALSE for rejected candidates (the scorer uses them).

- [ ] **Step 2: Write the failing test for `compile-answer-key.ts`**

```typescript
// experiments/cr-local-kg/scripts/compile-answer-key.test.ts
import { test } from 'node:test';
import assert from 'node:assert/strict';
import * as fs from 'node:fs';
import * as os from 'node:os';
import * as path from 'node:path';
import { compileAnswerKey } from './compile-answer-key.ts';

function tmpTriaged(files: Record<string, unknown[]>): string {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'cr-ak-'));
  for (const [id, arr] of Object.entries(files)) {
    fs.writeFileSync(path.join(dir, `${id}.json`), JSON.stringify(arr));
  }
  return dir;
}

test('groups triaged entries by task id into Record<id, entries>', () => {
  const entry = { bot: 'claude-oracle', severity: 'HIGH', file: 'a.ts', line: '1',
    description: 'd', verdict: 'TRUE', action: 'FIX', reason: 'r' };
  const dir = tmpTriaged({ '101': [entry], '202': [entry, entry] });
  const key = compileAnswerKey(dir);
  assert.equal(key['101'].length, 1);
  assert.equal(key['202'].length, 2);
});

test('throws with the offending id when verdict/action missing', () => {
  const bad = { bot: 'x', severity: 'HIGH', file: 'a.ts', line: '1', description: 'd' };
  const dir = tmpTriaged({ '101': [bad] });
  assert.throws(() => compileAnswerKey(dir), /101/);
});
```

- [ ] **Step 3: Run the test, verify it fails**

Run: `cd experiments/cr-local-kg && npx tsx --test scripts/compile-answer-key.test.ts`
Expected: FAIL — `Cannot find module './compile-answer-key.ts'`.

- [ ] **Step 4: Implement `compile-answer-key.ts`**

```typescript
// experiments/cr-local-kg/scripts/compile-answer-key.ts
import * as fs from 'node:fs';
import * as path from 'node:path';

const VERDICTS = ['TRUE', 'FALSE', 'UNCERTAIN'];
const ACTIONS = ['FIX', 'DEFER', 'IGNORE'];

export interface AnswerKeyEntry {
  bot: string; severity: string; file: string; line: string; description: string;
  verdict: string; action: string; reason: string;
}

/** Compile gold/triaged/<id>.json files into one answer key keyed by task id. */
export function compileAnswerKey(triagedDir: string): Record<string, AnswerKeyEntry[]> {
  const out: Record<string, AnswerKeyEntry[]> = {};
  for (const f of fs.readdirSync(triagedDir).filter((x) => /^\d+\.json$/.test(x)).sort()) {
    const id = f.replace(/\.json$/, '');
    const arr = JSON.parse(fs.readFileSync(path.join(triagedDir, f), 'utf8')) as AnswerKeyEntry[];
    if (!Array.isArray(arr)) throw new Error(`compile: ${f} is not an array`);
    arr.forEach((e, i) => {
      if (!VERDICTS.includes(e.verdict)) throw new Error(`compile: task ${id} entry ${i} bad/missing verdict`);
      if (!ACTIONS.includes(e.action)) throw new Error(`compile: task ${id} entry ${i} bad/missing action`);
      e.line = String(e.line ?? '');
    });
    out[id] = arr;
  }
  return out;
}

// CLI: compile-answer-key.ts --triaged gold/triaged --out answer-key.json
if (import.meta.url === `file://${process.argv[1]}`) {
  const a: Record<string, string> = {};
  const argv = process.argv.slice(2);
  for (let i = 0; i < argv.length; i += 1) {
    if (argv[i].startsWith('--')) { a[argv[i].slice(2)] = argv[i + 1] ?? ''; i += 1; }
  }
  const key = compileAnswerKey(a.triaged ?? 'gold/triaged');
  fs.writeFileSync(a.out ?? 'answer-key.json', JSON.stringify(key, null, 2));
  const n = Object.values(key).reduce((s, v) => s + v.length, 0);
  console.error(`compile: ${Object.keys(key).length} tasks, ${n} labels → ${a.out ?? 'answer-key.json'}`);
}
```

- [ ] **Step 5: Run the test, verify it passes**

Run: `cd experiments/cr-local-kg && npx tsx --test scripts/compile-answer-key.test.ts`
Expected: PASS (2 tests).

- [ ] **Step 6: Compile the real answer key + commit**

```bash
cd experiments/cr-local-kg
npx tsx scripts/compile-answer-key.ts --triaged gold/triaged --out answer-key.json
git add scripts/compile-answer-key.ts scripts/compile-answer-key.test.ts gold/triaged answer-key.json
git commit -m "feat(cr-local-kg): triaged gold + answer-key compiler (TDD)"
```

---

## Task 11: Full sweep (3 reps × 2 conditions)

**Files:** none (produces `results/raw/**`)

- [ ] **Step 1: Run all reps and conditions**

Local gemma is slow (~20 tasks × 2 × 3 ≈ 120 runs). Run in the background per CLAUDE.md (use a subagent / background command and filter output) and watch progress.

```bash
cd experiments/cr-local-kg
for rep in 1 2 3; do
  for cond in control treatment; do
    ./scripts/run-condition.sh --condition "$cond" --rep "$rep"
  done
done
```

- [ ] **Step 2: Verify completeness**

```bash
cd experiments/cr-local-kg
EXPECTED=$(npx tsx -e 'console.log(JSON.parse(require("fs").readFileSync("tasks/tasks.json")).tasks.length)')
for rep in 1 2 3; do for cond in control treatment; do
  n=$(find results/raw/rep-$rep/$cond -name 'PR-*.findings.json' | wc -l)
  echo "rep $rep $cond: $n / $EXPECTED"
done; done
```
Expected: every cell equals the task count. Investigate (re-run the task) any shortfall before scoring.

- [ ] **Step 3: Commit findings (sessions are git-ignored)**

```bash
git add experiments/cr-local-kg/results/raw/**/PR-*.findings.json
git commit -m "data(cr-local-kg): full sweep findings — 3 reps × 2 conditions"
```

---

## Task 12: Score & aggregate per class × condition × rep

**Files:**
- Create: `experiments/cr-local-kg/scripts/score-sweep.sh`

- [ ] **Step 1: Write `score-sweep.sh`**

Calls the framework `aggregate.ts` once per (condition, rep, class), pointing it at this experiment's own answer key. Writes one `results-row.json` per cell. Control is scored first so its F1 can seed the treatment's `--baseline-f1`.

```bash
#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXP_DIR="$(dirname "$SCRIPT_DIR")"
AGG="$EXP_DIR/../code-review/scripts/aggregate.ts"
AK="$EXP_DIR/answer-key.json"
OUT="$EXP_DIR/results/rows"; mkdir -p "$OUT"

agg() { # cond rep class hid baseline
  local cond="$1" rep="$2" cls="$3" hid="$4" base="$5"
  local dir="$EXP_DIR/results/raw/rep-${rep}/${cond}/${cls}s"
  [[ -d "$dir" ]] || { echo "skip missing $dir"; return; }
  local kg="empty"; [[ "$cond" == "treatment" ]] && kg="populated"
  local baseflag=(); [[ -n "$base" ]] && baseflag=(--baseline-f1 "$base")
  npx tsx "$AGG" --findings-dir "$dir" \
    --answer-key-path "$AK" --answer-key-version orig \
    --experiment cr-local-kg --hypothesis "$hid" \
    --variant "${cond} rep-${rep} ${cls}" \
    --skill-version review.md --model ollama/gemma4:12b-96k \
    --kg-state "$kg" "${baseflag[@]}" \
    --log-link "experiments/cr-local-kg/analysis/report.md" \
    --out "$OUT/${cond}-rep${rep}-${cls}.row.json"
  echo "wrote $OUT/${cond}-rep${rep}-${cls}.row.json"
}

f1of() { npx tsx -e 'console.log(JSON.parse(require("fs").readFileSync(process.argv[1])).f1)' "$1"; }

for rep in 1 2 3; do
  for cls in file module; do
    # H-local-1 carries the file-class rows (overall KG effect, near-control);
    # H-local-2 carries the module-class rows (effect concentrates on modules).
    hid=H-local-1; [[ "$cls" == "module" ]] && hid=H-local-2
    agg control "$rep" "$cls" "$hid" ""
    base="$(f1of "$OUT/control-rep${rep}-${cls}.row.json")"
    agg treatment "$rep" "$cls" "$hid" "$base"
  done
done
echo "all rows written → $OUT"
```

- [ ] **Step 2: Run it**

```bash
chmod +x experiments/cr-local-kg/scripts/score-sweep.sh
cd experiments/cr-local-kg && ./scripts/score-sweep.sh
ls results/rows
```
Expected: 12 row files (3 reps × 2 conditions × 2 classes), each a valid Results row (aggregate.ts validates on write; it throws on any malformed/missing findings — fix and re-run if so).

- [ ] **Step 3: Eyeball the headline delta**

```bash
cd experiments/cr-local-kg
for f in results/rows/*.row.json; do
  npx tsx -e 'const r=require(process.argv[1]); console.log(process.argv[1].split("/").pop(), "F1="+r.f1, "P="+r.precision, "R="+r.recall, "ΔF1="+r.deltaF1)' "$PWD/$f"
done
```
Expected: per-class treatment-vs-control ΔF1 visible. Module ΔF1 ≥ file ΔF1 would support H-local-2.

- [ ] **Step 4: Commit rows**

```bash
git add experiments/cr-local-kg/scripts/score-sweep.sh experiments/cr-local-kg/results/rows
git commit -m "feat(cr-local-kg): score-sweep → 12 micro-averaged Results rows"
```

---

## Task 13: Register in the Google Sheet (hypotheses + results)

**Files:** none (writes to the Sheet via google-sheets MCP, in-session)

- [ ] **Step 1: Append the two hypotheses to the `Hypotheses` tab**

Use the google-sheets MCP. Spreadsheet `1txtt4rYQULxMZQHOgOqn8TcAx5bQBPEjknRsDxIUU4Q`, tab `Hypotheses`. Add:
- `H-local-1` · experiment `cr-local-kg` · Knob `KG` · "Local gemma4:12b-96k catches more real issues with KG MCP than without" · Predicted `+recall/+F1, +cost`.
- `H-local-2` · experiment `cr-local-kg` · Knob `KG` · "The KG effect concentrates on module (cross-file) tasks, ~0 on single files" · Predicted `+F1 on modules only`.

Use the exact `Hypotheses` column order already in the sheet (read row 1 first with `get_sheet_data`).

- [ ] **Step 2: Validate + shape each Results row, then append**

For each of the 12 rows, run the framework's `sync-sheet.ts` to validate and produce the append payload:

```bash
cd experiments/cr-local-kg
for f in results/rows/*.row.json; do
  npx tsx ../code-review/scripts/sync-sheet.ts --in "$f" --known-hids H-local-1,H-local-2
done
```
Expected: each prints `{ sheet, values }` with an ordered 19-cell array; it throws if a row's H-ID is unknown or a column is missing.

- [ ] **Step 3: Append the validated rows to the `Results` tab**

Feed each printed `values` array to the google-sheets MCP (`update_cells`/`batch_update_cells`), assigning the next `R-ID` per row (read the current max from the sheet first). File-class rows already carry `H-local-1` and module-class rows `H-local-2` (set in Task 12), so no re-tagging is needed.

- [ ] **Step 4: No git commit** (the Sheet is the artifact). Note the appended R-ID range in `analysis/report.md` in Task 14.

---

## Task 14: Conclude — novel triage, report, README

**Files:**
- Modify: `experiments/cr-local-kg/analysis/report.md`
- Create: `experiments/cr-local-kg/README.md`

- [ ] **Step 1: Triage novels (conservative invariant)**

Novel findings (gemma findings with no answer-key match) are in each `ScoreResult.notes.novel`. Extract and adjudicate them; do **not** auto-score as FP. Confirmed-real novels may be folded back into `gold/triaged/` and the key recompiled (Task 10 Step 6) as an `extended` version — if you do, re-run Task 12 with `--answer-key-version extended` and add those rows too.

```bash
cd experiments/cr-local-kg
for f in $(find results/raw -name 'PR-*.findings.json'); do
  id=$(basename "$f" | sed 's/PR-//;s/.findings.json//')
  CR_LOOP_ANSWER_KEY="$PWD/answer-key.json" \
    npx tsx ../cr-loop/scripts/score.ts --findings "$f" --pr "$id" \
    | npx tsx -e 'let s="";process.stdin.on("data",d=>s+=d).on("end",()=>{const r=JSON.parse(s); if(r.notes.novel.length) console.log(process.argv[1], r.notes.novel.length, "novels")})' "$f"
done
```

- [ ] **Step 2: Write `analysis/report.md`**

Cover: feasibility (Task 3/7 outcomes), the per-class ΔF1 table (control vs treatment × file vs module, averaged over 3 reps with the spread), verdict on H-local-1 and H-local-2 (flag deltas within ~0.01 single-seed noise as inconclusive), KG tool-call counts (treatment), cost/latency if captured, and caveats (one model, one repo, oracle-defined gold → low absolute F1 by design).

- [ ] **Step 3: Write `README.md`** (mirror cr-loop's structure: what it tests, conditions, layout, how to replicate, caveats; link the spec + this plan + the Sheet).

- [ ] **Step 4: Update the `Hypotheses` Status/Learning** in the Sheet to confirmed/refuted/inconclusive with a one-line learning each.

- [ ] **Step 5: Commit**

```bash
git add experiments/cr-local-kg/README.md experiments/cr-local-kg/analysis/report.md
git commit -m "docs(cr-local-kg): results report + README + conclusions"
```

- [ ] **Step 6: Clean up the worktree**

```bash
git -C ../aictrl_main worktree remove ../aictrl_main-cr-pin
```

---

## Self-Review notes (addressed)

- **Spec coverage:** conditions/toggle (T2), current-file mix tasks (T8), KG-neutral Claude oracle gold (T9–T10), score.ts + framework aggregate reuse (T5/T12), registry sync (T13), Medium 3-seed scale (T11), all four §7 risks have a gate: tool-calling (T3), KG/code sync (T3 step 2 checks real results; pin = current HEAD), 96k truncation (watch in T7/T11 session output), opencode provider (T2 step 3).
- **Reps vs seeds:** ollama seed isn't settable per-run via `opencode run`, so reps are independent samples at `temperature 0.7`; documented as a reproducibility caveat in the report (T14).
- **Naming consistency:** `PR-<id>.findings.json` / `{prNumber,findings}` / `severity∈{CRITICAL,HIGH,MEDIUM,LOW}` / `AnswerKeyEntry` fields are identical across T5, T6, T9, T10, T12 and match the reused `score.ts` and `aggregate.ts`.
