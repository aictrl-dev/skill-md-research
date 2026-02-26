#!/usr/bin/env bash
set -euo pipefail

# ─────────────────────────────────────────────────────────────────────────────
# KPI Target Experiment Runner
# Runs pseudocode+target condition to test whether performance framing affects
# agent effort and outcomes.
# ─────────────────────────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

# Prevent claude CLI nesting error
unset CLAUDECODE 2>/dev/null || true

# Empty MCP config to bypass plugin tool-name conflicts
EMPTY_MCP="/tmp/experiment-empty-mcp.json"
echo '{"mcpServers":{}}' > "$EMPTY_MCP"

# ─── Parse Arguments ────────────────────────────────────────────────────────

DOMAIN=""
PILOT=false
FULL=false

usage() {
  echo "Usage: $0 --domain <domain-name> [--pilot] [--full]"
  echo ""
  echo "Runs the pseudocode+target condition to test KPI framing effects."
  echo ""
  echo "Options:"
  echo "  --domain <name>   Domain to run (commit-message, dockerfile, etc.)"
  echo "  --pilot           Run 1 rep per model, task 1 only"
  echo "  --full            Run all 4 conditions (none, md, pc, pc+target)"
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
    --full)
      FULL=true
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

DOMAIN_DIR="${ROOT_DIR}/domains/${DOMAIN}"

if [[ ! -d "$DOMAIN_DIR" ]]; then
  echo "ERROR: Domain directory not found: ${DOMAIN_DIR}"
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

