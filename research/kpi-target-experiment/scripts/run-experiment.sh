#!/usr/bin/env bash
set -euo pipefail

# ─────────────────────────────────────────────────────────────────────────────
# KPI Target Experiment Runner
# Tests whether performance framing (KPI targets + history) affects agent effort
# and outcomes. Completely separate from the original paper's scripts.
#
# Conditions tested:
#   - markdown (baseline from original paper)
#   - markdown+target (new: KPI + historical context)
# ─────────────────────────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RESEARCH_DIR="$(dirname "$SCRIPT_DIR")"   # kpi-target-experiment/
PARENT_RESEARCH="$(dirname "$RESEARCH_DIR")"  # research/
ROOT_DIR="$(dirname "$PARENT_RESEARCH")"  # skill-md-research/

# Prevent claude CLI nesting error
unset CLAUDECODE 2>/dev/null || true

# Empty MCP config to bypass plugin tool-name conflicts
EMPTY_MCP="/tmp/experiment-empty-mcp.json"
echo '{"mcpServers":{}}' > "$EMPTY_MCP"

# ─── Parse Arguments ────────────────────────────────────────────────────────

DOMAIN=""
PILOT=false

usage() {
  echo "Usage: $0 --domain <domain-name> [--pilot]"
  echo ""
  echo "Domains: sql-query, chart"
  echo ""
  echo "Options:"
  echo "  --domain <name>   Domain to run (required)"
  echo "  --pilot           Run 1 rep per model, task 1 only"
  echo "  --help            Show this help"
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --domain)
      DOMAIN="$2"
      shift 2
      ;;
    --pilot)
      PILOT=true
      shift
      ;;
    --help|-h)
      usage
      ;;
    *)
      echo "Unknown option: $1"
      usage
      ;;
  esac
done

if [[ -z "$DOMAIN" ]]; then
  echo "ERROR: --domain is required"
  usage
fi

# ─── Domain Configuration ──────────────────────────────────────────────────

# Use original domain's skills and test-data, but save results to our folder
ORIG_DOMAIN_DIR="${ROOT_DIR}/domains/${DOMAIN}"
OUR_RESULTS_DIR="${RESEARCH_DIR}/domains/${DOMAIN}/results"

if [[ ! -d "$ORIG_DOMAIN_DIR" ]]; then
  echo "ERROR: Domain not found: ${ORIG_DOMAIN_DIR}"
  echo "Available: sql-query, chart"
  exit 1
fi

DATA_DIR="${ORIG_DOMAIN_DIR}/test-data"
SKILLS_DIR="${ORIG_DOMAIN_DIR}/skills"

