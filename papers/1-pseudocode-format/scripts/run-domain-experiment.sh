#!/usr/bin/env bash
set -euo pipefail

# ─────────────────────────────────────────────────────────────────────────────
# Multi-Domain Experiment Runner
# Parameterized by --domain flag. Same 3x3x5x5 = 225 runs per domain.
# ─────────────────────────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

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
  echo "Domains: commit-message, openapi-spec, dockerfile, sql-query, terraform"
  echo ""
  echo "Options:"
  echo "  --domain <name>   Domain to run experiment for (required)"
  echo "  --pilot            Run 1 rep per model, markdown condition, task 1 only"
  echo "  --help             Show this help"
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

DOMAIN_DIR="${SCRIPT_DIR}/domains/${DOMAIN}"

if [[ ! -d "$DOMAIN_DIR" ]]; then
  echo "ERROR: Domain directory not found: ${DOMAIN_DIR}"
  echo "Available domains:"
  ls -1 "${SCRIPT_DIR}/domains/" 2>/dev/null || echo "  (none)"
  exit 1
fi

DATA_DIR="${DOMAIN_DIR}/test-data"
SKILLS_DIR="${DOMAIN_DIR}/skills"
RESULTS_DIR="${DOMAIN_DIR}/results"

# Load domain-specific configuration from task files
TASK_FILES=($(ls "${DATA_DIR}"/task-*.json 2>/dev/null | sort))
if [[ ${#TASK_FILES[@]} -eq 0 ]]; then
  echo "ERROR: No task files found in ${DATA_DIR}"
  exit 1
fi

TASK_COUNT=${#TASK_FILES[@]}
echo "Domain: ${DOMAIN}"
echo "Tasks found: ${TASK_COUNT}"

# Detect skill directory names (pattern: *-markdown and *-pseudocode)
MARKDOWN_SKILL_DIR=$(ls -d "${SKILLS_DIR}"/*-markdown 2>/dev/null | head -1)
PSEUDOCODE_SKILL_DIR=$(ls -d "${SKILLS_DIR}"/*-pseudocode 2>/dev/null | head -1)

if [[ -z "$MARKDOWN_SKILL_DIR" || -z "$PSEUDOCODE_SKILL_DIR" ]]; then
  echo "ERROR: Could not find skill directories in ${SKILLS_DIR}"
  echo "Expected: *-markdown/ and *-pseudocode/"
  ls -1 "${SKILLS_DIR}/" 2>/dev/null
  exit 1
fi

echo "Markdown skill: $(basename "$MARKDOWN_SKILL_DIR")"
echo "Pseudocode skill: $(basename "$PSEUDOCODE_SKILL_DIR")"

# ─── Domain-Specific Prompt Configuration ───────────────────────────────────

# Each domain defines how to build the task prompt and output instruction
build_task_prompt() {
  local task_file="$1"
  local task_json
  task_json=$(cat "$task_file")

  case "$DOMAIN" in
    commit-message)
      local description change_type files_changed ticket author breaking breaking_desc
      description=$(echo "$task_json" | jq -r '.description')
      change_type=$(echo "$task_json" | jq -r '.change_type')
      files_changed=$(echo "$task_json" | jq -r '.files_changed | join(", ")')
      ticket=$(echo "$task_json" | jq -r '.ticket // empty')
      author=$(echo "$task_json" | jq -r '.author // empty')
      breaking=$(echo "$task_json" | jq -r '.breaking_change')
      breaking_desc=$(echo "$task_json" | jq -r '.breaking_change_description // empty')

      cat <<PROMPT
Write a conventional commit message for the following change:

Change type: ${change_type}
Description: ${description}
Files changed: ${files_changed}
PROMPT
      [[ -n "$ticket" ]] && echo "Ticket: ${ticket}"
      [[ -n "$author" ]] && echo "Author: ${author}"
      [[ "$breaking" == "true" ]] && echo "Breaking change: ${breaking_desc}"
      echo ""
      echo "Output ONLY the commit message. No explanation."
      ;;

    openapi-spec)
      local description
      description=$(echo "$task_json" | jq -r '.description')
      cat <<PROMPT
${description}

Output ONLY the OpenAPI specification as JSON or YAML. No explanation.
PROMPT
      ;;

    dockerfile)
      local description
      description=$(echo "$task_json" | jq -r '.description')
      cat <<PROMPT
${description}

Output ONLY the Dockerfile. No explanation.
PROMPT
      ;;

    sql-query)
      local description
      description=$(echo "$task_json" | jq -r '.description')
      cat <<PROMPT
${description}

Structure your answer as multiple SQL files. Output each file as a separate fenced SQL block with a filename comment line above it. Format:

-- filename.sql
\`\`\`sql
SELECT ...
\`\`\`

Output ONLY the SQL files. No explanation.
PROMPT
      ;;

    terraform)
      local description
      description=$(echo "$task_json" | jq -r '.description')
      cat <<PROMPT
${description}

Output ONLY the Terraform configuration. No explanation.
PROMPT
      ;;

    *)
      echo "ERROR: Unknown domain prompt config: ${DOMAIN}" >&2
      return 1
      ;;
  esac
}

get_output_instruction() {
  case "$DOMAIN" in
    commit-message) echo "Output ONLY the commit message. No explanation." ;;
    openapi-spec)   echo "Output ONLY the OpenAPI specification as JSON or YAML. No explanation." ;;
    dockerfile)     echo "Output ONLY the Dockerfile. No explanation." ;;
    sql-query)      echo "Output ONLY the SQL files. No explanation." ;;
    terraform)      echo "Output ONLY the Terraform configuration. No explanation." ;;
  esac
}

get_domain_label() {
  case "$DOMAIN" in
    commit-message) echo "conventional commit" ;;
    openapi-spec)   echo "OpenAPI specification" ;;
    dockerfile)     echo "Dockerfile" ;;
    sql-query)      echo "SQL analytics pipeline" ;;
    terraform)      echo "Terraform configuration" ;;
  esac
}

# ─── Shared Configuration ──────────────────────────────────────────────────

CONDITIONS=("none" "markdown" "pseudocode")

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

# ─── Functions ──────────────────────────────────────────────────────────────

build_prompt() {
  local condition="$1"
  local task_file="$2"

  local task_prompt
  task_prompt=$(build_task_prompt "$task_file")
  local domain_label
  domain_label=$(get_domain_label)

  case "$condition" in
    none)
      echo "$task_prompt"
      ;;
    markdown)
      local skill_content
      skill_content=$(cat "${MARKDOWN_SKILL_DIR}/SKILL.md")
      cat <<EOF
Follow these ${domain_label} guidelines:

${skill_content}

---

${task_prompt}
EOF
      ;;
    pseudocode)
      local skill_content
      skill_content=$(cat "${PSEUDOCODE_SKILL_DIR}/SKILL.md")
      cat <<EOF
Follow these ${domain_label} guidelines:

${skill_content}

---

${task_prompt}
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
  echo "=== PILOT MODE: ${DOMAIN} — 1 run per model, condition=markdown, task=1 ==="
  mkdir -p "$RESULTS_DIR"

  task_file="${TASK_FILES[0]}"
  task_id=$(jq -r '.task_id' "$task_file")

  for model_entry in "${MODELS[@]}"; do
    IFS='|' read -r model_id cli_tool <<< "$model_entry"
    safe_model=$(sanitize "$model_id")
    run_id="${safe_model}_markdown_task${task_id}_pilot"

    if [[ -f "${RESULTS_DIR}/${run_id}.json" ]]; then
      echo "SKIP: ${run_id} (already exists)"
      continue
    fi

    echo "PILOT: ${run_id} (${cli_tool})"
    prompt=$(build_prompt "markdown" "$task_file")

    start_time=$(date +%s%N)
    output=$(run_model "$model_id" "$cli_tool" "$prompt" 2>&1 || echo '{"error": "CLI failed"}')
    end_time=$(date +%s%N)
    duration_ms=$(( (end_time - start_time) / 1000000 ))

    complexity=$(jq -r '.complexity' "$task_file")

    jq -n \
      --arg run_id "$run_id" \
      --arg model "$model_id" \
      --arg condition "markdown" \
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
      }' > "${RESULTS_DIR}/${run_id}.json"

    echo "  Done: ${duration_ms}ms"
    sleep "$SLEEP_BETWEEN"
  done

  echo "=== Pilot complete. Check ${RESULTS_DIR}/ ==="
  exit 0
fi

# ─── Full Experiment ────────────────────────────────────────────────────────

total=$((${#CONDITIONS[@]} * TASK_COUNT * ${#MODELS[@]} * REPS))

echo ""
echo "=== FULL EXPERIMENT: ${DOMAIN} — ${total} runs ==="
echo "Conditions: ${CONDITIONS[*]}"
echo "Tasks: ${TASK_COUNT}"
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
    for task_file in "${TASK_FILES[@]}"; do
      task_id=$(jq -r '.task_id' "$task_file")
      complexity=$(jq -r '.complexity' "$task_file")

      for rep in $(seq 1 "$REPS"); do
        run_id="${safe_model}_${condition}_task${task_id}_rep${rep}"

        # Skip if already completed
        if [[ -f "${RESULTS_DIR}/${run_id}.json" ]]; then
          skipped=$((skipped + 1))
          continue
        fi

        echo "[$(( completed + skipped + failed + 1 ))/${total}] ${run_id}"

        prompt=$(build_prompt "$condition" "$task_file")

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
          --arg condition "$condition" \
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
          }' > "${RESULTS_DIR}/${run_id}.json"

        completed=$((completed + 1))
        echo "  Done: ${duration_ms}ms"

        sleep "$SLEEP_BETWEEN"
      done
    done
  done
done

echo ""
echo "=== Experiment complete: ${DOMAIN} ==="
echo "Completed: ${completed}"
echo "Skipped (existing): ${skipped}"
echo "Failed: ${failed}"
echo "Results in: ${RESULTS_DIR}/"
