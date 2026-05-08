#!/usr/bin/env bash
set -euo pipefail

# KG A/B Experiment Runner
# Usage:
#   ./run-experiment.sh                           # Run all 6 combinations
#   ./run-experiment.sh --task 1 --condition control   # Run single combination
#   ./run-experiment.sh --dry-run                 # Test with trivial prompt

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="/home/bulat/code/kg-blog-update"
RESULTS_RAW="${SCRIPT_DIR}/results/raw"
RESULTS_GEN="${SCRIPT_DIR}/results/generated"

# Defaults
TASK_FILTER=""
CONDITION_FILTER=""
DRY_RUN=false

# Parse args
while [[ $# -gt 0 ]]; do
  case $1 in
    --task) TASK_FILTER="$2"; shift 2 ;;
    --condition) CONDITION_FILTER="$2"; shift 2 ;;
    --dry-run) DRY_RUN=true; shift ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

TASKS=(1 2 3)
CONDITIONS=(control treatment)
TASK_FILES=("task-1-easy.md" "task-2-medium.md" "task-3-hard.md")

# Support custom task IDs like "2b"
declare -A CUSTOM_TASK_FILES
CUSTOM_TASK_FILES["2b"]="task-2b-medium-discovery.md"
CUSTOM_TASK_FILES["3b"]="task-3b-hard-discovery.md"

# Apply filters
if [[ -n "$TASK_FILTER" ]]; then
  TASKS=("$TASK_FILTER")
fi
if [[ -n "$CONDITION_FILTER" ]]; then
  CONDITIONS=("$CONDITION_FILTER")
fi

log() {
  echo "[$(date '+%H:%M:%S')] $*"
}

run_single() {
  local task_num="$1"
  local condition="$2"
  local task_file=""
  if [[ -n "${CUSTOM_TASK_FILES[$task_num]+x}" ]]; then
    task_file="${CUSTOM_TASK_FILES[$task_num]}"
  else
    local task_idx=$((task_num - 1))
    task_file="${TASK_FILES[$task_idx]}"
  fi
  local run_id="${condition}-task-${task_num}"

  log "=== Starting: ${run_id} ==="

  # Ensure output dirs exist
  mkdir -p "${RESULTS_RAW}" "${RESULTS_GEN}/${run_id}"

  # Reset workspace to baseline (undo any commits/changes from previous runs)
  log "Resetting workspace..."
  cd "${REPO_DIR}"
  git reset --hard "${BASELINE_COMMIT}" 2>/dev/null || true
  git clean -fd 2>/dev/null || true

  # Build prompt
  local prompt
  if [[ "$DRY_RUN" == "true" ]]; then
    prompt="Create a file called /tmp/kg-ab-test-${run_id}.txt with the text 'hello from ${run_id}'"
  else
    prompt="$(cat "${SCRIPT_DIR}/tasks/${task_file}")"
  fi

  # Select config
  local config="${SCRIPT_DIR}/opencode-${condition}.json"

  log "Running OpenCode (condition=${condition}, task=${task_num})..."
  local start_time
  start_time=$(date +%s)

  # Run OpenCode headless
  OPENCODE_CONFIG="${config}" \
  opencode run \
    --format json \
    --model zai-coding-plan/glm-5 \
    --dir "${REPO_DIR}" \
    --title "kg-ab-${run_id}" \
    "${prompt}" \
    > "${RESULTS_RAW}/${run_id}.jsonl" 2>&1 || true

  local end_time
  end_time=$(date +%s)
  local duration=$((end_time - start_time))
  log "OpenCode finished in ${duration}s"

  # Capture generated code: both uncommitted changes and new commits
  cd "${REPO_DIR}"
  git diff > "${RESULTS_GEN}/${run_id}/changes.patch" 2>/dev/null || true
  git diff --stat > "${RESULTS_GEN}/${run_id}/diff-stat.txt" 2>/dev/null || true
  # Also capture committed changes since baseline
  git diff "${BASELINE_COMMIT}"..HEAD > "${RESULTS_GEN}/${run_id}/all-changes.patch" 2>/dev/null || true
  git diff --stat "${BASELINE_COMMIT}"..HEAD > "${RESULTS_GEN}/${run_id}/all-diff-stat.txt" 2>/dev/null || true
  git log --oneline "${BASELINE_COMMIT}"..HEAD > "${RESULTS_GEN}/${run_id}/commits.txt" 2>/dev/null || true

  # Also copy any new files
  local new_files
  new_files=$(git ls-files --others --exclude-standard 2>/dev/null || true)
  if [[ -n "$new_files" ]]; then
    echo "$new_files" > "${RESULTS_GEN}/${run_id}/new-files.txt"
    while IFS= read -r f; do
      mkdir -p "${RESULTS_GEN}/${run_id}/$(dirname "$f")"
      cp "$f" "${RESULTS_GEN}/${run_id}/$f"
    done <<< "$new_files"
  fi

  # Run automated checks
  log "Running automated checks..."
  local build_exit=0 lint_exit=0 ui_build_exit=0 ui_lint_exit=0

  cd "${REPO_DIR}"
  npm run build > "${RESULTS_GEN}/${run_id}/build.log" 2>&1 || build_exit=$?
  npm run lint > "${RESULTS_GEN}/${run_id}/lint.log" 2>&1 || lint_exit=$?

  # UI checks only for task 3
  if [[ "$task_num" == "3" ]]; then
    cd "${REPO_DIR}/ui"
    npm run build > "${RESULTS_GEN}/${run_id}/ui-build.log" 2>&1 || ui_build_exit=$?
    npm run lint > "${RESULTS_GEN}/${run_id}/ui-lint.log" 2>&1 || ui_lint_exit=$?
  fi

  # Record check results
  cat > "${RESULTS_GEN}/${run_id}/checks.json" <<EOF
{
  "run_id": "${run_id}",
  "duration_seconds": ${duration},
  "build_exit": ${build_exit},
  "lint_exit": ${lint_exit},
  "ui_build_exit": ${ui_build_exit},
  "ui_lint_exit": ${ui_lint_exit},
  "compiles": $([ $build_exit -eq 0 ] && echo "true" || echo "false"),
  "lints": $([ $lint_exit -eq 0 ] && echo "true" || echo "false")
}
EOF

  log "Checks: build=${build_exit} lint=${lint_exit} ui_build=${ui_build_exit} ui_lint=${ui_lint_exit}"

  # Reset workspace for next run (undo any commits/changes)
  cd "${REPO_DIR}"
  git reset --hard "${BASELINE_COMMIT}" 2>/dev/null || true
  git clean -fd 2>/dev/null || true

  log "=== Completed: ${run_id} ==="
  echo ""
}

# Capture baseline commit before any runs modify the repo
BASELINE_COMMIT=$(git -C "${REPO_DIR}" rev-parse HEAD)

# Main execution - interleaved order to minimize temporal bias
log "Starting KG A/B experiment"
log "Baseline commit: ${BASELINE_COMMIT}"
log "Tasks: ${TASKS[*]}"
log "Conditions: ${CONDITIONS[*]}"
log "Dry run: ${DRY_RUN}"
echo ""

for task_num in "${TASKS[@]}"; do
  for condition in "${CONDITIONS[@]}"; do
    run_single "$task_num" "$condition"
  done
done

log "All runs complete!"
log "Next steps:"
log "  1. Run: ./analysis/extract-metrics.sh"
log "  2. Score quality: edit analysis/score-quality.md"
log "  3. Generate report: see analysis/report.md template"
