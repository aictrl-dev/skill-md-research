#!/usr/bin/env bash
set -euo pipefail

# Run a single model for a domain experiment.
# Usage: run-single-model.sh --domain sql-query --model-index 0

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

unset CLAUDECODE 2>/dev/null || true

EMPTY_MCP="/tmp/experiment-empty-mcp.json"
echo '{"mcpServers":{}}' > "$EMPTY_MCP"

DOMAIN=""
MODEL_INDEX=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --domain) DOMAIN="$2"; shift 2 ;;
    --model-index) MODEL_INDEX="$2"; shift 2 ;;
    *) echo "Unknown: $1"; exit 1 ;;
  esac
done

[[ -z "$DOMAIN" || -z "$MODEL_INDEX" ]] && { echo "Usage: $0 --domain <name> --model-index <N>"; exit 1; }

DOMAIN_DIR="${SCRIPT_DIR}/domains/${DOMAIN}"
DATA_DIR="${DOMAIN_DIR}/test-data"
SKILLS_DIR="${DOMAIN_DIR}/skills"
RESULTS_DIR="${DOMAIN_DIR}/results"
TASK_FILES=($(ls "${DATA_DIR}"/task-*.json 2>/dev/null | sort))
MARKDOWN_SKILL_DIR=$(ls -d "${SKILLS_DIR}"/*-markdown 2>/dev/null | head -1)
PSEUDOCODE_SKILL_DIR=$(ls -d "${SKILLS_DIR}"/*-pseudocode 2>/dev/null | head -1)

CONDITIONS=("none" "markdown" "pseudocode")
MODELS=(
  "haiku|claude"
  "opus|claude"
  "zai-coding-plan/glm-4.7-flash|opencode"
  "zai-coding-plan/glm-4.7|opencode"
  "zai-coding-plan/glm-5|opencode"
)
REPS=5
SLEEP_BETWEEN=5

# Source the prompt-building functions from the main script
source <(sed -n '/^build_task_prompt/,/^}/p' "${SCRIPT_DIR}/run-domain-experiment.sh")
source <(sed -n '/^get_output_instruction/,/^}/p' "${SCRIPT_DIR}/run-domain-experiment.sh")
source <(sed -n '/^get_domain_label/,/^}/p' "${SCRIPT_DIR}/run-domain-experiment.sh")

build_prompt() {
  local condition="$1"
  local task_file="$2"
  local task_prompt
  task_prompt=$(build_task_prompt "$task_file")
  local domain_label
  domain_label=$(get_domain_label)

  case "$condition" in
    none) echo "$task_prompt" ;;
    markdown)
      local skill_content
      skill_content=$(cat "${MARKDOWN_SKILL_DIR}/SKILL.md")
      printf "Follow these %s guidelines:\n\n%s\n\n---\n\n%s" "$domain_label" "$skill_content" "$task_prompt"
      ;;
    pseudocode)
      local skill_content
      skill_content=$(cat "${PSEUDOCODE_SKILL_DIR}/SKILL.md")
      printf "Follow these %s guidelines:\n\n%s\n\n---\n\n%s" "$domain_label" "$skill_content" "$task_prompt"
      ;;
  esac
}

run_model() {
  local model_id="$1"
  local cli_tool="$2"
  local prompt="$3"
  local prompt_file="/tmp/experiment-prompt-$$.txt"
  printf '%s' "$prompt" > "$prompt_file"
  local result=""
  case "$cli_tool" in
    claude) result=$(cd /tmp && claude -p "$(cat "$prompt_file")" --model "$model_id" --output-format json --no-session-persistence --mcp-config "$EMPTY_MCP" 2>&1) || true ;;
    opencode) result=$(opencode run -m "$model_id" --format json -f "$prompt_file" -- "Follow the instructions." 2>&1) || true ;;
  esac
  rm -f "$prompt_file"
  echo "$result"
}

sanitize() { echo "$1" | tr '/' '-'; }

# Pick the model for this index
IFS='|' read -r model_id cli_tool <<< "${MODELS[$MODEL_INDEX]}"
safe_model=$(sanitize "$model_id")

total=$((${#CONDITIONS[@]} * ${#TASK_FILES[@]} * REPS))
echo "=== Model: ${model_id} (${cli_tool}) — ${total} runs ==="

mkdir -p "$RESULTS_DIR"
completed=0
skipped=0

for condition in "${CONDITIONS[@]}"; do
  for task_file in "${TASK_FILES[@]}"; do
    task_id=$(jq -r '.task_id' "$task_file")
    complexity=$(jq -r '.complexity' "$task_file")

    for rep in $(seq 1 "$REPS"); do
      run_id="${safe_model}_${condition}_task${task_id}_rep${rep}"

      if [[ -f "${RESULTS_DIR}/${run_id}.json" ]]; then
        skipped=$((skipped + 1))
        continue
      fi

      echo "[$(( completed + skipped + 1 ))/${total}] ${run_id}"

      prompt=$(build_prompt "$condition" "$task_file")

      start_time=$(date +%s%N)
      output=$(run_model "$model_id" "$cli_tool" "$prompt" 2>&1 || true)
      end_time=$(date +%s%N)
      duration_ms=$(( (end_time - start_time) / 1000000 ))

      if [[ -z "$output" ]]; then
        echo "  FAILED: empty output"
        output='{"error": "empty output"}'
      fi

      # Write output to temp file to avoid "Argument list too long" with jq --arg
      output_tmp="/tmp/experiment-output-$$.txt"
      printf '%s' "$output" > "$output_tmp"

      jq -n \
        --arg run_id "$run_id" \
        --arg model "$model_id" \
        --arg condition "$condition" \
        --arg task "$task_id" \
        --arg complexity "$complexity" \
        --arg domain "$DOMAIN" \
        --argjson rep "$rep" \
        --arg timestamp "$(date -Iseconds)" \
        --argjson duration_ms "$duration_ms" \
        --arg cli_tool "$cli_tool" \
        --rawfile raw_output "$output_tmp" \
        '{
          run_id: $run_id,
          model: $model,
          condition: $condition,
          task: $task,
          task_complexity: $complexity,
          domain: $domain,
          rep: $rep,
          timestamp: $timestamp,
          duration_ms: $duration_ms,
          cli_tool: $cli_tool,
          raw_output: $raw_output
        }' > "${RESULTS_DIR}/${run_id}.json"

      rm -f "$output_tmp"

      completed=$((completed + 1))
      echo "  Done: ${duration_ms}ms"
      sleep "$SLEEP_BETWEEN"
    done
  done
done

echo "=== Done: ${model_id} — completed=${completed}, skipped=${skipped} ==="
