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
