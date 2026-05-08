#!/usr/bin/env bash
set -euo pipefail

# Parse OpenCode JSONL results → CSV
# OpenCode emits tool_use events with part.state.time.{start,end} in epoch ms

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RAW_DIR="${SCRIPT_DIR}/../results/raw"
OUT_CSV="${SCRIPT_DIR}/../results/opencode-tools.csv"

echo "cli,test_id,run,tool,latency_ms" > "$OUT_CSV"

for f in "${RAW_DIR}"/opencode-T*-r*.jsonl; do
  [[ -f "$f" ]] || continue
  basename=$(basename "$f" .jsonl)
  # Extract test_id and run from filename: opencode-T1-r1
  test_id=$(echo "$basename" | sed 's/opencode-\(T[0-9]*\)-.*/\1/')
  run=$(echo "$basename" | sed 's/.*-r\([0-9]*\)/\1/')

  # Extract tool_use events with timing
  jq -r '
    select(.type == "tool_use")
    | select(.part.state.time.start != null and .part.state.time.end != null)
    | [
        .part.tool // .part.state.tool // "unknown",
        ((.part.state.time.end - .part.state.time.start) | tostring)
      ]
    | @csv
  ' "$f" 2>/dev/null | while IFS= read -r line; do
    echo "opencode,${test_id},${run},${line}" >> "$OUT_CSV"
  done
done

rows=$(wc -l < "$OUT_CSV")
echo "OpenCode: parsed $((rows - 1)) tool calls → ${OUT_CSV}"
