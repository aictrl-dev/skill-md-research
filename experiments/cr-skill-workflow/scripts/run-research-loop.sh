#!/usr/bin/env bash
# Autoresearch-style eval loop for cr-skill-workflow.
# Runs the current/ experiment, scores it, commits if F1 improved vs baseline,
# reverts if not. Appends one row to research/results.tsv.
#
# Usage:
#   run-research-loop.sh --eval               probe + full sweep + commit/revert
#   run-research-loop.sh --eval --probe-only  probe only (no commit)
#
# The researcher (Claude) edits current/ before calling this script.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXP_DIR="$(dirname "$SCRIPT_DIR")"
REPO_ROOT="$(git -C "$EXP_DIR" rev-parse --show-toplevel 2>/dev/null || echo "$EXP_DIR")"
BASELINE_F1="0.204"
MIN_IMPROVEMENT="${MIN_IMPROVEMENT:-0.005}"
PROBE_ONLY=false
EVAL=false

while [[ $# -gt 0 ]]; do case $1 in
  --eval)        EVAL=true; shift;; # explicit eval mode (required)
  --probe-only)  PROBE_ONLY=true; shift;;
  --min-improvement) MIN_IMPROVEMENT="$2"; shift 2;;
  *) echo "Usage: run-research-loop.sh --eval [--probe-only]"; exit 1;;
esac; done

# --eval is required: running the model is expensive, so never start on a bare
# invocation (the bare case used to fall through and silently launch a full sweep).
[[ "$EVAL" == "true" ]] || { echo "Usage: run-research-loop.sh --eval [--probe-only]"; exit 1; }

PROBE_TASKS_FILE="$EXP_DIR/research/probe-tasks.txt"
RESULTS_TSV="$EXP_DIR/research/results.tsv"
CURRENT_EXP="$EXP_DIR/current"

[[ -d "$CURRENT_EXP" ]] || { echo "current/ not found — create a SKILL.md or dag.yaml there first"; exit 1; }

# Determine if current/ is type 1 or type 2
if [[ -f "$CURRENT_EXP/dag.yaml" ]]; then
  CURRENT_TYPE=2
else
  CURRENT_TYPE=1
fi

# Temporary experiment ID for this run
PROBE_ID="probe-$(date +%Y%m%d-%H%M%S)"
FULL_ID="run-$(date +%Y%m%d-%H%M%S)"
# The probe-*/run-* experiment dirs are throwaway copies that live under
# experiments/ (NOT gitignored). A keeper is archived separately as exp-NNN and
# committed before we get here, so these two are always safe to delete. Cleaning
# up on EXIT means a SIGINT/OOM mid-sweep never strands stray dirs in a tracked
# path (which a later `git add` could accidentally stage).
cleanup() {
  rm -rf "$EXP_DIR/experiments/$PROBE_ID" "$EXP_DIR/experiments/$FULL_ID" 2>/dev/null || true
}
trap cleanup EXIT

# Stage the current/ candidate into a named experiment dir the harness can run.
stage_experiment() {
  local dest="$EXP_DIR/experiments/$1"
  mkdir -p "$dest"
  if [[ $CURRENT_TYPE -eq 1 ]]; then
    cp -r "$CURRENT_EXP/skills" "$dest/"
    [[ -f "$CURRENT_EXP/prompt.md" ]] && cp "$CURRENT_EXP/prompt.md" "$dest/"
  else
    cp "$CURRENT_EXP/dag.yaml" "$dest/"
    [[ -d "$CURRENT_EXP/prompts" ]] && cp -r "$CURRENT_EXP/prompts" "$dest/"
  fi
}

# Read a numeric field out of a scores.json (echoes 0 on any failure).
read_score() {
  npx tsx -e "
    try { const s=JSON.parse(require('fs').readFileSync(process.argv[1],'utf8'));
      const v=process.argv[2].split('.').reduce((o,k)=>o?.[k], s);
      process.stdout.write(String(v ?? 0)); }
    catch { process.stdout.write('0'); }
  " "$1" "$2" 2>/dev/null || echo 0
}

# ── Probe ──
echo "=== PROBE: $PROBE_ID ==="
stage_experiment "$PROBE_ID"

while IFS= read -r TASK_ID; do
  [[ -z "$TASK_ID" ]] && continue
  bash "$SCRIPT_DIR/run-workflow.sh" --exp "$PROBE_ID" --rep 1 --task "$TASK_ID" || true
done < "$PROBE_TASKS_FILE"

PROBE_F1="0"
if npx tsx "$SCRIPT_DIR/score.ts" --exp "$PROBE_ID" --reps 1 2>/dev/null; then
  PROBE_F1="$(read_score "$EXP_DIR/results/$PROBE_ID/scores.json" "overall.f1")"
fi
echo "Probe F1: $PROBE_F1  (baseline: $BASELINE_F1)"

# Clean up probe experiment definition (results stay for inspection)
rm -rf "$EXP_DIR/experiments/$PROBE_ID"

