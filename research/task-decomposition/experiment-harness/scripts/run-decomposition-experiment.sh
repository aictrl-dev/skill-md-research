#!/usr/bin/env bash
set -euo pipefail

# ─────────────────────────────────────────────────────────────────────────────
# Task Decomposition Experiment Runner
# Tests decomposition strategies and artifact formats on Outline codebase
# ─────────────────────────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HARNESS_DIR="$(dirname "$SCRIPT_DIR")"
TASKS_DIR="$HARNESS_DIR/tasks"
RESULTS_DIR="$HARNESS_DIR/results"

# Prevent claude CLI nesting error
unset CLAUDECODE 2>/dev/null || true

# Empty MCP config
EMPTY_MCP="/tmp/experiment-empty-mcp.json"
echo '{"mcpServers":{}}' > "$EMPTY_MCP"

# ─── Configuration ────────────────────────────────────────────────────────────

TASKS=(
  "outline_crud_001_word_count"
  "outline_workflow_001_approval"
  "outline_integration_001_slack"
  "outline_uiflow_001_wizard"
)

DECOMPOSITIONS=(
  "stack"
  "domain"
  "journey"
)

ARTIFACT_FORMATS=(
  "nl"
  "gherkin"
  "gherkin_api"
  "full"
)

MODELS=(
  "haiku"
  "opus"
  "zai-coding-plan/glm-4.5-flash"
)

REPS=3

# ─── Parse Arguments ──────────────────────────────────────────────────────────

TASK=""
DECOMPOSITION=""
ARTIFACTS=""
MODEL=""
REP=""
PILOT=false
DRY_RUN=false
FULL=false

usage() {
  cat << EOF
Usage: $0 [OPTIONS]

Options:
  --task <id>          Task ID (e.g., outline_crud_001_word_count)
  --decomposition <s>  Strategy: stack, domain, journey
  --artifacts <fmt>    Format: nl, gherkin, gherkin_api, full
  --model <model>      Model to use (default: claude-3-5-haiku@20241022)
  --rep <n>            Repetition number (default: 1)
  --pilot              Run pilot: 1 task, 1 decomp, 1 format, all models
  --full               Run full experiment: all tasks × decomps × formats
  --dry-run            Print what would run without executing
  --help               Show this help

Examples:
  # Single run
  $0 --task outline_crud_001_word_count --decomposition stack --artifacts full --rep 1

  # Pilot (quick test)
  $0 --pilot

  # Dry run full experiment
  $0 --full --dry-run
EOF
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --task)
      TASK="$2"
      shift 2
      ;;
    --decomposition)
      DECOMPOSITION="$2"
      shift 2
      ;;
    --artifacts)
      ARTIFACTS="$2"
      shift 2
      ;;
    --model)
      MODEL="$2"
      shift 2
      ;;
    --rep)
      REP="$2"
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
    --dry-run)
      DRY_RUN=true
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

# ─── Helper Functions ─────────────────────────────────────────────────────────

