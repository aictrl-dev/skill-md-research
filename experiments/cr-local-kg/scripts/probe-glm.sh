#!/usr/bin/env bash
# Quick probe: verify Zhipu GLM models are reachable and support tool use.
# Usage: ZHIPU_API_KEY=<key> bash probe-glm.sh [glm-4.7|glm-4.7-flash]
set -euo pipefail
MODEL="${1:-glm-4.7}"
[[ -n "${ZHIPU_API_KEY:-}" ]] || { echo "set ZHIPU_API_KEY first"; exit 1; }

echo "=== probing $MODEL ==="
curl -s -X POST "https://open.bigmodel.cn/api/paas/v4/chat/completions" \
  -H "Authorization: Bearer $ZHIPU_API_KEY" \
  -H "Content-Type: application/json" \
  -d "$(jq -n --arg m "$MODEL" '{
    model: $m,
    messages: [{role:"user", content:"Reply with the single word: READY"}],
    max_tokens: 10,
    temperature: 0.0
  }')" | jq '{
    model: .model,
    reply: .choices[0].message.content,
    finish: .choices[0].finish_reason,
    usage: .usage,
    error: .error
  }'

echo ""
echo "=== tool-use probe ($MODEL) ==="
curl -s -X POST "https://open.bigmodel.cn/api/paas/v4/chat/completions" \
  -H "Authorization: Bearer $ZHIPU_API_KEY" \
  -H "Content-Type: application/json" \
  -d "$(jq -n --arg m "$MODEL" '{
    model: $m,
    messages: [{role:"user", content:"Call the greet tool with name=world"}],
    tools: [{
      type: "function",
      function: {
        name: "greet",
        description: "Greet someone",
        parameters: {type:"object", properties:{name:{type:"string"}}, required:["name"]}
      }
    }],
    tool_choice: "auto",
    temperature: 0.0
  }')" | jq '{
    model: .model,
    finish: .choices[0].finish_reason,
    tool_calls: .choices[0].message.tool_calls,
    error: .error
  }'
