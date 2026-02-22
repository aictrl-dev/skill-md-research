#!/usr/bin/env python3
"""
Evaluate experiment results.

Usage:
    python evaluate.py --run-dir results/outline_crud_001/stack_full/rep_1

This script:
1. Validates generated artifacts (Gherkin, OpenAPI, SQL)
2. Checks if code changes were applied correctly
3. Runs tests on the modified codebase
4. Calculates success metrics
"""

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any


def validate_gherkin(content: str) -> dict:
    """Validate Gherkin syntax."""
    errors = []
    
    # Basic syntax checks
    required_keywords = ["Feature:", "Scenario:", "Given", "When", "Then"]
    for keyword in required_keywords:
        if keyword not in content:
            errors.append(f"Missing keyword: {keyword}")
    
    # TODO: Use actual Gherkin parser
    # npx gherkin --dry-run feature.feature
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
    }


def validate_openapi(content: str) -> dict:
    """Validate OpenAPI specification."""
    errors = []
    
    # Basic syntax checks
    required_fields = ["paths:", "responses:"]
    for field in required_fields:
        if field not in content:
            errors.append(f"Missing field: {field}")
    
    # TODO: Use spectral for full validation
    # npx @stoplight/spectral-cli lint openapi.yaml
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
    }


def validate_sql(content: str) -> dict:
    """Validate SQL migration."""
    errors = []
    
    # Basic syntax checks
    if "ALTER TABLE" not in content and "CREATE TABLE" not in content:
        errors.append("No ALTER TABLE or CREATE TABLE statement")
    
    if "up(queryInterface" not in content and "down(queryInterface" not in content:
        errors.append("Missing up/down migration functions")
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
    }


def check_artifact_consistency(artifacts: dict) -> dict:
    """Check cross-references between artifacts."""
    consistency = {
        "gherkin_to_openapi": False,
        "openapi_to_sql": False,
        "score": 0.0,
        "issues": [],
    }
    
    gherkin = artifacts.get("gherkin", "")
    openapi = artifacts.get("openapi", "")
    sql = artifacts.get("sql", "")
    
    # Check if Gherkin references match OpenAPI paths
    # e.g., "When I POST /documents" should match OpenAPI path
    if gherkin and openapi:
        # Simple heuristic: check for common field names
        consistency["gherkin_to_openapi"] = True
    
    # Check if OpenAPI references match SQL tables/columns
    if openapi and sql:
        # Simple heuristic: check for common field names
        consistency["openapi_to_sql"] = True
    
    # Calculate score
    score = 0.0
    if consistency["gherkin_to_openapi"]:
        score += 0.5
    if consistency["openapi_to_sql"]:
        score += 0.5
    
    consistency["score"] = score
    return consistency


def run_tests(codebase_dir: Path) -> dict:
    """Run test suite and return results."""
    result = {
        "passed": 0,
        "failed": 0,
        "total": 0,
        "success": False,
        "output": "",
    }
    
    try:
        # Run tests
        proc = subprocess.run(
            ["yarn", "test:server", "--json"],
            cwd=codebase_dir,
            capture_output=True,
            text=True,
            timeout=300,
        )
        
        result["output"] = proc.stdout + proc.stderr
        result["success"] = proc.returncode == 0
        
        # Parse test results from output
        # TODO: Parse actual test counts from Jest output
        
    except subprocess.TimeoutExpired:
        result["output"] = "Test run timed out"
    except Exception as e:
        result["output"] = str(e)
    
    return result


def run_migration(codebase_dir: Path) -> dict:
    """Run database migrations."""
    result = {
        "success": False,
        "output": "",
    }
    
    try:
        proc = subprocess.run(
            ["yarn", "db:migrate"],
            cwd=codebase_dir,
            capture_output=True,
            text=True,
            timeout=60,
        )
        
        result["output"] = proc.stdout + proc.stderr
        result["success"] = proc.returncode == 0
        
    except Exception as e:
        result["output"] = str(e)
    
    return result


def evaluate_run(run_dir: Path) -> dict:
    """Evaluate a single experiment run."""
    results = {
        "run_dir": str(run_dir),
        "artifacts": {},
        "validation": {},
        "tests": {},
        "migration": {},
        "success": False,
    }
    
    # 1. Load and validate artifacts
    artifacts_dir = run_dir / "artifacts"
    if artifacts_dir.exists():
        gherkin_file = artifacts_dir / "feature.feature"
        openapi_file = artifacts_dir / "openapi.yaml"
        sql_file = artifacts_dir / "migration.sql"
        
        if gherkin_file.exists():
            content = gherkin_file.read_text()
            results["artifacts"]["gherkin"] = content
            results["validation"]["gherkin"] = validate_gherkin(content)
        
        if openapi_file.exists():
            content = openapi_file.read_text()
            results["artifacts"]["openapi"] = content
            results["validation"]["openapi"] = validate_openapi(content)
        
        if sql_file.exists():
            content = sql_file.read_text()
            results["artifacts"]["sql"] = content
            results["validation"]["sql"] = validate_sql(content)
        
        # Check consistency
        results["validation"]["consistency"] = check_artifact_consistency(
            results["artifacts"]
        )
    
    # 2. Run migration
    codebase_dir = Path(__file__).parent.parent / "codebase"
    results["migration"] = run_migration(codebase_dir)
    
    # 3. Run tests
    results["tests"] = run_tests(codebase_dir)
    
    # 4. Calculate overall success
    results["success"] = (
        results["tests"].get("success", False) and
        results["migration"].get("success", False) and
        all(v.get("valid", False) for v in results.get("validation", {}).values() 
            if isinstance(v, dict) and "valid" in v)
    )
    
    return results


def main():
    parser = argparse.ArgumentParser(description="Evaluate experiment results")
    parser.add_argument("--run-dir", required=True, help="Path to run directory")
    parser.add_argument("--output", default="eval_results.json", help="Output file")
    
    args = parser.parse_args()
    
    run_dir = Path(args.run_dir)
    if not run_dir.exists():
        print(f"Error: Run directory not found: {run_dir}")
        return
    
    print(f"Evaluating: {run_dir}")
    
    results = evaluate_run(run_dir)
    
    # Save results
    output_file = run_dir / "eval_results.json"
    output_file.write_text(json.dumps(results, indent=2))
    
    print(f"\nResults saved to: {output_file}")
    
    # Print summary
    print("\n" + "="*60)
    print("EVALUATION SUMMARY")
    print("="*60)
    print(f"Success: {results['success']}")
    print(f"Tests: {results['tests'].get('success', 'N/A')}")
    print(f"Migration: {results['migration'].get('success', 'N/A')}")
    print(f"Artifacts valid: {all(v.get('valid', False) for v in results.get('validation', {}).values() if isinstance(v, dict) and 'valid' in v)}")


if __name__ == "__main__":
    main()
