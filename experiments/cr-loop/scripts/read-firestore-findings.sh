#!/usr/bin/env bash
# Read findings recorded by a code-review run from the local Firestore emulator
# and convert them to the experiment's SkillFinding shape (same as runs/<n>/*.json).
#
# After a successful run, the prod skill writes findings under
#   organizations/cr-loop/pullRequests/{prId}/reviews/{reviewId}/findings/{findingId}
#
# We discover the reviewId via the `executionId` we set per-run, then dump
# every finding in that review into a JSON file alongside the NDJSON.
#
# Usage: bash experiments/cr-loop/scripts/read-firestore-findings.sh <pr-number> <run-id>

set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

PR="${1:?Usage: $0 <pr-number> <run-id>}"
RUN_ID="${2:?Usage: $0 <pr-number> <run-id>}"

ORG_ID="cr-loop"
REPO="aictrl-dev/aictrl"
PR_ID="${ORG_ID}-aictrl-dev-aictrl-${PR}"
EXEC_ID="phase-a-${PR}-${RUN_ID}"

EMULATOR="http://localhost:8088/v1/projects/session-control-dev/databases/(default)"
RUNS_DIR="experiments/cr-loop/${CR_LOOP_RUNS_SUBDIR:-runs-prod}/$PR"
OUT="$RUNS_DIR/$RUN_ID.findings.json"

# 1. List reviews for this PR
REVIEWS_URL="$EMULATOR/documents/organizations/$ORG_ID/pullRequests/$PR_ID/reviews"
echo "[fetch] reviews under $PR_ID"
REVIEWS_JSON=$(curl -s "$REVIEWS_URL" 2>&1)
REVIEW_NAMES=$(echo "$REVIEWS_JSON" | jq -r '.documents[]?.name // empty')
if [[ -z "$REVIEW_NAMES" ]]; then
  echo "[warn] no reviews found at $REVIEWS_URL" >&2
  echo '{"prNumber": '"$PR"', "runId": "'"$RUN_ID"'", "reviews": [], "findings": []}' > "$OUT"
  exit 0
fi

# 2. For each review, pull metadata + findings; pick the one matching execId
COMBINED='{"prNumber": '"$PR"', "runId": "'"$RUN_ID"'", "executionId": "'"$EXEC_ID"'", "reviews": [], "findings": []}'

while IFS= read -r REVIEW_NAME; do
  REVIEW_ID=$(basename "$REVIEW_NAME")
  REVIEW_DOC_URL="$EMULATOR/documents/organizations/$ORG_ID/pullRequests/$PR_ID/reviews/$REVIEW_ID"
  REVIEW_DOC=$(curl -s "$REVIEW_DOC_URL" 2>&1)
  REVIEW_EXEC_ID=$(echo "$REVIEW_DOC" | jq -r '.fields.executionRunId.stringValue // .fields.execution_run_id.stringValue // .fields.executionId.stringValue // empty')

  # Collect findings under this review
  FINDINGS_URL="$REVIEW_DOC_URL/findings"
  FINDINGS_JSON=$(curl -s "$FINDINGS_URL" 2>&1)
  FINDINGS=$(echo "$FINDINGS_JSON" | jq -c '[
    .documents[]? |
    {
      reviewId: (.name | split("/")[-3]),
      findingId: (.name | split("/")[-1]),
      file: (.fields.filePath.stringValue // .fields.file.stringValue // ""),
      line: (.fields.line.integerValue // .fields.line.stringValue // null),
      severity: (.fields.severity.stringValue // ""),
      title: (.fields.title.stringValue // ""),
      description: (.fields.description.stringValue // ""),
      rule: (.fields.rule.stringValue // ""),
      concern: (.fields.concern.stringValue // "")
    }
  ]' 2>&1)

  REVIEW_META=$(jq -n --arg id "$REVIEW_ID" --arg exec "$REVIEW_EXEC_ID" '{reviewId: $id, executionRunId: $exec}')
  # Match by either: review_id == execution_id (prod skill convention),
  # OR executionRunId field equals execution_id (older convention).
  COMBINED=$(echo "$COMBINED" | jq --argjson meta "$REVIEW_META" --argjson findings "$FINDINGS" \
    '.reviews += [$meta]
     | (if ($meta.reviewId == .executionId) or ($meta.executionRunId == .executionId)
        then .findings += $findings else . end)')
done <<< "$REVIEW_NAMES"

echo "$COMBINED" | jq '.' > "$OUT"
echo "[done] wrote $OUT"
echo "  reviews: $(jq '.reviews | length' "$OUT")"
echo "  findings (matching execId): $(jq '.findings | length' "$OUT")"
