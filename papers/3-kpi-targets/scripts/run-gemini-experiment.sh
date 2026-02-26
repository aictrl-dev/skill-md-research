#!/usr/bin/env bash
set -euo pipefail

# ─────────────────────────────────────────────────────────────────────────────
# Gemini 3.1 Pro Experiment Runner
# 3 conditions (none, markdown, pseudocode) x 3 tasks x 3 reps = 27 per domain
# ─────────────────────────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RESEARCH_DIR="$(dirname "$SCRIPT_DIR")"
ROOT_DIR="$(dirname "$(dirname "$RESEARCH_DIR")")"

MODEL="gemini-3.1-pro-preview"
SAFE_MODEL="gemini-3.1-pro-preview"
CONDITIONS=("none" "markdown" "pseudocode")
REPS=3
SLEEP=5

# ─── Parse Arguments ────────────────────────────────────────────────────────

DOMAIN=""

usage() {
  echo "Usage: $0 --domain <chart|sql-query|dockerfile|terraform>"
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --domain) DOMAIN="$2"; shift 2 ;;
    *) echo "Unknown: $1"; usage ;;
  esac
done

[[ -z "$DOMAIN" ]] && usage

# ─── Domain Configuration ──────────────────────────────────────────────────

ORIG_DOMAIN_DIR="${ROOT_DIR}/domains/${DOMAIN}"
OUR_RESULTS_DIR="${RESEARCH_DIR}/domains/${DOMAIN}/results"

if [[ ! -d "$ORIG_DOMAIN_DIR" ]]; then
  echo "ERROR: Domain not found: ${ORIG_DOMAIN_DIR}"
  exit 1
fi

DATA_DIR="${ORIG_DOMAIN_DIR}/test-data"
SKILLS_DIR="${ORIG_DOMAIN_DIR}/skills"
mkdir -p "$OUR_RESULTS_DIR"

