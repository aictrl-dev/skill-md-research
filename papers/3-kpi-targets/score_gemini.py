#!/usr/bin/env python3
"""
Score all Gemini 3.1 Pro experiment results across 4 domains and compare
with existing baselines (haiku, opus, glm-5).

The Gemini CLI wrapper produces raw_output that starts with
"Loaded cached credentials.\n" followed by a JSON object:
  { session_id, response, stats: { models: { ... } } }

We extract the 'response' field and feed it to each domain's evaluator.
"""

import csv
import json
import re
import sys
import glob
from pathlib import Path
from collections import defaultdict

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
EXPERIMENT_ROOT = Path(__file__).resolve().parent

# Add project root to path for imports
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

# Import chart evaluator
from evaluate import extract_json as chart_extract_json
from evaluate_deep import RULES as CHART_RULES, TASK_META

# Import SQL evaluator
sys.path.insert(0, str(PROJECT_ROOT / "domains" / "sql-query"))
from evaluate_sql import (
    extract_dbt_models, PER_FILE_RULES as SQL_PER_FILE_RULES,
    CROSS_FILE_RULES as SQL_CROSS_FILE_RULES, load_task as sql_load_task,
    _strip_comments_and_strings, _strip_jinja
)

# Import Dockerfile evaluator
sys.path.insert(0, str(PROJECT_ROOT / "domains" / "dockerfile"))
from evaluate_dockerfile import (
    extract_dockerfile, RULE_CHECKS as DOCKER_RULE_CHECKS,
    EXCLUDED_RULES as DOCKER_EXCLUDED_RULES,
    load_task as docker_load_task, validate_structure as docker_validate_structure,
    OUTCOME_CHECKS as DOCKER_OUTCOME_CHECKS,
)

# Import Terraform evaluator
sys.path.insert(0, str(PROJECT_ROOT / "domains" / "terraform"))
from evaluate_terraform import (
    extract_terraform, RULE_CHECKS as TF_RULE_CHECKS,
    EXCLUDED_RULES as TF_EXCLUDED_RULES,
    load_task as tf_load_task, validate_structure as tf_validate_structure,
    OUTCOME_CHECKS as TF_OUTCOME_CHECKS,
)


# ── Gemini raw_output parser ─────────────────────────────────────────────────

def parse_gemini_raw_output(raw_output: str) -> tuple[str, dict]:
    """Parse Gemini CLI wrapper output.

    Returns (response_text, token_stats).
    """
    if not raw_output:
        return "", {}

    # Find the first { to get the JSON part
    idx = raw_output.find("{")
    if idx < 0:
        return raw_output, {}

    json_str = raw_output[idx:]
    try:
        obj = json.loads(json_str)
    except json.JSONDecodeError:
        return raw_output, {}

    response = obj.get("response", "")
    stats = obj.get("stats", {})
    models = stats.get("models", {})

    token_info = {}
    for model_name, model_stats in models.items():
        tokens = model_stats.get("tokens", {})
        token_info = {
            "input_tokens": tokens.get("input", 0),
            "output_tokens": tokens.get("candidates", 0),
            "thought_tokens": tokens.get("thoughts", 0),
        }
        break  # first model only

    return response, token_info


# ── Chart domain scorer ──────────────────────────────────────────────────────

def score_chart(response_text: str, task_id: str) -> dict:
    """Score a chart response using all 15 deep rules."""
    meta = TASK_META.get(str(task_id), {})

    # extract_json expects text with markdown fences
    chart, json_error = chart_extract_json(response_text)

    result = {"json_valid": chart is not None, "json_error": json_error or ""}

    if chart is None:
        result["deep_score"] = 0
        result["pass_count"] = 0
        result["fail_count"] = 0
        result["absent_count"] = 15
        result["rule_details"] = {}
        return result

    pass_count = 0
    fail_count = 0
    absent_count = 0
    rule_details = {}

    for rule_id, rule_name, check_fn in CHART_RULES:
        verdict, detail = check_fn(chart, meta)
        rule_details[rule_id] = (verdict, detail)
        if verdict == "pass":
            pass_count += 1
        elif verdict == "fail":
            fail_count += 1
        else:
            absent_count += 1

    result["deep_score"] = pass_count
    result["pass_count"] = pass_count
    result["fail_count"] = fail_count
    result["absent_count"] = absent_count
    result["rule_details"] = rule_details
    return result


