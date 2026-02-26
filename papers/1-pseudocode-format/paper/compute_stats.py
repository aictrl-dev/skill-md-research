#!/usr/bin/env python3
"""Compute all statistics reported in the paper from the raw CSV data.

Loads four domains (Chart, Dockerfile, SQL, Terraform) and five models
(Haiku 4.5, Opus 4.6, GLM-4.7, GLM-5, Gemini 3.1 Pro).  GLM-4.7-flash
is excluded from analysis (not in the paper).

Chart uses scores_deep.csv with pass_count/fail_count columns;
the other three use scores.csv with auto_score/scored_rules.

NOTE: Gemini 3.1 Pro data is included in the paper (108 runs) but has
not yet been scored into the domain CSVs.  When Gemini CSVs are added,
this script will pick them up automatically.  Until then, the totals
here reflect the four original models (629 runs).
"""

import os
import sys

import pandas as pd
import numpy as np
from scipy import stats

# ─── Resolve paths relative to this script ──────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PAPER1_ROOT = os.path.dirname(SCRIPT_DIR)  # papers/1-pseudocode-format/
DOMAINS_DIR = os.path.join(PAPER1_ROOT, "domains")

# Models to exclude from analysis (not in the paper)
EXCLUDE_MODELS = {"glm-4.7-flash"}


# ─── Load data ───────────────────────────────────────────────────────────────

def load_chart():
    """Load Chart domain from scores_deep.csv (pass_count/fail_count)."""
    path = os.path.join(DOMAINS_DIR, "chart", "results", "scores_deep.csv")
    if not os.path.exists(path):
        print(f"WARNING: Chart data not found at {path}", file=sys.stderr)
        return pd.DataFrame()
    df = pd.read_csv(path)
    df["domain"] = "Chart"
    df["model"] = df["model"].str.replace("zai-coding-plan/", "", regex=False)
    # Chart uses pass_count / (pass_count + fail_count) as score
    df["auto_score"] = df["pass_count"]
    df["scored_rules"] = df["pass_count"] + df["fail_count"]
    return df


def load_standard_domain(name, subdir):
    """Load a standard domain from scores.csv (auto_score/scored_rules)."""
    path = os.path.join(DOMAINS_DIR, subdir, "results", "scores.csv")
    if not os.path.exists(path):
        print(f"WARNING: {name} data not found at {path}", file=sys.stderr)
        return pd.DataFrame()
    df = pd.read_csv(path)
    df["domain"] = name
    df["model"] = df["model"].str.replace("zai-coding-plan/", "", regex=False)
    return df


frames = []
for loader in [
    lambda: load_chart(),
    lambda: load_standard_domain("Dockerfile", "dockerfile"),
    lambda: load_standard_domain("SQL", "sql-query"),
    lambda: load_standard_domain("Terraform", "terraform"),
]:
    df = loader()
    if not df.empty:
        # Compute failure rate; scored_rules=0 → total extraction failure → FR=1.0
        df["failure_rate"] = np.where(
            df["scored_rules"] == 0,
            1.0,
            1.0 - df["auto_score"] / df["scored_rules"]
        )
        frames.append(df)

if not frames:
    print("ERROR: No data loaded.", file=sys.stderr)
    sys.exit(1)

data = pd.concat(frames, ignore_index=True)

# Exclude models not in the paper
data = data[~data["model"].isin(EXCLUDE_MODELS)]

ALL_DOMAINS = sorted(data["domain"].unique())


print("=" * 80)
print("DATA OVERVIEW")
print("=" * 80)
print(f"Total runs: {len(data)}")
for d in ALL_DOMAINS:
    n = len(data[data["domain"] == d])
    print(f"  {d}: {n} runs")
print()
print("Runs by condition:")
for cond in ["none", "markdown", "pseudocode"]:
    n = len(data[data["condition"] == cond])
    print(f"  {cond}: {n}")
print()
print("Unique models:", sorted(data["model"].unique()))
print()


# ─── Cliff's delta ───────────────────────────────────────────────────────────

def cliffs_delta(x, y):
    """Compute Cliff's delta. Positive delta means x > y."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    more = less = 0
    for xi in x:
        for yi in y:
            if xi > yi:
                more += 1
            elif xi < yi:
                less += 1
    n = len(x) * len(y)
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
    """Mann-Whitney U with numpy conversion to avoid pandas issues."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    u, p = stats.mannwhitneyu(x, y, alternative=alternative)
    return u, p


