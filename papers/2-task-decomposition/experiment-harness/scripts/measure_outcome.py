#!/usr/bin/env python3
"""
Outcome Measurer: Apply generated code and verify compilation
"""

import os
import re
import subprocess
import json
from pathlib import Path

HARNESS_DIR = Path(__file__).parent.parent
CODEBASE_DIR = HARNESS_DIR / "codebase"
RESULTS_DIR = HARNESS_DIR / "results"


def extract_code_blocks(content: str) -> list[dict]:
    """Extract code blocks with their file paths from LLM output."""
    blocks = []
    
    # Pattern: **server/path/to/file.ts** or File: server/path/to/file.ts
    # followed by ```language ... ```
    
    lines = content.split('\n')
    current_file = None
    in_block = False
    block_content = []
    block_lang = None
    
    for i, line in enumerate(lines):
        # Detect file path markers
        file_match = re.match(r'\*\*([^*]+\.(ts|js|sql))\*\*', line)
        if not file_match:
            file_match = re.match(r'(?:File|file):\s*([^\s]+\.(ts|js|sql))', line)
        
        if file_match:
            current_file = file_match.group(1).strip()
            continue
        
        # Detect code block start
        if line.startswith('```'):
            if not in_block:
                in_block = True
                block_lang = line[3:].strip()
                block_content = []
            else:
                # End of block
                if current_file and block_content:
                    blocks.append({
                        'file': current_file,
                        'lang': block_lang,
                        'content': '\n'.join(block_content)
                    })
                in_block = False
                current_file = None
            continue
        
        if in_block:
            block_content.append(line)
    
    return blocks


def apply_code_block(block: dict, codebase_dir: Path) -> dict:
    """Apply a code block to the codebase."""
    file_path = codebase_dir / block['file']
    
    result = {
        'file': block['file'],
        'action': None,
        'success': False,
        'error': None
    }
    
    try:
        # Create parent directories
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write the file
        with open(file_path, 'w') as f:
            f.write(block['content'])
        
        result['action'] = 'created' if not file_path.exists() else 'overwritten'
        result['success'] = True
        
    except Exception as e:
        result['error'] = str(e)
    
    return result


def run_typecheck(codebase_dir: Path) -> dict:
    """Run TypeScript type check."""
    result = {
        'success': False,
        'errors': [],
        'output': ''
    }
    
    try:
        proc = subprocess.run(
            ['npx', 'tsc', '--noEmit'],
            cwd=codebase_dir,
            capture_output=True,
            text=True,
            timeout=120
        )
        
        result['output'] = proc.stdout + proc.stderr
        result['success'] = proc.returncode == 0
        
        if not result['success']:
            # Parse errors
            for line in result['output'].split('\n'):
                if 'error TS' in line:
                    result['errors'].append(line.strip())
                    
    except subprocess.TimeoutExpired:
        result['errors'] = ['Timeout']
    except Exception as e:
        result['errors'] = [str(e)]
    
    return result


def run_lint(codebase_dir: Path) -> dict:
    """Run linter."""
    result = {
        'success': False,
        'errors': [],
        'output': ''
    }
    
    try:
        proc = subprocess.run(
            ['yarn', 'lint'],
            cwd=codebase_dir,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        result['output'] = proc.stdout + proc.stderr
        result['success'] = proc.returncode == 0
        
    except Exception as e:
        result['errors'] = [str(e)]
    
    return result


def measure_outcome(experiment_dir: Path, codebase_dir: Path) -> dict:
    """Measure outcome for an experiment."""
    
    # Find output files
    output_files = list(experiment_dir.glob('*.md')) + list(experiment_dir.glob('output.md'))
    
    if not output_files:
        return {'error': 'No output files found'}
    
    # Read and extract code
    all_blocks = []
    for output_file in output_files:
        content = output_file.read_text()
        blocks = extract_code_blocks(content)
        all_blocks.extend(blocks)
    
    print(f"Found {len(all_blocks)} code blocks")
    
    # Apply each block
    apply_results = []
    for block in all_blocks:
        print(f"  Applying: {block['file']}")
        result = apply_code_block(block, codebase_dir)
        apply_results.append(result)
    
    # Run typecheck
    print("Running typecheck...")
    typecheck_result = run_typecheck(codebase_dir)
    
    # Run lint
    print("Running lint...")
    lint_result = run_lint(codebase_dir)
    
    return {
        'code_blocks_found': len(all_blocks),
        'files_applied': sum(1 for r in apply_results if r['success']),
        'apply_results': apply_results,
        'typecheck': typecheck_result,
        'lint': lint_result,
        'outcome': {
            'compiles': typecheck_result['success'],
            'passes_lint': lint_result['success'],
            'success': typecheck_result['success'] and lint_result['success']
        }
    }


def main():
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python measure_outcome.py <experiment_dir>")
        print("Example: python measure_outcome.py results/outline_workflow_001_approval/one-shot-glm-4.7")
        sys.exit(1)
    
    experiment_dir = Path(sys.argv[1])
    if not experiment_dir.is_absolute():
        experiment_dir = RESULTS_DIR / experiment_dir
    
    print(f"=== Measuring Outcome ===")
    print(f"Experiment: {experiment_dir}")
    print(f"Codebase: {CODEBASE_DIR}")
    print()
    
    result = measure_outcome(experiment_dir, CODEBASE_DIR)
    
    print()
    print("=== Results ===")
    print(f"Code blocks found: {result.get('code_blocks_found', 0)}")
    print(f"Files applied: {result.get('files_applied', 0)}")
    print(f"Typecheck: {'✓ PASS' if result.get('typecheck', {}).get('success') else '✗ FAIL'}")
    print(f"Lint: {'✓ PASS' if result.get('lint', {}).get('success') else '✗ FAIL'}")
    print()
    print(f"OUTCOME: {'✓ SUCCESS' if result.get('outcome', {}).get('success') else '✗ FAILURE'}")
    
    if result.get('typecheck', {}).get('errors'):
        print()
        print("TypeScript errors:")
        for err in result['typecheck']['errors'][:5]:
            print(f"  {err}")
    
    # Save results
    result_file = experiment_dir / 'outcome.json'
    with open(result_file, 'w') as f:
        json.dump(result, f, indent=2, default=str)
    print(f"\nFull results saved to: {result_file}")


if __name__ == "__main__":
    main()
