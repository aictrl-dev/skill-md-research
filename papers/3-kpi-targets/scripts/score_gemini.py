#!/usr/bin/env python3
"""
Comprehensive Gemini 3.1 Pro scoring and paper statistics.

Scores all 108 Gemini result JSONs across 4 domains, then computes:
  - RQ1: Skill efficacy (Gemini-only and combined 5-model)
  - RQ2: Format effect (markdown vs pseudocode)
  - RQ3: Cross-family generalization
  - RQ5: Reliability (HDI, P(FR<10%), variance)
  - Combined pooled statistics for the updated paper (737 runs)
"""

import csv
import json
import re
import sys
import glob
import warnings
from pathlib import Path
from collections import defaultdict

import numpy as np
from scipy import stats

# ── Project paths ────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
EXPERIMENT_ROOT = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

# ── Import evaluators ────────────────────────────────────────────────────────

# Chart evaluator (deep rules)
from evaluate import extract_json as chart_extract_json
from evaluate_deep import RULES as CHART_RULES, TASK_META

# SQL evaluator
sys.path.insert(0, str(PROJECT_ROOT / "domains" / "sql-query"))
from evaluate_sql import (
    extract_dbt_models, PER_FILE_RULES as SQL_PER_FILE_RULES,
    CROSS_FILE_RULES as SQL_CROSS_FILE_RULES, load_task as sql_load_task,
    _strip_comments_and_strings, _strip_jinja,
)

# Dockerfile evaluator
sys.path.insert(0, str(PROJECT_ROOT / "domains" / "dockerfile"))
from evaluate_dockerfile import (
    extract_dockerfile, RULE_CHECKS as DOCKER_RULE_CHECKS,
    EXCLUDED_RULES as DOCKER_EXCLUDED_RULES,
    load_task as docker_load_task,
)

# Terraform evaluator
sys.path.insert(0, str(PROJECT_ROOT / "domains" / "terraform"))
from evaluate_terraform import (
    extract_terraform, RULE_CHECKS as TF_RULE_CHECKS,
    EXCLUDED_RULES as TF_EXCLUDED_RULES,
    load_task as tf_load_task,
)


# ── Gemini output parser ────────────────────────────────────────────────────

def parse_gemini_raw_output(raw_output: str) -> str:
    """Extract the model response text from Gemini CLI wrapper output.

    The raw_output starts with 'Loaded cached credentials.\n' followed
    by a JSON object containing { session_id, response, stats }.
    Returns the response text.
    """
    if not raw_output:
        return ""

    # Find the first { to get the JSON part
    idx = raw_output.find("{")
    if idx < 0:
        return raw_output

    json_str = raw_output[idx:]
    try:
        obj = json.loads(json_str)
    except json.JSONDecodeError:
        return raw_output

    return obj.get("response", "")


# ── Domain scorers ──────────────────────────────────────────────────────────

def score_chart(response_text: str, task_id: str) -> dict:
    """Score a chart response using all 15 deep rules.

    Returns dict with auto_score (=deep_score) and scored_rules (=15).
    """
    meta = TASK_META.get(str(task_id), {})
    chart, json_error = chart_extract_json(response_text)

    if chart is None:
        return {"auto_score": 0, "scored_rules": 15}

    pass_count = 0
    for rule_id, rule_name, check_fn in CHART_RULES:
        verdict, detail = check_fn(chart, meta)
        if verdict == "pass":
            pass_count += 1

    return {"auto_score": pass_count, "scored_rules": 15}


def score_sql(response_text: str, task_id: str) -> dict:
    """Score a SQL response. Returns dict with auto_score, scored_rules."""
    task = sql_load_task(str(task_id))
    models, extract_error = extract_dbt_models(response_text)

    n_rules = len(SQL_PER_FILE_RULES) + len(SQL_CROSS_FILE_RULES)
    if models is None:
        return {"auto_score": 0.0, "scored_rules": 0}

    auto_score = 0.0
    scored_rules = 0

    for rule_name, check_fn in SQL_PER_FILE_RULES:
        passes = 0
        applicable = 0

        for model_name, sql in models.items():
            if rule_name == "rule_8_coalesce_unknown" and model_name.startswith("stg_"):
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

        auto_score += rate
        scored_rules += 1

    for rule_name, check_fn in SQL_CROSS_FILE_RULES:
        passed, detail = check_fn(models, task)
        scored_rules += 1
        if passed:
            auto_score += 1.0

    return {"auto_score": round(auto_score, 4), "scored_rules": scored_rules}