def fmt_p(p):
    if p < 0.001:
        return "< 0.001"
    else:
        return f"{p:.3f}"


# ═════════════════════════════════════════════════════════════════════════════
# TABLE 3 — RQ1: Skill files vs. no-skill baseline (pooled)
# ═════════════════════════════════════════════════════════════════════════════
print("=" * 80)
print("TABLE 3 — RQ1: Skill files vs. no-skill baseline (pooled)")
print("=" * 80)

none_fr = data[data["condition"] == "none"]["failure_rate"].values
skill_fr = data[data["condition"].isin(["markdown", "pseudocode"])]["failure_rate"].values

print(f"No skill:     N={len(none_fr)}, Mean FR = {none_fr.mean():.4f} ({none_fr.mean()*100:.1f}%)")
print(f"Skill (both): N={len(skill_fr)}, Mean FR = {skill_fr.mean():.4f} ({skill_fr.mean()*100:.1f}%)")

# Cliff's delta: none vs skill — positive means none has HIGHER failure rate (skill is better)
delta_rq1, mag_rq1 = cliffs_delta(none_fr, skill_fr)
print(f"Cliff's delta = {delta_rq1:.3f} ({mag_rq1})")

# Mann-Whitney U, one-tailed: alternative="greater" means none > skill
u_rq1, p_rq1 = mwu(none_fr, skill_fr, alternative="greater")
print(f"Mann-Whitney U = {u_rq1:.0f}, p = {fmt_p(p_rq1)}")

# Reduction factor
reduction = none_fr.mean() / skill_fr.mean()
print(f"Reduction factor: {reduction:.2f}x")
print()

# ═════════════════════════════════════════════════════════════════════════════
# TABLE 4 — RQ1 per domain: failure rate by condition
# ═════════════════════════════════════════════════════════════════════════════
print("=" * 80)
print("TABLE 4 — RQ1 per domain: failure rate by condition")
print("=" * 80)

for domain in ALL_DOMAINS:
    d = data[data["domain"] == domain]
    none_d = d[d["condition"] == "none"]["failure_rate"].mean()
    md_d = d[d["condition"] == "markdown"]["failure_rate"].mean()
    pc_d = d[d["condition"] == "pseudocode"]["failure_rate"].mean()
    print(f"{domain:12s}  None={none_d*100:5.1f}%  MD={md_d*100:5.1f}%  PC={pc_d*100:5.1f}%")

# Pooled
none_p = data[data["condition"] == "none"]["failure_rate"].mean()
md_p = data[data["condition"] == "markdown"]["failure_rate"].mean()
pc_p = data[data["condition"] == "pseudocode"]["failure_rate"].mean()
print(f"{'Pooled':12s}  None={none_p*100:5.1f}%  MD={md_p*100:5.1f}%  PC={pc_p*100:5.1f}%")
print()

# ═════════════════════════════════════════════════════════════════════════════
# TABLE 5 — RQ2: Pseudocode vs. Markdown (pooled)
# ═════════════════════════════════════════════════════════════════════════════
print("=" * 80)
print("TABLE 5 — RQ2: Pseudocode vs. Markdown (pooled)")
print("=" * 80)

md_all = data[data["condition"] == "markdown"]["failure_rate"].values
pc_all = data[data["condition"] == "pseudocode"]["failure_rate"].values

print(f"Markdown:    N={len(md_all)}, Mean FR = {md_all.mean()*100:.1f}%")
print(f"Pseudocode:  N={len(pc_all)}, Mean FR = {pc_all.mean()*100:.1f}%")

# Mann-Whitney: one-tailed, alternative="greater" means markdown > pseudocode (pseudocode better)
u_rq2, p_rq2 = mwu(md_all, pc_all, alternative="greater")
print(f"Mann-Whitney U = {u_rq2:.0f}, p = {fmt_p(p_rq2)}")

# Cliff's delta: positive means markdown has higher FR (pseudocode better)
delta_rq2, mag_rq2 = cliffs_delta(md_all, pc_all)
print(f"Cliff's delta = {delta_rq2:.3f} ({mag_rq2})")
print()

# ═════════════════════════════════════════════════════════════════════════════
# TABLE 5 — RQ2 per domain
# ═════════════════════════════════════════════════════════════════════════════
print("=" * 80)
print("TABLE 5 — RQ2 per domain: Pseudocode vs. Markdown")
print("=" * 80)

