#!/usr/bin/env bash
# Stage a .cr/ workspace per PR so the prod code-review skill's "Step 1 fetch"
# finds local files instead of needing live `gh`. We keep the prod commands
# (gh pr view --json + gh api repos/.../pulls/N/files) so the data shape is
# identical to what the skill expects.
#
# Output: experiments/cr-loop/workspaces/PR-<n>/.cr/{pr-meta.json,pr-files.json}
#
# Idempotent: skips PRs that already have both files.

set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

REPO="aictrl-dev/aictrl"
PR_LIST_JSON="experiments/cr-loop/pr-set.json"
WORKSPACES_ROOT="experiments/cr-loop/workspaces"

mkdir -p "$WORKSPACES_ROOT"

PRS=$(jq -r '.prs[].number' "$PR_LIST_JSON")
for pr in $PRS; do
  ws="$WORKSPACES_ROOT/PR-$pr/.cr"
  meta="$ws/pr-meta.json"
  files="$ws/pr-files.json"
  if [[ -s "$meta" && -s "$files" ]]; then
    echo "  [skip] PR #$pr already staged"
    continue
  fi
  mkdir -p "$ws"
  echo "  [fetch] PR #$pr meta + files"
  gh pr view "$pr" --repo "$REPO" \
    --json number,title,body,baseRefName,headRefName,author,headRefOid,additions,deletions,changedFiles,url \
    > "$meta"
  gh api "repos/$REPO/pulls/$pr/files" --paginate > "$files"
done

echo "[done] staged $(echo "$PRS" | wc -l | tr -d ' ') workspaces under $WORKSPACES_ROOT"
