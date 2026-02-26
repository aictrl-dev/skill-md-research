#!/usr/bin/env python3
"""
Compute ALL statistics needed for the paper update.

Loads baseline CSV data + Gemini JSON results, scores everything,
then outputs every statistic the paper needs.
"""

import csv
import json
import sys
import tempfile
import os
from pathlib import Path
from collections import defaultdict
import warnings

import numpy as np
from scipy import stats as sp_stats

# ── Paths ──────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent.parent.parent  # skill-md-research
BASELINE_CSVS = {
    "chart":      ROOT / "domains" / "chart" / "results" / "scores_deep.csv",
    "sql-query":  ROOT / "domains" / "sql-query" / "results" / "scores.csv",
    "dockerfile": ROOT / "domains" / "dockerfile" / "results" / "scores.csv",
    "terraform":  ROOT / "domains" / "terraform" / "results" / "scores.csv",
}
GEMINI_DIR = Path(__file__).resolve().parent.parent / "domains"

# Add project root to path for evaluator imports
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "domains" / "sql-query"))
sys.path.insert(0, str(ROOT / "domains" / "dockerfile"))
sys.path.insert(0, str(ROOT / "domains" / "terraform"))


# ── Model normalization ────────────────────────────────────────────────────────
MODEL_NORM = {
    "haiku": "Haiku 4.5",
    "opus": "Opus 4.6",
    "zai-coding-plan/glm-4.7": "GLM-4.7",
    "glm-4.7": "GLM-4.7",
    "zai-coding-plan/glm-5": "GLM-5",
    "glm-5": "GLM-5",
    "gemini-3.1-pro-preview": "Gemini 3.1 Pro",
}
FAMILY_MAP = {
    "Haiku 4.5": "Claude (Anthropic)",
    "Opus 4.6": "Claude (Anthropic)",
    "GLM-4.7": "GLM (ZhipuAI)",
    "GLM-5": "GLM (ZhipuAI)",
    "Gemini 3.1 Pro": "Gemini (Google)",
}
# Models to exclude
EXCLUDE_MODELS = {"zai-coding-plan/glm-4.7-flash", "glm-4.7-flash"}

# Chart excludes glm-4.7 too (only 3 models: haiku, opus, glm-5)
CHART_EXCLUDE = EXCLUDE_MODELS | {"zai-coding-plan/glm-4.7", "glm-4.7"}

# Scored rules per domain
SCORED_RULES = {
    "chart": 15,
    "sql-query": 12,
    "dockerfile": 13,
    "terraform": 13,
}


def norm_model(m):
    return MODEL_NORM.get(m, m)


def get_family(norm_name):
    return FAMILY_MAP.get(norm_name, "Unknown")


# ── Cliff's delta ──────────────────────────────────────────────────────────────
def cliffs_delta(x, y):
    """Compute Cliff's delta effect size."""
    nx, ny = len(x), len(y)
    if nx == 0 or ny == 0:
        return 0.0, "negligible"
    more = sum(1 for xi in x for yi in y if xi > yi)
    less = sum(1 for xi in x for yi in y if xi < yi)
    delta = (more - less) / (nx * ny)
    abs_d = abs(delta)
    if abs_d < 0.147:
        mag = "negligible"
    elif abs_d < 0.33:
        mag = "small"
    elif abs_d < 0.474:
        mag = "medium"
    else:
        mag = "large"
    return delta, mag


# ── Load baseline data ─────────────────────────────────────────────────────────
def load_baseline():
    """Load all baseline CSV data, returning list of dicts with normalized fields."""
    rows = []
    for domain, csv_path in BASELINE_CSVS.items():
        exclude = CHART_EXCLUDE if domain == "chart" else EXCLUDE_MODELS
        with open(csv_path) as f:
            reader = csv.DictReader(f)
            for r in reader:
                model_raw = r["model"]
                if model_raw in exclude:
                    continue
                # Get score
                if domain == "chart":
                    score = float(r.get("deep_score", r.get("auto_score", 0)))
                    max_rules = 15
                else:
                    score = float(r.get("auto_score", 0))
                    max_rules = int(r.get("scored_rules", SCORED_RULES[domain]))
                fr = 1.0 - (score / max_rules) if max_rules > 0 else 1.0
                rows.append({
                    "domain": domain,
                    "model_raw": model_raw,
                    "model": norm_model(model_raw),
                    "family": get_family(norm_model(model_raw)),
                    "condition": r["condition"],
                    "task": str(r["task"]),
                    "rep": str(r.get("rep", "")),
                    "score": score,
                    "max_rules": max_rules,
                    "failure_rate": fr,
                })
    return rows


