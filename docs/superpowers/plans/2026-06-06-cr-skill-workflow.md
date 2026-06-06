# cr-skill-workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `cr-skill-workflow` experiment sandbox — a harness for iterating on Gemma 4 code review DAG workflows, with autoresearch-style probe→sweep→commit/revert loop.

**Architecture:** A new sibling experiment directory shares tasks/answer-key with `cr-local-kg` via symlinks. `run-workflow.sh` drives type-1 experiments (single `aictrl run` with a workflow SKILL.md) and type-2 experiments (chained `aictrl run` calls with Jinja2-style `{{node.artefact}}` template injection). `run-research-loop.sh` implements the probe→full-sweep→git-commit/revert iteration cycle.

**Tech stack:** bash, TypeScript (npx tsx), aictrl CLI, ollama gemma4:12b-cr, existing `parse-session.ts` / `parse-findings.ts` from cr-local-kg.

---

## File map

```
experiments/cr-skill-workflow/
  aictrl-workflow.jsonc          Task 1  shared aictrl config template (__SKILLS_PATH__ placeholder)
  .gitignore                     Task 1  ignore results/, research/results.tsv
  tasks/                         Task 1  symlink → ../cr-local-kg/tasks
  answer-key.json                Task 1  symlink → ../cr-local-kg/answer-key.json
  task-files/                    Task 1  symlink → ../cr-local-kg/task-files
  .env.local                     Task 1  symlink → ../cr-local-kg/.env.local
  current/                       Task 13 live candidate edited by the researcher
    skills/code-review/SKILL.md
  experiments/
    exp-001-multistep-prompt/    Task 3  type-1: 4-step workflow
      skills/code-review/SKILL.md
    exp-002-two-pass/            Task 7  type-2: two-pass chain
      dag.yaml
      prompts/pass1.md
      prompts/pass2.md.j2
  scripts/
    run-workflow.sh              Tasks 2,6  main harness (type 1 + type 2)
    render-template.ts           Task 5   {{node.artefact}} substitution
    render-template.test.ts      Task 5   unit tests
    score.ts                     Task 9   F1 scorer, writes scores.json
    sync-experiment.ts           Task 10  append row to Google Sheet
    run-research-loop.sh         Task 12  probe→sweep→commit/revert loop
  research/
    loop.md                      Task 11  AI researcher standing instructions
    probe-tasks.txt              Task 11  5 representative task IDs
    results.tsv                  Task 11  header only (gitignored, append-only)
  results/                               gitignored
```

---

### Task 1: Scaffold directory, symlinks, shared config

**Files:**
- Create: `experiments/cr-skill-workflow/aictrl-workflow.jsonc`
- Create: `experiments/cr-skill-workflow/.gitignore`

- [ ] **Step 1: Create directories**

```bash
cd /home/bulat/code/skill-md-research/experiments
mkdir -p cr-skill-workflow/experiments
mkdir -p cr-skill-workflow/scripts
mkdir -p cr-skill-workflow/research
mkdir -p cr-skill-workflow/results
mkdir -p cr-skill-workflow/current/skills/code-review
```

- [ ] **Step 2: Create symlinks**

```bash
cd /home/bulat/code/skill-md-research/experiments/cr-skill-workflow
ln -s ../cr-local-kg/tasks tasks
ln -s ../cr-local-kg/answer-key.json answer-key.json
ln -s ../cr-local-kg/task-files task-files
ln -s ../cr-local-kg/.env.local .env.local
```

- [ ] **Step 3: Create `.gitignore`**

```
results/
research/results.tsv
/current/
```

- [ ] **Step 4: Create `aictrl-workflow.jsonc`**

```json
{
  "$schema": "https://aictrl.dev/config.json",
  "provider": {
    "ollama": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "Ollama (local)",
      "options": { "baseURL": "http://localhost:11434/v1" },
      "models": {
        "gemma4:12b-cr": {
          "name": "Gemma4 12B (64k ctx, review)",
          "tools": true,
          "options": { "temperature": 0.7, "reasoningEffort": "none" }
        }
      }
    }
  },
  "mcp": {
    "aictrl": {
      "type": "remote",
      "url": "https://aictrl.dev/aictrl/mcp",
      "enabled": true,
      "headers": { "X-API-Key": "{env:AICTRL_MCP_TOKEN}" }
    }
  },
  "skills": {
    "paths": ["__SKILLS_PATH__"]
  }
}
```

- [ ] **Step 5: Verify symlinks resolve**

```bash
cd /home/bulat/code/skill-md-research/experiments/cr-skill-workflow
ls -la tasks answer-key.json task-files
# Expected: symlinks pointing to cr-local-kg equivalents
npx tsx -e 'console.log(JSON.parse(require("fs").readFileSync("answer-key.json")).["101"]?.length ?? "no pr 101")' 2>/dev/null || true
```

- [ ] **Step 6: Commit**

```bash
cd /home/bulat/code/skill-md-research
git add experiments/cr-skill-workflow/
git commit -m "feat(cr-skill-workflow): scaffold directory, symlinks, shared aictrl config"
```

---

### Task 2: Core harness — `run-workflow.sh` (type-1 path)

**Files:**
- Create: `experiments/cr-skill-workflow/scripts/run-workflow.sh`

- [ ] **Step 1: Write `run-workflow.sh`**

