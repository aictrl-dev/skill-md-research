#!/usr/bin/env bash
set -euo pipefail

# ─────────────────────────────────────────────────────────────────────────────
# Pseudocode vs Markdown Experiment Runner
# 3 conditions x 3 tasks x 5 models x 5 reps = 225 runs
# ─────────────────────────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RESULTS_DIR="${SCRIPT_DIR}/results"
SKILLS_DIR="${SCRIPT_DIR}/skills"
DATA_DIR="${SCRIPT_DIR}/test-data"

# Prevent claude CLI nesting error
unset CLAUDECODE 2>/dev/null || true

# Empty MCP config to bypass plugin tool-name conflicts
EMPTY_MCP="/tmp/experiment-empty-mcp.json"
echo '{"mcpServers":{}}' > "$EMPTY_MCP"

# ─── Configuration ───────────────────────────────────────────────────────────

CONDITIONS=("none" "markdown" "pseudocode")
TASKS=("1" "2" "3")
TASK_FILES=("task-1-gdp.json" "task-2-ai-models.json" "task-3-cloud-revenue.json")
TASK_PROMPTS=(
  "Create a bar chart comparing 2023 GDP for these economies:\n\nData (USD billions):\n- USA: 25,462\n- China: 17,963\n- Germany: 4,072\n- Japan: 4,231\n- India: 3,385\n\nHighlight: The gap between USA and China\nSource: IMF World Economic Outlook, 2024"
  "Create a line chart showing the growth of AI model sizes:\n\nData (parameters in billions):\nYear | Largest Model\n2017 | 0.094   (Transformer)\n2018 | 0.310   (BERT)\n2019 | 1.5     (GPT-2)\n2020 | 17      (GPT-3)\n2021 | 175     (Gopher)\n2022 | 540     (PaLM)\n2023 | 1800    (GPT-4, estimated)\n2024 | 12000   (Gemini Ultra)\n\nHighlight: The 1000x growth from 2020 to 2024\nAnnotation: Mark GPT-4 at 1.8T parameters\nSource: Epoch AI, \"Trends in Machine Learning\", 2024"
  "Create a chart comparing the three major cloud providers:\n\nData (quarterly revenue in USD billions):\nQuarter | AWS  | Azure | GCP\n2023-Q1 | 21.3 | 21.0  | 7.0\n2023-Q2 | 22.1 | 23.0  | 8.0\n2023-Q3 | 23.1 | 24.0  | 8.4\n2023-Q4 | 24.2 | 25.0  | 9.2\n2024-Q1 | 25.0 | 26.0  | 9.6\n2024-Q2 | 26.0 | 28.0  | 10.3\n2024-Q3 | 27.5 | 29.0  | 11.4\n2024-Q4 | 28.8 | 30.0  | 12.0\n\nKey insight: Azure overtook AWS in Q2 2024\nHighlight: The crossover point\nSource: Company earnings reports, 2023-2024"
)

# Models: model_id|cli_tool
MODELS=(
  "haiku|claude"
  "opus|claude"
  "zai-coding-plan/glm-4.7-flash|opencode"
  "zai-coding-plan/glm-4.7|opencode"
  "zai-coding-plan/glm-5|opencode"
)

REPS=5
SLEEP_BETWEEN=5  # seconds between runs

# ─── Functions ───────────────────────────────────────────────────────────────

build_prompt() {
  local condition="$1"
  local task_index="$2"

  local task_prompt
  task_prompt=$(echo -e "${TASK_PROMPTS[$task_index]}")

  case "$condition" in
    none)
      cat <<EOF
${task_prompt}

Generate the chart specification as JSON. Include:
- chart_type
- title (with text and optional subtitle)
- source attribution
- data array
- axis configuration
- any annotations mentioned in requirements
EOF
      ;;
    markdown)
      local skill_content
      skill_content=$(cat "${SKILLS_DIR}/chart-style-markdown/SKILL.md")
      cat <<EOF
Follow these chart style guidelines:

${skill_content}

---

${task_prompt}

Generate a chart specification as JSON.
EOF
      ;;
    pseudocode)
      local skill_content
      skill_content=$(cat "${SKILLS_DIR}/chart-style-pseudocode/SKILL.md")
      cat <<EOF
Follow these chart style guidelines:

${skill_content}

---

${task_prompt}

Generate a chart specification as JSON.
EOF
      ;;
  esac
}

