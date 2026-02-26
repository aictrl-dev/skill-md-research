#!/usr/bin/env python3
"""
Score all 108 Gemini experiment results for figure generation.

Reads Gemini result JSONs from:
  research/kpi-target-experiment/domains/{chart,sql-query,dockerfile,terraform}/results/gemini-3.1-pro-preview_*.json

Unwraps the Gemini CLI wrapper to extract the LLM response, then applies
the domain-specific evaluators to compute per-run failure rates.

Outputs CSV at:
  research/kpi-target-experiment/gemini_scores.csv

Usage:
    python scripts/score_gemini_for_figures.py
"""

import csv
import json
import os
import sys
from pathlib import Path

# ── Project Root & Path Setup ─────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
EXPERIMENT_DIR = PROJECT_ROOT / "research" / "kpi-target-experiment"
OUTPUT_CSV = EXPERIMENT_DIR / "gemini_scores.csv"

# Add scripts/ to sys.path so evaluate.py is importable
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

# Add project root so domain evaluators can do their relative imports
sys.path.insert(0, str(PROJECT_ROOT))


# ── Gemini Response Unwrapper ─────────────────────────────────────────────────

def unwrap_gemini_response(raw_output: str) -> str:
    """Extract the LLM response from Gemini CLI wrapper output.

    The raw_output starts with "Loaded cached credentials.\n" followed by
    a JSON object with a "response" field. Sometimes Node.js warnings appear
    between the credentials line and the JSON.
    """
    lines = raw_output.split('\n')
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith('{'):
            json_str = '\n'.join(lines[i:])
            try:
                wrapper = json.loads(json_str)
                return wrapper.get('response', json_str)
            except json.JSONDecodeError:
                pass
    return raw_output  # fallback: return as-is


# ── Domain Evaluator Imports ──────────────────────────────────────────────────

# Dockerfile evaluator
sys.path.insert(0, str(PROJECT_ROOT / "domains" / "dockerfile"))
from evaluate_dockerfile import (
    extract_dockerfile,
    RULE_CHECKS as DOCKERFILE_RULE_CHECKS,
    EXCLUDED_RULES as DOCKERFILE_EXCLUDED_RULES,
    load_task as dockerfile_load_task,
)

# SQL evaluator
sys.path.insert(0, str(PROJECT_ROOT / "domains" / "sql-query"))
from evaluate_sql import (
    extract_dbt_models,
    PER_FILE_RULES as SQL_PER_FILE_RULES,
    CROSS_FILE_RULES as SQL_CROSS_FILE_RULES,
    load_task as sql_load_task,
    _strip_comments_and_strings,
    _strip_jinja,
)
import re as _re

# Terraform evaluator
sys.path.insert(0, str(PROJECT_ROOT / "domains" / "terraform"))
from evaluate_terraform import (
    extract_terraform,
    RULE_CHECKS as TF_RULE_CHECKS,
    EXCLUDED_RULES as TF_EXCLUDED_RULES,
    load_task as tf_load_task,
)

# Chart deep evaluator
from evaluate_deep import (
    extract_json as chart_extract_json,
    RULES as CHART_DEEP_RULES,
    TASK_META as CHART_TASK_META,
)


# ── Per-Domain Scoring Functions ──────────────────────────────────────────────

def score_dockerfile(response_text: str, task_id: str) -> dict:
    """Score a Dockerfile response. Returns dict with auto_score, scored_rules, failure_rate."""
    task = dockerfile_load_task(task_id)
    dockerfile, extract_error = extract_dockerfile(response_text)

    if dockerfile is None:
        scored_rules = len(DOCKERFILE_RULE_CHECKS) - len(DOCKERFILE_EXCLUDED_RULES)
        return {
            "extraction_ok": False,
            "auto_score": 0,
            "scored_rules": scored_rules,
            "failure_rate": 1.0,
        }

    auto_score = 0
    scored_rules = 0
    for name, check_fn in DOCKERFILE_RULE_CHECKS.items():
        if name in DOCKERFILE_EXCLUDED_RULES:
            continue
        passed, detail = check_fn(dockerfile, task)
        scored_rules += 1
        if passed:
            auto_score += 1

    failure_rate = 1.0 - (auto_score / scored_rules) if scored_rules > 0 else 1.0
    return {
        "extraction_ok": True,
        "auto_score": auto_score,
        "scored_rules": scored_rules,
        "failure_rate": round(failure_rate, 4),
    }