```bash
#!/usr/bin/env bash
set -uo pipefail   # NOT -e: one bad task must never kill the whole sweep

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXP_DIR="$(dirname "$SCRIPT_DIR")"
MODEL="ollama/gemma4:12b-cr"
SCRATCH=/tmp/cr-wf-scratch; mkdir -p "$SCRATCH"
PARSE_SESSION="$EXP_DIR/../cr-local-kg/scripts/parse-session.ts"

EXP_ID=""; REP=""; ONLY=""

while [[ $# -gt 0 ]]; do case $1 in
  --exp)   EXP_ID="$2"; shift 2;;
  --rep)   REP="$2";    shift 2;;
  --task)  ONLY="$2";   shift 2;;
  *) echo "unknown arg: $1"; exit 1;;
esac; done

[[ -n "$EXP_ID" && -n "$REP" ]] || { echo "Usage: run-workflow.sh --exp <id> --rep <N> [--task <id>]"; exit 1; }

EXP_PATH="$EXP_DIR/experiments/$EXP_ID"
[[ -d "$EXP_PATH" ]] || { echo "experiment not found: $EXP_PATH"; exit 1; }

# Load env (AICTRL_MCP_TOKEN etc.)
[[ -f "$EXP_DIR/.env.local" ]] && { set -a; . "$EXP_DIR/.env.local"; set +a; }
[[ -n "${AICTRL_MCP_TOKEN:-}" ]] || { echo "AICTRL_MCP_TOKEN not set in .env.local"; exit 1; }

PIN_DIR="$(npx tsx -e 'console.log(JSON.parse(require("fs").readFileSync(process.argv[1])).pinDir)' \
  "$EXP_DIR/tasks/tasks.json")"

# Generate per-experiment aictrl config (substitute __SKILLS_PATH__)
SKILLS_PATH="$EXP_PATH/skills"
TMP_CONFIG=$(mktemp /tmp/aictrl-wf-XXXXXX.jsonc)
trap 'rm -f "$TMP_CONFIG"' EXIT
sed "s|__SKILLS_PATH__|$SKILLS_PATH|g" "$EXP_DIR/aictrl-workflow.jsonc" > "$TMP_CONFIG"
export AICTRL_CONFIG="$TMP_CONFIG"

# --- TYPE DETECTION ---
if [[ -f "$EXP_PATH/dag.yaml" ]]; then
  # Type 2: harness-orchestrated DAG — handled in a later task
  echo "Type-2 experiment — dag.yaml execution not yet implemented"; exit 1
fi

# --- TYPE 1: single aictrl run per task ---
mapfile -t TASK_LINES < <(npx tsx -e '
  const t=JSON.parse(require("fs").readFileSync(process.argv[1]));
  for (const x of t.tasks) console.log([x.id,x.class,x.paths.join(",")].join("\t"));
' "$EXP_DIR/tasks/tasks.json")

for line in "${TASK_LINES[@]}"; do
  IFS=$'\t' read -r ID CLASS PATHS <<< "$line"
  [[ -n "$ONLY" && "$ID" != "$ONLY" ]] && continue

  miss=""
  IFS=',' read -ra PARR <<< "$PATHS"
  for p in "${PARR[@]}"; do [[ -f "$PIN_DIR/$p" ]] || miss="$p"; done
  if [[ -n "$miss" ]]; then echo "[$(date +%H:%M:%S)] SKIP task $ID — missing $miss"; continue; fi

  OUT_DIR="$EXP_DIR/results/$EXP_ID/rep-${REP}/treatment/${CLASS}s"; mkdir -p "$OUT_DIR"
  SESSION="$OUT_DIR/PR-${ID}.session.json"
  FIND="$OUT_DIR/PR-${ID}.findings.json"
  LOG="$OUT_DIR/PR-${ID}.log"

  PROMPT="$(npx tsx -e '
    const fs=require("fs");
    const repo=process.argv[1], paths=process.argv[2].split(",");
    const blocks=paths.map(p=>`\n--- FILE: ${p} ---\n\`\`\`\n${fs.readFileSync(repo+"/"+p,"utf8")}\n\`\`\`\n`).join("\n");
    process.stdout.write("Use your code-review skill to review the following source file(s) for real defects. Output findings as a JSON array.\n"+blocks);
  ' "$PIN_DIR" "$PATHS")"
  [[ -z "$PROMPT" ]] && { echo "[$(date +%H:%M:%S)] SKIP task $ID — empty prompt"; continue; }

  echo "[$(date +%H:%M:%S)] task $ID ($CLASS)"
  START=$(date +%s)
  aictrl run --print-logs --log-level INFO --format json --dir "$SCRATCH" \
    --model "$MODEL" --title "cr-wf-${EXP_ID}-${REP}-${ID}" "$PROMPT" \
    </dev/null >"$SESSION" 2>"$LOG" || true
  DUR=$(($(date +%s)-START))

  npx tsx "$PARSE_SESSION" --session "$SESSION" --pr "$ID" --out "$FIND" 2>/dev/null \
    || printf '{"prNumber":%s,"findings":[]}\n' "$ID" > "$FIND"

  KG=$(grep -c 'permission=aictrl_query_context' "$LOG" 2>/dev/null || echo 0)
  N=$(npx tsx -e 'try{console.log(JSON.parse(require("fs").readFileSync(process.argv[1])).findings.length)}catch{console.log(0)}' "$FIND" 2>/dev/null || echo 0)
  printf '{"prNumber":%s,"condition":"treatment","rep":%s,"class":"%s","durationSeconds":%s,"queryContextCalls":%s,"findings":%s}\n' \
    "$ID" "$REP" "$CLASS" "$DUR" "$KG" "$N" > "$OUT_DIR/PR-${ID}.meta.json"

  echo "   -> $N findings, $KG kg calls, ${DUR}s"
done
echo "done: rep $REP of $EXP_ID"
```

- [ ] **Step 2: Make executable**

```bash
chmod +x /home/bulat/code/skill-md-research/experiments/cr-skill-workflow/scripts/run-workflow.sh
```

- [ ] **Step 3: Smoke-test argument validation**

```bash
cd /home/bulat/code/skill-md-research/experiments/cr-skill-workflow
bash scripts/run-workflow.sh 2>&1 | grep -q "Usage:" && echo "PASS: usage guard works"
bash scripts/run-workflow.sh --exp nonexistent --rep 1 2>&1 | grep -q "not found" && echo "PASS: missing exp guard works"
```

Expected: both lines print PASS.

- [ ] **Step 4: Commit**

```bash
cd /home/bulat/code/skill-md-research
git add experiments/cr-skill-workflow/scripts/run-workflow.sh
git commit -m "feat(cr-skill-workflow): add type-1 harness run-workflow.sh"
```

---

### Task 3: exp-001 — 4-step workflow SKILL.md

**Files:**
- Create: `experiments/cr-skill-workflow/experiments/exp-001-multistep-prompt/skills/code-review/SKILL.md`

- [ ] **Step 1: Create the experiment's skill directory**

```bash
mkdir -p /home/bulat/code/skill-md-research/experiments/cr-skill-workflow/experiments/exp-001-multistep-prompt/skills/code-review
```

- [ ] **Step 2: Write `SKILL.md`**

```markdown
---
name: code-review
description: Multi-step workflow code review with explicit scan → enrich → filter → output stages.
allowedTools:
  - aictrl_query_context
version: "2.0.0"
---

# Code Review — Structured Workflow

You are reviewing the source file(s) provided in the prompt for **real, specific
defects**: security/authorization flaws, correctness bugs, data-loss / race
conditions, contract or type violations, resource leaks, missing validation, and
error-handling gaps. Ignore style nits.

Work through these four steps in order. Do not skip steps.

---

## Step 1 — Scan

Read the entire file(s). Write a **scratch list** of every suspicious location:
function name, line number, and one-line note. Aim for 10–20 candidates. At this
stage include anything that looks worth investigating — you will filter later.

Format the scratch list as a JSON comment block so you can reference it in later steps:

```json
// scratch
[
  { "fn": "getUserById", "line": 42, "note": "no null check before .id access" },
  ...
]
```

---

## Step 2 — KG Enrichment

For each candidate in your scratch list, run **one** `aictrl_query_context` call
to check real-world impact:

- `{"domain":"code","action":"callers","query":"<functionName>"}` — if zero callers, downgrade or drop.
- `{"domain":"code","action":"impact","query":"<filePath>"}` — understand blast radius.

Annotate each scratch entry with a `callers` count. Keep a running tally of calls
used (hard limit: **8 total** across all candidates — stop enriching once you hit 8).

---

## Step 3 — Filter

Apply these rules to your annotated scratch list:

1. Drop candidates where callers = 0 **and** confidence < 6.
2. Drop style/naming issues (not defects).
3. Promote severity to HIGH for any finding with callers > 5.
4. Keep at most **10 findings** — take the highest-confidence survivors.

---

## Step 4 — Output

Emit the surviving findings as a **single JSON array inside one ```json fenced
block** and nothing after it.

```json
[
  { "file": "server/lib/x.ts", "line": 42, "severity": "HIGH",
    "title": "short title", "description": "one specific sentence",
    "confidence": 8 }
]
```

- `file` = repo-relative path exactly as shown in the prompt.
- `line` = number or `start-end` range.
- `severity` ∈ CRITICAL, HIGH, MEDIUM, LOW.
- `confidence` = integer 1–10.
- Output `[]` only if you are genuinely confident the code is defect-free.
```

