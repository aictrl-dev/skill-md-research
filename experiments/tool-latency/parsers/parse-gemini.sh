#!/usr/bin/env bash
set -euo pipefail

# Parse Gemini CLI stream-json results → CSV
# Gemini emits paired events: functionCall (tool_use) and functionResponse (tool_result)
# with ISO timestamps. We diff timestamps between consecutive pairs.
#
# Gemini stream-json format (observed):
#   {"type":"functionCall","timestamp":"2025-...","name":"read_file",...}
#   {"type":"functionResponse","timestamp":"2025-...","name":"read_file",...}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RAW_DIR="${SCRIPT_DIR}/../results/raw"
OUT_CSV="${SCRIPT_DIR}/../results/gemini-tools.csv"

echo "cli,test_id,run,tool,latency_ms" > "$OUT_CSV"

for f in "${RAW_DIR}"/gemini-T*-r*.jsonl; do
  [[ -f "$f" ]] || continue
  basename=$(basename "$f" .jsonl)
  test_id=$(echo "$basename" | sed 's/gemini-\(T[0-9]*\)-.*/\1/')
  run=$(echo "$basename" | sed 's/.*-r\([0-9]*\)/\1/')

  # Strategy: extract all events with timestamps, pair functionCall with next functionResponse
  # Gemini may use different event schemas; we try multiple approaches

  # Approach 1: events have .type == "functionCall" / "functionResponse" with .timestamp
  jq -r '
    select(.type == "functionCall" or .type == "functionResponse")
    | [.type, .name // .toolName // "unknown", .timestamp // ""]
    | @tsv
  ' "$f" 2>/dev/null | {
    call_tool="" call_ts=""
    while IFS=$'\t' read -r etype tool ts; do
      if [[ "$etype" == "functionCall" ]]; then
        call_tool="$tool"
        call_ts="$ts"
      elif [[ "$etype" == "functionResponse" && -n "$call_ts" ]]; then
        # Compute ms diff between ISO timestamps
        if command -v python3 &>/dev/null; then
          latency=$(python3 -c "
from datetime import datetime
t1 = datetime.fromisoformat('${call_ts}'.replace('Z','+00:00'))
t2 = datetime.fromisoformat('${ts}'.replace('Z','+00:00'))
print(int((t2-t1).total_seconds()*1000))
" 2>/dev/null || echo "-1")
        else
          # Fallback: use date command (GNU date supports ISO)
          start_epoch=$(date -d "$call_ts" +%s%3N 2>/dev/null || echo "0")
          end_epoch=$(date -d "$ts" +%s%3N 2>/dev/null || echo "0")
          latency=$((end_epoch - start_epoch))
        fi
        echo "gemini,${test_id},${run},\"${call_tool}\",${latency}" >> "$OUT_CSV"
        call_tool="" call_ts=""
      fi
    done
  }

  # Approach 2: events have .serverContent.modelTurn.parts[].functionCall
  # (Gemini's actual streaming format may nest tool calls differently)
  # We also look for tool execution time in metadata if available
  jq -r '
    select(.toolCall != null or .tool_use != null)
    | .toolCall // .tool_use
    | [
        .name // .tool // "unknown",
        ((.endTime // .end_time // 0) - (.startTime // .start_time // 0)) | tostring
      ]
    | @csv
  ' "$f" 2>/dev/null | while IFS= read -r line; do
    # Only add if we got a valid latency (not 0)
    latency=$(echo "$line" | awk -F',' '{gsub(/"/, "", $2); print $2}')
    if [[ "$latency" != "0" && -n "$latency" ]]; then
      echo "gemini,${test_id},${run},${line}" >> "$OUT_CSV"
    fi
  done
done

rows=$(wc -l < "$OUT_CSV")
echo "Gemini: parsed $((rows - 1)) tool calls → ${OUT_CSV}"
