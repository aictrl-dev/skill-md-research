#!/usr/bin/env bash
set -euo pipefail

# Tool Dispatch Latency Benchmark
# Measures per-tool-call overhead across Claude Code, OpenCode, and Gemini CLI
#
# Usage:
#   ./run-benchmark.sh                              # Run all tests, all CLIs, 3 runs
#   ./run-benchmark.sh --cli opencode --test T1     # Single test, single CLI
#   ./run-benchmark.sh --runs 1 --cooldown 2        # Quick pilot
#   ./run-benchmark.sh --dry-run                    # Verify prompts load without executing

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="/home/bulat/code/kg-blog-update"
RESULTS_RAW="${SCRIPT_DIR}/results/raw"

# Defaults
CLI_FILTER=""
TEST_FILTER=""
RUNS=3
COOLDOWN=5
DRY_RUN=false

# Parse args
while [[ $# -gt 0 ]]; do
  case $1 in
    --cli) CLI_FILTER="$2"; shift 2 ;;
    --test) TEST_FILTER="$2"; shift 2 ;;
    --runs) RUNS="$2"; shift 2 ;;
    --cooldown) COOLDOWN="$2"; shift 2 ;;
    --dry-run) DRY_RUN=true; shift ;;
    -h|--help)
      echo "Usage: $0 [--cli claude|opencode|gemini] [--test T0-T8] [--runs N] [--cooldown S] [--dry-run]"
      exit 0 ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

# Test definitions: ID -> prompt file suffix
TESTS=(T0 T1 T2 T3 T4 T5 T6 T7 T8)
declare -A TEST_FILES
TEST_FILES[T0]="T0-calibration.txt"
TEST_FILES[T1]="T1-file-read-small.txt"
TEST_FILES[T2]="T2-file-read-large.txt"
TEST_FILES[T3]="T3-grep.txt"
TEST_FILES[T4]="T4-glob.txt"
TEST_FILES[T5]="T5-bash-echo.txt"
TEST_FILES[T6]="T6-bash-ls.txt"
TEST_FILES[T7]="T7-mcp-search.txt"
TEST_FILES[T8]="T8-mcp-read.txt"

# CLIs that support each test
declare -A TEST_CLIS
TEST_CLIS[T0]="claude opencode gemini"
TEST_CLIS[T1]="claude opencode gemini"
TEST_CLIS[T2]="claude opencode gemini"
TEST_CLIS[T3]="claude opencode gemini"
TEST_CLIS[T4]="claude opencode gemini"
TEST_CLIS[T5]="claude opencode gemini"
TEST_CLIS[T6]="claude opencode gemini"
TEST_CLIS[T7]="claude opencode"
TEST_CLIS[T8]="claude opencode"

ALL_CLIS=(claude opencode gemini)

log() {
  echo "[$(date '+%H:%M:%S')] $*"
}

# Apply filters
if [[ -n "$TEST_FILTER" ]]; then
  TESTS=("$TEST_FILTER")
fi

cli_supports_test() {
  local cli="$1" test_id="$2"
  [[ " ${TEST_CLIS[$test_id]} " == *" $cli "* ]]
}

get_clis_for_test() {
  local test_id="$1"
  if [[ -n "$CLI_FILTER" ]]; then
    if cli_supports_test "$CLI_FILTER" "$test_id"; then
      echo "$CLI_FILTER"
    fi
  else
    echo "${TEST_CLIS[$test_id]}"
  fi
}

# ── CLI runners ──────────────────────────────────────────────────────────────

run_claude() {
  local test_id="$1" run_num="$2" prompt_file="$3" output_file="$4"
  local timing_file="${output_file%.jsonl}.timing"

  # Claude Code: --verbose adds duration_ms/duration_api_ms to result event
  # For MCP tests, we'd need --mcp-config but the MCP server needs to be configured
  local mcp_flag=""
  if [[ "$test_id" == "T7" || "$test_id" == "T8" ]]; then
    mcp_flag="--mcp-config ${SCRIPT_DIR}/configs/opencode-mcp.json"
  fi

  local wall_start wall_end
  wall_start=$(date +%s%3N)

  env -u CLAUDECODE claude -p "$(cat "$prompt_file")" \
    --output-format stream-json \
    --verbose \
    --dangerously-skip-permissions \
    --model sonnet \
    --no-session-persistence \
    $mcp_flag \
    > "$output_file" 2>/dev/null || true

  wall_end=$(date +%s%3N)
  echo "${wall_start},${wall_end}" > "$timing_file"
}