- [ ] **Step 3: Commit**

```bash
cd /home/bulat/code/skill-md-research
git add experiments/cr-skill-workflow/experiments/exp-001-multistep-prompt/
git commit -m "feat(cr-skill-workflow): add exp-001 4-step workflow SKILL.md"
```

---

### Task 4: Verify exp-001 runs end-to-end against one task

- [ ] **Step 1: Run against task 101 (file-scope, risk-scoring.ts)**

```bash
cd /home/bulat/code/skill-md-research/experiments/cr-skill-workflow
bash scripts/run-workflow.sh --exp exp-001-multistep-prompt --rep 1 --task 101
```

Expected output (approximate):
```
[HH:MM:SS] task 101 (file)
   -> N findings, K kg calls, Xs
done: rep 1 of exp-001-multistep-prompt
```

- [ ] **Step 2: Verify findings file was created**

```bash
cat results/exp-001-multistep-prompt/rep-1/treatment/files/PR-101.findings.json | \
  npx tsx -e 'const d=JSON.parse(require("fs").readFileSync("/dev/stdin","utf8")); console.log("findings:",d.findings.length)'
```

Expected: `findings: N` (N ≥ 0, file must be valid JSON).

- [ ] **Step 3: Commit results (gitignored — nothing to commit; just verify the harness works)**

No commit needed — results/ is gitignored. Proceed to Task 5.

---

### Task 5: Template renderer with unit tests

**Files:**
- Create: `experiments/cr-skill-workflow/scripts/render-template.ts`
- Create: `experiments/cr-skill-workflow/scripts/render-template.test.ts`

- [ ] **Step 1: Write `render-template.ts`**

```typescript
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
```

- [ ] **Step 2: Write `render-template.test.ts`**

```typescript
import { renderTemplate } from './render-template.ts';
import assert from 'node:assert/strict';
import { describe, it } from 'node:test';

describe('renderTemplate', () => {
  it('substitutes a simple string artefact', () => {
    const result = renderTemplate('hello {{ pass1.findings }}', {
      pass1: { findings: 'world' },
    });
    assert.equal(result, 'hello world');
  });

  it('JSON-serialises non-string artefacts', () => {
    const findings = [{ file: 'x.ts', line: 1 }];
    const result = renderTemplate('data: {{ pass1.findings }}', {
      pass1: { findings },
    });
    assert.equal(result, `data: ${JSON.stringify(findings, null, 2)}`);
  });

  it('leaves unresolved placeholders intact', () => {
    const result = renderTemplate('{{ missing.key }}', {});
    assert.equal(result, '{{ missing.key }}');
  });

  it('handles multiple substitutions in one template', () => {
    const result = renderTemplate('A={{a.x}} B={{b.y}}', {
      a: { x: '1' },
      b: { y: '2' },
    });
    assert.equal(result, 'A=1 B=2');
  });

  it('handles whitespace inside braces', () => {
    const result = renderTemplate('{{ pass1.findings }}', {
      pass1: { findings: 'ok' },
    });
    assert.equal(result, 'ok');
  });
});
```

- [ ] **Step 3: Run tests**

```bash
cd /home/bulat/code/skill-md-research/experiments/cr-skill-workflow
npx tsx --test scripts/render-template.test.ts
```

Expected: `5 passing`

- [ ] **Step 4: Commit**

```bash
cd /home/bulat/code/skill-md-research
git add experiments/cr-skill-workflow/scripts/render-template.ts \
         experiments/cr-skill-workflow/scripts/render-template.test.ts
git commit -m "feat(cr-skill-workflow): add render-template with unit tests"
```

---

### Task 6: Type-2 harness additions to `run-workflow.sh`

**Files:**
- Modify: `experiments/cr-skill-workflow/scripts/run-workflow.sh`

Replace the `# --- TYPE 2 ---` stub (currently `echo "...not yet implemented"; exit 1`) with the dag.yaml execution logic.

- [ ] **Step 1: Replace the type-2 stub in `run-workflow.sh`**

Find the block:
```bash
if [[ -f "$EXP_PATH/dag.yaml" ]]; then
  # Type 2: harness-orchestrated DAG — handled in a later task
  echo "Type-2 experiment — dag.yaml execution not yet implemented"; exit 1
fi
```

Replace it with:

```bash
if [[ -f "$EXP_PATH/dag.yaml" ]]; then
  # --- TYPE 2: harness-orchestrated DAG ---
  # Parse dag.yaml into JSON (requires js-yaml via npx)
  DAG_JSON="$(npx tsx -e '
    const fs=require("fs");
    // minimal YAML parser for our simple dag.yaml format via npx js-yaml
    const yaml=require("js-yaml");
    const dag=yaml.load(fs.readFileSync(process.argv[1],"utf8"));
    process.stdout.write(JSON.stringify(dag));
  ' "$EXP_PATH/dag.yaml" 2>/dev/null)"

  if [[ -z "$DAG_JSON" ]]; then
    echo "Failed to parse dag.yaml — ensure js-yaml is installed: npm i -g js-yaml"
    exit 1
  fi

  OUTPUT_NODE="$(echo "$DAG_JSON" | npx tsx -e 'process.stdout.write(JSON.parse(require("fs").readFileSync("/dev/stdin","utf8")).output)')"

  mapfile -t TASK_LINES < <(npx tsx -e '
    const t=JSON.parse(require("fs").readFileSync(process.argv[1]));
    for (const x of t.tasks) console.log([x.id,x.class,x.paths.join(",")].join("\t"));
  ' "$EXP_DIR/tasks/tasks.json")

  for line in "${TASK_LINES[@]}"; do
    IFS=$'\t' read -r ID CLASS PATHS <<< "$line"
    [[ -n "$ONLY" && "$ID" != "$ONLY" ]] && continue

    miss=""
    IFS=',' read -ra PARR <<< "$PATHS"
    for p in "${PARR[@]}"; do [[ -f "$PIN_DIR/$p" ]] || miss="$p"; done
    [[ -n "$miss" ]] && { echo "[$(date +%H:%M:%S)] SKIP task $ID — missing $miss"; continue; }

    # Build code blocks for this task
    CODE_BLOCKS="$(npx tsx -e '
      const fs=require("fs");
      const repo=process.argv[1], paths=process.argv[2].split(",");
      const blocks=paths.map(p=>`\n--- FILE: ${p} ---\n\`\`\`\n${fs.readFileSync(repo+"/"+p,"utf8")}\n\`\`\`\n`).join("\n");
      process.stdout.write(blocks);
    ' "$PIN_DIR" "$PATHS")"

    TASK_SCRATCH="$SCRATCH/task-${ID}-rep-${REP}"
    mkdir -p "$TASK_SCRATCH"

    # Execute each node in declaration order
    # Collect artefacts as we go: ARTEFACTS_JSON is a JSON object {"nodeName":{"findings":[...]}}
    ARTEFACTS_JSON="{}"

    # Iterate over node names in dag.yaml order
    mapfile -t NODE_NAMES < <(echo "$DAG_JSON" | npx tsx -e '
      const dag=JSON.parse(require("fs").readFileSync("/dev/stdin","utf8"));
      Object.keys(dag.nodes).forEach(n=>console.log(n));
    ')

    START_TASK=$(date +%s)
    for NODE in "${NODE_NAMES[@]}"; do
      NODE_CONFIG="$(echo "$DAG_JSON" | npx tsx -e "
        const dag=JSON.parse(require('fs').readFileSync('/dev/stdin','utf8'));
        process.stdout.write(JSON.stringify(dag.nodes['$NODE']));
      ")"
      PROMPT_FILE="$(echo "$NODE_CONFIG" | npx tsx -e "
        process.stdout.write(JSON.parse(require('fs').readFileSync('/dev/stdin','utf8')).prompt);
      ")"
      PROMPT_PATH="$EXP_PATH/$PROMPT_FILE"

      # Render template: substitute {{node.artefact}} and inject code
      RENDERED="$(mktemp "$TASK_SCRATCH/prompt-${NODE}-XXXXXX.md")"
      npx tsx "$SCRIPT_DIR/render-template.ts" \
        --template "$PROMPT_PATH" \
        --artefacts "$ARTEFACTS_JSON" > "$RENDERED"

      # Append code blocks (task.code injection)
      printf "\n%s\n" "$CODE_BLOCKS" >> "$RENDERED"

      SESSION_FILE="$TASK_SCRATCH/session-${NODE}.json"
      LOG_FILE="$TASK_SCRATCH/log-${NODE}.txt"

      echo "[$(date +%H:%M:%S)] task $ID node $NODE ($CLASS)"
      aictrl run --print-logs --log-level INFO --format json --dir "$SCRATCH" \
        --model "$MODEL" --title "cr-wf-${EXP_ID}-${REP}-${ID}-${NODE}" \
        "$(cat "$RENDERED")" </dev/null >"$SESSION_FILE" 2>"$LOG_FILE" || true

      # Parse findings from this node's session
      NODE_FIND="$TASK_SCRATCH/findings-${NODE}.json"
      npx tsx "$PARSE_SESSION" --session "$SESSION_FILE" --pr "$ID" --out "$NODE_FIND" 2>/dev/null \
        || printf '{"prNumber":%s,"findings":[]}\n' "$ID" > "$NODE_FIND"

      # Add this node's findings to the artefacts map
      FINDINGS="$(npx tsx -e "
        const d=JSON.parse(require('fs').readFileSync(process.argv[1],'utf8'));
        process.stdout.write(JSON.stringify(d.findings));
      " "$NODE_FIND")"
      ARTEFACTS_JSON="$(npx tsx -e "
        const a=JSON.parse(process.argv[1]);
        a['$NODE']={findings: JSON.parse(process.argv[2])};
        process.stdout.write(JSON.stringify(a));
      " "$ARTEFACTS_JSON" "$FINDINGS")"
    done

    DUR_TASK=$(($(date +%s)-START_TASK))

    # Copy output node's findings to results
    OUT_DIR="$EXP_DIR/results/$EXP_ID/rep-${REP}/treatment/${CLASS}s"; mkdir -p "$OUT_DIR"
    FIND="$OUT_DIR/PR-${ID}.findings.json"
    cp "$TASK_SCRATCH/findings-${OUTPUT_NODE}.json" "$FIND"

    N=$(npx tsx -e 'try{console.log(JSON.parse(require("fs").readFileSync(process.argv[1])).findings.length)}catch{console.log(0)}' "$FIND" 2>/dev/null || echo 0)
    printf '{"prNumber":%s,"condition":"treatment","rep":%s,"class":"%s","durationSeconds":%s,"findings":%s}\n' \
      "$ID" "$REP" "$CLASS" "$DUR_TASK" "$N" > "$OUT_DIR/PR-${ID}.meta.json"
    echo "   -> $N findings total, ${DUR_TASK}s"
  done
  echo "done: rep $REP of $EXP_ID (type 2)"
  exit 0
fi
```

- [ ] **Step 2: Install `js-yaml` (needed for dag.yaml parsing)**

```bash
cd /home/bulat/code/skill-md-research/experiments/cr-skill-workflow
npm init -y 2>/dev/null || true
npm install js-yaml
```

Verify:
```bash
node -e "require('js-yaml'); console.log('js-yaml ok')"
```
Expected: `js-yaml ok`

- [ ] **Step 3: Commit**

```bash
cd /home/bulat/code/skill-md-research
git add experiments/cr-skill-workflow/
git commit -m "feat(cr-skill-workflow): add type-2 dag.yaml orchestration to harness"
```

---

### Task 7: exp-002 — two-pass dag.yaml + prompts

**Files:**
- Create: `experiments/cr-skill-workflow/experiments/exp-002-two-pass/dag.yaml`
- Create: `experiments/cr-skill-workflow/experiments/exp-002-two-pass/prompts/pass1.md`
- Create: `experiments/cr-skill-workflow/experiments/exp-002-two-pass/prompts/pass2.md.j2`

- [ ] **Step 1: Create directories**

```bash
mkdir -p /home/bulat/code/skill-md-research/experiments/cr-skill-workflow/experiments/exp-002-two-pass/prompts
```

- [ ] **Step 2: Write `dag.yaml`**

```yaml
id: exp-002-two-pass
hypothesis: "Second pass sees first-pass findings and hunts for what was missed, increasing recall"
reps: 3
nodes:
  pass1:
    prompt: prompts/pass1.md
    inputs: [code]
    outputs: [findings]
  pass2:
    prompt: prompts/pass2.md.j2
    inputs: [code, pass1.findings]
    outputs: [findings]
output: pass2
```

- [ ] **Step 3: Write `prompts/pass1.md`**

```markdown
Review the source file(s) below for **real, specific defects**: security/authorization
flaws, correctness bugs, data-loss / race conditions, contract or type violations,
resource leaks, missing validation, and error-handling gaps. Ignore style nits.

For each finding you are confident is a genuine defect, record it. If you are
uncertain, omit it. Precision over recall — a false positive is worse than a miss.

Output your findings as a **single JSON array inside one ```json fenced block**
and nothing after it.

```json
[
  { "file": "path/to/file.ts", "line": 42, "severity": "HIGH",
    "title": "short title", "description": "one specific sentence",
    "confidence": 8 }
]
```

- `severity` ∈ CRITICAL, HIGH, MEDIUM, LOW
- `confidence` = integer 1–10
- Output `[]` if the code is defect-free
```

- [ ] **Step 4: Write `prompts/pass2.md.j2`**

```markdown
A first pass has already reviewed the code below and found these issues:

```json
{{ pass1.findings }}
```

Your task is the **second pass**: find defects the first pass missed.

Rules:
1. Do NOT repeat findings already listed above (same file + line range).
2. Focus on code paths, edge cases, and interactions the first pass did not examine.
3. Pay special attention to: error paths, concurrent access, boundary conditions,
   implicit assumptions about caller behaviour.

Output **only new findings** (not in the first-pass list) as a single JSON array
inside one ```json fenced block** and nothing after it.

```json
[
  { "file": "path/to/file.ts", "line": 42, "severity": "HIGH",
    "title": "short title", "description": "one specific sentence",
    "confidence": 8 }
]
```

Output `[]` if you find nothing new.
```

- [ ] **Step 5: Commit**

```bash
cd /home/bulat/code/skill-md-research
git add experiments/cr-skill-workflow/experiments/exp-002-two-pass/
git commit -m "feat(cr-skill-workflow): add exp-002 two-pass dag.yaml + prompts"
```

---

### Task 8: Verify exp-002 runs end-to-end against one task

- [ ] **Step 1: Run against task 101**

```bash
cd /home/bulat/code/skill-md-research/experiments/cr-skill-workflow
bash scripts/run-workflow.sh --exp exp-002-two-pass --rep 1 --task 101
```

Expected output:
```
[HH:MM:SS] task 101 node pass1 (file)
[HH:MM:SS] task 101 node pass2 (file)
   -> N findings total, Xs
done: rep 1 of exp-002-two-pass (type 2)
```

- [ ] **Step 2: Verify pass2 findings do not duplicate pass1 findings**

```bash
cat results/exp-002-two-pass/rep-1/treatment/files/PR-101.findings.json | \
  npx tsx -e '
    const d=JSON.parse(require("fs").readFileSync("/dev/stdin","utf8"));
    console.log("pass2 findings:", d.findings.length);
    console.log("sample:", JSON.stringify(d.findings[0] ?? null, null, 2));
  '
```

Expected: valid JSON with findings array (may be empty if pass2 found nothing new — that is valid).

---

### Task 9: `score.ts` — F1 scorer for workflow results

**Files:**
- Create: `experiments/cr-skill-workflow/scripts/score.ts`

- [ ] **Step 1: Write `score.ts`**

```typescript
#!/usr/bin/env npx tsx
/**
 * Score an experiment's results against answer-key.json.
 * Relaxed matching: file + line±5, no severity requirement.
 * Writes results/<exp-id>/scores.json and prints F1 table.
 *
 * Usage: score.ts --exp <exp-id> [--results-base <path>] [--reps 1,2,3]
 *   --exp          experiment id (e.g. exp-001-multistep-prompt)
 *   --results-base base results directory (default: ../results)
 *   --reps         comma-separated rep numbers (default: 1,2,3)
 */
import * as fs from 'node:fs';
import * as path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const EXP_DIR = path.resolve(HERE, '..');
const LINE_TOL = 5;

// ── CLI args ──
const argv = process.argv.slice(2);
const get = (flag: string, def: string) => {
  const i = argv.indexOf(flag);
  return i !== -1 ? argv[i + 1] : def;
};
const expId = get('--exp', '');
const resultsBase = get('--results-base', path.join(EXP_DIR, 'results'));
const reps = get('--reps', '1,2,3').split(',').map(s => s.trim());
if (!expId) { console.error('Usage: score.ts --exp <exp-id>'); process.exit(1); }

const AK_PATH = path.join(EXP_DIR, 'answer-key.json');
const ak: Record<string, AKEntry[]> = JSON.parse(fs.readFileSync(AK_PATH, 'utf8'));

interface AKEntry { verdict: string; action: string; file: string; line: string; }
interface Finding { file: string; line?: number | string; }

function parseLine(l: string | number | undefined) {
  if (l == null || l === '') return null;
  const m = String(l).match(/^(\d+)(?:[-–](\d+))?$/);
  if (!m) return null;
  return { start: parseInt(m[1]), end: m[2] ? parseInt(m[2]) : parseInt(m[1]) };
}
function overlap(a: ReturnType<typeof parseLine>, b: ReturnType<typeof parseLine>) {
  if (!a || !b) return true;
  return Math.abs(a.start - b.start) <= LINE_TOL ||
    (a.start <= b.end + LINE_TOL && a.end + LINE_TOL >= b.start);
}
interface Agg { tp: number; fp: number; fn: number; n: number; }
const blank = (): Agg => ({ tp: 0, fp: 0, fn: 0, n: 0 });
function prf(g: Agg) {
  const p = g.tp + g.fp === 0 ? 0 : g.tp / (g.tp + g.fp);
  const r = g.tp + g.fn === 0 ? 0 : g.tp / (g.tp + g.fn);
  return { p, r, f1: p + r === 0 ? 0 : (2 * p * r) / (p + r) };
}
const r3 = (n: number) => (Math.round(n * 1000) / 1000).toFixed(3);

function scoreFile(fullPath: string, into: Agg) {
  const data = JSON.parse(fs.readFileSync(fullPath, 'utf8')) as { prNumber?: number; findings?: Finding[] };
  const pr = String(data.prNumber ?? fullPath.match(/PR-(\d+)/)?.[1]);
  const findings: Finding[] = data.findings ?? [];
  const labels = ak[pr] ?? [];
  const usedAK = new Set<number>(), usedF = new Set<number>();
  findings.forEach((sf, i) => {
    const sfLine = parseLine(sf.line);
    const idx = labels.findIndex((lbl, j) => !usedAK.has(j) && sf.file === lbl.file && overlap(sfLine, parseLine(lbl.line)));
    if (idx === -1) return;
    usedAK.add(idx); usedF.add(i);
  });
  let tp = 0, fp = 0;
  for (const j of usedAK) {
    const v = labels[j].verdict;
    if (v === 'TRUE') tp += 1; else if (v === 'FALSE') fp += 1; else if (v === 'UNCERTAIN') tp += 0.5;
  }
  let fn = 0;
  for (let j = 0; j < labels.length; j++) {
    if (usedAK.has(j)) continue;
    const lbl = labels[j];
    if (lbl.verdict !== 'TRUE') continue;
    fn += lbl.action === 'FIX' ? 1 : 0.5;
  }
  into.tp += tp; into.fp += fp; into.fn += fn; into.n += 1;
}

function scoreDir(dir: string, into: Agg) {
  if (!fs.existsSync(dir)) return;
  for (const f of fs.readdirSync(dir)) {
    if (/^PR-\d+\.findings\.json$/.test(f)) scoreFile(path.join(dir, f), into);
  }
}

const overall = blank(), byScope: Record<string, Agg> = { file: blank(), module: blank() };
for (const rep of reps) {
  for (const [scope, sub] of [['file','files'],['module','modules']] as const) {
    const dir = path.join(resultsBase, expId, `rep-${rep}`, 'treatment', sub);
    scoreDir(dir, overall);
    scoreDir(dir, byScope[scope]);
  }
}
const o = prf(overall);
console.log(`\n=== ${expId} ===`);
console.log(`  overall: P=${r3(o.p)} R=${r3(o.r)} F1=${r3(o.f1)} | TP=${overall.tp} FP=${overall.fp} FN=${overall.fn} n=${overall.n}`);
for (const s of ['file','module']) {
  const c = prf(byScope[s]); console.log(`  ${s}: F1=${r3(c.f1)} (n=${byScope[s].n})`);
}

// Write scores.json
const scoresPath = path.join(resultsBase, expId, 'scores.json');
fs.writeFileSync(scoresPath, JSON.stringify({ expId, reps, overall: { ...o, ...overall }, byScope: Object.fromEntries(Object.entries(byScope).map(([k,v])=>[k,{...prf(v),...v}])) }, null, 2));
console.log(`\nscores.json → ${scoresPath}`);
```

- [ ] **Step 2: Make executable and verify it runs against exp-001**

```bash
chmod +x /home/bulat/code/skill-md-research/experiments/cr-skill-workflow/scripts/score.ts

cd /home/bulat/code/skill-md-research/experiments/cr-skill-workflow
npx tsx scripts/score.ts --exp exp-001-multistep-prompt --reps 1
```

Expected: prints F1 table and writes `results/exp-001-multistep-prompt/scores.json`.

- [ ] **Step 3: Commit**

```bash
cd /home/bulat/code/skill-md-research
git add experiments/cr-skill-workflow/scripts/score.ts
git commit -m "feat(cr-skill-workflow): add score.ts — relaxed F1 scorer for workflow results"
```

---

### Task 10: `sync-experiment.ts` — append Google Sheet row

**Files:**
- Create: `experiments/cr-skill-workflow/scripts/sync-experiment.ts`

- [ ] **Step 1: Write `sync-experiment.ts`**

```typescript
#!/usr/bin/env npx tsx
/**
 * Append one experiment result row to the research tracker Google Sheet.
 * Reads scores.json produced by score.ts.
 *
 * Usage: sync-experiment.ts --exp <exp-id> [--results-base <path>]
 *
 * Columns (matching existing sheet layout):
 *   exp-id | hypothesis | F1 per-run | F1 file | F1 module | ΔF1 vs baseline | TP | FP | FN | n | notes
 *
 * Baseline (cr-local-kg treatment): per-run F1 = 0.204
 */
import * as fs from 'node:fs';
import * as path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const EXP_DIR = path.resolve(HERE, '..');
const BASELINE_F1 = 0.204;
const SHEET_ID = '1txtt4rYQULxMZQHOgOqn8TcAx5bQBPEjknRsDxIUU4Q';

const argv = process.argv.slice(2);
const get = (flag: string, def: string) => { const i = argv.indexOf(flag); return i !== -1 ? argv[i + 1] : def; };
const expId = get('--exp', '');
const resultsBase = get('--results-base', path.join(EXP_DIR, 'results'));
if (!expId) { console.error('Usage: sync-experiment.ts --exp <exp-id>'); process.exit(1); }

const scoresPath = path.join(resultsBase, expId, 'scores.json');
if (!fs.existsSync(scoresPath)) {
  console.error(`scores.json not found: ${scoresPath}\nRun score.ts first.`);
  process.exit(1);
}
const scores = JSON.parse(fs.readFileSync(scoresPath, 'utf8'));

// Try to read hypothesis from dag.yaml or SKILL.md header
let hypothesis = '';
const dagPath = path.join(EXP_DIR, 'experiments', expId, 'dag.yaml');
const skillPath = path.join(EXP_DIR, 'experiments', expId, 'skills', 'code-review', 'SKILL.md');
if (fs.existsSync(dagPath)) {
  const m = fs.readFileSync(dagPath, 'utf8').match(/hypothesis:\s*"(.+?)"/);
  if (m) hypothesis = m[1];
} else if (fs.existsSync(skillPath)) {
  const m = fs.readFileSync(skillPath, 'utf8').match(/description:\s*(.+)/);
  if (m) hypothesis = m[1].trim();
}

const f1 = (scores.overall.f1 as number).toFixed(3);
const deltaF1 = (scores.overall.f1 - BASELINE_F1).toFixed(3);
const fileF1 = (scores.byScope.file?.f1 ?? 0).toFixed(3);
const modF1 = (scores.byScope.module?.f1 ?? 0).toFixed(3);

const row = [
  expId,
  hypothesis,
  f1,
  fileF1,
  modF1,
  deltaF1,
  String(scores.overall.tp ?? ''),
  String(scores.overall.fp ?? ''),
  String(scores.overall.fn ?? ''),
  String(scores.overall.n ?? ''),
  '',
];

console.log('\nRow to append to Google Sheet:');
console.log(row.join('\t'));
console.log(`\nSheet: https://docs.google.com/spreadsheets/d/${SHEET_ID}`);
console.log('\nTo append via MCP, run this script inside a Claude session with Google Sheets MCP enabled.');
console.log('The row values above can be pasted manually if MCP is unavailable.');

// Emit MCP-ready format for use inside a Claude Code session
console.log('\n--- MCP PAYLOAD ---');
console.log(JSON.stringify({ spreadsheetId: SHEET_ID, range: 'Sheet1!A:K', values: [row] }, null, 2));
```

- [ ] **Step 2: Test it runs without error**

```bash
cd /home/bulat/code/skill-md-research/experiments/cr-skill-workflow
npx tsx scripts/sync-experiment.ts --exp exp-001-multistep-prompt
```

Expected: prints row values and MCP payload (no error). Sheet update happens when run inside Claude Code with Google Sheets MCP active.

- [ ] **Step 3: Commit**

```bash
cd /home/bulat/code/skill-md-research
git add experiments/cr-skill-workflow/scripts/sync-experiment.ts
git commit -m "feat(cr-skill-workflow): add sync-experiment.ts — Google Sheet row emitter"
```

---

### Task 11: `research/` — loop.md, probe-tasks.txt, results.tsv header

**Files:**
- Create: `experiments/cr-skill-workflow/research/loop.md`
- Create: `experiments/cr-skill-workflow/research/probe-tasks.txt`
- Create: `experiments/cr-skill-workflow/research/results.tsv`

- [ ] **Step 1: Write `research/loop.md`**

```markdown
# Code Review Research Loop

## Goal
Maximise per-run F1 for Gemma 4 (gemma4:12b-cr) on the 20-task benchmark.

**Baseline** (cr-local-kg treatment, relaxed F1):
- Per-run F1 = 0.204 | Union-of-3 F1 = 0.355
- TP = 34.5 | FP = 45 | FN = 241

## What you control
Edit files in `current/` only:
- `current/skills/code-review/SKILL.md` — for type-1 experiments (single session workflow)
- `current/dag.yaml` + `current/prompts/*.md.j2` — for type-2 experiments (chained calls)

Never modify: `answer-key.json`, task files, scoring scripts, or any file outside `current/`.

## Iteration protocol
1. Read `research/results.tsv` to see what has been tried and what worked.
2. Propose ONE change to `current/` with a clear hypothesis.
3. Run probe: `bash scripts/run-research-loop.sh --eval --probe-only`
4. If probe F1 ≥ baseline × 0.90, run full sweep: `bash scripts/run-research-loop.sh --eval`
5. The loop script commits on improvement, reverts on regression.

## Hypotheses backlog (try in order)

1. ✅ **exp-001**: Structured 4-step workflow (scan→enrich→filter→output) — did it beat baseline?
2. ✅ **exp-002**: Two-pass chain (pass 2 hunts for what pass 1 missed)
3. **Next**: KG pre-fetch node — inject callers/impact for all functions before the review model runs
4. Confidence threshold tuning — raise minimum confidence to reduce FP
5. Module-scope: cross-file summarisation before reviewing individual files
6. Iterative refinement: a third pass that only re-examines dropped candidates

## What has been tried
(see research/results.tsv)

## Constraints
- No oracle leakage: prompts must not reference known bugs or answer-key content
- Keep KG calls ≤ 8 per review to control latency
- Each experiment must run in ≤ 60 min total (20 tasks × 3 reps)
```

- [ ] **Step 2: Write `research/probe-tasks.txt`**

```
101
102
103
201
202
```

These are: 101 (risk-scoring, file), 102 (oauth-store, file), 103 (security-policy, file), 201 (validation pipeline, module), 202 (integration CRUD, module) — 3 file-scope and 2 module-scope tasks.

- [ ] **Step 3: Write `research/results.tsv` (header only)**

```
commit	exp_id	f1_probe	f1_full	f1_file	f1_module	tp	fp	fn	status	hypothesis
```

- [ ] **Step 4: Commit**

```bash
cd /home/bulat/code/skill-md-research
git add experiments/cr-skill-workflow/research/loop.md \
         experiments/cr-skill-workflow/research/probe-tasks.txt \
         experiments/cr-skill-workflow/research/results.tsv
git commit -m "feat(cr-skill-workflow): add research loop.md, probe task set, results.tsv"
```

---

### Task 12: `run-research-loop.sh` — probe→sweep→commit/revert

**Files:**
- Create: `experiments/cr-skill-workflow/scripts/run-research-loop.sh`

- [ ] **Step 1: Write `run-research-loop.sh`**

```bash
#!/usr/bin/env bash
# Autoresearch-style eval loop for cr-skill-workflow.
# Runs the current/ experiment, scores it, commits if F1 improved vs baseline,
# reverts if not. Appends one row to research/results.tsv.
#
# Usage:
#   run-research-loop.sh --eval               probe + full sweep + commit/revert
#   run-research-loop.sh --eval --probe-only  probe only (no commit)
#
# The researcher (Claude) edits current/ before calling this script.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXP_DIR="$(dirname "$SCRIPT_DIR")"
BASELINE_F1="0.204"
MIN_IMPROVEMENT="${MIN_IMPROVEMENT:-0.005}"
PROBE_ONLY=false

while [[ $# -gt 0 ]]; do case $1 in
  --eval)        shift;;           # explicit eval mode (required)
  --probe-only)  PROBE_ONLY=true; shift;;
  --min-improvement) MIN_IMPROVEMENT="$2"; shift 2;;
  *) echo "Usage: run-research-loop.sh --eval [--probe-only]"; exit 1;;
