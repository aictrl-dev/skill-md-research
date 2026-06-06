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

# Generate the aictrl config: the per-experiment skills dir holds the candidate
# being varied (code-review), while base-skills holds shared infrastructure
# (explore-context — the skill that actually drives query_context / KG usage).
# Both are loaded so every experiment can reach the knowledge graph.
SKILLS_PATH="$EXP_PATH/skills"
BASE_SKILLS_PATH="$EXP_DIR/base-skills"
# Per-experiment config override: experiments/<id>/aictrl.jsonc wins over the
# shared default (lets an experiment flip thinking on, change model opts, etc.).
CONFIG_SRC="$EXP_DIR/aictrl-workflow.jsonc"
[[ -f "$EXP_PATH/aictrl.jsonc" ]] && CONFIG_SRC="$EXP_PATH/aictrl.jsonc"
TMP_CONFIG=$(mktemp /tmp/aictrl-wf-XXXXXX.jsonc)
trap 'rm -f "$TMP_CONFIG"' EXIT
sed -e "s|__BASE_SKILLS_PATH__|$BASE_SKILLS_PATH|g" \
    -e "s|__SKILLS_PATH__|$SKILLS_PATH|g" \
    "$CONFIG_SRC" > "$TMP_CONFIG"
export AICTRL_CONFIG="$TMP_CONFIG"