# Find skill directories
MARKDOWN_SKILL_DIR=$(ls -d "${SKILLS_DIR}"/*-markdown 2>/dev/null | head -1)

if [[ -z "$MARKDOWN_SKILL_DIR" ]]; then
  echo "ERROR: Could not find markdown skill in ${SKILLS_DIR}"
  exit 1
fi

TASK_FILES=($(ls "${DATA_DIR}"/task-*.json 2>/dev/null | sort))
if [[ ${#TASK_FILES[@]} -eq 0 ]]; then
  # Try alternate naming
  TASK_FILES=($(ls "${DATA_DIR}"/*.json 2>/dev/null | sort))
fi
TASK_COUNT=${#TASK_FILES[@]}

echo "Domain: ${DOMAIN}"
echo "Tasks found: ${TASK_COUNT}"
echo "Markdown skill: $(basename "$MARKDOWN_SKILL_DIR")"
echo "Results dir: ${OUR_RESULTS_DIR}"

# ─── KPI Target Intervention ─────────────────────────────────────────────────

build_kpi_context() {
  local domain="$1"
  
  case "$domain" in
    sql-query)
      cat <<'EOF'
## Performance Context

Your target for this task is to achieve 97% compliance with dbt analytics pipeline best practices (13.6 out of 14 rules passing).

In previous evaluations on similar tasks:
- The baseline model achieved 73% compliance (10.2/14 rules)
- The skill-enhanced markdown model achieved 77% compliance (10.7/14 rules)
- The top-performing model achieved 86% compliance (12/14 rules)

Your current model family has historically achieved 76% compliance on dbt/SQL analytics tasks.

To reach the 97% target, pay particular attention to these low-baseline rules:
- Rule 7: Use LEFT JOIN only (no INNER JOIN) for analytics (~35% baseline)
- Rule 8: COALESCE nullable dimensions to '(unknown)' (~25% baseline)
- Rule 9: Use ROW_NUMBER() for deduplication before aggregation (~20% baseline)
- Rule 11: Use Jinja {{ ref('model_name') }} for cross-model references (~30% baseline)
- Rule 14: Ensure correct DAG order - files reference only previously-defined models (~35% baseline)

These 5 hard rules account for 70% of failures. Focus on:
1. Deduplicating source data with ROW_NUMBER() BEFORE joining
2. Using LEFT JOIN for all dimension table references (never INNER JOIN)
3. Wrapping all nullable dimension columns in COALESCE(col, '(unknown)')
4. Using {{ ref('upstream_model') }} syntax to reference other models
5. Defining models in dependency order (staging -> intermediate -> mart)
EOF
      ;;
    chart)
      cat <<'EOF'
## Performance Context

Your target for this task is to achieve 97% compliance with chart visualization best practices (14.5 out of 15 rules passing).

In previous evaluations on similar tasks:
- The baseline model achieved 49% compliance (7.4/15 rules)
- The skill-enhanced markdown model achieved 81% compliance (12.2/15 rules)
- The top-performing model achieved 100% compliance (15/15 rules)

Your current model family has historically achieved 81% compliance on chart specification tasks.

To reach the 97% target, pay particular attention to these low-baseline rules:
- Rule 6: Source attribution in chart metadata (~15% baseline)
- Rule 8: Data point labels configuration with formatter (~25% baseline)
- Rule 10: Y-axis scale.zero=true for bar charts (~35% baseline)
- Rule 11: Remove top and right chart spines (~30% baseline)
- Rule 13: Unit appears in axis label only once, not duplicated (~25% baseline)

These 5 rules account for 65% of failures. Focus on:
1. Including a "source" field with data attribution in the config
2. Adding dataLabels config with formatter for point values
3. Setting scale: { zero: true } for bar charts to show true magnitude
4. Removing chart spines (top and right axis lines)
5. Showing units in exactly one place (axis label preferred, not duplicated)
EOF
      ;;
    *)
      cat <<'EOF'
## Performance Context

Your target for this task is to achieve 97% compliance with the specification.

In previous evaluations on similar tasks:
- The baseline model achieved 55% compliance
- The skill-enhanced model achieved 80% compliance
- The top-performing model achieved 95% compliance

Focus on the rules with lowest baseline pass rates to maximize your improvement.
EOF
      ;;
  esac
}

# ─── Domain-Specific Prompt Configuration ───────────────────────────────────

build_task_prompt() {
  local task_file="$1"
  local task_json
  task_json=$(cat "$task_file")

  case "$DOMAIN" in
    sql-query)
      local description
      description=$(echo "$task_json" | jq -r '.description')
      cat <<PROMPT
${description}

Structure your answer as multiple SQL files. Output each file as a separate fenced SQL block with a filename comment line above it. Format:

-- models/staging/stg_table.sql
\`\`\`sql
WITH source AS (
    SELECT * FROM {{ source('raw', 'table') }}
)
SELECT ...
\`\`\`

Output ONLY the SQL files. No explanation.
PROMPT
      ;;

    chart)
      local chart_type data metadata requirements
      chart_type=$(echo "$task_json" | jq -r '.chart_type')
      data=$(echo "$task_json" | jq -c '.data // .series')
      metadata=$(echo "$task_json" | jq -c '.metadata')
      requirements=$(echo "$task_json" | jq -c '.requirements')

      cat <<PROMPT
Generate a ${chart_type} chart specification in JSON format.

Data: ${data}
Metadata: ${metadata}
Requirements: ${requirements}

Output ONLY the chart specification as a JSON object. No explanation.
PROMPT
      ;;

    *)
      local description
      description=$(echo "$task_json" | jq -r '.description')
      cat <<PROMPT
${description}

Output ONLY the requested artifact. No explanation.
PROMPT
      ;;
  esac
}

get_domain_label() {
  case "$DOMAIN" in
    sql-query)      echo "dbt analytics pipeline" ;;
    chart)          echo "chart specification" ;;
    *)              echo "specification" ;;
  esac
}

# ─── Model Configuration ────────────────────────────────────────────────────

# Note: glm-4.7-flash excluded due to high failure rate (~40%) and timeouts
MODELS=(
  "haiku|claude"
  "opus|claude"
  "zai-coding-plan/glm-4.7|opencode"
  "zai-coding-plan/glm-5|opencode"
)

CONDITION="markdown+target"
REPS=5
SLEEP_BETWEEN=5

# ─── Build Prompt Functions ─────────────────────────────────────────────────

build_prompt() {
  local condition="$1"
  local task_file="$2"

  local task_prompt
  task_prompt=$(build_task_prompt "$task_file")
  local domain_label
  domain_label=$(get_domain_label)
  local kpi_context
  kpi_context=$(build_kpi_context "$DOMAIN")

  # Prevent models from using file writing tools - MUST be at TOP of prompt
  local text_only_instruction
  text_only_instruction="IMPORTANT: Output your answer as TEXT only. Do NOT use file writing tools. Do NOT create files. Just output the content in text format using markdown code fences."

  local skill_content
  skill_content=$(cat "${MARKDOWN_SKILL_DIR}/SKILL.md")

  case "$condition" in
    markdown)
      cat <<EOF
${text_only_instruction}

---

Follow these ${domain_label} guidelines:

${skill_content}

---

${task_prompt}
EOF
      ;;
    markdown+target)
      cat <<EOF
${text_only_instruction}

---

${kpi_context}

---

Follow these ${domain_label} guidelines:

${skill_content}

---

${task_prompt}
EOF
      ;;
  esac
}

# ─── Run Model Function ─────────────────────────────────────────────────────

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
    *)
      echo "ERROR: Unknown CLI tool: $cli_tool" >&2
      rm -f "$prompt_file"
      return 1
      ;;
  esac

  rm -f "$prompt_file"
  echo "$result"
}

sanitize() {
  echo "$1" | tr '/' '-'
}

# ─── Pilot Mode ─────────────────────────────────────────────────────────────

if [[ "$PILOT" == true ]]; then
  echo ""
  echo "=== PILOT MODE: ${DOMAIN} — 1 run per model, ${CONDITION} condition, task 1 ==="
  mkdir -p "$OUR_RESULTS_DIR"

  task_file="${TASK_FILES[0]}"
  task_id=$(jq -r '.task_id' "$task_file")

  for model_entry in "${MODELS[@]}"; do
    IFS='|' read -r model_id cli_tool <<< "$model_entry"
    safe_model=$(sanitize "$model_id")
    run_id="${safe_model}_${CONDITION//+/-}_task${task_id}_pilot"

    if [[ -f "${OUR_RESULTS_DIR}/${run_id}.json" ]]; then
      echo "SKIP: ${run_id} (already exists)"
      continue
    fi

    echo "PILOT: ${run_id} (${cli_tool})"
    prompt=$(build_prompt "$CONDITION" "$task_file")

    start_time=$(date +%s%N)
    output=$(run_model "$model_id" "$cli_tool" "$prompt" 2>&1 || echo '{"error": "CLI failed"}')
    end_time=$(date +%s%N)
    duration_ms=$(( (end_time - start_time) / 1000000 ))

    complexity=$(jq -r '.complexity' "$task_file")

    jq -n \
      --arg run_id "$run_id" \
      --arg model "$model_id" \
      --arg condition "$CONDITION" \
      --arg task "$task_id" \
      --arg complexity "$complexity" \
      --arg domain "$DOMAIN" \
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
        domain: $domain,
        rep: $rep,
        timestamp: $timestamp,
        duration_ms: $duration_ms,
        cli_tool: $cli_tool,
        raw_output: $raw_output
      }' > "${OUR_RESULTS_DIR}/${run_id}.json"

    echo "  Done: ${duration_ms}ms"
    sleep "$SLEEP_BETWEEN"
  done

  echo "=== Pilot complete. Check ${OUR_RESULTS_DIR}/ ==="
  exit 0
fi

# ─── Full Experiment ────────────────────────────────────────────────────────

total=$((TASK_COUNT * ${#MODELS[@]} * REPS))

echo ""
echo "=== KPI TARGET EXPERIMENT: ${DOMAIN} — ${total} runs ==="
echo "Condition: ${CONDITION}"
echo "Tasks: ${TASK_COUNT}"
echo "Models: ${#MODELS[@]}"
echo "Reps: ${REPS}"
echo ""

mkdir -p "$OUR_RESULTS_DIR"

completed=0
skipped=0
failed=0

for model_entry in "${MODELS[@]}"; do
  IFS='|' read -r model_id cli_tool <<< "$model_entry"
  safe_model=$(sanitize "$model_id")

  for task_file in "${TASK_FILES[@]}"; do
    task_id=$(jq -r '.task_id' "$task_file")
    complexity=$(jq -r '.complexity' "$task_file")

    for rep in $(seq 1 "$REPS"); do
      run_id="${safe_model}_${CONDITION//+/-}_task${task_id}_rep${rep}"

      if [[ -f "${OUR_RESULTS_DIR}/${run_id}.json" ]]; then
        skipped=$((skipped + 1))
        continue
      fi

      echo "[$(( completed + skipped + failed + 1 ))/${total}] ${run_id}"

      prompt=$(build_prompt "$CONDITION" "$task_file")

      start_time=$(date +%s%N)
      output=$(run_model "$model_id" "$cli_tool" "$prompt" 2>&1 || true)
      end_time=$(date +%s%N)
      duration_ms=$(( (end_time - start_time) / 1000000 ))

      if [[ -z "$output" ]]; then
        echo "  FAILED: empty output"
        failed=$((failed + 1))
        output='{"error": "empty output"}'
      fi

      jq -n \
        --arg run_id "$run_id" \
        --arg model "$model_id" \
        --arg condition "$CONDITION" \
        --arg task "$task_id" \
        --arg complexity "$complexity" \
        --arg domain "$DOMAIN" \
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
        }' > "${OUR_RESULTS_DIR}/${run_id}.json"

      completed=$((completed + 1))
      echo "  Done: ${duration_ms}ms"

      sleep "$SLEEP_BETWEEN"
    done
  done
done

echo ""
echo "=== Experiment complete: ${DOMAIN} ==="
echo "Completed: ${completed}"
echo "Skipped (existing): ${skipped}"
echo "Failed: ${failed}"
echo "Results in: ${OUR_RESULTS_DIR}/"
