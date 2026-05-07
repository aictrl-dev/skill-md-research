#!/usr/bin/env bash
# Run the production code-review skill (with explore-context skill loaded) on
# one PR via aictrl + GLM-5.1, against local MCP wired to local KG.
#
# Per-experiment config: experiments/cr-loop/aictrl-config/aictrl/aictrl.jsonc
# overrides the global aictrl.jsonc by way of XDG_CONFIG_HOME, pointing the
# `aictrl` MCP server at http://localhost:4000/cr-loop/mcp.
#
# Output: experiments/cr-loop/runs-prod/<pr>/<runId>.{ndjson,json,prompt.md}
#
# Usage: bash experiments/cr-loop/scripts/run-prod-skill.sh <pr-number>

set -uo pipefail
cd "$(git rev-parse --show-toplevel)"

PR="${1:?Usage: $0 <pr-number>}"

ROOT="experiments/cr-loop"
WORKSPACE="$ROOT/workspaces/PR-$PR"
RUNS_DIR="$ROOT/${CR_LOOP_RUNS_SUBDIR:-runs-prod}/$PR"
mkdir -p "$RUNS_DIR"

if [[ ! -d "$WORKSPACE/.cr" ]]; then
  echo "ERROR: workspace $WORKSPACE/.cr is missing — run stage-workspaces.sh first"
  exit 1
fi

RUN_ID="$(date -u +%Y-%m-%dT%H-%M-%S)-$$"
NDJSON="$RUNS_DIR/$RUN_ID.ndjson"
JSON="$RUNS_DIR/$RUN_ID.json"
PROMPT="$RUNS_DIR/$RUN_ID.prompt.md"

# Build the prompt — the prod skill expects the agent to do its own gh fetch in
# Step 1, but we've pre-staged the data in .cr/. Tell the agent to read .cr/
# instead.
cat > "$PROMPT" <<EOF
Review pull request #${PR} in repository \`aictrl-dev/aictrl\`.

The Step 1 fetch has already been performed for you. Read these files instead
of running \`gh\`:

- \`.cr/pr-meta.json\` — output of \`gh pr view --json number,title,body,baseRefName,headRefName,author,headRefOid,additions,deletions,changedFiles,url\`
- \`.cr/pr-files.json\` — output of \`gh api repos/aictrl-dev/aictrl/pulls/${PR}/files\`

Follow the rest of the code-review skill exactly. Record review start, all
findings, and completion via the \`aictrl_*\` MCP tools. The \`explore-context\`
skill is also loaded — use \`aictrl_query_context\` whenever a graph query
would clarify a finding (impact, callers, prior findings on the same files).

Required environment variables are set: AICTRL_ORG_ID, AICTRL_EXECUTION_ID,
AICTRL_SKILL_VERSION, AICTRL_MODEL_FULL_PATH, AICTRL_MODEL_PROVIDER,
AICTRL_MODEL_NAME.
EOF

echo "[run] PR #$PR runId=$RUN_ID"
echo "[run] workspace=$WORKSPACE"
echo "[run] writing NDJSON to $NDJSON"

# Required by the prod code-review skill.
export AICTRL_ORG_ID="cr-loop"
export AICTRL_EXECUTION_ID="phase-a-${PR}-${RUN_ID}"
export AICTRL_SKILL_VERSION="code-review@6.0.0"
export AICTRL_MODEL_FULL_PATH="zai-coding-plan/glm-5.1"
export AICTRL_MODEL_PROVIDER="zhipuai"
export AICTRL_MODEL_NAME="glm-5.1"

# Per-experiment XDG so we don't touch the user's global aictrl config.
export XDG_CONFIG_HOME="$PWD/$ROOT/aictrl-config"

START=$(date +%s)
aictrl run \
  --model zai-coding-plan/glm-5.1 \
  --format json \
  --dir "$PWD/$WORKSPACE" \
  -f "$PWD/${CODE_REVIEW_SKILL:-data/default-skills/code-review/SKILL.md}" \
  -f "$PWD/${EXPLORE_CONTEXT_SKILL:-data/default-skills/explore-context/SKILL.md}" \
  < "$PROMPT" \
  > "$NDJSON" 2>"$RUNS_DIR/$RUN_ID.stderr"
EXIT=$?
END=$(date +%s)
DURATION=$((END - START))

echo "[run] exit=$EXIT duration=${DURATION}s ndjson_size=$(wc -c < "$NDJSON")B"

# Quick summary: count tool calls, pull final assistant text out
TOOL_CALLS=$(jq -rcs '[.[] | select(.type=="tool" and .part.tool!=null) | .part.tool] | group_by(.) | map({tool: .[0], count: length})' < "$NDJSON" 2>/dev/null || echo "[]")
echo "[run] tool calls: $TOOL_CALLS"

# Pull last text assistant chunk (skill response)
jq -rs '[.[] | select(.type=="text") | .part.text] | join("\n")' < "$NDJSON" > "$RUNS_DIR/$RUN_ID.text" 2>/dev/null

# Capture metadata
jq -n \
  --arg pr "$PR" \
  --arg runId "$RUN_ID" \
  --arg orgId "$AICTRL_ORG_ID" \
  --arg execId "$AICTRL_EXECUTION_ID" \
  --argjson durationSec "$DURATION" \
  --argjson exit "$EXIT" \
  --argjson toolCalls "$TOOL_CALLS" \
  '{prNumber: ($pr|tonumber), runId: $runId, orgId: $orgId, executionId: $execId, exitCode: $exit, durationSeconds: $durationSec, toolCalls: $toolCalls}' \
  > "$JSON"

echo "[run] saved metadata: $JSON"