esac; done

PROBE_TASKS_FILE="$EXP_DIR/research/probe-tasks.txt"
RESULTS_TSV="$EXP_DIR/research/results.tsv"
CURRENT_EXP="$EXP_DIR/current"

[[ -d "$CURRENT_EXP" ]] || { echo "current/ not found — create a SKILL.md or dag.yaml there first"; exit 1; }

# Determine if current/ is type 1 or type 2
if [[ -f "$CURRENT_EXP/dag.yaml" ]]; then
  CURRENT_TYPE=2
else
  CURRENT_TYPE=1
fi

# Temporary experiment ID for this run
PROBE_ID="probe-$(date +%Y%m%d-%H%M%S)"
FULL_ID="run-$(date +%Y%m%d-%H%M%S)"

# ── Probe ──
echo "=== PROBE: $PROBE_ID ==="
mkdir -p "$EXP_DIR/experiments/$PROBE_ID"

if [[ $CURRENT_TYPE -eq 1 ]]; then
  cp -r "$CURRENT_EXP/skills" "$EXP_DIR/experiments/$PROBE_ID/"
else
  cp "$CURRENT_EXP/dag.yaml" "$EXP_DIR/experiments/$PROBE_ID/"
  [[ -d "$CURRENT_EXP/prompts" ]] && cp -r "$CURRENT_EXP/prompts" "$EXP_DIR/experiments/$PROBE_ID/"
