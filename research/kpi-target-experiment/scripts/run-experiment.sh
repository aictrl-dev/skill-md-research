#!/usr/bin/env bash
set -euo pipefail

# ─────────────────────────────────────────────────────────────────────────────
# KPI Target Experiment Runner
# Tests whether performance framing (KPI targets + history) affects agent effort
# and outcomes. Separate from original paper scripts.
# ─────────────────────────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RESEARCH_DIR="$(dirname "$SCRIPT_DIR")"
ROOT_DIR="$(dirname "$(dirname "$RESEARCH_DIR")")"

# Prevent claude CLI nesting error
unset CLAUDECODE 2>/dev/null || true

# Empty MCP config
EMPTY_MCP="/tmp/experiment-empty-mcp.json"
echo '{"mcpServers":{}}' > "$EMPTY_MCP"

# ─── Parse Arguments ────────────────────────────────────────────────────────

DOMAIN=""

usage() {
  echo "Usage: $0 --domain <domain-name>"
  echo "Domains: sql-query, chart"
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --domain)
      DOMAIN="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1"
      usage
      ;;
  esac
done

if [[ -z "$DOMAIN" ]]; then
  usage
fi

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
if [[ -z "$MARKDOWN_SKILL_DIR" ]]; then
  echo "ERROR: Could not find markdown skill"
  exit 1
fi

TASK_FILES=($(ls "${DATA_DIR}"/*.json 2>/dev/null | sort))
TASK_COUNT=${#TASK_FILES[@]}

echo "Domain: ${DOMAIN}"
echo "Tasks: ${TASK_COUNT}"
echo "Results: ${OUR_RESULTS_DIR}"

# ─── KPI Context ─────────────────────────────────────────────────────────────

build_kpi_context() {
  case "$DOMAIN" in
    sql-query)
      cat <<'EOF'
## Performance Context

Your target for this task is to achieve 97% compliance with dbt analytics pipeline best practices (13.6 out of 14 rules passing).

In previous evaluations on similar tasks:
- The baseline model achieved 73% compliance (10.2/14 rules)
- The skill-enhanced markdown model achieved 77% compliance (10.7/14 rules)

Your current model family has historically achieved 76% compliance on dbt/SQL analytics tasks.

To reach the 97% target, focus on:
1. Deduplicating source data with ROW_NUMBER() BEFORE joining
2. Using LEFT JOIN for all dimension table references (never INNER JOIN)
3. Wrapping all nullable dimension columns in COALESCE(col, '(unknown)')
4. Using {{ ref('upstream_model') }} syntax
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

To reach the 97% target, focus on:
1. Including a "source" field with data attribution
2. Adding dataLabels config with formatter
3. Setting scale: { zero: true } for bar charts
4. Removing chart spines (top and right axis lines)
5. Showing units in exactly one place
EOF
      ;;
  esac
}

# ─── Task Prompts ────────────────────────────────────────────────────────────

build_task_prompt() {
  local task_file="$1"
  local task_json=$(cat "$task_file")

  case "$DOMAIN" in
    sql-query)
      local desc=$(echo "$task_json" | jq -r '.description')
      echo "${desc}

Structure your answer as multiple SQL files. Output each file as a separate fenced SQL block with a filename comment.

Output ONLY the SQL files. No explanation."
      ;;
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
  esac
}

get_domain_label() {
  case "$DOMAIN" in
    sql-query) echo "dbt analytics pipeline" ;;
    chart) echo "chart specification" ;;
  esac
}

# ─── Models ──────────────────────────────────────────────────────────────────

MODELS=(
  "haiku|claude"
  "opus|claude"
  "zai-coding-plan/glm-4.7|opencode"
  "zai-coding-plan/glm-5|opencode"
)

CONDITION="markdown+target"
REPS=5
SLEEP=3

# ─── Build Prompt ────────────────────────────────────────────────────────────

build_prompt() {
  local task_file="$1"
  local task_prompt=$(build_task_prompt "$task_file")
  local domain_label=$(get_domain_label)
  local kpi_context=$(build_kpi_context)
  local skill_content=$(cat "${MARKDOWN_SKILL_DIR}/SKILL.md")

  cat <<EOF
IMPORTANT: Output your answer as TEXT only. Do NOT use file writing tools. Do NOT create files. Just output the content in text format using markdown code fences.

---

${kpi_context}

---

Follow these ${domain_label} guidelines:

${skill_content}

---

${task_prompt}
EOF
}

# ─── Run Model ───────────────────────────────────────────────────────────────

run_model() {
  local model_id="$1"
  local cli_tool="$2"
  local prompt="$3"

  local prompt_file="/tmp/exp-prompt-$$.txt"
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

sanitize() {
  echo "$1" | tr '/' '-'
}

# ─── Main Loop ───────────────────────────────────────────────────────────────

total=$((TASK_COUNT * ${#MODELS[@]} * REPS))
echo ""
echo "=== Running ${total} experiments ==="

completed=0
skipped=0

for model_entry in "${MODELS[@]}"; do
  IFS='|' read -r model_id cli_tool <<< "$model_entry"
  safe_model=$(sanitize "$model_id")

  for task_file in "${TASK_FILES[@]}"; do
    task_id=$(jq -r '.task_id' "$task_file")

    for rep in $(seq 1 $REPS); do
      run_id="${safe_model}_markdown-target_task${task_id}_rep${rep}"

      if [[ -f "${OUR_RESULTS_DIR}/${run_id}.json" ]]; then
        skipped=$((skipped + 1))
        continue
      fi

      echo "[$((completed + skipped + 1))/${total}] ${run_id}"
      prompt=$(build_prompt "$task_file")

      start_time=$(date +%s%N)
      output=$(run_model "$model_id" "$cli_tool" "$prompt" 2>&1 || echo '{"error": "failed"}')
      end_time=$(date +%s%N)
      duration_ms=$(( (end_time - start_time) / 1000000 ))

      jq -n \
        --arg run_id "$run_id" \
        --arg model "$model_id" \
        --arg condition "$CONDITION" \
        --arg task "$task_id" \
        --arg domain "$DOMAIN" \
        --argjson rep "$rep" \
        --arg timestamp "$(date -Iseconds)" \
        --argjson duration_ms "$duration_ms" \
        --arg cli_tool "$cli_tool" \
        --arg raw_output "$output" \
        '{run_id, model, condition, task, domain, rep, timestamp, duration_ms, cli_tool, raw_output}' \
        > "${OUR_RESULTS_DIR}/${run_id}.json"

      completed=$((completed + 1))
      echo "  Done: ${duration_ms}ms"
      sleep $SLEEP
    done
  done
done

echo ""
echo "=== Complete: ${completed} new, ${skipped} skipped ==="
