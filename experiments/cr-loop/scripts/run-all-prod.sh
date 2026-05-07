#!/usr/bin/env bash
# Run the production code-review skill against all 10 PRs in pr-set.json.
# Serial (one aictrl at a time) so we don't hit GLM rate limits.
# Skips PRs that already have a finished run (looks for .findings.json).
#
# After each run, pulls findings from local Firestore via read-firestore-findings.sh
# so the scorer can read them.
#
# Usage: bash experiments/cr-loop/scripts/run-all-prod.sh

set -uo pipefail
cd "$(git rev-parse --show-toplevel)"

ROOT="experiments/cr-loop"
PR_LIST="$ROOT/pr-set.json"

PRS=$(jq -r '.prs[].number' "$PR_LIST")
echo "PRs to run: $(echo $PRS | tr '\n' ' ')"

for pr in $PRS; do
  EXISTING=$(ls "$ROOT/${CR_LOOP_RUNS_SUBDIR:-runs-prod}/$pr"/*.findings.json 2>/dev/null | head -1)
  if [[ -n "$EXISTING" ]]; then
    echo "[skip] PR #$pr — existing findings: $(basename "$EXISTING")"
    continue
  fi

  echo "=== PR #$pr ==="
  bash "$ROOT/scripts/run-prod-skill.sh" "$pr"
  RUN_JSON=$(ls -t "$ROOT/${CR_LOOP_RUNS_SUBDIR:-runs-prod}/$pr"/*.json 2>/dev/null | grep -v findings | head -1)
  if [[ -z "$RUN_JSON" ]]; then
    echo "[error] no run JSON for PR #$pr — skipping firestore pull"
    continue
  fi
  RUN_ID=$(basename "$RUN_JSON" .json)
  bash "$ROOT/scripts/read-firestore-findings.sh" "$pr" "$RUN_ID"
done

echo
echo "=== summary ==="
for pr in $PRS; do
  FF=$(ls "$ROOT/${CR_LOOP_RUNS_SUBDIR:-runs-prod}/$pr"/*.findings.json 2>/dev/null | head -1)
  if [[ -n "$FF" ]]; then
    N=$(jq '.findings | length' "$FF" 2>/dev/null || echo "?")
    R=$(jq '.reviews | length' "$FF" 2>/dev/null || echo "?")
    echo "PR #$pr: $N findings across $R review(s) ($FF)"
  else
    echo "PR #$pr: no findings.json"
  fi
done
