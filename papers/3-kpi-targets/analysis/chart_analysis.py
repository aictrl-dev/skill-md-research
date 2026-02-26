#!/usr/bin/env python3
"""Compute Chart domain summary statistics for the KPI Target experiment."""

import sys
import os
import json
import csv
from collections import defaultdict
from pathlib import Path

# Add scripts dir to path for evaluate modules
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from evaluate_deep import evaluate_run, RULES, TASK_META
from evaluate import extract_json, extract_token_usage, TOKEN_FIELDS

# ── 1. BASELINE: Load scored data from CSV ──
baseline_csv = REPO_ROOT / "domains" / "chart" / "results-v2" / "scores_deep.csv"
baseline_runs = []

with open(baseline_csv) as f:
    reader = csv.DictReader(f)
    for row in reader:
        if row["condition"] != "markdown":
            continue
        model_raw = row["model"]
        if model_raw == "haiku":
            model_label = "haiku"
        elif model_raw == "opus":
            model_label = "opus"
        elif model_raw == "zai-coding-plan/glm-5":
            model_label = "glm-5"
        else:
            continue  # skip glm-4.7-flash (broken)

        baseline_runs.append({
            "model": model_label,
            "task": row["task"],
            "rep": int(row["rep"]),
            "deep_score": int(row["deep_score"]),
            "output_tokens": int(row["output_tokens"]),
            "input_tokens": int(row["input_tokens"]),
        })

# Also load baseline rule-level data for per-rule comparison
baseline_rule_data_by_model = defaultdict(list)
with open(baseline_csv) as f:
    reader = csv.DictReader(f)
    for row in reader:
        if row["condition"] != "markdown":
            continue
        model_raw = row["model"]
        if model_raw == "haiku":
            model_label = "haiku"
        elif model_raw == "opus":
            model_label = "opus"
        elif model_raw == "zai-coding-plan/glm-5":
            model_label = "glm-5"
        else:
            continue
        baseline_rule_data_by_model[model_label].append(row)

# ── 2. TARGET: Score the raw JSON files ──
target_dir = REPO_ROOT / "research" / "kpi-target-experiment" / "domains" / "chart" / "results"
target_runs = []

for fname in sorted(os.listdir(target_dir)):
    if not fname.endswith(".json"):
        continue
    fpath = target_dir / fname
    with open(fpath) as f:
        data = json.load(f)

    if data.get("run_id") is None or data.get("raw_output") is None:
        continue

    model_raw = data.get("model", "")
    if "glm-4.7" in model_raw and "flash" not in model_raw:
        model_label = "glm-4.7"
    elif "glm-5" in model_raw:
        model_label = "glm-5"
    elif "haiku" in model_raw:
        model_label = "haiku"
    elif "opus" in model_raw:
        model_label = "opus"
    else:
        model_label = model_raw

    raw = data.get("raw_output", "")

    # Extract token usage
    token_info = extract_token_usage(raw)

    # Extract and score chart JSON
    chart, json_error = extract_json(raw)

    task_id = str(data.get("task", ""))
    meta = TASK_META.get(task_id, {})

    if chart is not None:
        pass_count = 0
        fail_count = 0
        absent_count = 0
        rule_results = {}
        for rule_id, rule_name, check_fn in RULES:
            verdict, detail = check_fn(chart, meta)
            rule_results[rule_id] = (verdict, detail)
            if verdict == "pass":
                pass_count += 1
            elif verdict == "fail":
                fail_count += 1
            else:
                absent_count += 1
        deep_score = pass_count
        json_valid = True
    else:
        deep_score = 0
        json_valid = False
        pass_count = 0
        fail_count = 0
        absent_count = 15
        rule_results = {}

    output_tokens = int(token_info.get("output_tokens", 0) or 0)
    input_tokens = int(token_info.get("input_tokens", 0) or 0)

    target_runs.append({
        "model": model_label,
        "task": task_id,
        "rep": data.get("rep", 0),
        "deep_score": deep_score,
        "output_tokens": output_tokens,
        "input_tokens": input_tokens,
        "json_valid": json_valid,
        "pass_count": pass_count,
        "fail_count": fail_count,
        "absent_count": absent_count,
        "rule_results": rule_results,
        "fname": fname,
    })

