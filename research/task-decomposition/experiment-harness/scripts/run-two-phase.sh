#!/bin/bash
set -euo pipefail

# ─────────────────────────────────────────────────────────────────────────────
# Two-Phase Experiment Runner
# Phase 1: Generate artifacts only (Gherkin, OpenAPI, SQL)
# Phase 2: Implement code using artifacts
# ─────────────────────────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HARNESS_DIR="$(dirname "$SCRIPT_DIR")"
TASKS_DIR="$HARNESS_DIR/tasks"
RESULTS_DIR="$HARNESS_DIR/results"

# ─── Parse Arguments ──────────────────────────────────────────────────────────

TASK=""
PHASE=""
MODEL="haiku"
DECOMPOSITION="stack"

usage() {
  cat << 'USAGE_EOF'
Usage: $0 --task <id> --phase <1|2> [--model <model>] [--decomposition <strategy>]

Options:
  --task          Task ID (e.g., outline_crud_001_word_count)
  --phase         1 (artifacts) or 2 (implementation)
  --model         Model to use (default: haiku)
  --decomposition Strategy for phase 2 (default: stack)
  --help          Show this help
USAGE_EOF
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --task) TASK="$2"; shift 2 ;;
    --phase) PHASE="$2"; shift 2 ;;
    --model) MODEL="$2"; shift 2 ;;
    --decomposition) DECOMPOSITION="$2"; shift 2 ;;
    --help|-h) usage ;;
    *) echo "Unknown option: $1"; usage ;;
  esac
done

if [[ -z "$TASK" || -z "$PHASE" ]]; then
  echo "Error: --task and --phase are required"
  usage
fi

# ─── Setup Paths ──────────────────────────────────────────────────────────────

TASK_FILE="$TASKS_DIR/${TASK}.md"
if [[ ! -f "$TASK_FILE" ]]; then
  echo "Error: Task file not found: $TASK_FILE"
  exit 1
fi

MODEL_SAFE=$(echo "$MODEL" | sed 's/[\/@]/-/g')
OUTPUT_DIR="$RESULTS_DIR/${TASK}/two-phase/${MODEL_SAFE}"
mkdir -p "$OUTPUT_DIR"

# ─── Phase 1: Artifact Generation ─────────────────────────────────────────────

run_phase1() {
  echo "=== Phase 1: Artifact Generation ==="
  echo "Task: $TASK"
  echo "Model: $MODEL"
  echo ""

  PROMPT_FILE="$OUTPUT_DIR/phase1_prompt.md"
  OUTPUT_FILE="$OUTPUT_DIR/phase1_output.md"

  # Build prompt using Python to avoid heredoc issues
  python3 << PYEOF
import os

task_file = "$TASK_FILE"
prompt_file = "$PROMPT_FILE"

# Read task description
with open(task_file, 'r') as f:
    content = f.read()
    
# Extract description section
desc_start = content.find('## Description')
desc_end = content.find('##', desc_start + 5)
if desc_end == -1:
    desc_end = len(content)
task_desc = content[desc_start:desc_end].strip()

prompt = '''You are a software architect. Design this feature BEFORE implementation.

## Task
''' + task_desc + '''

## Output Requirements

Generate exactly THREE artifacts. Each must be complete and valid.

### 1. GHERKIN TEST SCENARIOS

Output a valid Gherkin feature file with at least 3 scenarios covering:
- Happy path
- Edge cases  
- Error handling

Format:
```gherkin
Feature: [name]
  Scenario: [name]
    Given [context]
    When [action]
    Then [result]
```

### 2. OPENAPI SPECIFICATION

Output a valid OpenAPI 3.0 spec for the API changes.

Format:
```yaml
openapi: 3.0.0
info:
  title: [title]
  version: 1.0.0
paths:
  /api/path:
    get/post:
      summary: [description]
      responses:
        200:
          ...
```

### 3. SQL MIGRATION

Output valid PostgreSQL migration with up and down.

Format:
```sql
-- Up
ALTER TABLE [table] ADD COLUMN [column] [type];

-- Down  
ALTER TABLE [table] DROP COLUMN [column];
```

## CRITICAL RULES

1. Output ALL THREE artifacts with code blocks
2. Each artifact must be syntactically valid
3. DO NOT write implementation code
4. Use exact format: ```gherkin, ```yaml, ```sql

Now generate the three artifacts:
'''

with open(prompt_file, 'w') as f:
    f.write(prompt)
    
print(f"Prompt written: {prompt_file}")
PYEOF

  echo "Output: $OUTPUT_FILE"
  echo ""

  # Run LLM
  if [[ "$MODEL" == "haiku" || "$MODEL" == "opus" || "$MODEL" == "sonnet" ]]; then
    claude --print --dangerously-skip-permissions --model "$MODEL" \
           < "$PROMPT_FILE" > "$OUTPUT_FILE" 2>&1
  else
    timeout 300 opencode run -m "$MODEL" -- "$(cat "$PROMPT_FILE")" > "$OUTPUT_FILE" 2>&1 || true
  fi

  # Clean ANSI codes
  sed -i 's/\x1b\[[0-9;]*m//g' "$OUTPUT_FILE" 2>/dev/null || true

  echo ""
  echo "Phase 1 complete!"
  echo "Lines: $(wc -l < "$OUTPUT_FILE")"
  echo "Words: $(wc -w < "$OUTPUT_FILE")"
  
  # Check for artifacts
  echo ""
  echo "=== Artifact Check ==="
  grep -c '```gherkin' "$OUTPUT_FILE" > /dev/null 2>&1 && echo "✓ Gherkin found" || echo "✗ Gherkin missing"
  grep -c '```yaml' "$OUTPUT_FILE" > /dev/null 2>&1 && echo "✓ OpenAPI found" || echo "✗ OpenAPI missing"
  grep -c '```sql' "$OUTPUT_FILE" > /dev/null 2>&1 && echo "✓ SQL found" || echo "✗ SQL missing"
}