THRESHOLD=$(npx tsx -e "process.stdout.write(String($BASELINE_F1 * 0.90))" 2>/dev/null || echo "0.184")
PROBE_PASS=$(npx tsx -e "process.stdout.write(String(parseFloat('$PROBE_F1') >= parseFloat('$THRESHOLD')))" 2>/dev/null || echo "false")

if [[ "$PROBE_ONLY" == "true" ]]; then
  echo "Probe-only mode — done. F1=$PROBE_F1 (threshold=$THRESHOLD, pass=$PROBE_PASS)"
  exit 0
fi

if [[ "$PROBE_PASS" != "true" ]]; then
  echo "Probe below threshold ($PROBE_F1 < $THRESHOLD) — skipping full sweep"
  COMMIT="$(git -C "$EXP_DIR" rev-parse --short HEAD 2>/dev/null || echo 'HEAD')"
  printf '%s\t%s\t%s\t%s\t\t\t\t\t\tdiscard-probe\t%s\n' \
    "$COMMIT" "$FULL_ID" "$PROBE_F1" "" "probe below threshold" >> "$RESULTS_TSV"
  echo "Recorded discard in results.tsv"
  exit 0
fi

# ── Full sweep ──
echo "=== FULL SWEEP: $FULL_ID ==="
stage_experiment "$FULL_ID"

for REP in 1 2 3; do
  bash "$SCRIPT_DIR/run-workflow.sh" --exp "$FULL_ID" --rep "$REP" || true
done

npx tsx "$SCRIPT_DIR/score.ts" --exp "$FULL_ID" --reps 1,2,3
SCORES_JSON="$EXP_DIR/results/$FULL_ID/scores.json"
FULL_F1="$(read_score "$SCORES_JSON" "overall.f1")"
FILE_F1="$(read_score "$SCORES_JSON" "byScope.file.f1")"
MOD_F1="$(read_score "$SCORES_JSON" "byScope.module.f1")"
TP="$(read_score "$SCORES_JSON" "overall.tp")"
FP="$(read_score "$SCORES_JSON" "overall.fp")"
FN="$(read_score "$SCORES_JSON" "overall.fn")"

echo "Full sweep F1: $FULL_F1  (baseline: $BASELINE_F1, min-improvement: $MIN_IMPROVEMENT)"

IMPROVED=$(npx tsx -e "
  process.stdout.write(String(parseFloat('$FULL_F1') >= parseFloat('$BASELINE_F1') + parseFloat('$MIN_IMPROVEMENT')));
" 2>/dev/null || echo "false")

COMMIT="$(git -C "$EXP_DIR" rev-parse --short HEAD 2>/dev/null || echo 'HEAD')"

# Read hypothesis from current/
HYPOTHESIS=""
if [[ -f "$CURRENT_EXP/dag.yaml" ]]; then
  HYPOTHESIS="$(grep 'hypothesis:' "$CURRENT_EXP/dag.yaml" | sed 's/.*hypothesis:[ "]*//' | tr -d '"' || true)"
elif [[ -f "$CURRENT_EXP/skills/code-review/SKILL.md" ]]; then
  HYPOTHESIS="$(grep 'description:' "$CURRENT_EXP/skills/code-review/SKILL.md" | head -1 | sed 's/description:[ ]*//' || true)"
fi

if [[ "$IMPROVED" == "true" ]]; then
  # Archive current/ as a named experiment and commit (paths relative to repo root)
  EXISTING=$(ls -d "$EXP_DIR/experiments"/exp-* 2>/dev/null | wc -l | tr -d ' ')
  FINAL_ID="exp-$(printf '%03d' "$((EXISTING + 1))")-$(date +%Y%m%d)"
  cp -r "$EXP_DIR/experiments/$FULL_ID" "$EXP_DIR/experiments/$FINAL_ID"
  DELTA="$(npx tsx -e "process.stdout.write((parseFloat('$FULL_F1')-$BASELINE_F1).toFixed(3))" 2>/dev/null || echo '?')"
  git -C "$REPO_ROOT" add "experiments/cr-skill-workflow/experiments/$FINAL_ID"
  git -C "$REPO_ROOT" commit -m "feat(cr-skill-workflow): $FINAL_ID — F1=${FULL_F1} (+${DELTA})"
  COMMIT_NEW="$(git -C "$EXP_DIR" rev-parse --short HEAD 2>/dev/null || echo 'HEAD')"
  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\tkeep\t%s\n' \
    "$COMMIT_NEW" "$FINAL_ID" "$PROBE_F1" "$FULL_F1" "$FILE_F1" "$MOD_F1" "$TP" "$FP" "$FN" "$HYPOTHESIS" >> "$RESULTS_TSV"
  echo "✓ IMPROVED — committed as $FINAL_ID (ΔF1=${DELTA})"
else
  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\tdiscard\t%s\n' \
    "$COMMIT" "$FULL_ID" "$PROBE_F1" "$FULL_F1" "$FILE_F1" "$MOD_F1" "$TP" "$FP" "$FN" "$HYPOTHESIS" >> "$RESULTS_TSV"
  echo "✗ NO IMPROVEMENT — results saved, current/ unchanged"
fi
rm -rf "$EXP_DIR/experiments/$FULL_ID" 2>/dev/null || true
echo "Done."
