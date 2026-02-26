#!/usr/bin/env python3
"""Compute all statistics reported in the paper from the raw CSV data."""

import pandas as pd
import numpy as np
from scipy import stats

# ─── Load data ───────────────────────────────────────────────────────────────
domains = {
    "Dockerfile": "/home/bulat/code/skill-md-research/domains/dockerfile/results/scores.csv",
    "SQL": "/home/bulat/code/skill-md-research/domains/sql-query/results/scores.csv",
    "Terraform": "/home/bulat/code/skill-md-research/domains/terraform/results/scores.csv",
}

frames = []
for domain, path in domains.items():
    df = pd.read_csv(path)
    df["domain"] = domain
    # Strip "zai-coding-plan/" prefix from model names
    df["model"] = df["model"].str.replace("zai-coding-plan/", "", regex=False)
    # Compute failure rate; scored_rules=0 means total extraction failure → FR=1.0
    df["failure_rate"] = np.where(
        df["scored_rules"] == 0,
        1.0,
        1.0 - df["auto_score"] / df["scored_rules"]
    )
    frames.append(df)

data = pd.concat(frames, ignore_index=True)

print("=" * 80)
print("DATA OVERVIEW")
print("=" * 80)
print(f"Total runs: {len(data)}")
for d in ["Dockerfile", "SQL", "Terraform"]:
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

for domain in ["Dockerfile", "SQL", "Terraform"]:
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

for domain in ["Dockerfile", "SQL", "Terraform"]:
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
print(f"Claude models: {claude_models}")
print(f"GLM models: {glm_models}")
print()

for family_name, family_models in [("Claude", claude_models), ("GLM", glm_models)]:
    for domain in ["Dockerfile", "SQL", "Terraform"]:
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
# TABLE 7 — RQ3: Frontier models (Opus and GLM-5)
# ═════════════════════════════════════════════════════════════════════════════
print("=" * 80)
print("TABLE 7 — RQ3: Frontier model failure rates (pooled across domains)")
print("=" * 80)

for model_name in ["opus", "glm-5"]:
    d = data[data["model"] == model_name]
    md_d = d[d["condition"] == "markdown"]["failure_rate"].values
    pc_d = d[d["condition"] == "pseudocode"]["failure_rate"].values

    md_mean = md_d.mean() * 100
    pc_mean = pc_d.mean() * 100
    abs_diff = md_mean - pc_mean
    rel_diff = (pc_mean - md_mean) / md_mean * 100

    print(f"{model_name:10s}  MD FR={md_mean:5.1f}%  PC FR={pc_mean:5.1f}%  "
          f"Delta=+{abs_diff:.1f}pp  Rel={rel_diff:+.0f}%")

print()

# ═════════════════════════════════════════════════════════════════════════════
# ABSTRACT NUMBERS
# ═════════════════════════════════════════════════════════════════════════════
print("=" * 80)
print("ABSTRACT / KEY NUMBERS SUMMARY")
print("=" * 80)

print(f"Total scored runs: {len(data)}")
print(f"Runs per domain: Dockerfile={len(data[data['domain']=='Dockerfile'])}, "
      f"SQL={len(data[data['domain']=='SQL'])}, "
      f"Terraform={len(data[data['domain']=='Terraform'])}")
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
opus_md = data[(data["model"] == "opus") & (data["condition"] == "markdown")]["failure_rate"].mean() * 100
opus_pc = data[(data["model"] == "opus") & (data["condition"] == "pseudocode")]["failure_rate"].mean() * 100
glm5_md = data[(data["model"] == "glm-5") & (data["condition"] == "markdown")]["failure_rate"].mean() * 100
glm5_pc = data[(data["model"] == "glm-5") & (data["condition"] == "pseudocode")]["failure_rate"].mean() * 100

print(f"Frontier: Opus MD={opus_md:.1f}% PC={opus_pc:.1f}%   GLM-5 MD={glm5_md:.1f}% PC={glm5_pc:.1f}%")
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
gap_ratio = skill_presence_gap / format_gap
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

for domain in ["Dockerfile", "SQL", "Terraform"]:
    print(f"\n--- {domain} ---")
    d = data[data["domain"] == domain]
    pivot = d.groupby(["model", "condition"])["failure_rate"].agg(["count", "mean"]).unstack("condition")
    print(pivot.to_string())