# Detect skill directories
PSEUDOCODE_SKILL_DIR=$(ls -d "${SKILLS_DIR}"/*-pseudocode 2>/dev/null | head -1)
MARKDOWN_SKILL_DIR=$(ls -d "${SKILLS_DIR}"/*-markdown 2>/dev/null | head -1)

if [[ -z "$PSEUDOCODE_SKILL_DIR" ]]; then
  echo "ERROR: Could not find pseudocode skill directory"
  exit 1
fi

echo "Pseudocode skill: $(basename "$PSEUDOCODE_SKILL_DIR")"

# ─── KPI Target Intervention ─────────────────────────────────────────────────

# These are the actual baseline numbers from the commit-message domain results
# For other domains, we use estimates based on rubric baseline expectations

build_kpi_context() {
  local domain="$1"
  
  case "$domain" in
    commit-message)
      cat <<EOF
## Performance Context

Your target for this task is to achieve 97% compliance with the specification (13.5 out of 14 rules passing).

In previous evaluations on similar tasks:
- The baseline model achieved 57% compliance (8/14 rules)
- The skill-enhanced model achieved 86% compliance (12/14 rules)
- The top-performing model achieved 100% compliance (14/14 rules)

Your current model family has historically achieved 80% compliance (11.2/14 rules) on this task type.

To reach the 97% target, pay particular attention to:
- Rule 6: Scope must be from the allowed vocabulary (20% baseline pass rate)
- Rule 7: Gitmoji must be included after type (0% baseline pass rate)
- Rule 11: Signed-off-by footer is required (5% baseline pass rate)
- Rule 13: JIRA-style ticket reference format (5% baseline pass rate)

These 4 rules account for 80% of failures. Focusing on them will maximize your improvement.
EOF
      ;;
    dockerfile)
      cat <<EOF
## Performance Context

Your target for this task is to achieve 95% compliance with Dockerfile best practices (14 out of 15 rules passing).

In previous evaluations:
- The baseline model achieved 45% compliance (7/15 rules)
- The skill-enhanced model achieved 80% compliance (12/15 rules)
- The top-performing model achieved 93% compliance (14/15 rules)

Your current model family has historically achieved 70% compliance on Dockerfile tasks.

To reach the 95% target, pay particular attention to:
- Multi-stage builds for smaller images
- Proper layer ordering to maximize cache efficiency
- Security best practices (non-root user, minimal packages)
- Health checks and proper signal handling
EOF
      ;;
    terraform)
      cat <<EOF
## Performance Context

Your target for this task is to achieve 94% compliance with Terraform best practices (17 out of 18 rules passing).

In previous evaluations:
- The baseline model achieved 40% compliance (7/18 rules)
- The skill-enhanced model achieved 78% compliance (14/18 rules)
- The top-performing model achieved 89% compliance (16/18 rules)

Your current model family has historically achieved 65% compliance on Terraform tasks.

To reach the 94% target, pay particular attention to:
- Proper resource tagging (Name, Environment, ManagedBy)
- Variable validation and descriptions
- Output descriptions and sensitivity marking
- Backend configuration and state management
EOF
      ;;
    openapi-spec)
      cat <<EOF
## Performance Context

Your target for this task is to achieve 92% compliance with OpenAPI specification standards (11 out of 12 rules passing).

In previous evaluations:
- The baseline model achieved 55% compliance (7/12 rules)
- The skill-enhanced model achieved 83% compliance (10/12 rules)
- The top-performing model achieved 100% compliance (12/12 rules)

Your current model family has historically achieved 75% compliance on OpenAPI tasks.

To reach the 92% target, pay particular attention to:
- Complete schema definitions with proper types
- Descriptions for all operations and parameters
- Proper response codes and error schemas
- Security scheme definitions
EOF
      ;;
    sql-query)
      cat <<EOF
## Performance Context

Your target for this task is to achieve 90% compliance with SQL analytics best practices (9 out of 10 rules passing).

In previous evaluations:
- The baseline model achieved 60% compliance (6/10 rules)
- The skill-enhanced model achieved 85% compliance (8.5/10 rules)
- The top-performing model achieved 100% compliance (10/10 rules)

Your current model family has historically achieved 72% compliance on SQL tasks.

To reach the 90% target, pay particular attention to:
- Proper CTE usage for readability
- Window functions instead of self-joins
- Explicit column lists (no SELECT *)
- Proper date handling and timezone awareness
EOF
      ;;
    *)
      # Generic fallback
      cat <<EOF
## Performance Context

Your target for this task is to achieve 95% compliance with the specification.

In previous evaluations on similar tasks:
- The baseline model achieved 55% compliance
- The skill-enhanced model achieved 82% compliance
- The top-performing model achieved 97% compliance

Your current model family has historically achieved 75% compliance on this task type.

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

    dockerfile)
      local description
      description=$(echo "$task_json" | jq -r '.description')
      cat <<PROMPT
${description}

Output ONLY the Dockerfile. No explanation.
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

    openapi-spec)
      local description
      description=$(echo "$task_json" | jq -r '.description')
      cat <<PROMPT
${description}

Output ONLY the OpenAPI specification as JSON or YAML. No explanation.
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
    commit-message) echo "conventional commit" ;;
    dockerfile)     echo "Dockerfile" ;;
    terraform)      echo "Terraform configuration" ;;
    openapi-spec)   echo "OpenAPI specification" ;;
    sql-query)      echo "SQL analytics pipeline" ;;
    *)              echo "specification" ;;
  esac
}

# ─── Model Configuration ────────────────────────────────────────────────────

MODELS=(
  "haiku|claude"
  "opus|claude"
  "zai-coding-plan/glm-4.7-flash|opencode"
  "zai-coding-plan/glm-4.7|opencode"
  "zai-coding-plan/glm-5|opencode"
)

if [[ "$FULL" == true ]]; then
  CONDITIONS=("none" "markdown" "pseudocode" "pseudocode+target")
else
  CONDITIONS=("pseudocode+target")
fi

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
    pseudocode+target)
      local skill_content
      skill_content=$(cat "${PSEUDOCODE_SKILL_DIR}/SKILL.md")
      cat <<EOF
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
  echo "=== PILOT MODE: ${DOMAIN} — 1 run per model, pseudocode+target condition, task 1 ==="
  mkdir -p "$RESULTS_DIR"

  task_file="${TASK_FILES[0]}"
  task_id=$(jq -r '.task_id' "$task_file")

  for model_entry in "${MODELS[@]}"; do
    IFS='|' read -r model_id cli_tool <<< "$model_entry"
    safe_model=$(sanitize "$model_id")
    run_id="${safe_model}_pseudocode-target_task${task_id}_pilot"

    if [[ -f "${RESULTS_DIR}/${run_id}.json" ]]; then
      echo "SKIP: ${run_id} (already exists)"
      continue
    fi

    echo "PILOT: ${run_id} (${cli_tool})"
    prompt=$(build_prompt "pseudocode+target" "$task_file")

    start_time=$(date +%s%N)
    output=$(run_model "$model_id" "$cli_tool" "$prompt" 2>&1 || echo '{"error": "CLI failed"}')
    end_time=$(date +%s%N)
    duration_ms=$(( (end_time - start_time) / 1000000 ))

    complexity=$(jq -r '.complexity' "$task_file")

    jq -n \
      --arg run_id "$run_id" \
      --arg model "$model_id" \
      --arg condition "pseudocode+target" \
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
echo "=== KPI TARGET EXPERIMENT: ${DOMAIN} — ${total} runs ==="
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
        # Use hyphen for pseudocode+target to match filename conventions
        condition_file=$(echo "$condition" | tr '+' '-')
        run_id="${safe_model}_${condition_file}_task${task_id}_rep${rep}"

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