run_model() {
  local model_id="$1"
  local cli_tool="$2"
  local prompt="$3"

  # Write prompt to temp file to avoid arg length limits
  local prompt_file="/tmp/experiment-prompt-$$.txt"
  printf '%s' "$prompt" > "$prompt_file"

  local result=""
  case "$cli_tool" in
    claude)
      # Run from /tmp to avoid project .mcp.json / plugin conflicts
      result=$(cd /tmp && claude -p "$(cat "$prompt_file")" --model "$model_id" --output-format json --no-session-persistence --mcp-config "$EMPTY_MCP" 2>&1) || true
      ;;
    opencode)
      # opencode needs -f for file attachment and -- to separate message
      result=$(opencode run -m "$model_id" --format json -f "$prompt_file" -- "Follow the instructions." 2>&1) || true
      ;;
    *)
      echo "ERROR: Unknown CLI tool: $cli_tool" >&2
      rm -f "$prompt_file"
      return 1
      ;;
  esac

  rm -f "$prompt_file"
  echo "$result"
}

# Sanitize model ID for filename (replace / with -)
sanitize() {
  echo "$1" | tr '/' '-'
}

# ─── Pilot Mode ──────────────────────────────────────────────────────────────

if [[ "${1:-}" == "--pilot" ]]; then
  echo "=== PILOT MODE: 1 run per model, condition=markdown, task=1 ==="
  mkdir -p "$RESULTS_DIR"

  for model_entry in "${MODELS[@]}"; do
    IFS='|' read -r model_id cli_tool <<< "$model_entry"
    safe_model=$(sanitize "$model_id")
    run_id="${safe_model}_markdown_task1_pilot"

    if [[ -f "${RESULTS_DIR}/${run_id}.json" ]]; then
      echo "SKIP: ${run_id} (already exists)"
      continue
    fi

    echo "PILOT: ${run_id} (${cli_tool})"
    prompt=$(build_prompt "markdown" 0)

    start_time=$(date +%s%N)
    output=$(run_model "$model_id" "$cli_tool" "$prompt" 2>&1 || echo '{"error": "CLI failed"}')
    end_time=$(date +%s%N)
    duration_ms=$(( (end_time - start_time) / 1000000 ))

    # Save result
    jq -n \
      --arg run_id "$run_id" \
      --arg model "$model_id" \
      --arg condition "markdown" \
      --arg task "1" \
      --arg complexity "simple" \
      --argjson rep 0 \
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
        rep: $rep,
        timestamp: $timestamp,
        duration_ms: $duration_ms,
        cli_tool: $cli_tool,
        raw_output: $raw_output
      }' > "${RESULTS_DIR}/${run_id}.json"

    echo "  Done: ${duration_ms}ms"
    sleep "$SLEEP_BETWEEN"
  done

  echo "=== Pilot complete. Check results/ ==="
  exit 0
fi

# ─── Full Experiment ─────────────────────────────────────────────────────────

total=$((${#CONDITIONS[@]} * ${#TASKS[@]} * ${#MODELS[@]} * REPS))

echo "=== FULL EXPERIMENT: ${total} runs ==="
echo "Conditions: ${CONDITIONS[*]}"
echo "Tasks: ${TASKS[*]}"
echo "Models: ${#MODELS[@]}"
echo "Reps: ${REPS}"
echo ""

mkdir -p "$RESULTS_DIR"

completed=0
skipped=0
failed=0

for model_entry in "${MODELS[@]}"; do
  IFS='|' read -r model_id cli_tool <<< "$model_entry"
  safe_model=$(sanitize "$model_id")

  for condition in "${CONDITIONS[@]}"; do
    for task_idx in "${!TASKS[@]}"; do
      task="${TASKS[$task_idx]}"

      for rep in $(seq 1 "$REPS"); do
        run_id="${safe_model}_${condition}_task${task}_rep${rep}"

        # Skip if already completed
        if [[ -f "${RESULTS_DIR}/${run_id}.json" ]]; then
          skipped=$((skipped + 1))
          continue
        fi

        echo "[$(( completed + skipped + failed + 1 ))/${total}] ${run_id}"

        prompt=$(build_prompt "$condition" "$task_idx")

        start_time=$(date +%s%N)
        output=$(run_model "$model_id" "$cli_tool" "$prompt" 2>&1 || true)
        end_time=$(date +%s%N)
        duration_ms=$(( (end_time - start_time) / 1000000 ))

        if [[ -z "$output" ]]; then
          echo "  FAILED: empty output"
          failed=$((failed + 1))
          output='{"error": "empty output"}'
        fi

        # Determine task complexity
        case "$task" in
          1) complexity="simple" ;;
          2) complexity="medium" ;;
          3) complexity="complex" ;;
        esac

        # Save result
        jq -n \
          --arg run_id "$run_id" \
          --arg model "$model_id" \
          --arg condition "$condition" \
          --arg task "$task" \
          --arg complexity "$complexity" \
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
echo "=== Experiment complete ==="
echo "Completed: ${completed}"
echo "Skipped (existing): ${skipped}"
echo "Failed: ${failed}"
echo "Results in: ${RESULTS_DIR}/"
