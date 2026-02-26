#!/usr/bin/env python3
"""
Run task decomposition experiment.

Usage:
    python run_experiment.py --task outline_crud_001 --decomposition stack --artifacts full --rep 1

Options:
    --task          Task ID (e.g., outline_crud_001)
    --decomposition Decomposition strategy (stack, domain, journey)
    --artifacts     Artifact format (nl, gherkin, gherkin_api, full)
    --rep           Repetition number (default: 1)
    --model         Model to use (default: claude-opus-4)
    --dry-run       Print prompt without running
"""

import argparse
import json
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent.parent
TASKS_DIR = BASE_DIR / "tasks"
PROMPTS_DIR = BASE_DIR / "prompts"
CODEBASE_DIR = BASE_DIR / "codebase"
RESULTS_DIR = BASE_DIR / "results"


def load_task_spec(task_id: str) -> dict:
    """Load task specification from markdown file."""
    task_file = TASKS_DIR / f"{task_id}.md"
    if not task_file.exists():
        raise FileNotFoundError(f"Task spec not found: {task_file}")
    
    # Parse markdown to extract structured data
    content = task_file.read_text()
    return {
        "id": task_id,
        "content": content,
        "type": "CRUD",  # Parse from content
    }


def load_decomposition_prompt(strategy: str) -> str:
    """Load decomposition strategy prompt."""
    prompt_file = PROMPTS_DIR / "decomposition" / f"{strategy}.md"
    if not prompt_file.exists():
        raise FileNotFoundError(f"Decomposition prompt not found: {prompt_file}")
    return prompt_file.read_text()


def load_artifact_prompt(format_name: str) -> str:
    """Load artifact format prompt."""
    prompt_file = PROMPTS_DIR / "artifacts" / f"{format_name}.md"
    if not prompt_file.exists():
        raise FileNotFoundError(f"Artifact prompt not found: {prompt_file}")
    return prompt_file.read_text()


def build_prompt(task: dict, decomposition: str, artifacts: str) -> str:
    """Build the full prompt for the LLM."""
    
    decomp_prompt = load_decomposition_prompt(decomposition)
    artifact_prompt = load_artifact_prompt(artifacts)
    
    # Combine prompts
    full_prompt = f"""
# Task Decomposition Experiment

## Your Role
You are an expert software engineer working on the Outline codebase.

## Task
{task['content']}

## Decomposition Strategy
{decomp_prompt}

## Artifact Format
{artifact_prompt}

## Instructions
1. Decompose the task according to the specified strategy
2. Generate artifacts in the specified format
3. Implement the code changes
4. Ensure all tests pass

## Output Format
Output your work in the following structure:

### Step 1: [Step Name]
**Artifact:**
```[format]
[artifact content]
```

**Implementation:**
```[language]
[code]
```

[Repeat for each step]

### Final Verification
- [ ] Migration runs
- [ ] Tests pass
- [ ] API works
"""
    return full_prompt


def run_llm(prompt: str, model: str) -> str:
    """Run LLM with the given prompt."""
    # TODO: Integrate with actual LLM API
    # For now, return placeholder
    return f"[LLM output for model {model}]\n\n{prompt[:500]}..."


def save_results(task_id: str, decomposition: str, artifacts: str, rep: int, 
                 prompt: str, output: str, metrics: dict):
    """Save experiment results."""
    
    run_dir = RESULTS_DIR / task_id / f"{decomposition}_{artifacts}" / f"rep_{rep}"
    run_dir.mkdir(parents=True, exist_ok=True)
    
    (run_dir / "prompt.md").write_text(prompt)
    (run_dir / "output.md").write_text(output)
    (run_dir / "metrics.json").write_text(json.dumps(metrics, indent=2))
    
    print(f"Results saved to: {run_dir}")


def main():
    parser = argparse.ArgumentParser(description="Run task decomposition experiment")
    parser.add_argument("--task", required=True, help="Task ID")
    parser.add_argument("--decomposition", choices=["stack", "domain", "journey"], 
                        required=True, help="Decomposition strategy")
    parser.add_argument("--artifacts", choices=["nl", "gherkin", "gherkin_api", "full"],
                        required=True, help="Artifact format")
    parser.add_argument("--rep", type=int, default=1, help="Repetition number")
    parser.add_argument("--model", default="claude-opus-4", help="Model to use")
    parser.add_argument("--dry-run", action="store_true", help="Print prompt without running")
    
    args = parser.parse_args()
    
    # Load task spec
    task = load_task_spec(args.task)
    print(f"Loaded task: {task['id']}")
    
    # Build prompt
    prompt = build_prompt(task, args.decomposition, args.artifacts)
    
    if args.dry_run:
        print("\n" + "="*80)
        print("PROMPT (dry run)")
        print("="*80)
        print(prompt)
        return
    
    # Run LLM
    print(f"Running with model: {args.model}")
    output = run_llm(prompt, args.model)
    
    # Save results
    metrics = {
        "task_id": args.task,
        "decomposition": args.decomposition,
        "artifacts": args.artifacts,
        "rep": args.rep,
        "model": args.model,
        "timestamp": datetime.now().isoformat(),
        "prompt_tokens": len(prompt.split()),
        "output_tokens": len(output.split()),
    }
    
    save_results(args.task, args.decomposition, args.artifacts, args.rep,
                 prompt, output, metrics)
    
    print("\nExperiment complete!")


if __name__ == "__main__":
    main()
