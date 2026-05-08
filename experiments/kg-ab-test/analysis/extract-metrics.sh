#!/usr/bin/env bash
set -euo pipefail

# Extract token usage metrics from OpenCode JSONL output files
# OpenCode format: step_finish events with part.tokens

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RAW_DIR="${SCRIPT_DIR}/../results/raw"
GEN_DIR="${SCRIPT_DIR}/../results/generated"

if ! command -v jq &> /dev/null; then
  echo "Error: jq is required. Install with: sudo apt install jq"
  exit 1
fi

echo "========================================="
echo "KG A/B Experiment - Token Metrics"
echo "========================================="
echo ""

# CSV header
echo "run_id,input_tokens,output_tokens,reasoning_tokens,cache_read,total_tokens,steps,duration_s,compiles,lints" \
  > "${SCRIPT_DIR}/metrics.csv"

for jsonl_file in "${RAW_DIR}"/*.jsonl; do
  [[ -f "$jsonl_file" ]] || continue

  run_id=$(basename "$jsonl_file" .jsonl)

  # Extract token usage from step_finish events
  metrics=$(cat "$jsonl_file" | \
    jq -s '[.[] | select(.type=="step_finish") | .part.tokens // empty] | {
      input_tokens: (map(.input // 0) | add // 0),
      output_tokens: (map(.output // 0) | add // 0),
      reasoning_tokens: (map(.reasoning // 0) | add // 0),
      cache_read: (map(.cache.read // 0) | add // 0),
      total_tokens: (map(.total // 0) | add // 0),
      steps: length
    }' 2>/dev/null || echo '{"input_tokens":0,"output_tokens":0,"reasoning_tokens":0,"cache_read":0,"total_tokens":0,"steps":0}')

  input_tokens=$(echo "$metrics" | jq '.input_tokens')
  output_tokens=$(echo "$metrics" | jq '.output_tokens')
  reasoning_tokens=$(echo "$metrics" | jq '.reasoning_tokens')
  cache_read=$(echo "$metrics" | jq '.cache_read')
  total_tokens=$(echo "$metrics" | jq '.total_tokens')
  steps=$(echo "$metrics" | jq '.steps')

  # Calculate cost from step_finish events
  total_cost=$(cat "$jsonl_file" | \
    jq -s '[.[] | select(.type=="step_finish") | .part.cost // 0] | add // 0' 2>/dev/null || echo 0)

  # Count tool uses
  tool_uses=$(cat "$jsonl_file" | \
    jq -s '[.[] | select(.type=="tool_start")] | length' 2>/dev/null || echo 0)

  # Get duration and check results from checks.json
  checks_file="${GEN_DIR}/${run_id}/checks.json"
  duration="N/A"
  compiles="N/A"
  lints="N/A"
  if [[ -f "$checks_file" ]]; then
    duration=$(jq -r '.duration_seconds' "$checks_file")
    compiles=$(jq -r '.compiles' "$checks_file")
    lints=$(jq -r '.lints' "$checks_file")
  fi

  echo "--- ${run_id} ---"
  echo "  Input tokens:      ${input_tokens}"
  echo "  Output tokens:     ${output_tokens}"
  echo "  Reasoning tokens:  ${reasoning_tokens}"
  echo "  Cache read:        ${cache_read}"
  echo "  Total tokens:      ${total_tokens}"
  echo "  Steps:             ${steps}"
  echo "  Tool uses:         ${tool_uses}"
  echo "  Cost:              \$${total_cost}"
  echo "  Duration:          ${duration}s"
  echo "  Compiles:          ${compiles}"
  echo "  Lints:             ${lints}"
  echo ""

  # Append to CSV
  echo "${run_id},${input_tokens},${output_tokens},${reasoning_tokens},${cache_read},${total_tokens},${steps},${duration},${compiles},${lints}" \
    >> "${SCRIPT_DIR}/metrics.csv"
done

echo "========================================="
echo "Comparison Summary"
echo "========================================="
echo ""

# Compare control vs treatment for each task
for task_num in 1 2 3; do
  control_file="${RAW_DIR}/control-task-${task_num}.jsonl"
  treatment_file="${RAW_DIR}/treatment-task-${task_num}.jsonl"

  if [[ -f "$control_file" && -f "$treatment_file" ]]; then
    control_tokens=$(cat "$control_file" | jq -s '[.[] | select(.type=="step_finish") | .part.tokens.total // 0] | add // 0' 2>/dev/null || echo 0)
    treatment_tokens=$(cat "$treatment_file" | jq -s '[.[] | select(.type=="step_finish") | .part.tokens.total // 0] | add // 0' 2>/dev/null || echo 0)

    if [[ "$control_tokens" -gt 0 ]]; then
      reduction=$(echo "scale=1; ($control_tokens - $treatment_tokens) * 100 / $control_tokens" | bc 2>/dev/null || echo "N/A")
      echo "Task ${task_num}: Control=${control_tokens} tokens, Treatment=${treatment_tokens} tokens, Reduction=${reduction}%"
    else
      echo "Task ${task_num}: No data yet"
    fi
  else
    echo "Task ${task_num}: Missing results (need both control and treatment runs)"
  fi
done

echo ""
echo "CSV exported to: ${SCRIPT_DIR}/metrics.csv"