# ── SQL domain scorer ────────────────────────────────────────────────────────

def score_sql(response_text: str, task_id: str) -> dict:
    """Score a SQL response using all per-file and cross-file rules."""
    task = sql_load_task(str(task_id))
    models, extract_error = extract_dbt_models(response_text)

    result = {
        "extraction_ok": models is not None,
        "extraction_error": extract_error or "",
        "model_count": len(models) if models else 0,
    }

    if models is None:
        result["auto_score"] = 0.0
        result["rule_details"] = {}
        return result

    auto_score = 0.0
    rule_details = {}

    for rule_name, check_fn in SQL_PER_FILE_RULES:
        passes = 0
        applicable = 0

        for model_name, sql in models.items():
            if rule_name == "rule_8_coalesce_unknown":
                if model_name.startswith("stg_"):
                    continue
            elif rule_name == "rule_9_row_number_dedup":
                if model_name.startswith("stg_") or model_name.startswith("fct_") or model_name.startswith("dim_"):
                    continue
            elif rule_name == "rule_7_left_join_only":
                cleaned = _strip_comments_and_strings(_strip_jinja(sql))
                if not re.search(r'\bJOIN\b', cleaned, re.IGNORECASE):
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

        rule_details[rule_name] = rate
        auto_score += rate

    for rule_name, check_fn in SQL_CROSS_FILE_RULES:
        passed, detail = check_fn(models, task)
        rule_details[rule_name] = 1.0 if passed else 0.0
        if passed:
            auto_score += 1.0

    result["auto_score"] = round(auto_score, 2)
    result["rule_details"] = rule_details
    return result


# ── Dockerfile domain scorer ─────────────────────────────────────────────────

def score_dockerfile(response_text: str, task_id: str) -> dict:
    """Score a Dockerfile response."""
    task = docker_load_task(str(task_id))
    dockerfile, extract_error = extract_dockerfile(response_text)

    result = {
        "extraction_ok": dockerfile is not None,
        "extraction_error": extract_error or "",
    }

    if dockerfile is None:
        result["auto_score"] = 0
        result["outcome_score"] = 0
        result["rule_details"] = {}
        return result

    auto_score = 0
    rule_details = {}

    for name, check_fn in DOCKER_RULE_CHECKS.items():
        passed, detail = check_fn(dockerfile, task)
        rule_details[name] = (passed, detail)
        if name not in DOCKER_EXCLUDED_RULES:
            if passed:
                auto_score += 1

    result["auto_score"] = auto_score
    result["rule_details"] = rule_details

    # Outcome checks
    outcome_score = 0
    for outcome_name, check_fn in DOCKER_OUTCOME_CHECKS:
        passed, detail = check_fn(dockerfile, task)
        if passed:
            outcome_score += 1
    result["outcome_score"] = outcome_score

    return result


# ── Terraform domain scorer ──────────────────────────────────────────────────

def score_terraform(response_text: str, task_id: str) -> dict:
    """Score a Terraform response."""
    task = tf_load_task(str(task_id))
    tf_text, extract_error = extract_terraform(response_text)

    result = {
        "extraction_ok": tf_text is not None,
        "extraction_error": extract_error or "",
    }

    if tf_text is None:
        result["auto_score"] = 0
        result["outcome_score"] = 0
        result["rule_details"] = {}
        return result

    auto_score = 0
    rule_details = {}

    for rule_name, check_fn in TF_RULE_CHECKS:
        passed, detail = check_fn(tf_text, task)
        rule_details[rule_name] = (passed, detail)
        if rule_name not in TF_EXCLUDED_RULES:
            if passed:
                auto_score += 1

    result["auto_score"] = auto_score
    result["rule_details"] = rule_details

    # Outcome checks
    outcome_score = 0
    for outcome_name, check_fn in TF_OUTCOME_CHECKS:
        passed, detail = check_fn(tf_text, task)
        if passed:
            outcome_score += 1
    result["outcome_score"] = outcome_score

    return result


# ── Main scoring loop ────────────────────────────────────────────────────────