fi

PROBE_F1="0"
while IFS= read -r TASK_ID; do
  [[ -z "$TASK_ID" ]] && continue
  bash "$SCRIPT_DIR/run-workflow.sh" --exp "$PROBE_ID" --rep 1 --task "$TASK_ID" || true
done < "$PROBE_TASKS_FILE"

if npx tsx "$SCRIPT_DIR/score.ts" --exp "$PROBE_ID" --reps 1 2>/dev/null; then
  PROBE_F1="$(npx tsx -e "
    const s=JSON.parse(require('fs').readFileSync('$EXP_DIR/results/$PROBE_ID/scores.json','utf8'));
    process.stdout.write(String(s.overall.f1));
  " 2>/dev/null || echo 0)"
fi
echo "Probe F1: $PROBE_F1  (baseline: $BASELINE_F1)"

# Clean up probe experiment definition (results stay for inspection)
rm -rf "$EXP_DIR/experiments/$PROBE_ID"

THRESHOLD=$(npx tsx -e "process.stdout.write(String($BASELINE_F1 * 0.90))" 2>/dev/null || echo "0.184")
PROBE_PASS=$(npx tsx -e "process.stdout.write(String(parseFloat('$PROBE_F1') >= parseFloat('$THRESHOLD')))" 2>/dev/null || echo "false")