def score_dockerfile(response_text: str, task_id: str) -> dict:
    """Score a Dockerfile response."""
    task = docker_load_task(str(task_id))
    dockerfile, extract_error = extract_dockerfile(response_text)

    if dockerfile is None:
        return {"auto_score": 0, "scored_rules": 0}

    auto_score = 0
    scored_rules = 0
    for name, check_fn in DOCKER_RULE_CHECKS.items():
        passed, detail = check_fn(dockerfile, task)
        if name not in DOCKER_EXCLUDED_RULES:
            scored_rules += 1
            if passed:
                auto_score += 1

    return {"auto_score": auto_score, "scored_rules": scored_rules}


def score_terraform(response_text: str, task_id: str) -> dict:
    """Score a Terraform response."""
    task = tf_load_task(str(task_id))
    tf_text, extract_error = extract_terraform(response_text)

    if tf_text is None:
        return {"auto_score": 0, "scored_rules": 0}

    auto_score = 0
    scored_rules = 0
    for rule_name, check_fn in TF_RULE_CHECKS:
        passed, detail = check_fn(tf_text, task)
        if rule_name not in TF_EXCLUDED_RULES:
            scored_rules += 1
            if passed:
                auto_score += 1

    return {"auto_score": auto_score, "scored_rules": scored_rules}


DOMAIN_SCORERS = {
    "chart": score_chart,
    "sql-query": score_sql,
    "dockerfile": score_dockerfile,
    "terraform": score_terraform,
}


# ── Statistical helpers ─────────────────────────────────────────────────────

def cliffs_delta(x, y):
    """Cliff's delta. Positive means x > y."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    n = len(x) * len(y)
    if n == 0:
        return 0.0, "undefined"
    more = less = 0
    for xi in x:
        for yi in y:
            if xi > yi:
                more += 1
            elif xi < yi:
                less += 1
    delta = (more - less) / n
    abs_d = abs(delta)
    if abs_d < 0.147:
        mag = "negl."
    elif abs_d < 0.33:
        mag = "small"
    elif abs_d < 0.474:
        mag = "medium"
    else:
        mag = "large"
    return delta, mag


def mwu(x, y, alternative="two-sided"):
    """Mann-Whitney U. Returns (U, p)."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if len(x) < 2 or len(y) < 2:
        return np.nan, np.nan
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        u, p = stats.mannwhitneyu(x, y, alternative=alternative)
    return u, p


def fmt_p(p):
    if np.isnan(p):
        return "N/A"
    return "< 0.001" if p < 0.001 else f"{p:.3f}"


def beta_hdi(successes, trials, width=0.95, n_samples=50000):
    """Compute HDI width and P(FR < threshold) using Beta-Binomial posterior.

    Parameters:
        successes: number of 'passing' runs (auto_score / scored_rules >= threshold)
        trials: total runs
        width: credible interval width
        n_samples: MCMC samples

    Returns (hdi_width, p_below_10pct) where p_below_10pct = P(FR < 0.10).
    """
    # Beta posterior for failure rate
    # If we observe 'failures' out of 'trials', posterior for FR ~ Beta(failures+1, successes+1)
    failures = trials - successes
    alpha = failures + 1
    beta_param = successes + 1

    samples = np.random.beta(alpha, beta_param, n_samples)
    samples.sort()

    # HDI
    ci_start = int((1 - width) / 2 * n_samples)
    ci_end = int((1 + width) / 2 * n_samples)
    hdi_lo = samples[ci_start]
    hdi_hi = samples[ci_end]
    hdi_w = hdi_hi - hdi_lo

    # P(FR < 10%)
    p_below_10 = np.mean(samples < 0.10)

    return hdi_w, p_below_10


# ── Score all Gemini results ────────────────────────────────────────────────