run_single() {
  local task="$1"
  local decomp="$2"
  local artifacts="$3"
  local model="$4"
  local rep="$5"

  # Convert model name to safe directory name
  local model_safe=$(echo "$model" | sed 's/[\/@]/-/g')
  local run_name="${task}/${decomp}_${artifacts}/${model_safe}/rep_${rep}"
  local output_dir="$RESULTS_DIR/$run_name"
  
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "Running: $run_name"
  echo "Model: $model"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

  if [[ "$DRY_RUN" == "true" ]]; then
    echo "[DRY RUN] Would execute:"
    echo "  Task: $task"
    echo "  Decomposition: $decomp"
    echo "  Artifacts: $artifacts"
    echo "  Model: $model"
    echo "  Rep: $rep"
    echo "  Output: $output_dir"
    return 0
  fi

  mkdir -p "$output_dir"

  # Build prompt from task spec and decomposition/artifact prompts
  local task_file="$TASKS_DIR/${task}.md"
  local decomp_prompt="$HARNESS_DIR/prompts/decomposition/${decomp}.md"
  local artifact_prompt="$HARNESS_DIR/prompts/artifacts/${artifacts}.md"

  if [[ ! -f "$task_file" ]]; then
    echo "ERROR: Task file not found: $task_file"
    return 1
  fi

  # Create combined prompt
  local prompt_file="$output_dir/prompt.md"
  {
    echo "# Task Decomposition Experiment"
    echo ""
    echo "## Task Specification"
    echo ""
    cat "$task_file"
    echo ""
    echo "---"
    echo ""
    echo "## Decomposition Strategy: $decomp"
    echo ""
    cat "$decomp_prompt"
    echo ""
    echo "---"
    echo ""
    echo "## Artifact Format: $artifacts"
    echo ""
    cat "$artifact_prompt"
    echo ""
    echo "---"
    echo ""
    echo "## Instructions"
    echo ""
    echo "1. Decompose the task according to the specified strategy"
    echo "2. Generate artifacts in the specified format for each step"
    echo "3. Implement the code changes for each step"
    echo "4. Ensure all tests pass"
    echo ""
    echo "## Output Format"
    echo ""
    echo "For each step, output:"
    echo ""
    echo '```'
    echo "### Step N: [Step Name]"
    echo ""
    echo "**Artifact:**"
    echo '```[format]'
    echo "[artifact content]"
    echo '```'
    echo ""
    echo "**Implementation:**"
    echo '```[language]'
    echo "[code]"
    echo '```'
  } > "$prompt_file"

  echo "Prompt written to: $prompt_file"

  # Run LLM
  local output_file="$output_dir/output.md"
  local metrics_file="$output_dir/metrics.json"

  echo "Running LLM..."

  if [[ "$model" == *"claude"* || "$model" == "haiku" || "$model" == "opus" || "$model" == "sonnet" ]]; then
    # Use claude CLI for Claude models
    claude --print --dangerously-skip-permissions \
           --mcp-config "$EMPTY_MCP" \
           --model "$model" \
           < "$prompt_file" > "$output_file" 2>&1 || true
  else
    # Use opencode CLI for other models
    opencode run -m "$model" -- "$(cat "$prompt_file")" > "$output_file" 2>&1 || true
  fi

  # Record metrics
  local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  local prompt_tokens=$(wc -w < "$prompt_file")
  local output_tokens=$(wc -w < "$output_file")

  cat > "$metrics_file" << EOF
{
  "task": "$task",
  "decomposition": "$decomp",
  "artifacts": "$artifacts",
  "model": "$model",
  "rep": $rep,
  "timestamp": "$timestamp",
  "prompt_tokens": $prompt_tokens,
  "output_tokens": $output_tokens
}
EOF

  echo "Output written to: $output_file"
  echo "Metrics written to: $metrics_file"
  echo ""
}

# ─── Main Execution ──────────────────────────────────────────────────────────

MODEL="${MODEL:-claude-3-5-haiku@20241022}"
REP="${REP:-1}"

if [[ "$PILOT" == "true" ]]; then
  echo "╔══════════════════════════════════════════════════════════════╗"
  echo "║                    PILOT RUN                                 ║"
  echo "╚══════════════════════════════════════════════════════════════╝"
  echo ""
  
  # Run first task with first decomp, first format, all models
  for model in "${MODELS[@]}"; do
    run_single "${TASKS[0]}" "${DECOMPOSITIONS[0]}" "${ARTIFACT_FORMATS[3]}" "$model" 1
  done
  
  echo "Pilot complete!"
  exit 0
fi

if [[ "$FULL" == "true" ]]; then
  echo "╔══════════════════════════════════════════════════════════════╗"
  echo "║                    FULL EXPERIMENT                           ║"
  echo "╚══════════════════════════════════════════════════════════════╝"
  
  total=$((${#TASKS[@]} * ${#DECOMPOSITIONS[@]} * ${#ARTIFACT_FORMATS[@]} * ${#MODELS[@]} * REPS))
  echo "Total runs: $total"
  echo ""
  
  current=0
  for task in "${TASKS[@]}"; do
    for decomp in "${DECOMPOSITIONS[@]}"; do
      for artifacts in "${ARTIFACT_FORMATS[@]}"; do
        for model in "${MODELS[@]}"; do
          for ((rep=1; rep<=REPS; rep++)); do
            ((current++))
            echo "Progress: $current / $total"
            run_single "$task" "$decomp" "$artifacts" "$model" "$rep"
          done
        done
      done
    done
  done
  
  echo "Full experiment complete!"
  exit 0
fi

# Single run
if [[ -n "$TASK" && -n "$DECOMPOSITION" && -n "$ARTIFACTS" ]]; then
  run_single "$TASK" "$DECOMPOSITION" "$ARTIFACTS" "$MODEL" "$REP"
else
  echo "Error: Must specify --task, --decomposition, and --artifacts for single run"
  echo ""
  usage
fi