def score_all_gemini_results():
    """Score all Gemini 3.1 Pro results across all 4 domains."""
    domains = ["chart", "sql-query", "dockerfile", "terraform"]
    all_results = {}  # domain -> list of scored dicts

    for domain in domains:
        pattern = str(EXPERIMENT_ROOT / "domains" / domain / "results" / "gemini-3.1-pro-preview_*.json")
        files = sorted(glob.glob(pattern))
        print(f"\n{'='*60}")
        print(f"DOMAIN: {domain.upper()} ({len(files)} files)")
        print(f"{'='*60}")

        results = []
        for filepath in files:
            with open(filepath) as f:
                data = json.load(f)

            raw_output = data.get("raw_output", "")
            response_text, token_info = parse_gemini_raw_output(raw_output)

            run_info = {
                "run_id": data.get("run_id", ""),
                "model": data.get("model", ""),
                "condition": data.get("condition", ""),
                "task": str(data.get("task", "")),
                "rep": data.get("rep", ""),
                "duration_ms": data.get("duration_ms", ""),
                **token_info,
            }

            if domain == "chart":
                scores = score_chart(response_text, run_info["task"])
                run_info["score"] = scores["deep_score"]
                run_info["score_type"] = "deep_score"
                run_info["max_score"] = 15
                run_info["details"] = scores
            elif domain == "sql-query":
                scores = score_sql(response_text, run_info["task"])
                run_info["score"] = scores["auto_score"]
                run_info["score_type"] = "auto_score"
                run_info["max_score"] = 12
                run_info["details"] = scores
            elif domain == "dockerfile":
                scores = score_dockerfile(response_text, run_info["task"])
                run_info["score"] = scores["auto_score"]
                run_info["score_type"] = "auto_score"
                run_info["max_score"] = 13
                run_info["details"] = scores
            elif domain == "terraform":
                scores = score_terraform(response_text, run_info["task"])
                run_info["score"] = scores["auto_score"]
                run_info["score_type"] = "auto_score"
                run_info["max_score"] = 13
                run_info["details"] = scores

            results.append(run_info)

        all_results[domain] = results

        # Print individual scores
        print(f"\n  Individual runs:")
        for r in sorted(results, key=lambda x: (x["condition"], x["task"], x["rep"])):
            print(f"    {r['condition']:>12s} task{r['task']} rep{r['rep']}: {r['score']:>5} / {r['max_score']}"
                  f"  (tokens: in={r.get('input_tokens', '?')}, out={r.get('output_tokens', '?')}, think={r.get('thought_tokens', '?')})")

        # Summary by condition
        print(f"\n  Summary by condition:")
        conditions_order = ["none", "markdown", "pseudocode"]
        for cond in conditions_order:
            cond_results = [r for r in results if r["condition"] == cond]
            if cond_results:
                scores = [r["score"] for r in cond_results]
                mean = sum(scores) / len(scores)
                max_s = r["max_score"]
                print(f"    {cond:>12s}: mean={mean:.2f}/{max_s} ({mean/max_s*100:.1f}%), n={len(scores)}, "
                      f"scores={[r['score'] for r in cond_results]}")

        # Summary by task
        print(f"\n  Summary by task:")
        for task in ["1", "2", "3"]:
            task_results = [r for r in results if r["task"] == task]
            if task_results:
                for cond in conditions_order:
                    cond_task = [r for r in task_results if r["condition"] == cond]
                    if cond_task:
                        scores = [r["score"] for r in cond_task]
                        mean = sum(scores) / len(scores)
                        max_s = cond_task[0]["max_score"]
                        print(f"    task{task} {cond:>12s}: mean={mean:.2f}/{max_s}")

    return all_results


# ── Load baselines ───────────────────────────────────────────────────────────

