#!/usr/bin/env bash
set -uo pipefail   # NOT -e: one bad task must never kill the whole sweep
# Production-relatable sweep runner: drives `aictrl run` (the real code-review
# CLI) over every task for ONE condition x ONE rep.
#   control   = aictrl-control.jsonc   (KG MCP disabled; reviews inlined code only)
#   treatment = aictrl-treatment.jsonc (aictrl KG MCP + explore-context skill)
# Model: ollama gemma, reasoningEffort:none (thinking off). Reps vary by
# temperature 0.7 sampling (aictrl run has no --seed; documented caveat).
# Reads task source from tasks.json pinDir (a stable local snapshot — see
# snapshot-task-files.sh — NOT a git worktree, which can be pruned mid-run).
#
# Usage: run-aictrl.sh --condition control|treatment --rep 1 [--task 205]
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXP_DIR="$(dirname "$SCRIPT_DIR")"
MODEL="ollama/gemma4:12b-cr"
SCRATCH=/tmp/cr-scratch; mkdir -p "$SCRATCH"

COND=""; REP=""; ONLY=""; CONFIG_OVERRIDE=""
while [[ $# -gt 0 ]]; do case $1 in
  --condition) COND="$2"; shift 2;;
  --rep) REP="$2"; shift 2;;
  --task) ONLY="$2"; shift 2;;
  --model) MODEL="$2"; shift 2;;
  --config) CONFIG_OVERRIDE="$2"; shift 2;;
  *) echo "unknown arg $1"; exit 1;;
esac; done
[[ -n "$COND" && -n "$REP" ]] || { echo "need --condition and --rep"; exit 1; }

# config: explicit --config wins; else default aictrl-{cond}.jsonc
if [[ -n "$CONFIG_OVERRIDE" ]]; then
  export AICTRL_CONFIG="$CONFIG_OVERRIDE"
else
  export AICTRL_CONFIG="$EXP_DIR/aictrl-${COND}.jsonc"
fi
# always source .env.local for AICTRL_MCP_TOKEN + ZHIPU_API_KEY etc.
[[ -f "$EXP_DIR/.env.local" ]] && { set -a; . "$EXP_DIR/.env.local"; set +a; }
if [[ "$COND" == "treatment" ]]; then
  [[ -n "${AICTRL_MCP_TOKEN:-}" ]] || { echo "treatment needs AICTRL_MCP_TOKEN in .env.local"; exit 1; }
fi

PIN_DIR="$(npx tsx -e 'console.log(JSON.parse(require("fs").readFileSync(process.argv[1])).pinDir)' "$EXP_DIR/tasks/tasks.json")"

# Read task list into an array (no pipe-to-while: avoids subshell + stdin issues)
mapfile -t TASK_LINES < <(npx tsx -e '
  const t=JSON.parse(require("fs").readFileSync(process.argv[1]));
  for (const x of t.tasks) console.log([x.id,x.class,x.paths.join(",")].join("\t"));
' "$EXP_DIR/tasks/tasks.json")

for line in "${TASK_LINES[@]}"; do
  IFS=$'\t' read -r ID CLASS PATHS <<< "$line"
  [[ -n "$ONLY" && "$ID" != "$ONLY" ]] && continue

  # verify every source file exists in the snapshot; skip the task if not
  miss=""
  IFS=',' read -ra PARR <<< "$PATHS"
  for p in "${PARR[@]}"; do [[ -f "$PIN_DIR/$p" ]] || miss="$p"; done
  if [[ -n "$miss" ]]; then echo "[$(date +%H:%M:%S)] SKIP $COND rep$REP task $ID — missing $miss"; continue; fi

  OUT_DIR="$EXP_DIR/results/raw/rep-${REP}/${COND}/${CLASS}s"; mkdir -p "$OUT_DIR"
  SESSION="$OUT_DIR/PR-${ID}.session.json"; LOG="$OUT_DIR/PR-${ID}.log"
  FIND="$OUT_DIR/PR-${ID}.findings.json"

  PROMPT="$(npx tsx -e '
    const fs=require("fs");const repo=process.argv[1];const paths=process.argv[2].split(",");const cond=process.argv[3];
    const blocks=paths.map(p=>`\n--- FILE: ${p} ---\n\`\`\`\n${fs.readFileSync(repo+"/"+p,"utf8")}\n\`\`\`\n`).join("\n");
    const kgNote = cond==="treatment"
      ? "Follow the explore-context protocol: verify findings with query_context (callers/impact/search) before recording them."
      : "The code is provided inline — review it directly without graph tools.";
    process.stdout.write(`Use your code-review skill to review the following aictrl source file(s) for real defects. ${kgNote} Output findings as a JSON array.\n${blocks}`);
  ' "$PIN_DIR" "$PATHS" "$COND")"
  if [[ -z "$PROMPT" ]]; then echo "[$(date +%H:%M:%S)] SKIP $COND rep$REP task $ID — empty prompt"; continue; fi

  echo "[$(date +%H:%M:%S)] $COND rep$REP task $ID ($CLASS)"
  START=$(date +%s)
  aictrl run --print-logs --log-level INFO --format json --dir "$SCRATCH" --model "$MODEL" \
    --title "cr-${COND}-${REP}-${ID}" "$PROMPT" </dev/null >"$SESSION" 2>"$LOG" || true
  DUR=$(($(date +%s)-START))

  # parse findings (fail-soft: empty array if the session produced nothing)
  npx tsx "$SCRIPT_DIR/parse-session.ts" --session "$SESSION" --pr "$ID" --out "$FIND" 2>/dev/null \
    || printf '{"prNumber":%s,"findings":[]}\n' "$ID" > "$FIND"

  KG=$(grep -c 'permission=aictrl_query_context' "$LOG" 2>/dev/null) || true
  [[ "$KG" =~ ^[0-9]+$ ]] || KG=0
  N=$(npx tsx -e 'try{console.log(JSON.parse(require("fs").readFileSync(process.argv[1])).findings.length)}catch{console.log(0)}' "$FIND" 2>/dev/null || echo 0)
  [[ "$N" =~ ^[0-9]+$ ]] || N=0

  printf '{"prNumber":%s,"condition":"%s","rep":%s,"class":"%s","durationSeconds":%s,"queryContextCalls":%s,"findings":%s}\n' \
    "$ID" "$COND" "$REP" "$CLASS" "$DUR" "$KG" "$N" > "$OUT_DIR/PR-${ID}.meta.json"
  echo "$ID,$CLASS,$COND,$REP,$N,$KG,$DUR" >> "$EXP_DIR/results/timing.csv"
  echo "   -> $N findings, $KG query_context calls, ${DUR}s"
done
echo "done: $COND rep $REP"
