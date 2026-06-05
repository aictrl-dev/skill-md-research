#!/usr/bin/env bash
set -euo pipefail
# Production-relatable sweep runner: drives `aictrl run` (the real code-review
# CLI) over every task for ONE condition x ONE rep.
#   control   = aictrl-control.jsonc   (no KG MCP; reviews inlined code only)
#   treatment = aictrl-treatment.jsonc (aictrl KG MCP + explore-context skill)
# Model: ollama gemma with reasoningEffort:none (thinking off). Reps vary by
# temperature 0.7 sampling (aictrl run has no --seed; documented caveat).
#
# Usage: run-aictrl.sh --condition control|treatment --rep 1 [--task 205]
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXP_DIR="$(dirname "$SCRIPT_DIR")"
MODEL="ollama/gemma4:12b-cr"
SCRATCH=/tmp/cr-scratch; mkdir -p "$SCRATCH"

COND=""; REP=""; ONLY=""
while [[ $# -gt 0 ]]; do case $1 in
  --condition) COND="$2"; shift 2;;
  --rep) REP="$2"; shift 2;;
  --task) ONLY="$2"; shift 2;;
  *) echo "unknown arg $1"; exit 1;;
esac; done
[[ -n "$COND" && -n "$REP" ]] || { echo "need --condition and --rep"; exit 1; }

export AICTRL_CONFIG="$EXP_DIR/aictrl-${COND}.jsonc"
if [[ "$COND" == "treatment" ]]; then
  set -a; . "$EXP_DIR/.env.local"; set +a
  [[ -n "${AICTRL_MCP_TOKEN:-}" ]] || { echo "treatment needs AICTRL_MCP_TOKEN in .env.local"; exit 1; }
fi

PIN_DIR="$(npx tsx -e 'console.log(JSON.parse(require("fs").readFileSync(process.argv[1])).pinDir)' "$EXP_DIR/tasks/tasks.json")"

npx tsx -e '
  const t=JSON.parse(require("fs").readFileSync(process.argv[1]));
  for (const x of t.tasks) console.log([x.id,x.class,x.paths.join(",")].join("\t"));
' "$EXP_DIR/tasks/tasks.json" | while IFS=$'\t' read -r ID CLASS PATHS; do
  [[ -n "$ONLY" && "$ID" != "$ONLY" ]] && continue
  OUT_DIR="$EXP_DIR/results/raw/rep-${REP}/${COND}/${CLASS}s"; mkdir -p "$OUT_DIR"
  SESSION="$OUT_DIR/PR-${ID}.session.json"; LOG="$OUT_DIR/PR-${ID}.log"
  # skill-driven prompt: instruct the code-review skill + explore-context KG protocol, inline the file(s)
  PROMPT="$(npx tsx -e '
    const fs=require("fs");const repo=process.argv[1];const paths=process.argv[2].split(",");
    const blocks=paths.map(p=>`\n--- FILE: ${p} ---\n\`\`\`\n${fs.readFileSync(repo+"/"+p,"utf8")}\n\`\`\`\n`).join("\n");
    process.stdout.write("Use your code-review skill to review the following aictrl source file(s) for real defects. Follow the explore-context protocol: verify findings with query_context (callers/impact/search) before recording them. Output findings as a JSON array.\n"+blocks);
  ' "$PIN_DIR" "$PATHS")"
  echo "[$(date +%H:%M:%S)] $COND rep$REP task $ID ($CLASS)"
  START=$(date +%s)
  # </dev/null: stop aictrl from consuming the while-loop's piped stdin (task list)
  aictrl run --print-logs --log-level INFO --format json --dir "$SCRATCH" --model "$MODEL" \
    --title "cr-${COND}-${REP}-${ID}" "$PROMPT" </dev/null >"$SESSION" 2>"$LOG" || true
  DUR=$(($(date +%s)-START))
  npx tsx "$SCRIPT_DIR/parse-session.ts" --session "$SESSION" --pr "$ID" --out "$OUT_DIR/PR-${ID}.findings.json"
  # grep -c prints "0" AND exits 1 on no-match — capture cleanly (no '|| echo 0'
  # which would emit "0\n0" and corrupt the CSV/meta). Force a single integer.
  KG=$(grep -c 'permission=aictrl_query_context' "$LOG" 2>/dev/null) || true
  [[ "$KG" =~ ^[0-9]+$ ]] || KG=0
  N=$(npx tsx -e 'console.log(JSON.parse(require("fs").readFileSync(process.argv[1])).findings.length)' "$OUT_DIR/PR-${ID}.findings.json")
  # persist per-review timing/KG so aggregate.ts + the report can use it
  printf '{"prNumber":%s,"condition":"%s","rep":%s,"class":"%s","durationSeconds":%s,"queryContextCalls":%s,"findings":%s}\n' \
    "$ID" "$COND" "$REP" "$CLASS" "$DUR" "$KG" "$N" > "$OUT_DIR/PR-${ID}.meta.json"
  echo "$ID,$CLASS,$COND,$REP,$N,$KG,$DUR" >> "$EXP_DIR/results/timing.csv"
  echo "   -> $N findings, $KG query_context calls, ${DUR}s"
done
echo "done: $COND rep $REP"