if [[ "$PROBE_ONLY" == "true" ]]; then
  echo "Probe-only mode — done. F1=$PROBE_F1 (threshold=$THRESHOLD, pass=$PROBE_PASS)"
  exit 0
fi

if [[ "$PROBE_PASS" != "true" ]]; then
  echo "Probe below threshold ($PROBE_F1 < $THRESHOLD) — skipping full sweep"
  COMMIT="$(git -C "$EXP_DIR" rev-parse --short HEAD 2>/dev/null || echo 'HEAD')"
  printf '%s\t%s\t%s\t%s\t\t\t\t\t\tdiscard-probe\t%s\n' \
    "$COMMIT" "$FULL_ID" "$PROBE_F1" "" "probe below threshold" >> "$RESULTS_TSV"
  echo "Recorded discard in results.tsv"
  exit 0
fi

# ── Full sweep ──
echo "=== FULL SWEEP: $FULL_ID ==="
mkdir -p "$EXP_DIR/experiments/$FULL_ID"
if [[ $CURRENT_TYPE -eq 1 ]]; then
  cp -r "$CURRENT_EXP/skills" "$EXP_DIR/experiments/$FULL_ID/"
else
  cp "$CURRENT_EXP/dag.yaml" "$EXP_DIR/experiments/$FULL_ID/"
  [[ -d "$CURRENT_EXP/prompts" ]] && cp -r "$CURRENT_EXP/prompts" "$EXP_DIR/experiments/$FULL_ID/"
fi

for REP in 1 2 3; do
  bash "$SCRIPT_DIR/run-workflow.sh" --exp "$FULL_ID" --rep "$REP" || true
done

npx tsx "$SCRIPT_DIR/score.ts" --exp "$FULL_ID" --reps 1,2,3
FULL_F1="$(npx tsx -e "
  const s=JSON.parse(require('fs').readFileSync('$EXP_DIR/results/$FULL_ID/scores.json','utf8'));
  process.stdout.write(String(s.overall.f1));
" 2>/dev/null || echo 0)"
FILE_F1="$(npx tsx -e "
  const s=JSON.parse(require('fs').readFileSync('$EXP_DIR/results/$FULL_ID/scores.json','utf8'));
  process.stdout.write(String(s.byScope.file?.f1 ?? 0));
" 2>/dev/null || echo 0)"
MOD_F1="$(npx tsx -e "
  const s=JSON.parse(require('fs').readFileSync('$EXP_DIR/results/$FULL_ID/scores.json','utf8'));
  process.stdout.write(String(s.byScope.module?.f1 ?? 0));
" 2>/dev/null || echo 0)"

echo "Full sweep F1: $FULL_F1  (baseline: $BASELINE_F1, min-improvement: $MIN_IMPROVEMENT)"