def score_gemini_results():
    """Score all 108 Gemini result JSONs. Returns list of dicts."""
    domains = ["chart", "sql-query", "dockerfile", "terraform"]
    all_rows = []

    for domain in domains:
        pattern = str(EXPERIMENT_ROOT / "domains" / domain / "results" /
                      "gemini-3.1-pro-preview_*.json")
        files = sorted(glob.glob(pattern))
        scorer = DOMAIN_SCORERS[domain]

        for filepath in files:
            with open(filepath) as f:
                data = json.load(f)

            raw_output = data.get("raw_output", "")
            response_text = parse_gemini_raw_output(raw_output)

            task_id = str(data.get("task", ""))
            scores = scorer(response_text, task_id)

            # Compute failure rate
            if scores["scored_rules"] == 0:
                fr = 1.0
            else:
                fr = 1.0 - scores["auto_score"] / scores["scored_rules"]

            row = {
                "model": "gemini-3.1-pro-preview",
                "condition": data.get("condition", ""),
                "task": task_id,
                "rep": data.get("rep", ""),
                "domain": domain,
                "auto_score": scores["auto_score"],
                "scored_rules": scores["scored_rules"],
                "failure_rate": fr,
            }
            all_rows.append(row)

        n = len([r for r in all_rows if r["domain"] == domain])
        print(f"  Scored {n} Gemini runs for {domain}")

    return all_rows


# ── Load baseline data ──────────────────────────────────────────────────────

def load_baseline_data():
    """Load existing scores from the 4-domain CSVs.

    Returns list of dicts with model, condition, domain, auto_score,
    scored_rules, failure_rate.
    """
    rows = []

    # Chart deep scores (15 rules)
    chart_csv = PROJECT_ROOT / "domains" / "chart" / "results" / "scores_deep.csv"
    if chart_csv.exists():
        with open(chart_csv) as f:
            for r in csv.DictReader(f):
                if r["condition"] not in ("none", "markdown", "pseudocode"):
                    continue
                scored = 15
                auto = int(r["deep_score"])
                fr = 1.0 - auto / scored
                model = r["model"].replace("zai-coding-plan/", "")
                rows.append({
                    "model": model,
                    "condition": r["condition"],
                    "task": r["task"],
                    "domain": "chart",
                    "auto_score": auto,
                    "scored_rules": scored,
                    "failure_rate": fr,
                })

    # Dockerfile
    docker_csv = PROJECT_ROOT / "domains" / "dockerfile" / "results" / "scores.csv"
    if docker_csv.exists():
        with open(docker_csv) as f:
            for r in csv.DictReader(f):
                if r["condition"] not in ("none", "markdown", "pseudocode"):
                    continue
                scored = int(r.get("scored_rules", 0))
                auto = float(r.get("auto_score", 0))
                fr = 1.0 if scored == 0 else 1.0 - auto / scored
                model = r["model"].replace("zai-coding-plan/", "")
                rows.append({
                    "model": model,
                    "condition": r["condition"],
                    "task": r.get("task", ""),
                    "domain": "dockerfile",
                    "auto_score": auto,
                    "scored_rules": scored,
                    "failure_rate": fr,
                })

    # Terraform
    tf_csv = PROJECT_ROOT / "domains" / "terraform" / "results" / "scores.csv"
    if tf_csv.exists():
        with open(tf_csv) as f:
            for r in csv.DictReader(f):
                if r["condition"] not in ("none", "markdown", "pseudocode"):
                    continue
                scored = int(r.get("scored_rules", 0))
                auto = float(r.get("auto_score", 0))
                fr = 1.0 if scored == 0 else 1.0 - auto / scored
                model = r["model"].replace("zai-coding-plan/", "")
                rows.append({
                    "model": model,
                    "condition": r["condition"],
                    "task": r.get("task", ""),
                    "domain": "terraform",
                    "auto_score": auto,
                    "scored_rules": scored,
                    "failure_rate": fr,
                })

    # SQL: the ablation CSV maps to our conditions
    sql_csv = PROJECT_ROOT / "domains" / "sql-query" / "results" / "scores.csv"
    cond_map = {
        "ablation-none": "none",
        "ablation-full": "markdown",
        "ablation-kpi-only": "pseudocode",
    }
    if sql_csv.exists():
        with open(sql_csv) as f:
            for r in csv.DictReader(f):
                mapped_cond = cond_map.get(r["condition"])
                if mapped_cond is None:
                    continue
                scored = int(r.get("scored_rules", 0))
                auto = float(r.get("auto_score", 0))
                fr = 1.0 if scored == 0 else 1.0 - auto / scored
                model = r["model"].replace("zai-coding-plan/", "")
                rows.append({
                    "model": model,
                    "condition": mapped_cond,
                    "task": r.get("task", ""),
                    "domain": "sql-query",
                    "auto_score": auto,
                    "scored_rules": scored,
                    "failure_rate": fr,
                })

    return rows