def load_baselines():
    """Load baseline scores from existing CSV files."""
    baselines = {}

    # Chart: deep_score from scores_deep.csv
    chart_csv = PROJECT_ROOT / "domains" / "chart" / "results-v2" / "scores_deep.csv"
    if chart_csv.exists():
        with open(chart_csv) as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        baselines["chart"] = [
            {"model": r["model"], "condition": r["condition"],
             "task": r["task"], "score": int(r["deep_score"]),
             "max_score": 15}
            for r in rows
        ]

    # SQL: auto_score from scores.csv
    sql_csv = PROJECT_ROOT / "domains" / "sql-query" / "results" / "scores.csv"
    if sql_csv.exists():
        with open(sql_csv) as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        # Map ablation conditions to standard names for comparison
        cond_map = {
            "ablation-none": "none",
            "ablation-full": "markdown",
            "ablation-kpi-only": "pseudocode",
            "ablation-simple-context": "simple-context",
        }
        baselines["sql-query"] = [
            {"model": r["model"],
             "condition": cond_map.get(r["condition"], r["condition"]),
             "task": r.get("task", ""),
             "score": float(r["auto_score"]),
             "max_score": 12}
            for r in rows
        ]

    # Dockerfile
    docker_csv = PROJECT_ROOT / "domains" / "dockerfile" / "results" / "scores.csv"
    if docker_csv.exists():
        with open(docker_csv) as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        baselines["dockerfile"] = [
            {"model": r["model"], "condition": r["condition"],
             "task": r.get("task", ""),
             "score": int(r["auto_score"]),
             "max_score": 13}
            for r in rows
        ]

    # Terraform
    tf_csv = PROJECT_ROOT / "domains" / "terraform" / "results" / "scores.csv"
    if tf_csv.exists():
        with open(tf_csv) as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        baselines["terraform"] = [
            {"model": r["model"], "condition": r["condition"],
             "task": r.get("task", ""),
             "score": int(r["auto_score"]),
             "max_score": 13}
            for r in rows
        ]

    return baselines


# ── Comparison report ────────────────────────────────────────────────────────