# ─── Phase 2: Implementation ──────────────────────────────────────────────────

run_phase2() {
  echo "=== Phase 2: Implementation ==="
  echo "Task: $TASK"
  echo "Model: $MODEL"
  echo "Decomposition: $DECOMPOSITION"
  echo ""

  PHASE1_FILE="$OUTPUT_DIR/phase1_output.md"
  if [[ ! -f "$PHASE1_FILE" ]]; then
    echo "Error: Phase 1 output not found. Run phase 1 first."
    exit 1
  fi

  PROMPT_FILE="$OUTPUT_DIR/phase2_prompt.md"
  OUTPUT_FILE="$OUTPUT_DIR/phase2_output.md"

  DECOMP_FILE="$HARNESS_DIR/prompts/decomposition/${DECOMPOSITION}.md"
  
  python3 << PYEOF
import os

task_file = "$TASK_FILE"
phase1_file = "$PHASE1_FILE"
decomp_file = "$DECOMP_FILE"
prompt_file = "$PROMPT_FILE"

with open(task_file, 'r') as f:
    content = f.read()
desc_start = content.find('## Description')
desc_end = content.find('##', desc_start + 5)
if desc_end == -1:
    desc_end = len(content)
task_desc = content[desc_start:desc_end].strip()

with open(phase1_file, 'r') as f:
    artifacts = f.read()

try:
    with open(decomp_file, 'r') as f:
        decomp = f.read()
except:
    decomp = "Stack: DB → Model → API → Tests"

prompt = '''You are a software engineer. Implement using the pre-designed artifacts.

## Task
''' + task_desc + '''

## Pre-designed Artifacts

''' + artifacts + '''

## Decomposition Strategy

''' + decomp + '''

## Implementation

For each step, output the code changes:

### Step N: [Name]

File: path/to/file.ts
```typescript
[actual code]
```

Now implement:
'''

with open(prompt_file, 'w') as f:
    f.write(prompt)
PYEOF

  echo "Output: $OUTPUT_FILE"
  echo ""

  if [[ "$MODEL" == "haiku" || "$MODEL" == "opus" || "$MODEL" == "sonnet" ]]; then
    claude --print --dangerously-skip-permissions --model "$MODEL" \
           < "$PROMPT_FILE" > "$OUTPUT_FILE" 2>&1
  else
    timeout 300 opencode run -m "$MODEL" -- "$(cat "$PROMPT_FILE")" > "$OUTPUT_FILE" 2>&1 || true
  fi

  sed -i 's/\x1b\[[0-9;]*m//g' "$OUTPUT_FILE" 2>/dev/null || true

  echo ""
  echo "Phase 2 complete!"
  echo "Lines: $(wc -l < "$OUTPUT_FILE")"
  echo "Words: $(wc -w < "$OUTPUT_FILE")"
}

# ─── Main ─────────────────────────────────────────────────────────────────────

case "$PHASE" in
  1) run_phase1 ;;
  2) run_phase2 ;;
  both) run_phase1; run_phase2 ;;
  *) echo "Error: Phase must be 1, 2, or both"; usage ;;
esac