# ── Print statistics ────────────────────────────────────────────────────────

def print_gemini_stats(gemini_rows):
    """Print Gemini-only statistics for the paper."""
    g = gemini_rows  # shorthand

    print("\n" + "=" * 80)
    print("  GEMINI 3.1 PRO - SCORED RESULTS")
    print("=" * 80)

    # Summary by domain x condition
    domains = ["chart", "sql-query", "dockerfile", "terraform"]
    conditions = ["none", "markdown", "pseudocode"]

    print(f"\n  {'Domain':<15s}", end="")
    for c in conditions:
        print(f"  {c:>12s}", end="")
    print(f"  {'N':>5s}")
    print("  " + "-" * 65)

    for d in domains:
        print(f"  {d:<15s}", end="")
        for c in conditions:
            rows = [r for r in g if r["domain"] == d and r["condition"] == c]
            if rows:
                mean_fr = np.mean([r["failure_rate"] for r in rows])
                mean_score = np.mean([r["auto_score"] for r in rows])
                max_s = rows[0]["scored_rules"]
                print(f"  {mean_score:>5.1f}/{max_s:<2d}({mean_fr*100:4.1f}%)", end="")
            else:
                print(f"  {'--':>12s}", end="")
        n = len([r for r in g if r["domain"] == d])
        print(f"  {n:>5d}")

    print(f"\n  Total Gemini runs: {len(g)}")

    # ── RQ1: Skill Efficacy (Gemini-only) ────────────────────────────────
    print("\n" + "=" * 80)
    print("  RQ1: SKILL EFFICACY (Gemini 3.1 Pro only)")
    print("=" * 80)

    none_fr = np.array([r["failure_rate"] for r in g if r["condition"] == "none"])
    skill_fr = np.array([r["failure_rate"] for r in g
                         if r["condition"] in ("markdown", "pseudocode")])

    print(f"\n  Pooled failure rates:")
    print(f"    No skill:     N={len(none_fr):>3d}, Mean FR = {none_fr.mean()*100:.1f}%")
    print(f"    Skill (both): N={len(skill_fr):>3d}, Mean FR = {skill_fr.mean()*100:.1f}%")

    delta_rq1, mag_rq1 = cliffs_delta(none_fr, skill_fr)
    u_rq1, p_rq1 = mwu(none_fr, skill_fr, alternative="greater")
    reduction = none_fr.mean() / skill_fr.mean() if skill_fr.mean() > 0 else float("inf")
    print(f"    Cliff's delta = {delta_rq1:+.3f} ({mag_rq1})")
    print(f"    Mann-Whitney p = {fmt_p(p_rq1)}")
    print(f"    Reduction factor: {reduction:.2f}x")

    # Per-domain failure rates for Gemini
    print(f"\n  Per-domain failure rates (Gemini):")
    print(f"    {'Domain':<15s}  {'none':>8s}  {'markdown':>8s}  {'pseudo':>8s}")
    print("    " + "-" * 50)
    for d in domains:
        print(f"    {d:<15s}", end="")
        for c in conditions:
            rows = [r for r in g if r["domain"] == d and r["condition"] == c]
            if rows:
                fr = np.mean([r["failure_rate"] for r in rows])
                print(f"  {fr*100:>7.1f}%", end="")
            else:
                print(f"  {'--':>8s}", end="")
        print()

    # ── RQ2: Format Effect (Gemini-only) ──────────────────────────────────
    print("\n" + "=" * 80)
    print("  RQ2: FORMAT EFFECT (Gemini 3.1 Pro only)")
    print("=" * 80)

    md_fr = np.array([r["failure_rate"] for r in g if r["condition"] == "markdown"])
    pc_fr = np.array([r["failure_rate"] for r in g if r["condition"] == "pseudocode"])

    print(f"\n  Pooled:")
    print(f"    Markdown:    N={len(md_fr):>3d}, Mean FR = {md_fr.mean()*100:.1f}%")
    print(f"    Pseudocode:  N={len(pc_fr):>3d}, Mean FR = {pc_fr.mean()*100:.1f}%")

    delta_rq2, mag_rq2 = cliffs_delta(md_fr, pc_fr)
    u_rq2, p_rq2 = mwu(md_fr, pc_fr, alternative="greater")
    print(f"    Cliff's delta = {delta_rq2:+.3f} ({mag_rq2})")
    print(f"    Mann-Whitney p = {fmt_p(p_rq2)}")

    print(f"\n  Per-domain:")
    print(f"    {'Domain':<15s}  {'MD FR':>8s}  {'PC FR':>8s}  {'delta':>8s}  {'mag':>8s}  {'p':>8s}")
    print("    " + "-" * 60)
    for d in domains:
        md_d = np.array([r["failure_rate"] for r in g
                         if r["domain"] == d and r["condition"] == "markdown"])
        pc_d = np.array([r["failure_rate"] for r in g
                         if r["domain"] == d and r["condition"] == "pseudocode"])
        if len(md_d) == 0 or len(pc_d) == 0:
            continue
        delta_d, mag_d = cliffs_delta(md_d, pc_d)
        _, p_d = mwu(md_d, pc_d, alternative="greater")
        print(f"    {d:<15s}  {md_d.mean()*100:>7.1f}%  {pc_d.mean()*100:>7.1f}%  "
              f"{delta_d:>+7.3f}  {mag_d:>8s}  {fmt_p(p_d):>8s}")

    # ── RQ3: Cross-family (Gemini per-domain delta) ──────────────────────
    print("\n" + "=" * 80)
    print("  RQ3: CROSS-FAMILY (Gemini per-domain Cliff's delta)")
    print("=" * 80)

    print(f"    {'Domain':<15s}  {'delta':>8s}  {'mag':>8s}  {'p':>8s}")
    print("    " + "-" * 45)
    for d in domains:
        md_d = np.array([r["failure_rate"] for r in g
                         if r["domain"] == d and r["condition"] == "markdown"])
        pc_d = np.array([r["failure_rate"] for r in g
                         if r["domain"] == d and r["condition"] == "pseudocode"])
        if len(md_d) == 0 or len(pc_d) == 0:
            continue
        delta_d, mag_d = cliffs_delta(md_d, pc_d)
        _, p_d = mwu(md_d, pc_d, alternative="two-sided")
        print(f"    {d:<15s}  {delta_d:>+7.3f}  {mag_d:>8s}  {fmt_p(p_d):>8s}")

    # ── RQ5: Reliability (Gemini HDI, P(FR<10%), variance) ───────────────
    print("\n" + "=" * 80)
    print("  RQ5: RELIABILITY (Gemini 3.1 Pro)")
    print("=" * 80)

    np.random.seed(42)

    for cond in ["markdown", "pseudocode"]:
        cond_rows = [r for r in g if r["condition"] == cond]
        fr_vals = [r["failure_rate"] for r in cond_rows]
        n_total = len(cond_rows)
        n_passing = sum(1 for r in cond_rows if r["failure_rate"] < 0.10)

        hdi_w, p_below_10 = beta_hdi(n_passing, n_total)
        var_fr = np.var(fr_vals)

        print(f"\n  {cond.upper()}:")
        print(f"    N = {n_total}")
        print(f"    Mean FR = {np.mean(fr_vals)*100:.1f}%")
        print(f"    Var(FR) = {var_fr:.4f}")
        print(f"    HDI width (95%) = {hdi_w:.3f}")
        print(f"    P(FR < 10%) = {p_below_10:.3f}")

    return {
        "none_fr": none_fr,
        "skill_fr": skill_fr,
        "md_fr": md_fr,
        "pc_fr": pc_fr,
    }