for domain in ALL_DOMAINS:
    d = data[data["domain"] == domain]
    md_d = d[d["condition"] == "markdown"]["failure_rate"].values
    pc_d = d[d["condition"] == "pseudocode"]["failure_rate"].values

    u_d, p_d = mwu(md_d, pc_d, alternative="greater")
    delta_d, mag_d = cliffs_delta(md_d, pc_d)

    print(f"{domain:12s}  MD FR={np.mean(md_d)*100:5.1f}%  PC FR={np.mean(pc_d)*100:5.1f}%  "
          f"delta={delta_d:+.3f} ({mag_d:6s})  U={u_d:.0f}  p={fmt_p(p_d)}")

print()

# ═════════════════════════════════════════════════════════════════════════════
# TABLE 6 — RQ3: Cliff's delta by family and domain (two-tailed)
# ═════════════════════════════════════════════════════════════════════════════
print("=" * 80)
print("TABLE 6 — RQ3: Cliff's delta by family and domain (two-tailed)")
print("=" * 80)

# Define families
claude_models = ["haiku", "opus"]
glm_models = sorted([m for m in data["model"].unique() if m.startswith("glm")])
gemini_models = sorted([m for m in data["model"].unique() if m.startswith("gemini")])
print(f"Claude models: {claude_models}")
print(f"GLM models: {glm_models}")
print(f"Gemini models: {gemini_models}")
print()

families = [("Claude", claude_models), ("GLM", glm_models)]
if gemini_models:
    families.append(("Gemini", gemini_models))

for family_name, family_models in families:
    for domain in ALL_DOMAINS:
        d = data[(data["domain"] == domain) & (data["model"].isin(family_models))]
        md_d = d[d["condition"] == "markdown"]["failure_rate"].values
        pc_d = d[d["condition"] == "pseudocode"]["failure_rate"].values

        if len(md_d) == 0 or len(pc_d) == 0:
            print(f"{family_name:6s}  {domain:12s}  NO DATA")
            continue

        # Two-tailed test
        u_d, p_d = mwu(md_d, pc_d, alternative="two-sided")
        # Positive delta = markdown > pseudocode = pseudocode better
        delta_d, mag_d = cliffs_delta(md_d, pc_d)

        print(f"{family_name:6s}  {domain:12s}  delta={delta_d:+.3f}  p={fmt_p(p_d):8s}  mag={mag_d}")

print()

# ═════════════════════════════════════════════════════════════════════════════
# TABLE 7 — RQ3: Frontier models
# ═════════════════════════════════════════════════════════════════════════════
print("=" * 80)
print("TABLE 7 — RQ3: Frontier model failure rates (pooled across domains)")
print("=" * 80)

frontier_models = ["opus", "glm-5"]
# Include Gemini if present
for m in data["model"].unique():
    if "gemini" in m.lower():
        frontier_models.append(m)

for model_name in frontier_models:
    d = data[data["model"] == model_name]
    if len(d) == 0:
        continue
    md_d = d[d["condition"] == "markdown"]["failure_rate"].values
    pc_d = d[d["condition"] == "pseudocode"]["failure_rate"].values

    if len(md_d) == 0 or len(pc_d) == 0:
        continue

    md_mean = md_d.mean() * 100
    pc_mean = pc_d.mean() * 100
    abs_diff = md_mean - pc_mean
    rel_diff = (pc_mean - md_mean) / md_mean * 100 if md_mean > 0 else 0

    print(f"{model_name:20s}  MD FR={md_mean:5.1f}%  PC FR={pc_mean:5.1f}%  "
          f"Delta={abs_diff:+.1f}pp  Rel={rel_diff:+.0f}%")

print()

# ═════════════════════════════════════════════════════════════════════════════
# RQ5: Variance analysis
# ═════════════════════════════════════════════════════════════════════════════
print("=" * 80)
print("RQ5: Variance analysis (Levene's test, HDI)")
print("=" * 80)

# Pooled variance
md_var = np.var(md_all, ddof=1)
pc_var = np.var(pc_all, ddof=1)
var_ratio = md_var / pc_var
levene_stat, levene_p = stats.levene(md_all, pc_all, center="median")
print(f"Markdown variance:   {md_var:.4f}")
print(f"Pseudocode variance: {pc_var:.4f}")
print(f"Variance ratio (MD/PC): {var_ratio:.2f}")
print(f"Levene's test: F={levene_stat:.2f}, p={fmt_p(levene_p)}")
print()

