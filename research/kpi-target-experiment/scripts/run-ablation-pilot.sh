#!/usr/bin/env bash
set -euo pipefail

# ─────────────────────────────────────────────────────────────────────────────
# Ablation Pilot — KPI Framing Variants
# SQL domain, task 1, 5 reps per condition
# Tests whether KPI context blocks add value on top of SKILL.md
#
# All conditions include the full SKILL.md (which already has the rule
# checklist). The KPI context block is the ONLY thing that varies.
# ─────────────────────────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RESEARCH_DIR="$(dirname "$SCRIPT_DIR")"
ROOT_DIR="$(dirname "$(dirname "$RESEARCH_DIR")")"

# Prevent claude CLI nesting error
unset CLAUDECODE 2>/dev/null || true

# Empty MCP config
EMPTY_MCP="/tmp/experiment-empty-mcp.json"
echo '{"mcpServers":{}}' > "$EMPTY_MCP"

# ─── Fixed Parameters ────────────────────────────────────────────────────────

DOMAIN="sql-query"
TASK_NUM="1"
REPS=5
SLEEP=3

ORIG_DOMAIN_DIR="${ROOT_DIR}/domains/${DOMAIN}"
RESULTS_DIR="${RESEARCH_DIR}/domains/${DOMAIN}/results/ablation"
DATA_DIR="${ORIG_DOMAIN_DIR}/test-data"
SKILLS_DIR="${ORIG_DOMAIN_DIR}/skills"