def print_combined_stats(gemini_rows, baseline_rows):
    """Print combined statistics (baseline + Gemini)."""
    all_rows = baseline_rows + [{
        **r,
        "model": "gemini-3.1-pro-preview",
    } for r in gemini_rows]

    print("\n\n" + "=" * 80)
    print("  COMBINED STATISTICS (Baseline + Gemini)")
    print("=" * 80)

    # Overview
    n_baseline = len(baseline_rows)
    n_gemini = len(gemini_rows)
    n_total = len(all_rows)
    print(f"\n  Baseline runs: {n_baseline}")
    print(f"  Gemini runs:   {n_gemini}")
    print(f"  Total:         {n_total}")

    # Models
    models = sorted(set(r["model"] for r in all_rows))
    print(f"  Models: {models}")

    # Per-model counts
    for m in models:
        n = sum(1 for r in all_rows if r["model"] == m)
        print(f"    {m}: {n} runs")

    # Conditions
    conditions = ["none", "markdown", "pseudocode"]
    for c in conditions:
        n = sum(1 for r in all_rows if r["condition"] == c)
        print(f"    {c}: {n} runs")

    domains = sorted(set(r["domain"] for r in all_rows))
    for d in domains:
        n = sum(1 for r in all_rows if r["domain"] == d)
        print(f"    {d}: {n} runs")

    # ── Pooled failure rates for all 5+ models ──────────────────────────
    print("\n" + "-" * 80)
    print("  COMBINED POOLED FAILURE RATES")
    print("-" * 80)

    none_fr = np.array([r["failure_rate"] for r in all_rows if r["condition"] == "none"])
    skill_fr = np.array([r["failure_rate"] for r in all_rows
                         if r["condition"] in ("markdown", "pseudocode")])
    md_fr = np.array([r["failure_rate"] for r in all_rows if r["condition"] == "markdown"])
    pc_fr = np.array([r["failure_rate"] for r in all_rows if r["condition"] == "pseudocode"])

    print(f"\n  No skill:     N={len(none_fr):>4d}, Mean FR = {none_fr.mean()*100:.1f}%")
    print(f"  Skill (both): N={len(skill_fr):>4d}, Mean FR = {skill_fr.mean()*100:.1f}%")
    print(f"  Markdown:     N={len(md_fr):>4d}, Mean FR = {md_fr.mean()*100:.1f}%")
    print(f"  Pseudocode:   N={len(pc_fr):>4d}, Mean FR = {pc_fr.mean()*100:.1f}%")

    # RQ1: skill vs no-skill
    delta_rq1, mag_rq1 = cliffs_delta(none_fr, skill_fr)
    u_rq1, p_rq1 = mwu(none_fr, skill_fr, alternative="greater")
    reduction = none_fr.mean() / skill_fr.mean() if skill_fr.mean() > 0 else float("inf")
    print(f"\n  RQ1 (skill vs no-skill):")
    print(f"    Cliff's delta = {delta_rq1:+.3f} ({mag_rq1})")
    print(f"    Mann-Whitney p = {fmt_p(p_rq1)}")
    print(f"    Reduction factor: {reduction:.2f}x")

    # RQ2: pseudocode vs markdown
    delta_rq2, mag_rq2 = cliffs_delta(md_fr, pc_fr)
    u_rq2, p_rq2 = mwu(md_fr, pc_fr, alternative="greater")
    print(f"\n  RQ2 (markdown vs pseudocode):")
    print(f"    Cliff's delta = {delta_rq2:+.3f} ({mag_rq2})")
    print(f"    Mann-Whitney p = {fmt_p(p_rq2)}")

    # ── Per-domain pooled ────────────────────────────────────────────────
    print("\n" + "-" * 80)
    print("  COMBINED PER-DOMAIN FAILURE RATES")
    print("-" * 80)

    print(f"\n  {'Domain':<15s}  {'none':>8s}  {'markdown':>8s}  {'pseudo':>8s}  {'N':>5s}")
    print("  " + "-" * 55)
    for d in domains:
        print(f"  {d:<15s}", end="")
        for c in conditions:
            d_rows = [r for r in all_rows if r["domain"] == d and r["condition"] == c]
            if d_rows:
                fr = np.mean([r["failure_rate"] for r in d_rows])
                print(f"  {fr*100:>7.1f}%", end="")
            else:
                print(f"  {'--':>8s}", end="")
        n = len([r for r in all_rows if r["domain"] == d])
        print(f"  {n:>5d}")

    # ── Per-model pooled ─────────────────────────────────────────────────
    print("\n" + "-" * 80)
    print("  COMBINED PER-MODEL FAILURE RATES")
    print("-" * 80)

    display = {
        "haiku": "Haiku 4.5",
        "opus": "Opus 4.6",
        "glm-4.7": "GLM-4.7",
        "glm-4.7-flash": "GLM-4.7-flash",
        "glm-5": "GLM-5",
        "gemini-3.1-pro-preview": "Gemini 3.1 Pro",
    }

    print(f"\n  {'Model':<20s}  {'none':>8s}  {'markdown':>8s}  {'pseudo':>8s}")
    print("  " + "-" * 55)
    for m in models:
        name = display.get(m, m)
        print(f"  {name:<20s}", end="")
        for c in conditions:
            m_rows = [r for r in all_rows if r["model"] == m and r["condition"] == c]
            if m_rows:
                fr = np.mean([r["failure_rate"] for r in m_rows])
                print(f"  {fr*100:>7.1f}%", end="")
            else:
                print(f"  {'--':>8s}", end="")
        print()

    # ── Per-domain Cliff's delta (combined) ──────────────────────────────
    print("\n" + "-" * 80)
    print("  COMBINED PER-DOMAIN CLIFF'S DELTA")
    print("-" * 80)

    print(f"\n  Skill vs no-skill:")
    print(f"    {'Domain':<15s}  {'delta':>8s}  {'mag':>8s}  {'p':>8s}")
    print("    " + "-" * 45)
    for d in domains:
        none_d = np.array([r["failure_rate"] for r in all_rows
                           if r["domain"] == d and r["condition"] == "none"])
        skill_d = np.array([r["failure_rate"] for r in all_rows
                            if r["domain"] == d and r["condition"] in ("markdown", "pseudocode")])
        if len(none_d) == 0 or len(skill_d) == 0:
            continue
        delta_d, mag_d = cliffs_delta(none_d, skill_d)
        _, p_d = mwu(none_d, skill_d, alternative="greater")
        print(f"    {d:<15s}  {delta_d:>+7.3f}  {mag_d:>8s}  {fmt_p(p_d):>8s}")

    print(f"\n  Pseudocode vs markdown:")
    print(f"    {'Domain':<15s}  {'delta':>8s}  {'mag':>8s}  {'p':>8s}")
    print("    " + "-" * 45)
    for d in domains:
        md_d = np.array([r["failure_rate"] for r in all_rows
                         if r["domain"] == d and r["condition"] == "markdown"])
        pc_d = np.array([r["failure_rate"] for r in all_rows
                         if r["domain"] == d and r["condition"] == "pseudocode"])
        if len(md_d) == 0 or len(pc_d) == 0:
            continue
        delta_d, mag_d = cliffs_delta(md_d, pc_d)
        _, p_d = mwu(md_d, pc_d, alternative="greater")
        print(f"    {d:<15s}  {delta_d:>+7.3f}  {mag_d:>8s}  {fmt_p(p_d):>8s}")

    # ── Per-family per-domain Cliff's delta ──────────────────────────────
    print("\n" + "-" * 80)
    print("  COMBINED PER-FAMILY PER-DOMAIN CLIFF'S DELTA (pseudocode vs markdown)")
    print("-" * 80)

    families = {
        "Claude": ["haiku", "opus"],
        "GLM": ["glm-4.7", "glm-4.7-flash", "glm-5"],
        "Gemini": ["gemini-3.1-pro-preview"],
    }

    for fam_name, fam_models in families.items():
        print(f"\n  {fam_name}:")
        print(f"    {'Domain':<15s}  {'delta':>8s}  {'mag':>8s}  {'p':>8s}")
        print("    " + "-" * 45)
        for d in domains:
            md_d = np.array([r["failure_rate"] for r in all_rows
                             if r["domain"] == d and r["model"] in fam_models
                             and r["condition"] == "markdown"])
            pc_d = np.array([r["failure_rate"] for r in all_rows
                             if r["domain"] == d and r["model"] in fam_models
                             and r["condition"] == "pseudocode"])
            if len(md_d) == 0 or len(pc_d) == 0:
                print(f"    {d:<15s}  NO DATA")
                continue
            delta_d, mag_d = cliffs_delta(md_d, pc_d)
            _, p_d = mwu(md_d, pc_d, alternative="two-sided")
            print(f"    {d:<15s}  {delta_d:>+7.3f}  {mag_d:>8s}  {fmt_p(p_d):>8s}")

    # ── Summary for paper abstract ──────────────────────────────────────
    print("\n" + "=" * 80)
    print("  PAPER-READY NUMBERS")
    print("=" * 80)

    print(f"\n  Total scored runs: {n_total}")
    print(f"  Models: {len(models)} (from 3 families)")
    print(f"  Domains: {len(domains)}")
    print()
    print(f"  RQ1: Skill files reduce FR by {reduction:.1f}x "
          f"(from {none_fr.mean()*100:.1f}% to {skill_fr.mean()*100:.1f}%)")
    print(f"    delta = {delta_rq1:+.3f} ({mag_rq1}), p = {fmt_p(p_rq1)}")
    print()
    print(f"  RQ2: Pseudocode FR = {pc_fr.mean()*100:.1f}% vs "
          f"Markdown FR = {md_fr.mean()*100:.1f}%")
    print(f"    delta = {delta_rq2:+.3f} ({mag_rq2}), p = {fmt_p(p_rq2)}")

    # Relative reduction
    rel_reduction = (1 - pc_fr.mean() / md_fr.mean()) * 100
    print(f"    Relative reduction: {rel_reduction:.0f}%")
    print()

    # Skill presence effect vs format effect
    skill_gap = none_fr.mean() - skill_fr.mean()
    format_gap = md_fr.mean() - pc_fr.mean()
    if format_gap > 0:
        gap_ratio = skill_gap / format_gap
        print(f"  Gap ratio (skill presence / format): {gap_ratio:.0f}x")
    print(f"    Skill presence gap: {skill_gap*100:.1f}pp")
    print(f"    Format gap: {format_gap*100:.1f}pp")

    # Gemini-specific frontier numbers
    gem_md = np.mean([r["failure_rate"] for r in gemini_rows
                      if r["condition"] == "markdown"])
    gem_pc = np.mean([r["failure_rate"] for r in gemini_rows
                      if r["condition"] == "pseudocode"])
    print(f"\n  Gemini 3.1 Pro: MD FR={gem_md*100:.1f}%, PC FR={gem_pc*100:.1f}%")

    # Frontier model comparison
    for m in ["opus", "glm-5", "gemini-3.1-pro-preview"]:
        m_md = [r["failure_rate"] for r in all_rows
                if r["model"] == m and r["condition"] == "markdown"]
        m_pc = [r["failure_rate"] for r in all_rows
                if r["model"] == m and r["condition"] == "pseudocode"]
        if m_md and m_pc:
            name = display.get(m, m)
            print(f"    {name:<20s}: MD={np.mean(m_md)*100:.1f}%, PC={np.mean(m_pc)*100:.1f}%")


# ── Main ────────────────────────────────────────────────────────────────────

def main():
    print("=" * 80)
    print("  SCORING GEMINI 3.1 PRO EXPERIMENT RESULTS")
    print("=" * 80)

    # 1. Score all 108 Gemini results
    print("\n[1/3] Scoring Gemini results...")
    gemini_rows = score_gemini_results()
    print(f"\n  Total Gemini runs scored: {len(gemini_rows)}")

    # 2. Print Gemini-only statistics
    print("\n[2/3] Computing Gemini-only statistics...")
    gemini_stats = print_gemini_stats(gemini_rows)

    # 3. Load baselines and compute combined statistics
    print("\n[3/3] Loading baselines and computing combined statistics...")
    baseline_rows = load_baseline_data()
    print(f"  Loaded {len(baseline_rows)} baseline rows")
    print_combined_stats(gemini_rows, baseline_rows)

    print("\n\nDone.")


if __name__ == "__main__":
    main()
