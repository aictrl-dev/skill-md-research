#!/usr/bin/env bash
set -euo pipefail

# Parse Claude Code stream-json results → CSV
#
# Claude Code does NOT emit per-tool timestamps. Instead, the final "result" event
# contains session-level metrics:
#   - duration_ms: total wall-clock time
#   - duration_api_ms: time spent in API calls
#   - cli_overhead_ms = duration_ms - duration_api_ms (includes startup + tool dispatch)
#
# We also capture wall-clock timing from the .timing sidecar file (start_ms,end_ms)
# written by run-benchmark.sh.
#
# To isolate tool dispatch overhead, we subtract the T0 (calibration) baseline
# from each test's overhead. This is done in analysis/analyze.sh.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RAW_DIR="${SCRIPT_DIR}/../results/raw"
OUT_CSV="${SCRIPT_DIR}/../results/claude-tools.csv"

echo "cli,test_id,run,duration_ms,duration_api_ms,cli_overhead_ms,wall_ms,num_tool_calls" > "$OUT_CSV"

for f in "${RAW_DIR}"/claude-T*-r*.jsonl; do
  [[ -f "$f" ]] || continue
  basename=$(basename "$f" .jsonl)
  test_id=$(echo "$basename" | sed 's/claude-\(T[0-9]*\)-.*/\1/')
  run=$(echo "$basename" | sed 's/.*-r\([0-9]*\)/\1/')

  # Extract from result event (last event with type "result")
  result=$(jq -s '
    [.[] | select(.type == "result")] | last // empty
  ' "$f" 2>/dev/null)

  if [[ -z "$result" ]]; then
    # Fallback: try to find duration in any event
    result=$(jq -s '
      [.[] | select(.duration_ms != null)] | last // empty
    ' "$f" 2>/dev/null)
  fi

  if [[ -n "$result" && "$result" != "null" ]]; then
    duration_ms=$(echo "$result" | jq -r '.duration_ms // .stats.duration_ms // 0')
    duration_api_ms=$(echo "$result" | jq -r '.duration_api_ms // .stats.duration_api_ms // 0')
    cli_overhead_ms=$((duration_ms - duration_api_ms))

    # Count tool calls from the stream
    num_tools=$(jq -s '[.[] | select(.type == "tool_use" or .type == "assistant" and .tool_use != null)] | length' "$f" 2>/dev/null || echo "0")
  else
    duration_ms=0
    duration_api_ms=0
    cli_overhead_ms=0
    num_tools=0
  fi

  # Wall-clock timing from sidecar
  timing_file="${f%.jsonl}.timing"
  wall_ms=0
  if [[ -f "$timing_file" ]]; then
    wall_start=$(cut -d',' -f1 "$timing_file")
    wall_end=$(cut -d',' -f2 "$timing_file")
    wall_ms=$((wall_end - wall_start))
  fi

  echo "claude,${test_id},${run},${duration_ms},${duration_api_ms},${cli_overhead_ms},${wall_ms},${num_tools}" >> "$OUT_CSV"
done

rows=$(wc -l < "$OUT_CSV")
echo "Claude Code: parsed $((rows - 1)) sessions → ${OUT_CSV}"