# ── 3. COMPUTE STATISTICS ──

print("=" * 80)
print("CHART DOMAIN - KPI TARGET EXPERIMENT RESULTS")
print("=" * 80)

# 3a. Data availability
print()
print("DATA AVAILABILITY")
print("-" * 40)

for label, runs in [("Baseline (markdown)", baseline_runs), ("Target (markdown+target)", target_runs)]:
    by_model = defaultdict(list)
    for r in runs:
        by_model[r["model"]].append(r)
    print(f"{label}:")
    for m in sorted(by_model.keys()):
        print(f"  {m}: {len(by_model[m])} runs")
    print()

# 3b. JSON extraction rate for target
print("TARGET JSON EXTRACTION RATE")
print("-" * 40)
for m_label in ["glm-4.7", "glm-5"]:
    m_runs = [r for r in target_runs if r["model"] == m_label]
    valid = sum(1 for r in m_runs if r["json_valid"])
    pct = 100 * valid / len(m_runs) if m_runs else 0
    print(f"{m_label}: {valid}/{len(m_runs)} ({pct:.0f}%)")
print()

# 3c. Per-model baseline vs target scores
baseline_by_model = defaultdict(list)
for r in baseline_runs:
    baseline_by_model[r["model"]].append(r)

target_by_model = defaultdict(list)
for r in target_runs:
    target_by_model[r["model"]].append(r)

print()
print("PER-MODEL SCORES: BASELINE (markdown) vs TARGET (markdown+target)")
print("=" * 100)

all_models = ["haiku", "opus", "glm-4.7", "glm-5"]
header = f"{'Model':<12} | {'Baseline Score':>16} | {'Target Score':>16} | {'Score Delta':>14} | {'Baseline Tok':>12} | {'Target Tok':>11} | {'Token Delta':>12}"
print(header)
print("-" * len(header))

for model in all_models:
    b_runs = baseline_by_model.get(model, [])
    t_runs = target_by_model.get(model, [])

    b_scores = [r["deep_score"] for r in b_runs]
    t_scores = [r["deep_score"] for r in t_runs]
    b_tokens = [r["output_tokens"] for r in b_runs]
    t_tokens = [r["output_tokens"] for r in t_runs]

    b_mean_s = sum(b_scores) / len(b_scores) if b_scores else 0
    t_mean_s = sum(t_scores) / len(t_scores) if t_scores else 0
    b_mean_t = sum(b_tokens) / len(b_tokens) if b_tokens else 0
    t_mean_t = sum(t_tokens) / len(t_tokens) if t_tokens else 0

    if b_scores and t_scores:
        delta_s = t_mean_s - b_mean_s
        pct_s = delta_s / b_mean_s * 100 if b_mean_s else 0
        delta_str = f"{delta_s:+.2f} ({pct_s:+.0f}%)"
    elif t_scores:
        delta_str = "no baseline"
    else:
        delta_str = "no target"

    if b_tokens and t_tokens:
        tok_pct = (t_mean_t - b_mean_t) / b_mean_t * 100 if b_mean_t else 0
        token_delta_str = f"{tok_pct:+.0f}%"
    elif t_tokens:
        token_delta_str = "no baseline"
    else:
        token_delta_str = "no target"

    b_score_str = f"{b_mean_s:.2f}/15 (n={len(b_runs)})" if b_runs else "N/A"
    t_score_str = f"{t_mean_s:.2f}/15 (n={len(t_runs)})" if t_runs else "N/A"
    b_tok_str = f"{b_mean_t:.0f}" if b_runs else "N/A"
    t_tok_str = f"{t_mean_t:.0f}" if t_runs else "N/A"

    print(f"{model:<12} | {b_score_str:>16} | {t_score_str:>16} | {delta_str:>14} | {b_tok_str:>12} | {t_tok_str:>11} | {token_delta_str:>12}")