MARKDOWN_SKILL_DIR=$(ls -d "${SKILLS_DIR}"/*-markdown 2>/dev/null | head -1)
if [[ -z "$MARKDOWN_SKILL_DIR" ]]; then
  echo "ERROR: Could not find markdown skill"
  exit 1
fi

TASK_FILE="${DATA_DIR}/task-1-revenue-by-channel.json"
if [[ ! -f "$TASK_FILE" ]]; then
  echo "ERROR: Task file not found: ${TASK_FILE}"
  exit 1
fi

# ─── Model Definitions ───────────────────────────────────────────────────────
# Format: "display_name|model_id|cli_tool"

declare -A MODEL_MAP
MODEL_MAP[haiku]="haiku|claude"
MODEL_MAP[glm-4.7]="zai-coding-plan/glm-4.7|opencode"
MODEL_MAP[glm-5]="zai-coding-plan/glm-5|opencode"

ALL_CONDITIONS=(none full kpi-only simple-context)

# ─── Parse Arguments ──────────────────────────────────────────────────────────

CONDITIONS=()
MODELS=()

usage() {
  echo "Usage: $0 [--model <name>] [--condition <name>]"
  echo "Models: haiku, glm-4.7, glm-5 (default: all)"
  echo "Conditions: none, full, kpi-only, simple-context (default: all)"
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --model)
      MODELS+=("$2")
      shift 2
      ;;
    --condition)
      CONDITIONS+=("$2")
      shift 2
      ;;
    -h|--help)
      usage
      ;;
    *)
      echo "Unknown option: $1"
      usage
      ;;
  esac
done

if [[ ${#CONDITIONS[@]} -eq 0 ]]; then
  CONDITIONS=("${ALL_CONDITIONS[@]}")
fi

if [[ ${#MODELS[@]} -eq 0 ]]; then
  MODELS=(haiku glm-4.7 glm-5)
fi

# Validate models
for m in "${MODELS[@]}"; do
  if [[ -z "${MODEL_MAP[$m]+x}" ]]; then
    echo "ERROR: Unknown model: $m"
    usage
  fi
done

# ─── KPI Context Variants ────────────────────────────────────────────────────

build_kpi_context_full() {
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
}

build_kpi_context_kpi_only() {
  cat <<'EOF'
## Performance Context

Your target for this task is to achieve 97% compliance with dbt analytics pipeline best practices (13.6 out of 14 rules passing).
EOF
}

build_kpi_context_none() {
  # No KPI context — baseline with just skill + task
  echo ""
}

build_kpi_context_simple_context() {
  cat <<'EOF'
## Performance Context

Historical performance average for your model family is only 76% compliance on dbt/SQL analytics tasks. Your target is 97% compliance.
EOF
}


# ─── Task Prompt ──────────────────────────────────────────────────────────────

build_task_prompt() {
  local task_json
  task_json=$(cat "$TASK_FILE")
  local desc
  desc=$(echo "$task_json" | jq -r '.description')
  echo "${desc}

Structure your answer as multiple SQL files. Output each file as a separate fenced SQL block with a filename comment.

Output ONLY the SQL files. No explanation."
}

# ─── Build Full Prompt ────────────────────────────────────────────────────────

build_prompt() {
  local condition="$1"
  local rep_num="$2"
  local task_prompt
  task_prompt=$(build_task_prompt)
  local skill_content
  skill_content=$(cat "${MARKDOWN_SKILL_DIR}/SKILL.md")

  local kpi_context
  case "$condition" in
    none)            kpi_context=$(build_kpi_context_none) ;;
    full)            kpi_context=$(build_kpi_context_full) ;;
    kpi-only)        kpi_context=$(build_kpi_context_kpi_only) ;;
    simple-context)  kpi_context=$(build_kpi_context_simple_context) ;;
    *)
      echo "ERROR: Unknown condition: $condition" >&2
      exit 1
      ;;
  esac

  # Nonce to defeat API-level prompt caching across reps.
  # Without this, identical prompts return identical outputs.
  local nonce
  nonce=$(head -c 16 /dev/urandom | base64 | tr -d '/+=' | head -c 12)

  cat <<EOF
<!-- session: ${nonce} -->
IMPORTANT: Output your answer as TEXT only. Do NOT use file writing tools. Do NOT create files. Just output the content in text format using markdown code fences.

---

${kpi_context}

---

Follow these dbt analytics pipeline guidelines:

${skill_content}

---

${task_prompt}
EOF
}

# ─── Run Model ────────────────────────────────────────────────────────────────

run_model() {
  local model_id="$1"
  local cli_tool="$2"
  local prompt="$3"
  local prompt_file="/tmp/ablation-prompt-$$.txt"
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

# ─── Main Loop ────────────────────────────────────────────────────────────────

total=$((${#MODELS[@]} * ${#CONDITIONS[@]} * REPS))
echo "=== Ablation Pilot: ${#MODELS[@]} models × ${#CONDITIONS[@]} conditions × ${REPS} reps = ${total} runs ==="
echo "Models: ${MODELS[*]}"
echo "Conditions: ${CONDITIONS[*]}"
echo "Domain: ${DOMAIN}, Task: ${TASK_NUM}"
echo "Results: ${RESULTS_DIR}"
echo ""

completed=0
skipped=0

for model_name in "${MODELS[@]}"; do
  IFS='|' read -r model_id cli_tool <<< "${MODEL_MAP[$model_name]}"
  safe_model=$(sanitize "$model_id")

  for condition in "${CONDITIONS[@]}"; do
    for rep in $(seq 1 $REPS); do
      run_id="${safe_model}_ablation-${condition}_task${TASK_NUM}_rep${rep}"
      outfile="${RESULTS_DIR}/${run_id}.json"

      if [[ -f "$outfile" ]]; then
        echo "[SKIP] ${run_id} — already exists"
        skipped=$((skipped + 1))
        continue
      fi

      echo "[$((completed + skipped + 1))/${total}] ${run_id}"
      prompt=$(build_prompt "$condition" "$rep")

      start_time=$(date +%s%N)
      output=$(run_model "$model_id" "$cli_tool" "$prompt" 2>&1 || echo '{"error": "failed"}')
      end_time=$(date +%s%N)
      duration_ms=$(( (end_time - start_time) / 1000000 ))

      # Write output to temp file to avoid ARG_MAX limits with jq --arg
      output_tmp="/tmp/ablation-output-$$.txt"
      printf '%s' "$output" > "$output_tmp"

      jq -n \
        --arg run_id "$run_id" \
        --arg model "$model_id" \
        --arg condition "ablation-${condition}" \
        --arg task "$TASK_NUM" \
        --arg domain "$DOMAIN" \
        --argjson rep "$rep" \
        --arg timestamp "$(date -Iseconds)" \
        --argjson duration_ms "$duration_ms" \
        --arg cli_tool "$cli_tool" \
        --rawfile raw_output "$output_tmp" \
        '{run_id: $run_id, model: $model, condition: $condition, task: $task, domain: $domain, rep: $rep, timestamp: $timestamp, duration_ms: $duration_ms, cli_tool: $cli_tool, raw_output: $raw_output}' \
        > "$outfile"

      rm -f "$output_tmp"

      completed=$((completed + 1))
      echo "  Done: ${duration_ms}ms"
      sleep $SLEEP
    done
  done
done

echo ""
echo "=== Complete: ${completed} new, ${skipped} skipped ==="
