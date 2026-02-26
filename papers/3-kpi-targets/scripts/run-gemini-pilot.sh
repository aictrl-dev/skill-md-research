#!/usr/bin/env bash
set -euo pipefail

# ─────────────────────────────────────────────────────────────────────────────
# Gemini 3.1 Pro Pilot: Markdown vs Pseudocode on Chart Domain
# Quick test: 1 task, no reps, 2 conditions
# ─────────────────────────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RESEARCH_DIR="$(dirname "$SCRIPT_DIR")"
ROOT_DIR="$(dirname "$(dirname "$RESEARCH_DIR")")"

DOMAIN="chart"
MODEL="gemini-3.1-pro-preview"
SAFE_MODEL="gemini-3.1-pro-preview"
TASK_FILE="${ROOT_DIR}/domains/chart/test-data/task-1-gdp.json"

MARKDOWN_SKILL="${ROOT_DIR}/domains/chart/skills/chart-style-markdown/SKILL.md"
PSEUDOCODE_SKILL="${ROOT_DIR}/domains/chart/skills/chart-style-pseudocode/SKILL.md"

OUR_RESULTS_DIR="${RESEARCH_DIR}/domains/chart/results"
mkdir -p "$OUR_RESULTS_DIR"

# ─── Task Prompt ──────────────────────────────────────────────────────────────

build_task_prompt() {
  local task_file="$1"
  local task_json=$(cat "$task_file")
  local chart_type=$(echo "$task_json" | jq -r '.chart_type')
  local data=$(echo "$task_json" | jq -c '.data // .series')
  local metadata=$(echo "$task_json" | jq -c '.metadata')
  local requirements=$(echo "$task_json" | jq -c '.requirements')

  echo "Generate a ${chart_type} chart specification in JSON format.

Data: ${data}
Metadata: ${metadata}
Requirements: ${requirements}

Output ONLY the chart specification as JSON. No explanation."
}

# ─── Build Prompt ─────────────────────────────────────────────────────────────

build_prompt() {
  local skill_file="$1"
  local task_prompt=$(build_task_prompt "$TASK_FILE")
  local skill_content=$(cat "$skill_file")

  # Add a nonce to prevent caching between conditions
  local nonce=$(head -c 9 /dev/urandom | base64)

  cat <<EOF
IMPORTANT: Output your answer as TEXT only. Do NOT use file writing tools. Do NOT create files. Just output the content in text format using markdown code fences.

<!-- session: ${nonce} -->

---

Follow these chart specification guidelines:

${skill_content}

---

${task_prompt}
EOF
}

# ─── Run Gemini ───────────────────────────────────────────────────────────────

run_gemini() {
  local prompt="$1"
  local prompt_file="/tmp/gemini-exp-prompt-$$.txt"
  printf '%s' "$prompt" > "$prompt_file"

  local result=""
  result=$(gemini -p "$(cat "$prompt_file")" -m "$MODEL" --output-format json --sandbox false 2>&1) || true

  rm -f "$prompt_file"
  echo "$result"
}

# ─── Run Conditions ───────────────────────────────────────────────────────────

CONDITIONS=(
  "markdown|${MARKDOWN_SKILL}"
  "pseudocode|${PSEUDOCODE_SKILL}"
)

task_id=$(jq -r '.task_id' "$TASK_FILE")

echo "=== Gemini 3.1 Pro Pilot: Chart Task ${task_id} ==="
echo "Model: ${MODEL}"
echo "Results: ${OUR_RESULTS_DIR}"
echo ""

for entry in "${CONDITIONS[@]}"; do
  IFS='|' read -r condition skill_file <<< "$entry"
  run_id="${SAFE_MODEL}_${condition}_task${task_id}_rep1"

  if [[ -f "${OUR_RESULTS_DIR}/${run_id}.json" ]]; then
    echo "[SKIP] ${run_id} (already exists)"
    continue
  fi

  echo "[RUN] ${run_id}"
  prompt=$(build_prompt "$skill_file")

  output_file="/tmp/gemini-exp-output-$$.json"

  start_time=$(date +%s%N)
  output=$(run_gemini "$prompt" 2>&1 || echo '{"error": "failed"}')
  end_time=$(date +%s%N)
  duration_ms=$(( (end_time - start_time) / 1000000 ))

  # Write output to temp file, then use --rawfile to avoid shell escaping issues
  printf '%s' "$output" > "$output_file"

  jq -n \
    --arg run_id "$run_id" \
    --arg model "$MODEL" \
    --arg condition "$condition" \
    --arg task "$task_id" \
    --arg domain "$DOMAIN" \
    --argjson rep 1 \
    --arg timestamp "$(date -Iseconds)" \
    --argjson duration_ms "$duration_ms" \
    --arg cli_tool "gemini" \
    --rawfile raw_output "$output_file" \
    '{run_id: $run_id, model: $model, condition: $condition, task: $task, domain: $domain, rep: $rep, timestamp: $timestamp, duration_ms: $duration_ms, cli_tool: $cli_tool, raw_output: $raw_output}' \
    > "${OUR_RESULTS_DIR}/${run_id}.json"

  rm -f "$output_file"

  echo "  Done: ${duration_ms}ms"
  echo ""
  sleep 3
done

echo "=== Pilot complete ==="
echo ""
echo "Results:"
for entry in "${CONDITIONS[@]}"; do
  IFS='|' read -r condition skill_file <<< "$entry"
  run_id="${SAFE_MODEL}_${condition}_task${task_id}_rep1"
  if [[ -f "${OUR_RESULTS_DIR}/${run_id}.json" ]]; then
    echo "  ${run_id}.json"
  fi
done
