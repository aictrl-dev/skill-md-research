#!/bin/bash
# Generate a sample prompt for review

HARNESS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT_DIR="$HARNESS_DIR/results/sample"

mkdir -p "$OUTPUT_DIR"

TASK="outline_crud_001_word_count"
DECOMP="stack"
ARTIFACTS="full"

{
  echo "# Task Decomposition Experiment"
  echo ""
  echo "## Task Specification"
  echo ""
  cat "$HARNESS_DIR/tasks/${TASK}.md"
  echo ""
  echo "---"
  echo ""
  echo "## Decomposition Strategy: $DECOMP"
  echo ""
  cat "$HARNESS_DIR/prompts/decomposition/${DECOMP}.md"
  echo ""
  echo "---"
  echo ""
  echo "## Artifact Format: $ARTIFACTS"
  echo ""
  cat "$HARNESS_DIR/prompts/artifacts/${ARTIFACTS}.md"
  echo ""
  echo "---"
  echo ""
  echo "## Instructions"
  echo ""
  echo "1. Decompose the task according to the specified strategy"
  echo "2. Generate artifacts in the specified format for each step"
  echo "3. Implement the code changes for each step"
  echo "4. Ensure all tests pass"
} > "$OUTPUT_DIR/prompt_sample.md"

echo "Sample prompt written to: $OUTPUT_DIR/prompt_sample.md"
echo "Lines: $(wc -l < "$OUTPUT_DIR/prompt_sample.md")"
echo "Words: $(wc -w < "$OUTPUT_DIR/prompt_sample.md")"
