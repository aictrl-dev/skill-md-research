#!/usr/bin/env bash
set -euo pipefail

# ─────────────────────────────────────────────────────────────────────────────
# Re-run 15 extraction-failure runs
#
# Self-contained: deletes old results, re-runs via the original experiment
# runners, then re-evaluates to regenerate scores.csv.
# ─────────────────────────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

# Prevent claude CLI nesting error
unset CLAUDECODE 2>/dev/null || true

# Empty MCP config to bypass plugin tool-name conflicts
EMPTY_MCP="/tmp/experiment-empty-mcp.json"
echo '{"mcpServers":{}}' > "$EMPTY_MCP"

SLEEP_BETWEEN=5

# ─── Helpers ───────────────────────────────────────────────────────────────

run_model() {
  local model_id="$1"
  local cli_tool="$2"
  local prompt="$3"

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

save_result() {
  local run_id="$1" model="$2" condition="$3" task_id="$4" complexity="$5"
  local domain="$6" rep="$7" duration_ms="$8" cli_tool="$9" output="${10}"
  local out_file="${11}"

  jq -n \
    --arg run_id "$run_id" \
    --arg model "$model" \
    --arg condition "$condition" \
    --arg task "$task_id" \
    --arg complexity "$complexity" \
    --arg domain "$domain" \
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
    }' > "$out_file"
}

# ─── Build domain-specific prompts ──────────────────────────────────────────

build_chart_prompt() {
  local condition="$1"
  local task_id="$2"

  local chart_dir="${ROOT_DIR}/domains/chart"
  local task_prompt
  task_prompt=$(jq -r '.description // empty' "${chart_dir}/test-data/task-${task_id}-"*.json)

  # Task 3 is cloud-revenue
  local task_file="${chart_dir}/test-data/task-3-cloud-revenue.json"
  task_prompt="Create a chart comparing the three major cloud providers:

Data (quarterly revenue in USD billions):
Quarter | AWS  | Azure | GCP
2023-Q1 | 21.3 | 21.0  | 7.0
2023-Q2 | 22.1 | 23.0  | 8.0
2023-Q3 | 23.1 | 24.0  | 8.4
2023-Q4 | 24.2 | 25.0  | 9.2
2024-Q1 | 25.0 | 26.0  | 9.6
2024-Q2 | 26.0 | 28.0  | 10.3
2024-Q3 | 27.5 | 29.0  | 11.4
2024-Q4 | 28.8 | 30.0  | 12.0

Key insight: Azure overtook AWS in Q2 2024
Highlight: The crossover point
Source: Company earnings reports, 2023-2024"

  case "$condition" in
    markdown)
      local skill
      skill=$(cat "${chart_dir}/skills/chart-style-markdown/SKILL.md")
      cat <<EOF
Follow these chart style guidelines:

${skill}

---

${task_prompt}

Generate a chart specification as JSON.
EOF
      ;;
    pseudocode)
      local skill
      skill=$(cat "${chart_dir}/skills/chart-style-pseudocode/SKILL.md")
      cat <<EOF
Follow these chart style guidelines:

${skill}

---

${task_prompt}

Generate a chart specification as JSON.
EOF
      ;;
  esac
}

build_domain_prompt() {
  local domain="$1"
  local condition="$2"
  local task_id="$3"

  local domain_dir="${ROOT_DIR}/domains/${domain}"
  local task_file
  task_file=$(ls "${domain_dir}/test-data/task-${task_id}-"*.json 2>/dev/null | head -1)
  local description
  description=$(jq -r '.description' "$task_file")

  local output_instruction
  case "$domain" in
    dockerfile)
      output_instruction="Output ONLY the Dockerfile. No explanation."
      ;;
    sql-query)
      output_instruction="Structure your answer as multiple SQL files. Output each file as a separate fenced SQL block with a filename comment line above it. Format:

-- filename.sql
\`\`\`sql
SELECT ...
\`\`\`

Output ONLY the SQL files. No explanation."
      ;;
    terraform)
      output_instruction="Output ONLY the Terraform configuration. No explanation."
      ;;
  esac

  local task_prompt="${description}

${output_instruction}"

  local domain_label
  case "$domain" in
    dockerfile) domain_label="Dockerfile" ;;
    sql-query)  domain_label="SQL analytics pipeline" ;;
    terraform)  domain_label="Terraform configuration" ;;
  esac

  local skill_dir_name
  case "$domain" in
    dockerfile) skill_dir_name="dockerfile-style" ;;
    sql-query)  skill_dir_name="sql-style" ;;
    terraform)  skill_dir_name="terraform-style" ;;
  esac

  case "$condition" in
    markdown)
      local skill
      skill=$(cat "${domain_dir}/skills/${skill_dir_name}-markdown/SKILL.md")
      printf 'Follow these %s guidelines:\n\n%s\n\n---\n\n%s' "$domain_label" "$skill" "$task_prompt"
      ;;
    pseudocode)
      local skill
      skill=$(cat "${domain_dir}/skills/${skill_dir_name}-pseudocode/SKILL.md")
      printf 'Follow these %s guidelines:\n\n%s\n\n---\n\n%s' "$domain_label" "$skill" "$task_prompt"
      ;;
  esac
}

# ─── Define all 15 failures ─────────────────────────────────────────────────
# Format: domain|model_id|cli_tool|condition|task_id|rep|results_dir|run_id

FAILURES=(
  # Chart (2)
  "chart|haiku|claude|pseudocode|3|2|${ROOT_DIR}/domains/chart/results-v2|haiku_pseudocode_task3_rep2"
  "chart|opus|claude|markdown|3|2|${ROOT_DIR}/domains/chart/results-v2|opus_markdown_task3_rep2"
  # Dockerfile (4)
  "dockerfile|zai-coding-plan/glm-4.7|opencode|markdown|3|3|${ROOT_DIR}/domains/dockerfile/results|zai-coding-plan-glm-4.7_markdown_task3_rep3"
  "dockerfile|zai-coding-plan/glm-5|opencode|markdown|2|3|${ROOT_DIR}/domains/dockerfile/results|zai-coding-plan-glm-5_markdown_task2_rep3"
  "dockerfile|zai-coding-plan/glm-5|opencode|markdown|2|4|${ROOT_DIR}/domains/dockerfile/results|zai-coding-plan-glm-5_markdown_task2_rep4"
  "dockerfile|zai-coding-plan/glm-5|opencode|markdown|2|5|${ROOT_DIR}/domains/dockerfile/results|zai-coding-plan-glm-5_markdown_task2_rep5"
  # SQL (6)
  "sql-query|zai-coding-plan/glm-4.7|opencode|markdown|3|2|${ROOT_DIR}/domains/sql-query/results|zai-coding-plan-glm-4.7_markdown_task3_rep2"
  "sql-query|zai-coding-plan/glm-4.7|opencode|pseudocode|2|3|${ROOT_DIR}/domains/sql-query/results|zai-coding-plan-glm-4.7_pseudocode_task2_rep3"
  "sql-query|zai-coding-plan/glm-4.7|opencode|pseudocode|3|5|${ROOT_DIR}/domains/sql-query/results|zai-coding-plan-glm-4.7_pseudocode_task3_rep5"
  "sql-query|zai-coding-plan/glm-5|opencode|markdown|1|5|${ROOT_DIR}/domains/sql-query/results|zai-coding-plan-glm-5_markdown_task1_rep5"
  "sql-query|zai-coding-plan/glm-5|opencode|markdown|3|3|${ROOT_DIR}/domains/sql-query/results|zai-coding-plan-glm-5_markdown_task3_rep3"
  "sql-query|zai-coding-plan/glm-5|opencode|pseudocode|2|2|${ROOT_DIR}/domains/sql-query/results|zai-coding-plan-glm-5_pseudocode_task2_rep2"
  # Terraform (3)
  "terraform|zai-coding-plan/glm-5|opencode|markdown|2|2|${ROOT_DIR}/domains/terraform/results|zai-coding-plan-glm-5_markdown_task2_rep2"
  "terraform|zai-coding-plan/glm-5|opencode|pseudocode|2|1|${ROOT_DIR}/domains/terraform/results|zai-coding-plan-glm-5_pseudocode_task2_rep1"
  "terraform|haiku|claude|pseudocode|3|2|${ROOT_DIR}/domains/terraform/results|haiku_pseudocode_task3_rep2"
)

echo "=== Re-running ${#FAILURES[@]} extraction-failure runs ==="
echo ""

# ─── Phase 1: Delete old results ────────────────────────────────────────────

for entry in "${FAILURES[@]}"; do
  IFS='|' read -r domain model_id cli_tool condition task_id rep results_dir run_id <<< "$entry"
  f="${results_dir}/${run_id}.json"
  if [[ -f "$f" ]]; then
    echo "  Deleting: ${domain}/${run_id}.json"
    rm "$f"
  fi
done

echo ""
echo "=== Phase 2: Re-running ==="
echo ""

# ─── Phase 2: Re-run each ───────────────────────────────────────────────────

completed=0
failed=0

for entry in "${FAILURES[@]}"; do
  IFS='|' read -r domain model_id cli_tool condition task_id rep results_dir run_id <<< "$entry"

  out_file="${results_dir}/${run_id}.json"

  # Skip if somehow already re-created
  if [[ -f "$out_file" ]]; then
    echo "SKIP: ${run_id} (already exists)"
    continue
  fi

  echo "[$(( completed + failed + 1 ))/${#FAILURES[@]}] ${run_id} (${domain}, ${model_id}, ${condition}, task${task_id})"

  # Build prompt
  local_prompt=""
  if [[ "$domain" == "chart" ]]; then
    local_prompt=$(build_chart_prompt "$condition" "$task_id")
  else
    local_prompt=$(build_domain_prompt "$domain" "$condition" "$task_id")
  fi

  # Get complexity from task file
  task_file_for_meta=$(ls "${ROOT_DIR}/domains/${domain}/test-data/task-${task_id}-"*.json 2>/dev/null | head -1)
  complexity=$(jq -r '.complexity' "$task_file_for_meta")

  # Run
  start_time=$(date +%s%N)
  output=$(run_model "$model_id" "$cli_tool" "$local_prompt" 2>&1 || true)
  end_time=$(date +%s%N)
  duration_ms=$(( (end_time - start_time) / 1000000 ))

  if [[ -z "$output" ]]; then
    echo "  WARN: empty output"
    output='{"error": "empty output"}'
    failed=$((failed + 1))
  else
    completed=$((completed + 1))
  fi

  save_result "$run_id" "$model_id" "$condition" "$task_id" "$complexity" \
    "$domain" "$rep" "$duration_ms" "$cli_tool" "$output" "$out_file"

  echo "  Done: ${duration_ms}ms"
  sleep "$SLEEP_BETWEEN"
done

echo ""
echo "=== Phase 2 complete: ${completed} succeeded, ${failed} failed ==="
echo ""

# ─── Phase 3: Re-evaluate affected domains ──────────────────────────────────

echo "=== Phase 3: Re-evaluating affected domains ==="
echo ""

# Chart — evaluate_deep.py uses SCRIPT_DIR-relative paths.
# Override RESULTS_DIR and OUTPUT_CSV to point at results-v2.
echo "Re-evaluating chart..."
python3 -c "
import sys; sys.path.insert(0, '${ROOT_DIR}/scripts')
import evaluate_deep
from pathlib import Path
evaluate_deep.RESULTS_DIR = Path('${ROOT_DIR}/domains/chart/results-v2')
evaluate_deep.OUTPUT_CSV = evaluate_deep.RESULTS_DIR / 'scores_deep.csv'
evaluate_deep.main()
" 2>&1 | tail -3

echo "Re-evaluating dockerfile..."
python3 "${ROOT_DIR}/domains/dockerfile/evaluate_dockerfile.py" 2>&1 | tail -3

echo "Re-evaluating sql-query..."
python3 "${ROOT_DIR}/domains/sql-query/evaluate_sql.py" 2>&1 | tail -3

echo "Re-evaluating terraform..."
python3 "${ROOT_DIR}/domains/terraform/evaluate_terraform.py" 2>&1 | tail -3

echo ""
echo "=== All done! Re-run recompute_stats.py and generate_figures.py to update paper. ==="