def print_comparison_report(gemini_results, baselines):
    """Print comprehensive comparison between Gemini and baselines."""
    print("\n\n")
    print("=" * 80)
    print("  COMPREHENSIVE COMPARISON REPORT: Gemini 3.1 Pro vs Baselines")
    print("=" * 80)

    # Models to include in baseline comparison
    baseline_models = {"haiku", "opus", "zai-coding-plan/glm-5"}
    # Short display names
    display_names = {
        "haiku": "Haiku",
        "opus": "Opus",
        "zai-coding-plan/glm-5": "GLM-5",
        "gemini-3.1-pro-preview": "Gemini 3.1 Pro",
    }
    conditions_order = ["none", "markdown", "pseudocode"]

    for domain in ["chart", "sql-query", "dockerfile", "terraform"]:
        print(f"\n{'─'*80}")
        score_label = "deep_score" if domain == "chart" else "auto_score"
        max_score = gemini_results[domain][0]["max_score"] if gemini_results[domain] else "?"
        print(f"  {domain.upper()} ({score_label}, max={max_score})")
        print(f"{'─'*80}")

        # Collect all model data: model -> condition -> [scores]
        model_data = defaultdict(lambda: defaultdict(list))

        # Add Gemini data
        for r in gemini_results.get(domain, []):
            model_data["gemini-3.1-pro-preview"][r["condition"]].append(r["score"])

        # Add baseline data (filter to relevant models)
        for r in baselines.get(domain, []):
            if r["model"] in baseline_models:
                model_data[r["model"]][r["condition"]].append(r["score"])

        # Print table header
        print(f"\n  {'Model':>25s}", end="")
        for cond in conditions_order:
            print(f"  {cond:>12s}", end="")
        print(f"  {'md-none':>10s}")  # delta column

        print(f"  {'─'*25}", end="")
        for cond in conditions_order:
            print(f"  {'─'*12}", end="")
        print(f"  {'─'*10}")

        # Sorted: Gemini first, then baselines alphabetically
        model_order = []
        if "gemini-3.1-pro-preview" in model_data:
            model_order.append("gemini-3.1-pro-preview")
        for m in sorted(model_data.keys()):
            if m != "gemini-3.1-pro-preview":
                model_order.append(m)

        for model in model_order:
            name = display_names.get(model, model)
            print(f"  {name:>25s}", end="")
            means = {}
            for cond in conditions_order:
                scores = model_data[model].get(cond, [])
                if scores:
                    mean = sum(scores) / len(scores)
                    means[cond] = mean
                    print(f"  {mean:>8.2f}/{max_score}", end="")
                else:
                    print(f"  {'--':>12s}", end="")

            # Delta: markdown - none
            if "markdown" in means and "none" in means:
                delta = means["markdown"] - means["none"]
                sign = "+" if delta >= 0 else ""
                print(f"  {sign}{delta:>7.2f}", end="")
            else:
                print(f"  {'--':>10s}", end="")
            print()

        # Per-task breakdown for Gemini
        print(f"\n  Gemini 3.1 Pro per-task breakdown:")
        for task in ["1", "2", "3"]:
            print(f"    Task {task}:", end="")
            for cond in conditions_order:
                task_scores = [r["score"] for r in gemini_results.get(domain, [])
                               if r["task"] == task and r["condition"] == cond]
                if task_scores:
                    mean = sum(task_scores) / len(task_scores)
                    print(f"  {cond}={mean:.2f}", end="")
            print()

    # ── Grand Summary ──────────────────────────────────────────────────────
    print(f"\n{'='*80}")
    print(f"  GRAND SUMMARY: Normalized scores (% of max)")
    print(f"{'='*80}")

    print(f"\n  {'Model':>25s}", end="")
    for domain in ["chart", "sql-query", "dockerfile", "terraform"]:
        print(f"  {domain:>12s}", end="")
    print(f"  {'OVERALL':>10s}")

    print(f"  {'─'*25}", end="")
    for _ in range(4):
        print(f"  {'─'*12}", end="")
    print(f"  {'─'*10}")

    all_models = set()
    for domain in ["chart", "sql-query", "dockerfile", "terraform"]:
        for r in gemini_results.get(domain, []):
            all_models.add(r["model"])
        for r in baselines.get(domain, []):
            if r["model"] in baseline_models:
                all_models.add(r["model"])

    # For each condition
    for cond in conditions_order:
        print(f"\n  Condition: {cond}")
        model_order = []
        if "gemini-3.1-pro-preview" in all_models:
            model_order.append("gemini-3.1-pro-preview")
        for m in sorted(all_models):
            if m != "gemini-3.1-pro-preview":
                model_order.append(m)

        for model in model_order:
            name = display_names.get(model, model)
            print(f"  {name:>25s}", end="")
            domain_pcts = []
            for domain in ["chart", "sql-query", "dockerfile", "terraform"]:
                max_s = {"chart": 15, "sql-query": 12, "dockerfile": 13, "terraform": 13}[domain]
                # Collect scores for this model/condition/domain
                scores = []
                if model == "gemini-3.1-pro-preview":
                    scores = [r["score"] for r in gemini_results.get(domain, [])
                              if r["condition"] == cond]
                else:
                    scores = [r["score"] for r in baselines.get(domain, [])
                              if r["model"] == model and r["condition"] == cond]

                if scores:
                    mean = sum(scores) / len(scores)
                    pct = mean / max_s * 100
                    domain_pcts.append(pct)
                    print(f"  {pct:>10.1f}%", end="")
                else:
                    print(f"  {'--':>12s}", end="")

            if domain_pcts:
                overall = sum(domain_pcts) / len(domain_pcts)
                print(f"  {overall:>8.1f}%", end="")
            else:
                print(f"  {'--':>10s}", end="")
            print()

    # Token usage summary for Gemini
    print(f"\n{'='*80}")
    print(f"  GEMINI 3.1 PRO TOKEN USAGE")
    print(f"{'='*80}")

    for domain in ["chart", "sql-query", "dockerfile", "terraform"]:
        results = gemini_results.get(domain, [])
        if not results:
            continue
        input_tokens = [r.get("input_tokens", 0) for r in results if r.get("input_tokens")]
        output_tokens = [r.get("output_tokens", 0) for r in results if r.get("output_tokens")]
        thought_tokens = [r.get("thought_tokens", 0) for r in results if r.get("thought_tokens")]

        if input_tokens:
            print(f"\n  {domain.upper()}:")
            print(f"    Input tokens:   mean={sum(input_tokens)/len(input_tokens):.0f}")
            print(f"    Output tokens:  mean={sum(output_tokens)/len(output_tokens):.0f}")
            print(f"    Thought tokens: mean={sum(thought_tokens)/len(thought_tokens):.0f}")

            # By condition
            for cond in conditions_order:
                cond_results = [r for r in results if r["condition"] == cond]
                if cond_results:
                    inp = [r.get("input_tokens", 0) for r in cond_results]
                    out = [r.get("output_tokens", 0) for r in cond_results]
                    think = [r.get("thought_tokens", 0) for r in cond_results]
                    print(f"    {cond:>12s}: in={sum(inp)/len(inp):.0f}, out={sum(out)/len(out):.0f}, think={sum(think)/len(think):.0f}")


if __name__ == "__main__":
    gemini_results = score_all_gemini_results()
    baselines = load_baselines()
    print_comparison_report(gemini_results, baselines)