MARKDOWN_SKILL_DIR=$(ls -d "${SKILLS_DIR}"/*-markdown 2>/dev/null | head -1)
PSEUDOCODE_SKILL_DIR=$(ls -d "${SKILLS_DIR}"/*-pseudocode 2>/dev/null | head -1)

if [[ -z "$MARKDOWN_SKILL_DIR" || -z "$PSEUDOCODE_SKILL_DIR" ]]; then
  echo "ERROR: Could not find skill directories in ${SKILLS_DIR}"
  exit 1
fi

TASK_FILES=($(ls "${DATA_DIR}"/task-*.json 2>/dev/null | sort))
TASK_COUNT=${#TASK_FILES[@]}

echo "Domain: ${DOMAIN}"
echo "Model: ${MODEL}"
echo "Tasks: ${TASK_COUNT}"
echo "Conditions: ${CONDITIONS[*]}"
echo "Reps: ${REPS}"
echo "Results: ${OUR_RESULTS_DIR}"

# ─── Task Prompt Builders ──────────────────────────────────────────────────

build_task_prompt() {
  local task_file="$1"
  local task_json=$(cat "$task_file")

  case "$DOMAIN" in
    chart)
      local chart_type=$(echo "$task_json" | jq -r '.chart_type')
      local data=$(echo "$task_json" | jq -c '.data // .series')
      local metadata=$(echo "$task_json" | jq -c '.metadata')
      local requirements=$(echo "$task_json" | jq -c '.requirements')
      echo "Generate a ${chart_type} chart specification in JSON format.

Data: ${data}
Metadata: ${metadata}
Requirements: ${requirements}

Output ONLY the chart specification as JSON. No explanation."
      ;;
    sql-query)
      local desc=$(echo "$task_json" | jq -r '.description')
      echo "${desc}

Structure your answer as multiple SQL files. Output each file as a separate fenced SQL block with a filename comment line above it. Format:

-- filename.sql
\`\`\`sql
SELECT ...
\`\`\`

Output ONLY the SQL files. No explanation."
      ;;
    dockerfile)
      local desc=$(echo "$task_json" | jq -r '.description')
      echo "${desc}

Output ONLY the Dockerfile. No explanation."
      ;;
    terraform)
      local desc=$(echo "$task_json" | jq -r '.description')
      echo "${desc}

Output ONLY the Terraform configuration. No explanation."
      ;;
  esac
}

get_domain_label() {
  case "$DOMAIN" in
    chart) echo "chart specification" ;;
    sql-query) echo "dbt analytics pipeline" ;;
    dockerfile) echo "Dockerfile" ;;
    terraform) echo "Terraform configuration" ;;
  esac
}

# ─── Build Prompt ───────────────────────────────────────────────────────────

build_prompt() {
  local condition="$1"
  local task_file="$2"
  local task_prompt=$(build_task_prompt "$task_file")
  local domain_label=$(get_domain_label)

  # Nonce to prevent caching
  local nonce=$(head -c 9 /dev/urandom | base64)

  case "$condition" in
    none)
      cat <<EOF
IMPORTANT: Output your answer as TEXT only. Do NOT use file writing tools. Do NOT create files. Just output the content in text format using markdown code fences.

<!-- session: ${nonce} -->

---

${task_prompt}
EOF
      ;;
    markdown)
      local skill_content=$(cat "${MARKDOWN_SKILL_DIR}/SKILL.md")
      cat <<EOF
IMPORTANT: Output your answer as TEXT only. Do NOT use file writing tools. Do NOT create files. Just output the content in text format using markdown code fences.

<!-- session: ${nonce} -->

---

Follow these ${domain_label} guidelines:

${skill_content}

---

${task_prompt}
EOF
      ;;
    pseudocode)
      local skill_content=$(cat "${PSEUDOCODE_SKILL_DIR}/SKILL.md")
      cat <<EOF
IMPORTANT: Output your answer as TEXT only. Do NOT use file writing tools. Do NOT create files. Just output the content in text format using markdown code fences.

<!-- session: ${nonce} -->

---

Follow these ${domain_label} guidelines:

${skill_content}

---

${task_prompt}
EOF
      ;;
  esac
}

# ─── Run Gemini ─────────────────────────────────────────────────────────────

run_gemini() {
  local prompt="$1"
  local prompt_file="/tmp/gemini-exp-prompt-$$.txt"
  printf '%s' "$prompt" > "$prompt_file"

  local result=""
  result=$(gemini -p "$(cat "$prompt_file")" -m "$MODEL" --output-format json --sandbox false 2>&1) || true

  rm -f "$prompt_file"
  echo "$result"
}

# ─── Main Loop ──────────────────────────────────────────────────────────────

total=$((${#CONDITIONS[@]} * TASK_COUNT * REPS))
echo ""
echo "=== Running ${total} experiments ==="

completed=0
skipped=0

for condition in "${CONDITIONS[@]}"; do
  for task_file in "${TASK_FILES[@]}"; do
    task_id=$(jq -r '.task_id' "$task_file")
    complexity=$(jq -r '.complexity // "medium"' "$task_file")

    for rep in $(seq 1 $REPS); do
      run_id="${SAFE_MODEL}_${condition}_task${task_id}_rep${rep}"

      if [[ -f "${OUR_RESULTS_DIR}/${run_id}.json" ]]; then
        skipped=$((skipped + 1))
        continue
      fi

      echo "[$((completed + skipped + 1))/${total}] ${run_id}"
      prompt=$(build_prompt "$condition" "$task_file")

      output_file="/tmp/gemini-exp-output-$$.txt"

      start_time=$(date +%s%N)
      output=$(run_gemini "$prompt" 2>&1 || echo '{"error": "failed"}')
      end_time=$(date +%s%N)
      duration_ms=$(( (end_time - start_time) / 1000000 ))

      # Write output to temp file to avoid shell escaping issues with jq
      printf '%s' "$output" > "$output_file"

      jq -n \
        --arg run_id "$run_id" \
        --arg model "$MODEL" \
        --arg condition "$condition" \
        --arg task "$task_id" \
        --arg complexity "$complexity" \
        --arg domain "$DOMAIN" \
        --argjson rep "$rep" \
        --arg timestamp "$(date -Iseconds)" \
        --argjson duration_ms "$duration_ms" \
        --arg cli_tool "gemini" \
        --rawfile raw_output "$output_file" \
        '{run_id: $run_id, model: $model, condition: $condition, task: $task, task_complexity: $complexity, domain: $domain, rep: $rep, timestamp: $timestamp, duration_ms: $duration_ms, cli_tool: $cli_tool, raw_output: $raw_output}' \
        > "${OUR_RESULTS_DIR}/${run_id}.json"

      rm -f "$output_file"

      completed=$((completed + 1))
      echo "  Done: ${duration_ms}ms"
      sleep $SLEEP
    done
  done
done

echo ""
echo "=== Complete: ${completed} new, ${skipped} skipped ==="
