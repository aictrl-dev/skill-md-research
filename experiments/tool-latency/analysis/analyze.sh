#!/usr/bin/env bash
set -euo pipefail

# Merge parsed CSVs and compute summary statistics
# Outputs: analysis/summary.csv + console report

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RESULTS_DIR="${SCRIPT_DIR}/../results"
OUT_CSV="${SCRIPT_DIR}/summary.csv"

# ── Step 1: Compute Claude Code T0 baseline (startup overhead without tools) ──

claude_csv="${RESULTS_DIR}/claude-tools.csv"
claude_t0_overhead=0

if [[ -f "$claude_csv" ]]; then
  # Average cli_overhead_ms for T0 runs
  claude_t0_overhead=$(awk -F',' '
    $2 == "T0" { sum += $6; n++ }
    END { if (n > 0) printf "%.0f", sum/n; else print 0 }
  ' "$claude_csv")
  echo "Claude T0 baseline overhead: ${claude_t0_overhead}ms"
fi

# ── Step 2: Build unified CSV ──

echo "cli,test_id,run,tool,latency_ms,measurement" > "$OUT_CSV"

# OpenCode: direct per-tool latency
opencode_csv="${RESULTS_DIR}/opencode-tools.csv"
if [[ -f "$opencode_csv" ]]; then
  tail -n+2 "$opencode_csv" | while IFS= read -r line; do
    echo "${line},per_tool" >> "$OUT_CSV"
  done
fi

# Gemini: direct per-tool latency
gemini_csv="${RESULTS_DIR}/gemini-tools.csv"
if [[ -f "$gemini_csv" ]]; then
  tail -n+2 "$gemini_csv" | while IFS= read -r line; do
    echo "${line},per_tool" >> "$OUT_CSV"
  done
fi

# Claude Code: session-level overhead (adjusted by T0 baseline)
if [[ -f "$claude_csv" ]]; then
  tail -n+2 "$claude_csv" | while IFS=',' read -r cli test_id run duration_ms duration_api_ms cli_overhead_ms wall_ms num_tools; do
    if [[ "$test_id" == "T0" ]]; then
      # Calibration test: report raw overhead
      echo "claude,${test_id},${run},none,${cli_overhead_ms},session_overhead" >> "$OUT_CSV"
    elif [[ "$num_tools" -gt 0 ]]; then
      # Adjusted overhead = total overhead - baseline, divided by tool count
      adjusted=$((cli_overhead_ms - claude_t0_overhead))
      if [[ $adjusted -lt 0 ]]; then adjusted=0; fi
      per_tool=$((adjusted / num_tools))
      echo "claude,${test_id},${run},estimated,${per_tool},session_adjusted" >> "$OUT_CSV"
    fi
  done
fi

# ── Step 3: Compute summary stats per (cli, test_id) ──

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  Tool Dispatch Latency Summary"
echo "═══════════════════════════════════════════════════════════════"
printf "%-10s %-6s %8s %8s %8s %8s  %s\n" "CLI" "Test" "Mean" "Median" "Min" "Max" "Measurement"
echo "───────────────────────────────────────────────────────────────"

# Group by cli+test_id and compute stats
tail -n+2 "$OUT_CSV" | sort -t',' -k1,1 -k2,2 | awk -F',' '
{
  key = $1 "," $2
  vals[key] = vals[key] " " $5
  mtype[key] = $6
}
END {
  for (key in vals) {
    n = split(vals[key], a, " ")
    # Remove empty first element
    delete a[1]; n--

    # Sort values
    for (i = 2; i <= n+1; i++) {
      for (j = i+1; j <= n+1; j++) {
        if (a[i]+0 > a[j]+0) { t = a[i]; a[i] = a[j]; a[j] = t }
      }
    }

    sum = 0; min = 999999999; max = -999999999
    for (i = 2; i <= n+1; i++) {
      v = a[i] + 0
      sum += v
      if (v < min) min = v
      if (v > max) max = v
    }
    mean = sum / n

    # Median
    mid = int(n / 2) + 2  # +2 because array starts at 2
    if (n % 2 == 0) {
      median = (a[mid-1] + a[mid]) / 2
    } else {
      median = a[mid]
    }

    split(key, parts, ",")
    printf "%-10s %-6s %7.0fms %7.0fms %7.0fms %7.0fms  %s\n", parts[1], parts[2], mean, median, min, max, mtype[key]
  }
}
' | sort -k1,1 -k2,2

echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "Summary written to: ${OUT_CSV}"
echo ""
echo "Key:"
echo "  per_tool        = Direct tool execution time (OpenCode/Gemini)"
echo "  session_overhead = Raw CLI overhead including startup (Claude T0)"
echo "  session_adjusted = Estimated per-tool overhead after subtracting T0 baseline"