# 3d. Per-task breakdown for glm-5
print()
print()
print("PER-TASK BREAKDOWN: glm-5 (both conditions available)")
print("-" * 70)
header2 = f"{'Task':<6} | {'Baseline':>12} | {'Target':>12} | {'Score Delta':>12} | {'Token Delta':>12}"
print(header2)
print("-" * len(header2))

for task in ["1", "2", "3"]:
    b = [r for r in baseline_runs if r["model"] == "glm-5" and r["task"] == task]
    t = [r for r in target_runs if r["model"] == "glm-5" and r["task"] == task]

    b_scores = [r["deep_score"] for r in b]
    t_scores = [r["deep_score"] for r in t]
    b_tokens = [r["output_tokens"] for r in b]
    t_tokens = [r["output_tokens"] for r in t]

    b_mean_s = sum(b_scores) / len(b_scores) if b_scores else 0
    t_mean_s = sum(t_scores) / len(t_scores) if t_scores else 0
    b_mean_t = sum(b_tokens) / len(b_tokens) if b_tokens else 0
    t_mean_t = sum(t_tokens) / len(t_tokens) if t_tokens else 0

    delta_s = t_mean_s - b_mean_s if b and t else float("nan")
    if b_mean_t and t:
        token_pct = (t_mean_t - b_mean_t) / b_mean_t * 100
        token_str = f"{token_pct:+.0f}%"
    else:
        token_str = "N/A"

    b_str = f"{b_mean_s:.2f} (n={len(b)})" if b else "N/A"
    t_str = f"{t_mean_s:.2f} (n={len(t)})" if t else "N/A"
    d_str = f"{delta_s:+.2f}" if b and t else "N/A"

    print(f"{task:<6} | {b_str:>12} | {t_str:>12} | {d_str:>12} | {token_str:>12}")

# 3e. Per-task for glm-4.7 (target only)
print()
print("PER-TASK: glm-4.7 (target only, no markdown baseline)")
print("-" * 50)
for task in ["1", "2", "3"]:
    t = [r for r in target_runs if r["model"] == "glm-4.7" and r["task"] == task]
    if t:
        t_scores = [r["deep_score"] for r in t]
        t_tokens = [r["output_tokens"] for r in t]
        t_mean_s = sum(t_scores) / len(t_scores)
        t_mean_t = sum(t_tokens) / len(t_tokens)
        print(f"  Task {task}: score={t_mean_s:.2f}/15 (n={len(t)}), tokens={t_mean_t:.0f}")

# 3f. Overall (glm-5)
print()
print()
print("OVERALL CHART DOMAIN STATISTICS")
print("=" * 60)

b_all = [r["deep_score"] for r in baseline_runs if r["model"] == "glm-5"]
t_all = [r["deep_score"] for r in target_runs if r["model"] == "glm-5"]
b_tok = [r["output_tokens"] for r in baseline_runs if r["model"] == "glm-5"]
t_tok = [r["output_tokens"] for r in target_runs if r["model"] == "glm-5"]

b_mean = sum(b_all) / len(b_all) if b_all else 0
t_mean = sum(t_all) / len(t_all) if t_all else 0
delta = t_mean - b_mean
pct = delta / b_mean * 100 if b_mean else 0

b_tok_mean = sum(b_tok) / len(b_tok) if b_tok else 0
t_tok_mean = sum(t_tok) / len(t_tok) if t_tok else 0
tok_delta = t_tok_mean - b_tok_mean
tok_pct = tok_delta / b_tok_mean * 100 if b_tok_mean else 0