run_opencode() {
  local test_id="$1" run_num="$2" prompt_file="$3" output_file="$4"

  # Use MCP config for T7/T8, empty config otherwise
  local config="${SCRIPT_DIR}/configs/opencode-no-mcp.json"
  if [[ "$test_id" == "T7" || "$test_id" == "T8" ]]; then
    config="${SCRIPT_DIR}/configs/opencode-mcp.json"
  fi

  OPENCODE_CONFIG="$config" \
  opencode run \
    --format json \
    --model anthropic/claude-sonnet-4-20250514 \
    --dir "$REPO_DIR" \
    "$(cat "$prompt_file")" \
    > "$output_file" 2>/dev/null || true
}

run_gemini() {
  local test_id="$1" run_num="$2" prompt_file="$3" output_file="$4"

  gemini \
    --prompt "$(cat "$prompt_file")" \
    --output-format stream-json \
    --yolo \
    > "$output_file" 2>/dev/null || true
}

# ── Main execution ───────────────────────────────────────────────────────────

mkdir -p "$RESULTS_RAW"

log "Tool Dispatch Latency Benchmark"
log "Repo: ${REPO_DIR}"
log "Tests: ${TESTS[*]}"
log "Runs per test: ${RUNS}"
log "Cooldown: ${COOLDOWN}s"
log "CLI filter: ${CLI_FILTER:-all}"
log "Dry run: ${DRY_RUN}"
echo ""

if [[ "$DRY_RUN" == "true" ]]; then
  log "── Dry run: verifying prompt files ──"
  for test_id in "${TESTS[@]}"; do
    for cli in $(get_clis_for_test "$test_id"); do
      prompt_file="${SCRIPT_DIR}/prompts/${cli}/${TEST_FILES[$test_id]}"
      if [[ -f "$prompt_file" ]]; then
        log "  OK: ${cli}/${test_id} → $(head -1 "$prompt_file" | cut -c1-60)..."
      else
        log "  MISSING: ${prompt_file}"
      fi
    done
  done
  log "Dry run complete."
  exit 0
fi

# Interleaved execution: for each test, for each run, for each CLI
total_runs=0
for test_id in "${TESTS[@]}"; do
  for cli in $(get_clis_for_test "$test_id"); do
    total_runs=$((total_runs + RUNS))
  done
done

current_run=0
for test_id in "${TESTS[@]}"; do
  clis_for_test=$(get_clis_for_test "$test_id")
  [[ -z "$clis_for_test" ]] && continue

  log "━━━ ${test_id}: ${TEST_FILES[$test_id]%.txt} ━━━"

  for run_num in $(seq 1 "$RUNS"); do
    for cli in $clis_for_test; do
      current_run=$((current_run + 1))
      prompt_file="${SCRIPT_DIR}/prompts/${cli}/${TEST_FILES[$test_id]}"
      output_file="${RESULTS_RAW}/${cli}-${test_id}-r${run_num}.jsonl"

      log "  [${current_run}/${total_runs}] ${cli} ${test_id} run${run_num}"

      case "$cli" in
        claude)  run_claude  "$test_id" "$run_num" "$prompt_file" "$output_file" ;;
        opencode) run_opencode "$test_id" "$run_num" "$prompt_file" "$output_file" ;;
        gemini)  run_gemini  "$test_id" "$run_num" "$prompt_file" "$output_file" ;;
      esac

      # Cooldown between runs
      if [[ $current_run -lt $total_runs ]]; then
        sleep "$COOLDOWN"
      fi
    done
  done
done

log ""
log "All runs complete! Raw results in: ${RESULTS_RAW}/"
log "Next steps:"
log "  1. Parse: bash parsers/parse-opencode.sh && bash parsers/parse-gemini.sh && bash parsers/parse-claude.sh"
log "  2. Analyze: bash analysis/analyze.sh"
log "  3. View: cat analysis/summary.csv"