IMPROVED=$(npx tsx -e "
  process.stdout.write(String(parseFloat('$FULL_F1') >= parseFloat('$BASELINE_F1') + parseFloat('$MIN_IMPROVEMENT')));
" 2>/dev/null || echo "false")

COMMIT="$(git -C "$EXP_DIR" rev-parse --short HEAD 2>/dev/null || echo 'HEAD')"

# Read hypothesis from current/
HYPOTHESIS=""
if [[ -f "$CURRENT_EXP/dag.yaml" ]]; then
  HYPOTHESIS="$(grep 'hypothesis:' "$CURRENT_EXP/dag.yaml" | sed 's/.*hypothesis:[ "]*//' | tr -d '"' || true)"
elif [[ -f "$CURRENT_EXP/skills/code-review/SKILL.md" ]]; then
  HYPOTHESIS="$(grep 'description:' "$CURRENT_EXP/skills/code-review/SKILL.md" | head -1 | sed 's/description:[ ]*//' || true)"
fi

SCORES_JSON="$EXP_DIR/results/$FULL_ID/scores.json"
TP="$(npx tsx -e "const s=JSON.parse(require('fs').readFileSync('$SCORES_JSON','utf8'));process.stdout.write(String(s.overall.tp??''))" 2>/dev/null||echo '')"
FP="$(npx tsx -e "const s=JSON.parse(require('fs').readFileSync('$SCORES_JSON','utf8'));process.stdout.write(String(s.overall.fp??''))" 2>/dev/null||echo '')"
FN="$(npx tsx -e "const s=JSON.parse(require('fs').readFileSync('$SCORES_JSON','utf8'));process.stdout.write(String(s.overall.fn??''))" 2>/dev/null||echo '')"

if [[ "$IMPROVED" == "true" ]]; then
  # Archive current/ as a named experiment and commit
  FINAL_ID="exp-$(printf '%03d' "$(ls -d "$EXP_DIR/experiments"/exp-* 2>/dev/null | wc -l | tr -d ' ')")-$(date +%Y%m%d)"
  cp -r "$EXP_DIR/experiments/$FULL_ID" "$EXP_DIR/experiments/$FINAL_ID"
  git -C "$EXP_DIR/../../.." add "experiments/cr-skill-workflow/experiments/$FINAL_ID"
  git -C "$EXP_DIR/../../.." commit -m "feat(cr-skill-workflow): $FINAL_ID — F1=${FULL_F1} (+$(npx tsx -e "process.stdout.write((parseFloat('$FULL_F1')-$BASELINE_F1).toFixed(3))" 2>/dev/null||echo '?'))"
  COMMIT_NEW="$(git -C "$EXP_DIR" rev-parse --short HEAD 2>/dev/null || echo 'HEAD')"
  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\tkeep\t%s\n' \
    "$COMMIT_NEW" "$FINAL_ID" "$PROBE_F1" "$FULL_F1" "$FILE_F1" "$MOD_F1" "$TP" "$FP" "$FN" "$HYPOTHESIS" >> "$RESULTS_TSV"
  echo "✓ IMPROVED — committed as $FINAL_ID"
  BASELINE_F1="$FULL_F1"   # update in-memory baseline
else
  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\tdiscard\t%s\n' \
    "$COMMIT" "$FULL_ID" "$PROBE_F1" "$FULL_F1" "$FILE_F1" "$MOD_F1" "$TP" "$FP" "$FN" "$HYPOTHESIS" >> "$RESULTS_TSV"
  echo "✗ NO IMPROVEMENT — results saved, current/ unchanged"
fi
rm -rf "$EXP_DIR/experiments/$FULL_ID" "$EXP_DIR/experiments/$PROBE_ID" 2>/dev/null || true
echo "Done."
```

- [ ] **Step 2: Make executable**

```bash
chmod +x /home/bulat/code/skill-md-research/experiments/cr-skill-workflow/scripts/run-research-loop.sh
```

- [ ] **Step 3: Smoke-test argument validation**

```bash
cd /home/bulat/code/skill-md-research/experiments/cr-skill-workflow
bash scripts/run-research-loop.sh 2>&1 | grep -q "Usage:" && echo "PASS: usage guard works"
```

Expected: `PASS: usage guard works`

- [ ] **Step 4: Commit**

```bash
cd /home/bulat/code/skill-md-research
git add experiments/cr-skill-workflow/scripts/run-research-loop.sh
git commit -m "feat(cr-skill-workflow): add run-research-loop.sh — probe+sweep+commit/revert"
```

---

### Task 13: Wire up `current/` and do a probe dry-run

**Files:**
- Create: `experiments/cr-skill-workflow/current/skills/code-review/SKILL.md` (copy from exp-001)

- [ ] **Step 1: Seed `current/` with exp-001's SKILL.md**

```bash
cp /home/bulat/code/skill-md-research/experiments/cr-skill-workflow/experiments/exp-001-multistep-prompt/skills/code-review/SKILL.md \
   /home/bulat/code/skill-md-research/experiments/cr-skill-workflow/current/skills/code-review/SKILL.md
```

- [ ] **Step 2: Run a probe-only eval**

```bash
cd /home/bulat/code/skill-md-research/experiments/cr-skill-workflow
bash scripts/run-research-loop.sh --eval --probe-only
```

Expected output:
```
=== PROBE: probe-YYYYMMDD-HHMMSS ===
[HH:MM:SS] task 101 (file)
   -> N findings, K kg calls, Xs
... (tasks 102, 103, 201, 202)
Probe F1: 0.XXX  (baseline: 0.204)
Probe-only mode — done. F1=0.XXX (threshold=0.184, pass=true/false)
```

This confirms the full loop infrastructure works end-to-end.

- [ ] **Step 3: Verify `results.tsv` is gitignored**

```bash
cd /home/bulat/code/skill-md-research
git status experiments/cr-skill-workflow/research/results.tsv
```

Expected: file is not shown (gitignored) or shows as untracked but not staged.

- [ ] **Step 4: Commit**

```bash
cd /home/bulat/code/skill-md-research
# current/ is gitignored — only commit the final status
git add experiments/cr-skill-workflow/
git status  # verify no unintended files staged
git commit -m "feat(cr-skill-workflow): complete framework — all tasks done"
```

---

## Self-review checklist (done inline)

**Spec coverage:**
- ✅ Directory scaffold + symlinks (Task 1)
- ✅ `aictrl-workflow.jsonc` with `__SKILLS_PATH__` (Task 1)
- ✅ Type-1 harness (Task 2)
- ✅ exp-001 4-step SKILL.md (Task 3)
- ✅ `render-template.ts` + tests (Task 5)
- ✅ Type-2 dag.yaml harness (Task 6)
- ✅ exp-002 two-pass (Task 7)
- ✅ `score.ts` (Task 9)
- ✅ `sync-experiment.ts` (Task 10)
- ✅ `research/loop.md` + `probe-tasks.txt` + `results.tsv` header (Task 11)
- ✅ `run-research-loop.sh` (Task 12)
- ✅ `current/` seeded + probe dry-run (Task 13)

**Placeholders:** None found.

**Type consistency:** `scores.json` shape (written by `score.ts`, read by `sync-experiment.ts` and `run-research-loop.sh`) is consistent: `{ expId, overall: { f1, p, r, tp, fp, fn, n }, byScope: { file: {...}, module: {...} } }`.