# Per-model HDI and threshold analysis
print("Per-model 90% HDI width and P(FR < 10%):")
for model_name in sorted(data["model"].unique()):
    for cond in ["markdown", "pseudocode"]:
        vals = data[(data["model"] == model_name) & (data["condition"] == cond)]["failure_rate"].values
        if len(vals) < 3:
            continue
        sorted_vals = np.sort(vals)
        # 90% HDI (5th to 95th percentile)
        lo = np.percentile(sorted_vals, 5)
        hi = np.percentile(sorted_vals, 95)
        hdi_width = (hi - lo) * 100
        p_below_10 = np.mean(vals < 0.10) * 100
        print(f"  {model_name:20s}  {cond:12s}  HDI width={hdi_width:5.1f}%  P(FR<10%)={p_below_10:5.1f}%")

print()

# ═════════════════════════════════════════════════════════════════════════════
# ABSTRACT NUMBERS
# ═════════════════════════════════════════════════════════════════════════════
print("=" * 80)
print("ABSTRACT / KEY NUMBERS SUMMARY")
print("=" * 80)

print(f"Total scored runs: {len(data)}")
for d in ALL_DOMAINS:
    print(f"  {d}: {len(data[data['domain'] == d])}")
print()
print(f"RQ1: Skill files reduce FR by {reduction:.1f}x (from {none_fr.mean()*100:.1f}% to {skill_fr.mean()*100:.1f}%)")
print(f"  Cliff's delta = {delta_rq1:.3f} ({mag_rq1})")
print(f"  p = {fmt_p(p_rq1)}")
print()
print(f"RQ2: Pseudocode vs Markdown")
print(f"  MD FR = {md_all.mean()*100:.1f}%  PC FR = {pc_all.mean()*100:.1f}%")
print(f"  p = {fmt_p(p_rq2)}")
print(f"  Cliff's delta = {delta_rq2:.3f} ({mag_rq2})")
print()

# Frontier numbers for abstract
for model_name in ["opus", "glm-5"]:
    d = data[data["model"] == model_name]
    md_mean = d[d["condition"] == "markdown"]["failure_rate"].mean() * 100
    pc_mean = d[d["condition"] == "pseudocode"]["failure_rate"].mean() * 100
    print(f"  {model_name}: MD={md_mean:.1f}% PC={pc_mean:.1f}%")
print()

# Relative reduction for conclusion
rel_reduction_rq2 = (1 - pc_all.mean() / md_all.mean()) * 100
print(f"Relative reduction RQ2 (for conclusion): {rel_reduction_rq2:.0f}%")
print()

# pp effect size from discussion
pp_effect = (none_fr.mean() - skill_fr.mean()) * 100
print(f"Pooled skill presence effect: {pp_effect:.1f}pp ({none_fr.mean()*100:.1f}% -> {skill_fr.mean()*100:.1f}%)")
print()

# Gap ratio: skill presence effect vs format effect
skill_presence_gap = none_fr.mean() - skill_fr.mean()
format_gap = md_all.mean() - pc_all.mean()
gap_ratio = skill_presence_gap / format_gap if format_gap > 0 else float("inf")
print(f"Gap ratio (skill presence / format effect): {gap_ratio:.0f}x")
print(f"  Skill presence gap: {skill_presence_gap*100:.1f}pp")
print(f"  Format gap: {format_gap*100:.1f}pp")
print()

# ═════════════════════════════════════════════════════════════════════════════
# DETAILED BREAKDOWN: Runs by model x condition
# ═════════════════════════════════════════════════════════════════════════════
print("=" * 80)
print("DETAILED: Runs by model x condition")
print("=" * 80)

pivot = data.groupby(["model", "condition"]).agg(
    n=("failure_rate", "count"),
    mean_fr=("failure_rate", "mean"),
).unstack("condition")
print(pivot.to_string())
print()

# ═════════════════════════════════════════════════════════════════════════════
# DETAILED: Runs by model x condition x domain
# ═════════════════════════════════════════════════════════════════════════════
print("=" * 80)
print("DETAILED: Mean FR by model x condition x domain")
print("=" * 80)

for domain in ALL_DOMAINS:
    print(f"\n--- {domain} ---")
    d = data[data["domain"] == domain]
    pivot = d.groupby(["model", "condition"])["failure_rate"].agg(["count", "mean"]).unstack("condition")
    print(pivot.to_string())
