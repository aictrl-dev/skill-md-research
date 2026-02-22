#!/usr/bin/env bash
set -euo pipefail

# Re-run ONLY the 9 still-missing result files (SQL + Terraform)

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

unset CLAUDECODE 2>/dev/null || true
EMPTY_MCP="/tmp/experiment-empty-mcp.json"
echo '{"mcpServers":{}}' > "$EMPTY_MCP"

SLEEP_BETWEEN=5

run_model() {
  local model_id="$1" cli_tool="$2" prompt="$3"
  local prompt_file="/tmp/experiment-prompt-$$.txt"
  printf '%s' "$prompt" > "$prompt_file"
  local result=""
  case "$cli_tool" in
    claude)
      result=$(cd /tmp && claude -p "$(cat "$prompt_file")" --model "$model_id" --output-format json --no-session-persistence --mcp-config "$EMPTY_MCP" 2>&1) || true
      ;;
    opencode)
      result=$(opencode run -m "$model_id" --format json -f "$prompt_file" -- "Follow the instructions." 2>&1) || true
      ;;
  esac
  rm -f "$prompt_file"
  echo "$result"
}

build_sql_prompt() {
  local condition="$1" task_id="$2"
  local domain_dir="${ROOT_DIR}/domains/sql-query"
  local task_file
  task_file=$(ls "${domain_dir}/test-data/task-${task_id}-"*.json 2>/dev/null | head -1)
  local description
  description=$(jq -r '.description' "$task_file")
  local task_prompt="${description}

Structure your answer as multiple SQL files. Output each file as a separate fenced SQL block with a filename comment line above it. Format:

-- filename.sql
\`\`\`sql
SELECT ...
\`\`\`

Output ONLY the SQL files. No explanation."

  local skill
  skill=$(cat "${domain_dir}/skills/sql-style-${condition}/SKILL.md")
  printf 'Follow these SQL analytics pipeline guidelines:\n\n%s\n\n---\n\n%s' "$skill" "$task_prompt"
}

build_terraform_prompt() {
  local condition="$1" task_id="$2"
  local domain_dir="${ROOT_DIR}/domains/terraform"
  local task_file
  task_file=$(ls "${domain_dir}/test-data/task-${task_id}-"*.json 2>/dev/null | head -1)
  local description
  description=$(jq -r '.description' "$task_file")
  local task_prompt="${description}

Output ONLY the Terraform configuration. No explanation."

  local skill
  skill=$(cat "${domain_dir}/skills/terraform-style-${condition}/SKILL.md")
  printf 'Follow these Terraform configuration guidelines:\n\n%s\n\n---\n\n%s' "$skill" "$task_prompt"
}

# domain|model_id|cli_tool|condition|task_id|rep|results_dir|run_id
MISSING=(
  "sql-query|zai-coding-plan/glm-4.7|opencode|markdown|3|2|${ROOT_DIR}/domains/sql-query/results|zai-coding-plan-glm-4.7_markdown_task3_rep2"
  "sql-query|zai-coding-plan/glm-4.7|opencode|pseudocode|2|3|${ROOT_DIR}/domains/sql-query/results|zai-coding-plan-glm-4.7_pseudocode_task2_rep3"
  "sql-query|zai-coding-plan/glm-4.7|opencode|pseudocode|3|5|${ROOT_DIR}/domains/sql-query/results|zai-coding-plan-glm-4.7_pseudocode_task3_rep5"
  "sql-query|zai-coding-plan/glm-5|opencode|markdown|1|5|${ROOT_DIR}/domains/sql-query/results|zai-coding-plan-glm-5_markdown_task1_rep5"
  "sql-query|zai-coding-plan/glm-5|opencode|markdown|3|3|${ROOT_DIR}/domains/sql-query/results|zai-coding-plan-glm-5_markdown_task3_rep3"
  "sql-query|zai-coding-plan/glm-5|opencode|pseudocode|2|2|${ROOT_DIR}/domains/sql-query/results|zai-coding-plan-glm-5_pseudocode_task2_rep2"
  "terraform|zai-coding-plan/glm-5|opencode|markdown|2|2|${ROOT_DIR}/domains/terraform/results|zai-coding-plan-glm-5_markdown_task2_rep2"
  "terraform|zai-coding-plan/glm-5|opencode|pseudocode|2|1|${ROOT_DIR}/domains/terraform/results|zai-coding-plan-glm-5_pseudocode_task2_rep1"
  "terraform|haiku|claude|pseudocode|3|2|${ROOT_DIR}/domains/terraform/results|haiku_pseudocode_task3_rep2"
)

echo "=== Re-running ${#MISSING[@]} missing results ==="

completed=0
for entry in "${MISSING[@]}"; do
  IFS='|' read -r domain model_id cli_tool condition task_id rep results_dir run_id <<< "$entry"
  out_file="${results_dir}/${run_id}.json"

  if [[ -f "$out_file" ]]; then
    echo "SKIP: ${run_id} (exists)"
    continue
  fi

  echo "[$(( completed + 1 ))/${#MISSING[@]}] ${run_id}"

  prompt=""
  if [[ "$domain" == "sql-query" ]]; then
    prompt=$(build_sql_prompt "$condition" "$task_id")
  else
    prompt=$(build_terraform_prompt "$condition" "$task_id")
  fi

  task_file_meta=$(ls "${ROOT_DIR}/domains/${domain}/test-data/task-${task_id}-"*.json 2>/dev/null | head -1)
  complexity=$(jq -r '.complexity' "$task_file_meta")

  start_time=$(date +%s%N)
  output=$(run_model "$model_id" "$cli_tool" "$prompt" 2>&1 || true)
  end_time=$(date +%s%N)
  duration_ms=$(( (end_time - start_time) / 1000000 ))

  if [[ -z "$output" ]]; then
    echo "  WARN: empty output"
    output='{"error": "empty output"}'
  fi

  jq -n \
    --arg run_id "$run_id" \
    --arg model "$model_id" \
    --arg condition "$condition" \
    --arg task "$task_id" \
    --arg complexity "$complexity" \
    --arg domain "$domain" \
    --argjson rep "$rep" \
    --arg timestamp "$(date -Iseconds)" \
    --argjson duration_ms "$duration_ms" \
    --arg cli_tool "$cli_tool" \
    --arg raw_output "$output" \
    '{run_id: $run_id, model: $model, condition: $condition, task: $task,
      task_complexity: $complexity, domain: $domain, rep: $rep,
      timestamp: $timestamp, duration_ms: $duration_ms,
      cli_tool: $cli_tool, raw_output: $raw_output}' > "$out_file"

  completed=$((completed + 1))
  echo "  Done: ${duration_ms}ms"
  sleep "$SLEEP_BETWEEN"
done

echo ""
echo "=== Complete: ${completed} runs ==="