print(f"glm-5 (only model with both conditions):")
print(f"  Baseline Mean Score: {b_mean:.2f}/15 (n={len(b_all)})")
print(f"  Target Mean Score:   {t_mean:.2f}/15 (n={len(t_all)})")
print(f"  Score Change:        {delta:+.2f} ({pct:+.1f}%)")
print()
print(f"  Baseline Mean Tokens: {b_tok_mean:.0f}")
print(f"  Target Mean Tokens:   {t_tok_mean:.0f}")
print(f"  Token Change:         {tok_delta:+.0f} ({tok_pct:+.1f}%)")

# 3g. Context: all baselines
print()
print()
print("ALL BASELINE SCORES (markdown condition, for context)")
print("-" * 60)
for model in ["haiku", "opus", "glm-5"]:
    runs = [r for r in baseline_runs if r["model"] == model]
    scores = [r["deep_score"] for r in runs]
    tokens = [r["output_tokens"] for r in runs]
    mean_s = sum(scores) / len(scores) if scores else 0
    mean_t = sum(tokens) / len(tokens) if tokens else 0
    print(f"  {model:<8}: mean = {mean_s:.2f}/15, tokens = {mean_t:.0f}, scores = {scores}")

# 3h. Per-rule comparison for glm-5
print()
print()
print("PER-RULE PASS RATES: glm-5 baseline vs target")
print("-" * 70)
print(f"{'Rule':<35} | {'Baseline':>10} | {'Target':>10} | {'Delta':>8}")
print("-" * 70)

glm5_baseline_rules = baseline_rule_data_by_model.get("glm-5", [])
glm5_target = [r for r in target_runs if r["model"] == "glm-5"]

for rule_id, rule_name, _ in RULES:
    b_pass = sum(1 for r in glm5_baseline_rules if r.get(f"{rule_id}_verdict") == "pass")
    b_total = len(glm5_baseline_rules)
    b_rate = b_pass / b_total * 100 if b_total else 0

    t_pass = sum(1 for r in glm5_target if r["rule_results"].get(rule_id, ("", ""))[0] == "pass")
    t_total = len(glm5_target)
    t_rate = t_pass / t_total * 100 if t_total else 0

    delta_r = t_rate - b_rate
    print(f"  {rule_id} {rule_name:<28} | {b_rate:>8.0f}% | {t_rate:>8.0f}% | {delta_r:>+6.0f}%")

# 3i. Detailed target scores
print()
print()
print("DETAILED TARGET SCORES (all scored runs)")
print("-" * 85)
for r in sorted(target_runs, key=lambda x: (x["model"], x["task"], x["rep"])):
    rules_str = ""
    for rule_id, _, _ in RULES:
        v = r["rule_results"].get(rule_id, ("?", ""))[0]
        if v == "pass":
            rules_str += "P"
        elif v == "fail":
            rules_str += "F"
        else:
            rules_str += "-"
    print(f"  {r['model']:<8} task{r['task']} rep{r['rep']}: score={r['deep_score']:>2}/15  tokens={r['output_tokens']:>5}  valid={r['json_valid']}  [{rules_str}]")

# 3j. glm-4.7 target summary stats
print()
print()
print("GLM-4.7 TARGET SUMMARY")
print("-" * 40)
glm47 = [r for r in target_runs if r["model"] == "glm-4.7"]
glm47_scores = [r["deep_score"] for r in glm47]
glm47_tokens = [r["output_tokens"] for r in glm47]
if glm47_scores:
    import statistics
    print(f"  N = {len(glm47)}")
    print(f"  Mean Score: {sum(glm47_scores)/len(glm47_scores):.2f}/15")
    print(f"  Median Score: {statistics.median(glm47_scores)}/15")
    print(f"  Min/Max: {min(glm47_scores)}/{max(glm47_scores)}")
    print(f"  Std Dev: {statistics.stdev(glm47_scores):.2f}")
    print(f"  Mean Tokens: {sum(glm47_tokens)/len(glm47_tokens):.0f}")
