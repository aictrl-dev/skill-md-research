#!/usr/bin/env bash
set -euo pipefail

# Quick pilot: 9 runs — haiku × 3 conditions × 3 tasks, 1 rep each
# Tests whether commit-message domain evaluation makes sense

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOMAIN_DIR="${SCRIPT_DIR}/../domains/commit-message"
RESULTS_DIR="${DOMAIN_DIR}/results"
SKILLS_DIR="${DOMAIN_DIR}/skills"
DATA_DIR="${DOMAIN_DIR}/test-data"

# Prevent claude CLI nesting error
unset CLAUDECODE 2>/dev/null || true

EMPTY_MCP="/tmp/experiment-empty-mcp.json"
echo '{"mcpServers":{}}' > "$EMPTY_MCP"

MODEL="haiku"
CONDITIONS=("none" "markdown" "pseudocode")
TASK_FILES=("${DATA_DIR}/task-1-bugfix.json" "${DATA_DIR}/task-2-feature.json" "${DATA_DIR}/task-3-breaking.json")

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
  # Remove YAML frontmatter (--- ... ---) from start of file
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

total=9
count=0

for condition in "${CONDITIONS[@]}"; do
  for task_file in "${TASK_FILES[@]}"; do
    task_id=$(jq -r '.task_id' "$task_file")
    complexity=$(jq -r '.complexity' "$task_file")
    run_id="${MODEL}_${condition}_task${task_id}_rep1"

    if [[ -f "${RESULTS_DIR}/${run_id}.json" ]]; then
      echo "SKIP: ${run_id} (exists)"
      count=$((count + 1))
      continue
    fi

    count=$((count + 1))
    echo "[${count}/${total}] ${run_id}"

    prompt=$(build_prompt "$condition" "$task_file")
    prompt_file="/tmp/experiment-prompt-$$.txt"
    printf '%s' "$prompt" > "$prompt_file"

    start_time=$(date +%s%N)
    output=$(cd /tmp && cat "$prompt_file" | claude -p - --model "$MODEL" --output-format json --no-session-persistence --mcp-config "$EMPTY_MCP" 2>&1) || true
    end_time=$(date +%s%N)
    duration_ms=$(( (end_time - start_time) / 1000000 ))

    rm -f "$prompt_file"

    jq -n \
      --arg run_id "$run_id" \
      --arg model "$MODEL" \
      --arg condition "$condition" \
      --arg task "$task_id" \
      --arg complexity "$complexity" \
      --arg domain "commit-message" \
      --argjson rep 1 \
      --arg timestamp "$(date -Iseconds)" \
      --argjson duration_ms "$duration_ms" \
      --arg cli_tool "claude" \
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

    echo "  Done: ${duration_ms}ms"
    sleep 3
  done
done

echo ""
echo "=== Pilot complete. Run evaluator separately: ==="
echo "  cd domains/commit-message && python3 evaluate_commits.py results/haiku_*_rep1.json"