# ── Score Gemini results ───────────────────────────────────────────────────────
def score_gemini():
    """Load Gemini JSON files, evaluate each, return list of dicts."""
    from evaluate_deep import evaluate_run as eval_chart
    from evaluate_sql import evaluate_run as eval_sql
    from evaluate_dockerfile import evaluate_run as eval_dockerfile
    from evaluate_terraform import evaluate_run as eval_terraform

    evaluators = {
        "chart": eval_chart,
        "sql-query": eval_sql,
        "dockerfile": eval_dockerfile,
        "terraform": eval_terraform,
    }

    rows = []
    for domain in ["chart", "sql-query", "dockerfile", "terraform"]:
        domain_dir = GEMINI_DIR / domain / "results"
        json_files = sorted(domain_dir.glob("gemini-3.1-pro-preview_*.json"))
        evaluator = evaluators[domain]

        for jf in json_files:
            with open(jf) as f:
                data = json.load(f)

            # Unwrap raw_output: strip prefixes, parse JSON, extract response
            raw_out = data.get("raw_output", "")
            # Strip "Loaded cached credentials.\n" prefix
            if raw_out.startswith("Loaded cached credentials.\n"):
                raw_out = raw_out[len("Loaded cached credentials.\n"):]

            # Parse the remaining JSON wrapper.
            # Some outputs have extra Node.js warnings before the JSON object.
            # Find the first line starting with '{' and parse from there.
            response = raw_out
            try:
                wrapper = json.loads(raw_out)
                response = wrapper.get("response", "")
            except (json.JSONDecodeError, AttributeError):
                # Try to find JSON start in multi-line output
                lines = raw_out.split("\n")
                for idx, line in enumerate(lines):
                    if line.strip().startswith("{"):
                        rest = "\n".join(lines[idx:])
                        try:
                            wrapper = json.loads(rest)
                            response = wrapper.get("response", "")
                            break
                        except (json.JSONDecodeError, AttributeError):
                            continue

            # Create a temp JSON file for the evaluator
            temp_data = {
                "run_id": data.get("run_id", jf.stem),
                "model": data.get("model", "gemini-3.1-pro-preview"),
                "condition": data.get("condition", ""),
                "task": str(data.get("task", "")),
                "task_complexity": data.get("task_complexity", ""),
                "rep": data.get("rep", ""),
                "duration_ms": data.get("duration_ms", ""),
                "raw_output": response,
            }

            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", delete=False, dir=str(domain_dir)
            ) as tmp:
                json.dump(temp_data, tmp)
                tmp_path = Path(tmp.name)

            try:
                result = evaluator(tmp_path)
            finally:
                tmp_path.unlink(missing_ok=True)

            # Extract score
            if domain == "chart":
                score = float(result.get("deep_score", 0))
                max_rules = 15
            else:
                score = float(result.get("auto_score", 0))
                max_rules = int(result.get("scored_rules", SCORED_RULES[domain]))

            fr = 1.0 - (score / max_rules) if max_rules > 0 else 1.0
            rows.append({
                "domain": domain,
                "model_raw": "gemini-3.1-pro-preview",
                "model": "Gemini 3.1 Pro",
                "family": "Gemini (Google)",
                "condition": data.get("condition", ""),
                "task": str(data.get("task", "")),
                "rep": str(data.get("rep", "")),
                "score": score,
                "max_rules": max_rules,
                "failure_rate": fr,
            })

    return rows


