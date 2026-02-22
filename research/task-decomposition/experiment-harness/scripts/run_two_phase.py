#!/usr/bin/env python3
"""
Two-Phase Experiment Runner
Phase 1: Generate artifacts only (Gherkin, OpenAPI, SQL)
Phase 2: Implement code using artifacts
"""

import argparse
import os
import subprocess
import re

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
HARNESS_DIR = os.path.dirname(SCRIPT_DIR)
TASKS_DIR = os.path.join(HARNESS_DIR, "tasks")
RESULTS_DIR = os.path.join(HARNESS_DIR, "results")


def extract_description(task_file: str) -> str:
    """Extract task description from task spec file."""
    with open(task_file, 'r') as f:
        content = f.read()
    
    # Find description section
    match = re.search(r'## Description\n(.*?)(?=\n##|\Z)', content, re.DOTALL)
    if match:
        return match.group(1).strip()
    return content[:500]


def run_phase1(task: str, model: str):
    """Generate artifacts only."""
    print(f"=== Phase 1: Artifact Generation ===")
    print(f"Task: {task}")
    print(f"Model: {model}")
    print()
    
    task_file = os.path.join(TASKS_DIR, f"{task}.md")
    if not os.path.exists(task_file):
        print(f"Error: Task file not found: {task_file}")
        return
    
    model_safe = model.replace('/', '-').replace('@', '-')
    output_dir = os.path.join(RESULTS_DIR, task, "two-phase", model_safe)
    os.makedirs(output_dir, exist_ok=True)
    
    prompt_file = os.path.join(output_dir, "phase1_prompt.md")
    output_file = os.path.join(output_dir, "phase1_output.md")
    
    # Build prompt
    task_desc = extract_description(task_file)
    template_file = os.path.join(HARNESS_DIR, "prompts", "phase1_template.md")
    
    with open(template_file, 'r') as f:
        template = f.read()
    
    prompt = template.replace("{TASK_DESCRIPTION}", task_desc)
    
    with open(prompt_file, 'w') as f:
        f.write(prompt)
    
    print(f"Prompt: {prompt_file}")
    print(f"Output: {output_file}")
    print()
    
    # Run LLM
    if model in ['haiku', 'opus', 'sonnet']:
        cmd = ['claude', '--print', '--dangerously-skip-permissions', '--model', model]
        result = subprocess.run(cmd, input=prompt, capture_output=True, text=True)
        output = result.stdout + result.stderr
    else:
        cmd = ['opencode', 'run', '-m', model, '--', prompt]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        output = result.stdout + result.stderr
    
    # Clean ANSI codes
    output = re.sub(r'\x1b\[[0-9;]*m', '', output)
    
    with open(output_file, 'w') as f:
        f.write(output)
    
    print(f"Phase 1 complete!")
    print(f"Lines: {len(output.splitlines())}")
    print(f"Words: {len(output.split())}")
    print()
    
    # Check for artifacts
    print("=== Artifact Check ===")
    has_gherkin = '```gherkin' in output.lower() or 'feature:' in output.lower()
    has_yaml = '```yaml' in output.lower() or 'openapi:' in output.lower()
    has_sql = '```sql' in output.lower() or 'alter table' in output.lower()
    
    print(f"{'✓' if has_gherkin else '✗'} Gherkin")
    print(f"{'✓' if has_yaml else '✗'} OpenAPI")
    print(f"{'✓' if has_sql else '✗'} SQL")


def run_phase2(task: str, model: str, decomposition: str):
    """Implement using artifacts from phase 1."""
    print(f"=== Phase 2: Implementation ===")
    print(f"Task: {task}")
    print(f"Model: {model}")
    print(f"Decomposition: {decomposition}")
    print()
    
    model_safe = model.replace('/', '-').replace('@', '-')
    output_dir = os.path.join(RESULTS_DIR, task, "two-phase", model_safe)
    
    phase1_file = os.path.join(output_dir, "phase1_output.md")
    if not os.path.exists(phase1_file):
        print(f"Error: Phase 1 output not found: {phase1_file}")
        print("Run phase 1 first.")
        return
    
    prompt_file = os.path.join(output_dir, "phase2_prompt.md")
    output_file = os.path.join(output_dir, "phase2_output.md")
    
    task_file = os.path.join(TASKS_DIR, f"{task}.md")
    task_desc = extract_description(task_file)
    
    with open(phase1_file, 'r') as f:
        artifacts = f.read()
    
    decomp_file = os.path.join(HARNESS_DIR, "prompts", "decomposition", f"{decomposition}.md")
    if os.path.exists(decomp_file):
        with open(decomp_file, 'r') as f:
            decomp_strategy = f.read()
    else:
        decomp_strategy = "Stack: DB → Model → API → Tests"
    
    prompt = f"""You are a software engineer. Implement using the pre-designed artifacts.

## Task
{task_desc}

## Pre-designed Artifacts

{artifacts}

## Decomposition Strategy

{decomp_strategy}

## Implementation

For each step in the decomposition, output the code changes:

### Step N: [Name]

File: path/to/file.ts
```typescript
[actual code]
```

Now implement step by step:
"""
    
    with open(prompt_file, 'w') as f:
        f.write(prompt)
    
    print(f"Prompt: {prompt_file}")
    print(f"Output: {output_file}")
    print()
    
    # Run LLM
    if model in ['haiku', 'opus', 'sonnet']:
        cmd = ['claude', '--print', '--dangerously-skip-permissions', '--model', model]
        result = subprocess.run(cmd, input=prompt, capture_output=True, text=True)
        output = result.stdout + result.stderr
    else:
        cmd = ['opencode', 'run', '-m', model, '--', prompt]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        output = result.stdout + result.stderr
    
    # Clean ANSI codes
    output = re.sub(r'\x1b\[[0-9;]*m', '', output)
    
    with open(output_file, 'w') as f:
        f.write(output)
    
    print(f"Phase 2 complete!")
    print(f"Lines: {len(output.splitlines())}")
    print(f"Words: {len(output.split())}")


def main():
    parser = argparse.ArgumentParser(description="Two-phase experiment runner")
    parser.add_argument("--task", required=True, help="Task ID")
    parser.add_argument("--phase", required=True, choices=["1", "2", "both"], help="Phase to run")
    parser.add_argument("--model", default="haiku", help="Model to use")
    parser.add_argument("--decomposition", default="stack", help="Decomposition strategy")
    
    args = parser.parse_args()
    
    if args.phase in ["1", "both"]:
        run_phase1(args.task, args.model)
    
    if args.phase in ["2", "both"]:
        run_phase2(args.task, args.model, args.decomposition)


if __name__ == "__main__":
    main()