def score_sql(response_text: str, task_id: str) -> dict:
    """Score a SQL response. Returns dict with auto_score, scored_rules, failure_rate."""
    task = sql_load_task(task_id)
    models, extract_error = extract_dbt_models(response_text)

    if models is None:
        scored_rules = len(SQL_PER_FILE_RULES) + len(SQL_CROSS_FILE_RULES)
        return {
            "extraction_ok": False,
            "auto_score": 0.0,
            "scored_rules": scored_rules,
            "failure_rate": 1.0,
        }

    auto_score = 0.0
    scored_rules = 0

    # Per-file rules
    for rule_name, check_fn in SQL_PER_FILE_RULES:
        passes = 0
        applicable = 0

        for model_name, sql in models.items():
            # Skip non-applicable models (same logic as evaluate_sql.py)
            if rule_name == "rule_8_coalesce_unknown":
                if model_name.startswith("stg_"):
                    continue
            elif rule_name == "rule_9_row_number_dedup":
                if model_name.startswith("stg_") or model_name.startswith("fct_") or model_name.startswith("dim_"):
                    continue
            elif rule_name == "rule_7_left_join_only":
                cleaned = _strip_comments_and_strings(_strip_jinja(sql))
                if not _re.search(r'\bJOIN\b', cleaned, _re.IGNORECASE):
                    continue

            applicable += 1
            passed, detail = check_fn(sql, task)
            if passed:
                passes += 1

        if applicable == 0:
            if rule_name == "rule_7_left_join_only" and task.get("requires_left_join"):
                rate = 0.0
            elif rule_name == "rule_8_coalesce_unknown" and task.get("nullable_dimension_columns"):
                rate = 0.0
            elif rule_name == "rule_9_row_number_dedup" and task.get("requires_deduplication"):
                rate = 0.0
            else:
                rate = 1.0
        else:
            rate = passes / applicable

        scored_rules += 1
        auto_score += rate

    # Cross-file rules
    for rule_name, check_fn in SQL_CROSS_FILE_RULES:
        passed, detail = check_fn(models, task)
        scored_rules += 1
        if passed:
            auto_score += 1.0

    failure_rate = 1.0 - (auto_score / scored_rules) if scored_rules > 0 else 1.0
    return {
        "extraction_ok": True,
        "auto_score": round(auto_score, 2),
        "scored_rules": scored_rules,
        "failure_rate": round(failure_rate, 4),
    }


def score_terraform(response_text: str, task_id: str) -> dict:
    """Score a Terraform response. Returns dict with auto_score, scored_rules, failure_rate."""
    task = tf_load_task(task_id)
    tf_text, extract_error = extract_terraform(response_text)

    if tf_text is None:
        scored_rules = len(TF_RULE_CHECKS) - len(TF_EXCLUDED_RULES)
        return {
            "extraction_ok": False,
            "auto_score": 0,
            "scored_rules": scored_rules,
            "failure_rate": 1.0,
        }

    auto_score = 0
    scored_rules = 0
    for rule_name, check_fn in TF_RULE_CHECKS:
        if rule_name in TF_EXCLUDED_RULES:
            continue
        passed, detail = check_fn(tf_text, task)
        scored_rules += 1
        if passed:
            auto_score += 1

    failure_rate = 1.0 - (auto_score / scored_rules) if scored_rules > 0 else 1.0
    return {
        "extraction_ok": True,
        "auto_score": auto_score,
        "scored_rules": scored_rules,
        "failure_rate": round(failure_rate, 4),
    }


def score_chart(response_text: str, task_id: str) -> dict:
    """Score a chart response using the deep evaluator (15 rules).
    Returns dict with pass_count, fail_count, absent_count, deep_score, failure_rate."""
    meta = CHART_TASK_META.get(str(task_id), {})
    chart, json_error = chart_extract_json(response_text)

    if chart is None:
        return {
            "extraction_ok": False,
            "pass_count": 0,
            "fail_count": 0,
            "absent_count": 15,
            "deep_score": 0,
            "scored_rules": 15,
            "auto_score": 0,
            "failure_rate": 1.0,
        }

    pass_count = 0
    fail_count = 0
    absent_count = 0

    for rule_id, rule_name, check_fn in CHART_DEEP_RULES:
        verdict, detail = check_fn(chart, meta)
        if verdict == "pass":
            pass_count += 1
        elif verdict == "fail":
            fail_count += 1
        else:
            absent_count += 1

    # failure_rate = fail_count / (pass_count + fail_count) if any were scored
    total_scored = pass_count + fail_count
    failure_rate = fail_count / total_scored if total_scored > 0 else 1.0

    return {
        "extraction_ok": True,
        "pass_count": pass_count,
        "fail_count": fail_count,
        "absent_count": absent_count,
        "deep_score": pass_count,
        "scored_rules": 15,
        "auto_score": pass_count,
        "failure_rate": round(failure_rate, 4),
    }