# ── HDI computation ────────────────────────────────────────────────────────────
def compute_hdi(failure_rates, lo=5, hi=95):
    """Compute HDI width as p95 - p5 of failure rate distribution."""
    if len(failure_rates) == 0:
        return 0.0, 0.0, 0.0
    arr = np.array(failure_rates)
    p_lo = np.percentile(arr, lo)
    p_hi = np.percentile(arr, hi)
    return p_lo, p_hi, p_hi - p_lo


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    print("=" * 80)
    print("PAPER STATISTICS — FULL COMPUTATION")
    print("=" * 80)

    # Load data
    print("\n>>> Loading baseline data...")
    baseline = load_baseline()
    print(f"    Baseline rows (after exclusions): {len(baseline)}")

    print("\n>>> Scoring Gemini results...")
    gemini = score_gemini()
    print(f"    Gemini rows: {len(gemini)}")

    all_data = baseline + gemini
    print(f"    TOTAL rows: {len(all_data)}")

    # ══════════════════════════════════════════════════════════════════════════
    # 1. RUN COUNTS
    # ══════════════════════════════════════════════════════════════════════════
    print("\n" + "=" * 80)
    print("1. RUN COUNTS")
    print("=" * 80)

    print(f"\nTotal runs: {len(all_data)}")

    # Per domain
    print("\nPer domain:")
    domain_counts = defaultdict(int)
    for r in all_data:
        domain_counts[r["domain"]] += 1
    for d in ["chart", "sql-query", "dockerfile", "terraform"]:
        print(f"  {d:15s}: {domain_counts[d]:4d}")

    # Per condition
    print("\nPer condition:")
    cond_counts = defaultdict(int)
    for r in all_data:
        cond_counts[r["condition"]] += 1
    for c in ["none", "markdown", "pseudocode"]:
        print(f"  {c:15s}: {cond_counts[c]:4d}")

    # Per model
    print("\nPer model:")
    model_counts = defaultdict(int)
    for r in all_data:
        model_counts[r["model"]] += 1
    for m in sorted(model_counts.keys()):
        print(f"  {m:20s}: {model_counts[m]:4d}")

    # Per family
    print("\nPer family:")
    family_counts = defaultdict(int)
    for r in all_data:
        family_counts[r["family"]] += 1
    for fam in sorted(family_counts.keys()):
        print(f"  {fam:25s}: {family_counts[fam]:4d}")

    # ══════════════════════════════════════════════════════════════════════════
    # 2. RQ1: Skill vs No-Skill (ALL 5 models)
    # ══════════════════════════════════════════════════════════════════════════
    print("\n" + "=" * 80)
    print("2. RQ1: SKILL vs NO-SKILL (all 5 models combined)")
    print("=" * 80)

    no_skill = [r["failure_rate"] for r in all_data if r["condition"] == "none"]
    skill = [r["failure_rate"] for r in all_data if r["condition"] in ("markdown", "pseudocode")]

    print(f"\n  N(no-skill): {len(no_skill)}")
    print(f"  N(skill):    {len(skill)}")
    print(f"  Mean FR(no-skill): {np.mean(no_skill):.4f} ({np.mean(no_skill)*100:.1f}%)")
    print(f"  Mean FR(skill):    {np.mean(skill):.4f} ({np.mean(skill)*100:.1f}%)")

    delta, mag = cliffs_delta(no_skill, skill)
    U, p = sp_stats.mannwhitneyu(no_skill, skill, alternative="two-sided")
    print(f"  Cliff's delta: {delta:+.3f} ({mag})")
    print(f"  Mann-Whitney U: {U:.0f}, p = {p:.2e}")

    # Per-domain table
    print("\n  Per-domain breakdown:")
    print(f"  {'Domain':15s} {'None FR':>10s} {'MD FR':>10s} {'PC FR':>10s}")
    print(f"  {'-'*15} {'-'*10} {'-'*10} {'-'*10}")
    for domain in ["chart", "sql-query", "dockerfile", "terraform"]:
        none_fr = [r["failure_rate"] for r in all_data if r["domain"] == domain and r["condition"] == "none"]
        md_fr = [r["failure_rate"] for r in all_data if r["domain"] == domain and r["condition"] == "markdown"]
        pc_fr = [r["failure_rate"] for r in all_data if r["domain"] == domain and r["condition"] == "pseudocode"]
        print(f"  {domain:15s} {np.mean(none_fr)*100:9.1f}% {np.mean(md_fr)*100:9.1f}% {np.mean(pc_fr)*100:9.1f}%")

    # ══════════════════════════════════════════════════════════════════════════
    # 3. RQ2: Pseudocode vs Markdown (ALL 5 models)
    # ══════════════════════════════════════════════════════════════════════════
    print("\n" + "=" * 80)
    print("3. RQ2: PSEUDOCODE vs MARKDOWN (all 5 models combined)")
    print("=" * 80)

    md_all = [r["failure_rate"] for r in all_data if r["condition"] == "markdown"]
    pc_all = [r["failure_rate"] for r in all_data if r["condition"] == "pseudocode"]

    print(f"\n  Pooled:")
    print(f"    N(markdown):   {len(md_all)}")
    print(f"    N(pseudocode): {len(pc_all)}")
    print(f"    Mean FR(MD):   {np.mean(md_all):.4f} ({np.mean(md_all)*100:.1f}%)")
    print(f"    Mean FR(PC):   {np.mean(pc_all):.4f} ({np.mean(pc_all)*100:.1f}%)")
    delta_pool, mag_pool = cliffs_delta(md_all, pc_all)
    U_pool, p_pool = sp_stats.mannwhitneyu(md_all, pc_all, alternative="two-sided")
    print(f"    Cliff's delta: {delta_pool:+.3f} ({mag_pool})")
    print(f"    Mann-Whitney p: {p_pool:.4f}")

    # Per-domain
    print(f"\n  Per-domain MD vs PC:")
    print(f"  {'Domain':15s} {'MD FR':>10s} {'PC FR':>10s} {'delta':>8s} {'mag':>12s} {'p':>10s}")
    print(f"  {'-'*15} {'-'*10} {'-'*10} {'-'*8} {'-'*12} {'-'*10}")
    for domain in ["chart", "sql-query", "dockerfile", "terraform"]:
        md_d = [r["failure_rate"] for r in all_data if r["domain"] == domain and r["condition"] == "markdown"]
        pc_d = [r["failure_rate"] for r in all_data if r["domain"] == domain and r["condition"] == "pseudocode"]
        d, m = cliffs_delta(md_d, pc_d)
        _, p_d = sp_stats.mannwhitneyu(md_d, pc_d, alternative="two-sided")
        print(f"  {domain:15s} {np.mean(md_d)*100:9.1f}% {np.mean(pc_d)*100:9.1f}% {d:+7.3f} {m:>12s} {p_d:10.4f}")

    # ══════════════════════════════════════════════════════════════════════════
    # 4. RQ3: Cross-family analysis
    # ══════════════════════════════════════════════════════════════════════════
    print("\n" + "=" * 80)
    print("4. RQ3: CROSS-FAMILY ANALYSIS (3 families)")
    print("=" * 80)

    families = ["Claude (Anthropic)", "GLM (ZhipuAI)", "Gemini (Google)"]
    print(f"\n  Per family × domain: Cliff's delta (MD vs PC)")
    print(f"  {'Family':25s} {'Domain':15s} {'MD FR':>9s} {'PC FR':>9s} {'delta':>8s} {'mag':>12s} {'p':>10s}")
    print(f"  {'-'*25} {'-'*15} {'-'*9} {'-'*9} {'-'*8} {'-'*12} {'-'*10}")
    for fam in families:
        for domain in ["chart", "sql-query", "dockerfile", "terraform"]:
            md_fd = [r["failure_rate"] for r in all_data
                     if r["family"] == fam and r["domain"] == domain and r["condition"] == "markdown"]
            pc_fd = [r["failure_rate"] for r in all_data
                     if r["family"] == fam and r["domain"] == domain and r["condition"] == "pseudocode"]
            if len(md_fd) == 0 and len(pc_fd) == 0:
                continue
            if len(md_fd) > 0 and len(pc_fd) > 0:
                d, m = cliffs_delta(md_fd, pc_fd)
                _, p_d = sp_stats.mannwhitneyu(md_fd, pc_fd, alternative="two-sided")
                print(f"  {fam:25s} {domain:15s} {np.mean(md_fd)*100:8.1f}% {np.mean(pc_fd)*100:8.1f}% {d:+7.3f} {m:>12s} {p_d:10.4f}")
            else:
                print(f"  {fam:25s} {domain:15s} (insufficient data)")

    # Frontier model comparison: Opus 4.6, GLM-5, Gemini 3.1 Pro
    print(f"\n  Frontier model comparison:")
    frontier_models = ["Opus 4.6", "GLM-5", "Gemini 3.1 Pro"]
    print(f"  {'Model':20s} {'MD FR':>10s} {'PC FR':>10s} {'delta':>8s} {'mag':>12s} {'rel. reduction':>15s}")
    print(f"  {'-'*20} {'-'*10} {'-'*10} {'-'*8} {'-'*12} {'-'*15}")
    for model in frontier_models:
        md_m = [r["failure_rate"] for r in all_data if r["model"] == model and r["condition"] == "markdown"]
        pc_m = [r["failure_rate"] for r in all_data if r["model"] == model and r["condition"] == "pseudocode"]
        if len(md_m) > 0 and len(pc_m) > 0:
            d, m = cliffs_delta(md_m, pc_m)
            mean_md = np.mean(md_m)
            mean_pc = np.mean(pc_m)
            rel_red = (mean_md - mean_pc) / mean_md * 100 if mean_md > 0 else 0
            print(f"  {model:20s} {mean_md*100:9.1f}% {mean_pc*100:9.1f}% {d:+7.3f} {m:>12s} {rel_red:+14.1f}%")

    # ══════════════════════════════════════════════════════════════════════════
    # 5. RQ5: Reliability (per model) - HDI analysis
    # ══════════════════════════════════════════════════════════════════════════
    print("\n" + "=" * 80)
    print("5. RQ5: RELIABILITY — HDI ANALYSIS (per model)")
    print("=" * 80)

    all_models = ["Haiku 4.5", "Opus 4.6", "GLM-4.7", "GLM-5", "Gemini 3.1 Pro"]
    print(f"\n  {'Model':20s} {'HDI_MD':>12s} {'HDI_PC':>12s} {'Narrowing':>12s} {'P(FR<10%)_MD':>14s} {'P(FR<10%)_PC':>14s}")
    print(f"  {'-'*20} {'-'*12} {'-'*12} {'-'*12} {'-'*14} {'-'*14}")
    for model in all_models:
        md_fr = [r["failure_rate"] for r in all_data if r["model"] == model and r["condition"] == "markdown"]
        pc_fr = [r["failure_rate"] for r in all_data if r["model"] == model and r["condition"] == "pseudocode"]

        if len(md_fr) == 0 or len(pc_fr) == 0:
            print(f"  {model:20s} (insufficient data)")
            continue

        _, _, hdi_md = compute_hdi(md_fr)
        _, _, hdi_pc = compute_hdi(pc_fr)
        narrowing = hdi_md - hdi_pc

        # P(FR < 10%)
        p_md_10 = np.mean(np.array(md_fr) < 0.10)
        p_pc_10 = np.mean(np.array(pc_fr) < 0.10)

        print(f"  {model:20s} {hdi_md*100:10.1f}pp {hdi_pc*100:10.1f}pp {narrowing*100:+10.1f}pp {p_md_10*100:13.1f}% {p_pc_10*100:13.1f}%")

    # ══════════════════════════════════════════════════════════════════════════
    # 6. Gemini-only highlights
    # ══════════════════════════════════════════════════════════════════════════
    print("\n" + "=" * 80)
    print("6. GEMINI-ONLY HIGHLIGHTS")
    print("=" * 80)

    gemini_data = [r for r in all_data if r["model"] == "Gemini 3.1 Pro"]
    gem_none = [r["failure_rate"] for r in gemini_data if r["condition"] == "none"]
    gem_skill = [r["failure_rate"] for r in gemini_data if r["condition"] in ("markdown", "pseudocode")]
    gem_md = [r["failure_rate"] for r in gemini_data if r["condition"] == "markdown"]
    gem_pc = [r["failure_rate"] for r in gemini_data if r["condition"] == "pseudocode"]

    print(f"\n  Gemini baseline (none) FR:     {np.mean(gem_none)*100:.1f}%")
    print(f"  Gemini skill (MD+PC) FR:       {np.mean(gem_skill)*100:.1f}%")
    print(f"  Gemini markdown FR:            {np.mean(gem_md)*100:.1f}%")
    print(f"  Gemini pseudocode FR:          {np.mean(gem_pc)*100:.1f}%")

    delta_g, mag_g = cliffs_delta(gem_none, gem_skill)
    U_g, p_g = sp_stats.mannwhitneyu(gem_none, gem_skill, alternative="two-sided")
    print(f"  Cliff's delta (none vs skill): {delta_g:+.3f} ({mag_g})")
    print(f"  Mann-Whitney p:                {p_g:.4f}")

    print(f"\n  Per-domain breakdown:")
    print(f"  {'Domain':15s} {'None FR':>10s} {'MD FR':>10s} {'PC FR':>10s} {'Skill lift':>12s}")
    print(f"  {'-'*15} {'-'*10} {'-'*10} {'-'*10} {'-'*12}")
    for domain in ["chart", "sql-query", "dockerfile", "terraform"]:
        gn = [r["failure_rate"] for r in gemini_data if r["domain"] == domain and r["condition"] == "none"]
        gm = [r["failure_rate"] for r in gemini_data if r["domain"] == domain and r["condition"] == "markdown"]
        gp = [r["failure_rate"] for r in gemini_data if r["domain"] == domain and r["condition"] == "pseudocode"]
        mean_none = np.mean(gn) if gn else 0
        mean_md = np.mean(gm) if gm else 0
        mean_pc = np.mean(gp) if gp else 0
        best_skill = min(mean_md, mean_pc)
        lift = (mean_none - best_skill) / mean_none * 100 if mean_none > 0 else 0
        print(f"  {domain:15s} {mean_none*100:9.1f}% {mean_md*100:9.1f}% {mean_pc*100:9.1f}% {lift:+10.1f}%")

    # Largest skill lift comparison across ALL models
    print(f"\n  Largest skill lift comparison across ALL models (none→best-skill):")
    print(f"  {'Model':20s} {'None FR':>10s} {'Best Skill FR':>14s} {'Abs lift':>10s} {'Rel lift':>10s}")
    print(f"  {'-'*20} {'-'*10} {'-'*14} {'-'*10} {'-'*10}")
    for model in all_models:
        m_none = [r["failure_rate"] for r in all_data if r["model"] == model and r["condition"] == "none"]
        m_md = [r["failure_rate"] for r in all_data if r["model"] == model and r["condition"] == "markdown"]
        m_pc = [r["failure_rate"] for r in all_data if r["model"] == model and r["condition"] == "pseudocode"]
        if not m_none or (not m_md and not m_pc):
            continue
        mean_none = np.mean(m_none)
        mean_md = np.mean(m_md) if m_md else 999
        mean_pc = np.mean(m_pc) if m_pc else 999
        best = min(mean_md, mean_pc)
        best_label = "PC" if mean_pc <= mean_md else "MD"
        abs_lift = mean_none - best
        rel_lift = abs_lift / mean_none * 100 if mean_none > 0 else 0
        print(f"  {model:20s} {mean_none*100:9.1f}% {best*100:13.1f}% {abs_lift*100:+9.1f}pp {rel_lift:+9.1f}%")

    # ══════════════════════════════════════════════════════════════════════════
    # 7. LaTeX-ready summary table values
    # ══════════════════════════════════════════════════════════════════════════
    print("\n" + "=" * 80)
    print("7. LaTeX-READY SUMMARY VALUES")
    print("=" * 80)

    print("\n--- RQ1 Table: Per-model skill vs no-skill ---")
    print(f"{'Model':20s} & {'N':>4s} & {'None':>8s} & {'MD':>8s} & {'PC':>8s} & {'delta(N→S)':>12s} & {'p':>10s} \\\\")
    for model in all_models:
        m_none = [r["failure_rate"] for r in all_data if r["model"] == model and r["condition"] == "none"]
        m_md = [r["failure_rate"] for r in all_data if r["model"] == model and r["condition"] == "markdown"]
        m_pc = [r["failure_rate"] for r in all_data if r["model"] == model and r["condition"] == "pseudocode"]
        m_skill = m_md + m_pc
        n = len(m_none) + len(m_skill)
        if len(m_none) > 0 and len(m_skill) > 0:
            d, mag = cliffs_delta(m_none, m_skill)
            _, p = sp_stats.mannwhitneyu(m_none, m_skill, alternative="two-sided")
            print(f"{model:20s} & {n:4d} & {np.mean(m_none)*100:7.1f}\\% & {np.mean(m_md)*100:7.1f}\\% & {np.mean(m_pc)*100:7.1f}\\% & {d:+.3f} ({mag[:3]}) & {p:.3f} \\\\")

    print("\n--- RQ2 Table: Per-model MD vs PC ---")
    print(f"{'Model':20s} & {'MD':>8s} & {'PC':>8s} & {'delta':>8s} & {'p':>10s} \\\\")
    for model in all_models:
        m_md = [r["failure_rate"] for r in all_data if r["model"] == model and r["condition"] == "markdown"]
        m_pc = [r["failure_rate"] for r in all_data if r["model"] == model and r["condition"] == "pseudocode"]
        if len(m_md) > 0 and len(m_pc) > 0:
            d, mag = cliffs_delta(m_md, m_pc)
            _, p = sp_stats.mannwhitneyu(m_md, m_pc, alternative="two-sided")
            print(f"{model:20s} & {np.mean(m_md)*100:7.1f}\\% & {np.mean(m_pc)*100:7.1f}\\% & {d:+.3f} ({mag[:3]}) & {p:.3f} \\\\")

    # ══════════════════════════════════════════════════════════════════════════
    # 8. Grand summary numbers for abstract/intro
    # ══════════════════════════════════════════════════════════════════════════
    print("\n" + "=" * 80)
    print("8. GRAND SUMMARY (for abstract / intro)")
    print("=" * 80)

    # Overall skill effect
    overall_none_fr = np.mean([r["failure_rate"] for r in all_data if r["condition"] == "none"])
    overall_skill_fr = np.mean([r["failure_rate"] for r in all_data if r["condition"] in ("markdown", "pseudocode")])
    overall_md_fr = np.mean([r["failure_rate"] for r in all_data if r["condition"] == "markdown"])
    overall_pc_fr = np.mean([r["failure_rate"] for r in all_data if r["condition"] == "pseudocode"])

    print(f"\n  Models tested: {len(set(r['model'] for r in all_data))}")
    print(f"  Families: {len(set(r['family'] for r in all_data))}")
    print(f"  Domains: {len(set(r['domain'] for r in all_data))}")
    print(f"  Total runs: {len(all_data)}")
    print(f"\n  Overall no-skill FR:    {overall_none_fr*100:.1f}%")
    print(f"  Overall skill FR:       {overall_skill_fr*100:.1f}%")
    print(f"  Overall markdown FR:    {overall_md_fr*100:.1f}%")
    print(f"  Overall pseudocode FR:  {overall_pc_fr*100:.1f}%")
    print(f"  Absolute reduction:     {(overall_none_fr - overall_skill_fr)*100:.1f}pp")
    print(f"  Relative reduction:     {(overall_none_fr - overall_skill_fr)/overall_none_fr*100:.1f}%")

    # Best and worst skill effect by model
    print(f"\n  Per-model skill effect (none→best skill):")
    for model in all_models:
        m_none = np.mean([r["failure_rate"] for r in all_data if r["model"] == model and r["condition"] == "none"])
        m_md = [r["failure_rate"] for r in all_data if r["model"] == model and r["condition"] == "markdown"]
        m_pc = [r["failure_rate"] for r in all_data if r["model"] == model and r["condition"] == "pseudocode"]
        best = min(np.mean(m_md) if m_md else 999, np.mean(m_pc) if m_pc else 999)
        rel = (m_none - best) / m_none * 100 if m_none > 0 else 0
        print(f"    {model:20s}: {m_none*100:.1f}% → {best*100:.1f}% ({rel:+.1f}%)")

    # ══════════════════════════════════════════════════════════════════════════
    # 9. Detailed per-model per-domain table
    # ══════════════════════════════════════════════════════════════════════════
    print("\n" + "=" * 80)
    print("9. DETAILED: Per-model × Per-domain × Per-condition FR")
    print("=" * 80)

    print(f"\n  {'Model':20s} {'Domain':15s} {'None':>8s} {'MD':>8s} {'PC':>8s} {'N':>4s}")
    print(f"  {'-'*20} {'-'*15} {'-'*8} {'-'*8} {'-'*8} {'-'*4}")
    for model in all_models:
        for domain in ["chart", "sql-query", "dockerfile", "terraform"]:
            m_none = [r["failure_rate"] for r in all_data
                      if r["model"] == model and r["domain"] == domain and r["condition"] == "none"]
            m_md = [r["failure_rate"] for r in all_data
                    if r["model"] == model and r["domain"] == domain and r["condition"] == "markdown"]
            m_pc = [r["failure_rate"] for r in all_data
                    if r["model"] == model and r["domain"] == domain and r["condition"] == "pseudocode"]
            n = len(m_none) + len(m_md) + len(m_pc)
            if n == 0:
                continue
            none_str = f"{np.mean(m_none)*100:.1f}%" if m_none else "—"
            md_str = f"{np.mean(m_md)*100:.1f}%" if m_md else "—"
            pc_str = f"{np.mean(m_pc)*100:.1f}%" if m_pc else "—"
            print(f"  {model:20s} {domain:15s} {none_str:>8s} {md_str:>8s} {pc_str:>8s} {n:4d}")


if __name__ == "__main__":
    warnings.filterwarnings("ignore")
    main()