# --- TYPE DETECTION ---
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

    miss=()
    IFS=',' read -ra PARR <<< "$PATHS"
    for p in "${PARR[@]}"; do [[ -f "$PIN_DIR/$p" ]] || miss+=("$p"); done
    [[ ${#miss[@]} -gt 0 ]] && { echo "[$(date +%H:%M:%S)] SKIP task $ID — missing ${miss[*]}"; continue; }

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
      NODE_TYPE="$(echo "$NODE_CONFIG" | npx tsx -e "
        process.stdout.write(JSON.parse(require('fs').readFileSync('/dev/stdin','utf8')).type || 'model');
      ")"

      # --- SCRIPT node: deterministic, no AI budget. Runs an executable that
      # emits a context string on stdout; exposed downstream as {{NODE.context}}.
      # Produces NO findings (not unioned). run path is relative to the workflow root.
      if [[ "$NODE_TYPE" == "script" ]]; then
        RUN_REL="$(echo "$NODE_CONFIG" | npx tsx -e "process.stdout.write(JSON.parse(require('fs').readFileSync('/dev/stdin','utf8')).run);")"
        ART_FILE="$(mktemp "$TASK_SCRATCH/artefacts-${NODE}-XXXXXX.json")"; printf '%s' "$ARTEFACTS_JSON" > "$ART_FILE"
        CTX_FILE="$TASK_SCRATCH/context-${NODE}.txt"
        echo "[$(date +%H:%M:%S)] task $ID node $NODE (script: $RUN_REL)"
        npx tsx "$EXP_DIR/$RUN_REL" --pr "$ID" --paths "$PATHS" --pindir "$PIN_DIR" \
          --artefacts "$ART_FILE" >"$CTX_FILE" 2>"$TASK_SCRATCH/log-${NODE}.txt" || true
        ARTEFACTS_JSON="$(CTX="$(cat "$CTX_FILE")" npx tsx -e "
          const a=JSON.parse(process.argv[1]); a['$NODE']={context: process.env.CTX || ''};
          process.stdout.write(JSON.stringify(a));
        " "$ARTEFACTS_JSON")"
        continue
      fi

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

    # Write the final result. output: "union" merges every node's findings
    # (dedup on file+line) — required when later nodes emit only INCREMENTAL
    # findings (e.g. a two-pass chain where pass2 reports "what pass1 missed";
    # copying pass2 alone would silently drop pass1's true positives). Any other
    # value names a single node whose findings.json is copied verbatim (use this
    # for replace/filter passes that re-emit the full set).
    OUT_DIR="$EXP_DIR/results/$EXP_ID/rep-${REP}/treatment/${CLASS}s"; mkdir -p "$OUT_DIR"
    FIND="$OUT_DIR/PR-${ID}.findings.json"
    if [[ "$OUTPUT_NODE" == "union" ]]; then
      FIND="$FIND" npx tsx -e '
        const fs=require("fs");
        const pr=parseInt(process.argv[1]); const seen=new Set(); const all=[];
        for (const f of process.argv.slice(2)) {
          for (const x of (JSON.parse(fs.readFileSync(f,"utf8")).findings ?? [])) {
            const k=`${x.file}:${x.line}`;
            if (!seen.has(k)) { seen.add(k); all.push(x); }
          }
        }
        fs.writeFileSync(process.env.FIND, JSON.stringify({prNumber:pr, findings:all}, null, 2));
      ' "$ID" "$TASK_SCRATCH"/findings-*.json
    else
      cp "$TASK_SCRATCH/findings-${OUTPUT_NODE}.json" "$FIND"
    fi

    # Persist each node's findings too (enables per-lens ablation: score one node
    # in isolation via score.ts --node). Named PR-<id>.<node>.findings.json so the
    # PR-<id>.findings.json glob for the final result still matches only the result.
    for NF in "$TASK_SCRATCH"/findings-*.json; do
      NODE_OF="$(basename "$NF" .json)"; NODE_OF="${NODE_OF#findings-}"
      cp "$NF" "$OUT_DIR/PR-${ID}.${NODE_OF}.findings.json"
    done

    N=$(npx tsx -e 'try{console.log(JSON.parse(require("fs").readFileSync(process.argv[1])).findings.length)}catch{console.log(0)}' "$FIND" 2>/dev/null || echo 0)
    [[ "$N" =~ ^[0-9]+$ ]] || N=0
    printf '{"prNumber":%s,"condition":"treatment","rep":%s,"class":"%s","durationSeconds":%s,"findings":%s}\n' \
      "$ID" "$REP" "$CLASS" "$DUR_TASK" "$N" > "$OUT_DIR/PR-${ID}.meta.json"
    echo "   -> $N findings total, ${DUR_TASK}s"
  done
  echo "done: rep $REP of $EXP_ID (type 2)"
  exit 0
fi

# --- TYPE 1: single aictrl run per task ---
mapfile -t TASK_LINES < <(npx tsx -e '
  const t=JSON.parse(require("fs").readFileSync(process.argv[1]));
  for (const x of t.tasks) console.log([x.id,x.class,x.paths.join(",")].join("\t"));
' "$EXP_DIR/tasks/tasks.json")

for line in "${TASK_LINES[@]}"; do
  IFS=$'\t' read -r ID CLASS PATHS <<< "$line"
  [[ -n "$ONLY" && "$ID" != "$ONLY" ]] && continue

  miss=()
  IFS=',' read -ra PARR <<< "$PATHS"
  for p in "${PARR[@]}"; do [[ -f "$PIN_DIR/$p" ]] || miss+=("$p"); done
  if [[ ${#miss[@]} -gt 0 ]]; then echo "[$(date +%H:%M:%S)] SKIP task $ID — missing ${miss[*]}"; continue; fi

  OUT_DIR="$EXP_DIR/results/$EXP_ID/rep-${REP}/treatment/${CLASS}s"; mkdir -p "$OUT_DIR"
  SESSION="$OUT_DIR/PR-${ID}.session.json"
  FIND="$OUT_DIR/PR-${ID}.findings.json"
  LOG="$OUT_DIR/PR-${ID}.log"

  # Instruction line: an experiment may override the default via prompt.md.
  # This is where KG-nudging lives — gemma reliably calls query_context only
  # when the task prompt tells it to (the skill file alone is not enough for a
  # 12B model), so a KG experiment ships a prompt.md that names the protocol.
  DEFAULT_INSTRUCTION="Use your code-review skill to review the following source file(s) for real defects. Output findings as a JSON array."
  if [[ -f "$EXP_PATH/prompt.md" ]]; then
    INSTRUCTION="$(cat "$EXP_PATH/prompt.md")"
  else
    INSTRUCTION="$DEFAULT_INSTRUCTION"
  fi
  PROMPT="$(INSTRUCTION="$INSTRUCTION" npx tsx -e '
    const fs=require("fs");
    const repo=process.argv[1], paths=process.argv[2].split(",");
    const blocks=paths.map(p=>`\n--- FILE: ${p} ---\n\`\`\`\n${fs.readFileSync(repo+"/"+p,"utf8")}\n\`\`\`\n`).join("\n");
    process.stdout.write(process.env.INSTRUCTION+"\n"+blocks);
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

  # grep -c prints "0" AND exits non-zero on zero matches; capture, then sanitise
  # (a bare `|| echo 0` would append a second line and corrupt the JSON below).
  KG=$(grep -c 'permission=aictrl_query_context' "$LOG" 2>/dev/null) || true
  [[ "$KG" =~ ^[0-9]+$ ]] || KG=0
  N=$(npx tsx -e 'try{console.log(JSON.parse(require("fs").readFileSync(process.argv[1])).findings.length)}catch{console.log(0)}' "$FIND" 2>/dev/null || echo 0)
  [[ "$N" =~ ^[0-9]+$ ]] || N=0
  printf '{"prNumber":%s,"condition":"treatment","rep":%s,"class":"%s","durationSeconds":%s,"queryContextCalls":%s,"findings":%s}\n' \
    "$ID" "$REP" "$CLASS" "$DUR" "$KG" "$N" > "$OUT_DIR/PR-${ID}.meta.json"

  echo "   -> $N findings, $KG kg calls, ${DUR}s"
done
echo "done: rep $REP of $EXP_ID"