# ── Main Processing ──────────────────────────────────────────────────────────

DOMAIN_SCORERS = {
    "chart": score_chart,
    "sql-query": score_sql,
    "dockerfile": score_dockerfile,
    "terraform": score_terraform,
}

CSV_FIELDS = [
    "run_id",
    "model",
    "condition",
    "domain",
    "task",
    "task_complexity",
    "rep",
    "duration_ms",
    "extraction_ok",
    "auto_score",
    "scored_rules",
    "failure_rate",
    # Chart-specific (empty for other domains)
    "pass_count",
    "fail_count",
    "absent_count",
    "deep_score",
]


def process_gemini_file(json_path: Path) -> dict:
    """Process a single Gemini result JSON file."""
    with open(json_path) as f:
        result = json.load(f)

    domain = result.get("domain", "")
    task_id = str(result.get("task", ""))

    # Unwrap Gemini response
    raw_output = result.get("raw_output", "")
    response_text = unwrap_gemini_response(raw_output)

    # Score using domain-specific evaluator
    scorer = DOMAIN_SCORERS.get(domain)
    if scorer is None:
        print(f"  WARNING: Unknown domain '{domain}' in {json_path.name}")
        scores = {
            "extraction_ok": False,
            "auto_score": 0,
            "scored_rules": 0,
            "failure_rate": 1.0,
        }
    else:
        scores = scorer(response_text, task_id)

    row = {
        "run_id": result.get("run_id", json_path.stem),
        "model": result.get("model", ""),
        "condition": result.get("condition", ""),
        "domain": domain,
        "task": task_id,
        "task_complexity": result.get("task_complexity", ""),
        "rep": result.get("rep", ""),
        "duration_ms": result.get("duration_ms", ""),
    }
    # Merge scores
    for field in CSV_FIELDS:
        if field not in row:
            row[field] = scores.get(field, "")

    return row


def main():
    domains = ["chart", "sql-query", "dockerfile", "terraform"]
    all_files = []

    for domain in domains:
        domain_dir = EXPERIMENT_DIR / "domains" / domain / "results"
        files = sorted(domain_dir.glob("gemini-3.1-pro-preview_*.json"))
        print(f"  {domain}: {len(files)} files")
        all_files.extend(files)

    print(f"\nTotal Gemini result files: {len(all_files)}")

    if not all_files:
        print("ERROR: No Gemini result files found.")
        sys.exit(1)

    # Process all files
    rows = []
    errors = 0
    for f in all_files:
        try:
            row = process_gemini_file(f)
            rows.append(row)
        except Exception as e:
            print(f"  ERROR processing {f.name}: {e}")
            errors += 1

    # Write CSV
    os.makedirs(EXPERIMENT_DIR, exist_ok=True)
    with open(OUTPUT_CSV, "w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nResults written to {OUTPUT_CSV}")
    print(f"  Total scored: {len(rows)}")
    print(f"  Errors: {errors}")

    # Extraction summary
    extracted = sum(1 for r in rows if r.get("extraction_ok"))
    print(f"  Extraction ok: {extracted}/{len(rows)}")

    # ── Summary: Failure Rate by Domain x Condition ──────────────────────────
    print(f"\n{'Failure Rate by Domain x Condition':}")
    print(f"{'Domain':<12s} {'Condition':<12s} {'Mean FR':>8s}  {'N':>3s}")
    print("-" * 40)

    for domain in domains:
        for condition in ["none", "markdown", "pseudocode"]:
            domain_rows = [r for r in rows if r["domain"] == domain and r["condition"] == condition]
            if domain_rows:
                frs = [r["failure_rate"] for r in domain_rows]
                mean_fr = sum(frs) / len(frs) * 100
                print(f"{domain:<12s} {condition:<12s} {mean_fr:>7.1f}%  {len(domain_rows):>3d}")

    # ── Aggregate: By Domain only ────────────────────────────────────────────
    print(f"\n{'Aggregate Failure Rate by Condition (all domains):':}")
    for condition in ["none", "markdown", "pseudocode"]:
        cond_rows = [r for r in rows if r["condition"] == condition]
        if cond_rows:
            frs = [r["failure_rate"] for r in cond_rows]
            mean_fr = sum(frs) / len(frs) * 100
            print(f"  {condition:<12s} {mean_fr:>7.1f}%  (n={len(cond_rows)})")


if __name__ == "__main__":
    main()
