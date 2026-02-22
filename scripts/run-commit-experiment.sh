#!/usr/bin/env bash
set -euo pipefail

# Full commit-message experiment: 4 models × 3 conditions × 3 tasks × 5 reps = 180 runs
# (glm-4.7-flash excluded from analysis but not run here)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOMAIN_DIR="${SCRIPT_DIR}/../domains/commit-message"
RESULTS_DIR="${DOMAIN_DIR}/results"
SKILLS_DIR="${DOMAIN_DIR}/skills"
DATA_DIR="${DOMAIN_DIR}/test-data"

# Prevent claude CLI nesting error
unset CLAUDECODE 2>/dev/null || true

EMPTY_MCP="/tmp/experiment-empty-mcp.json"
echo '{"mcpServers":{}}' > "$EMPTY_MCP"

# Models: model_id|cli_tool|safe_name
MODELS=(
  "haiku|claude|haiku"
  "opus|claude|opus"
  "zai-coding-plan/glm-4.7|opencode|zai-coding-plan-glm-4.7"
  "zai-coding-plan/glm-5|opencode|zai-coding-plan-glm-5"
)

CONDITIONS=("none" "markdown" "pseudocode")
TASK_FILES=("${DATA_DIR}/task-1-bugfix.json" "${DATA_DIR}/task-2-feature.json" "${DATA_DIR}/task-3-breaking.json")
REPS=5
SLEEP_BETWEEN=3

mkdir -p "$RESULTS_DIR"

build_task_prompt() {
  local task_file="$1"
  local task_json
  task_json=$(cat "$task_file")

  local description change_type files_changed ticket author breaking breaking_desc
  description=$(echo "$task_json" | jq -r '.description')
  change_type=$(echo "$task_json" | jq -r '.change_type')
  files_changed=$(echo "$task_json" | jq -r '.files_changed | join(", ")')
  ticket=$(echo "$task_json" | jq -r '.ticket // empty')
  author=$(echo "$task_json" | jq -r '.author // empty')
  breaking=$(echo "$task_json" | jq -r '.breaking_change')
  breaking_desc=$(echo "$task_json" | jq -r '.breaking_change_description // empty')

  local prompt
  prompt="Write a conventional commit message for the following change:

Change type: ${change_type}
Description: ${description}
Files changed: ${files_changed}"
  [[ -n "$ticket" ]] && prompt="${prompt}
Ticket: ${ticket}"
  [[ -n "$author" ]] && prompt="${prompt}
Author: ${author}"
  [[ "$breaking" == "true" ]] && prompt="${prompt}
Breaking change: ${breaking_desc}"
  prompt="${prompt}

Output ONLY the commit message. No explanation."
  echo "$prompt"
}

strip_frontmatter() {
  local content="$1"
  echo "$content" | awk 'BEGIN{skip=0; fm=0} /^---$/{if(fm==0){fm=1;skip=1;next}else if(fm==1){fm=2;next}} fm==2||fm==0{print}'
}

build_prompt() {
  local condition="$1"
  local task_file="$2"
  local task_prompt
  task_prompt=$(build_task_prompt "$task_file")

  case "$condition" in
    none)
      echo "$task_prompt"
      ;;
    markdown)
      local skill_raw skill_content
      skill_raw=$(cat "${SKILLS_DIR}/commit-style-markdown/SKILL.md")
      skill_content=$(strip_frontmatter "$skill_raw")
      printf 'Follow these conventional commit guidelines:\n\n%s\n\n---\n\n%s' "$skill_content" "$task_prompt"
      ;;
    pseudocode)
      local skill_raw skill_content
      skill_raw=$(cat "${SKILLS_DIR}/commit-style-pseudocode/SKILL.md")
      skill_content=$(strip_frontmatter "$skill_raw")
      printf 'Follow these conventional commit guidelines:\n\n%s\n\n---\n\n%s' "$skill_content" "$task_prompt"
      ;;
  esac
}

run_model() {
  local model_id="$1"
  local cli_tool="$2"
  local prompt_file="$3"

  local result=""
  case "$cli_tool" in
    claude)
      result=$(cd /tmp && cat "$prompt_file" | claude -p - --model "$model_id" --output-format json --no-session-persistence --mcp-config "$EMPTY_MCP" 2>&1) || true
      ;;
    opencode)
      result=$(opencode run -m "$model_id" --format json -f "$prompt_file" -- "Follow the instructions." 2>&1) || true
      ;;
    *)
      echo "ERROR: Unknown CLI tool: $cli_tool" >&2
      return 1
      ;;
  esac
  echo "$result"
}

# Count total and existing
total=$(( ${#MODELS[@]} * ${#CONDITIONS[@]} * ${#TASK_FILES[@]} * REPS ))
echo "=== COMMIT-MESSAGE FULL EXPERIMENT ==="
echo "Models: ${#MODELS[@]} (haiku, opus, glm-4.7, glm-5)"
echo "Conditions: ${CONDITIONS[*]}"
echo "Tasks: ${#TASK_FILES[@]}"
echo "Reps: ${REPS}"
echo "Total: ${total} runs"
echo ""

completed=0
skipped=0
failed=0

for model_entry in "${MODELS[@]}"; do
  IFS='|' read -r model_id cli_tool safe_model <<< "$model_entry"

  for condition in "${CONDITIONS[@]}"; do
    for task_file in "${TASK_FILES[@]}"; do
      task_id=$(jq -r '.task_id' "$task_file")
      complexity=$(jq -r '.complexity' "$task_file")

      for rep in $(seq 1 "$REPS"); do
        run_id="${safe_model}_${condition}_task${task_id}_rep${rep}"
        progress=$(( completed + skipped + failed + 1 ))

        if [[ -f "${RESULTS_DIR}/${run_id}.json" ]]; then
          skipped=$((skipped + 1))
          continue
        fi

        echo "[${progress}/${total}] ${run_id} (${cli_tool})"

        prompt=$(build_prompt "$condition" "$task_file")
        prompt_file="/tmp/experiment-prompt-$$.txt"
        printf '%s' "$prompt" > "$prompt_file"

        start_time=$(date +%s%N)
        output=$(run_model "$model_id" "$cli_tool" "$prompt_file")
        end_time=$(date +%s%N)
        duration_ms=$(( (end_time - start_time) / 1000000 ))

        rm -f "$prompt_file"

        if [[ -z "$output" ]]; then
          echo "  FAILED: empty output"
          failed=$((failed + 1))
          output='{"error": "empty output"}'
        fi

        jq -n \
          --arg run_id "$run_id" \
          --arg model "$model_id" \
          --arg condition "$condition" \
          --arg task "$task_id" \
          --arg complexity "$complexity" \
          --arg domain "commit-message" \
          --argjson rep "$rep" \
          --arg timestamp "$(date -Iseconds)" \
          --argjson duration_ms "$duration_ms" \
          --arg cli_tool "$cli_tool" \
          --arg raw_output "$output" \
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

        completed=$((completed + 1))
        echo "  Done: ${duration_ms}ms"

        sleep "$SLEEP_BETWEEN"
      done
    done
  done
done

echo ""
echo "=== Experiment complete: commit-message ==="
echo "Completed: ${completed}"
echo "Skipped (existing): ${skipped}"
echo "Failed: ${failed}"
echo "Results in: ${RESULTS_DIR}/"
echo ""
echo "Run evaluator:"
echo "  PYTHONPATH=${SCRIPT_DIR} python3 ${DOMAIN_DIR}/evaluate_commits.py ${RESULTS_DIR}/*.json"
