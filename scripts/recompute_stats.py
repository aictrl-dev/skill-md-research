#!/usr/bin/env python3
"""Recompute all statistics cited in the paper for 4 domains, 4 models.

Loads Chart, Dockerfile, SQL, and Terraform data.
Excludes GLM-4.7-Flash.
Prints all values in a format easy to copy into LaTeX.
"""

import pandas as pd
import numpy as np
from scipy import stats
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

STANDARD_DOMAINS = {
    "chart":      ROOT / "domains" / "chart" / "results-v2" / "scores_deep.csv",
    "dockerfile": ROOT / "domains" / "dockerfile" / "results" / "scores.csv",
    "sql":        ROOT / "domains" / "sql-query" / "results" / "scores.csv",
    "terraform":  ROOT / "domains" / "terraform" / "results" / "scores.csv",
}

DOMAIN_LABELS = {
    "chart": "Chart",
    "dockerfile": "Dockerfile",
    "sql": "SQL (dbt)",
    "terraform": "Terraform",
}

MODEL_ORDER = ["haiku", "opus", "glm-4.7", "glm-5"]
MODEL_LABELS = {
    "haiku": "Haiku 4.5",
    "opus": "Opus 4.6",
    "glm-4.7": "GLM-4.7",
    "glm-5": "GLM-5",
}

CLAUDE_MODELS = {"haiku", "opus"}
GLM_MODELS = {"glm-4.7", "glm-5"}
FRONTIER_MODELS = {"opus", "glm-5"}


def load_all() -> pd.DataFrame:
    """Load all 4 domains, compute failure_rate, exclude GLM-4.7-Flash."""
    frames = []
    for domain, path in STANDARD_DOMAINS.items():
        df = pd.read_csv(path)
        df["domain"] = domain
        df["model"] = df["model"].str.replace("zai-coding-plan/", "", regex=False)

        if domain == "chart":
            total = df["pass_count"] + df["fail_count"]
            df["failure_rate"] = np.where(total > 0, df["fail_count"] / total, 1.0)
        else:
            df["failure_rate"] = np.where(
                df["scored_rules"] > 0,
                1 - df["auto_score"] / df["scored_rules"],
                1.0,
            )
        frames.append(df)

    data = pd.concat(frames, ignore_index=True)
    data = data[data["model"] != "glm-4.7-flash"].reset_index(drop=True)
    return data


def cliffs_delta(x, y):
    """Compute Cliff's delta: proportion of (x_i > y_j) - proportion of (x_i < y_j)."""
    nx, ny = len(x), len(y)
    count = 0
    for xi in x:
        for yj in y:
            if xi > yj:
                count += 1
            elif xi < yj:
                count -= 1
    return count / (nx * ny)


def magnitude(d):
    """Cliff's delta magnitude label."""
    ad = abs(d)
    if ad < 0.147:
        return "negl."
    elif ad < 0.33:
        return "small"
    elif ad < 0.474:
        return "medium"
    else:
        return "large"


def print_header(title):
    print()
    print("=" * 70)
    print(f"  {title}")
    print("=" * 70)


def main():
    data = load_all()
    print(f"Total runs: {len(data)}")
    print(f"Domains: {sorted(data['domain'].unique())}")
    print(f"Models: {sorted(data['model'].unique())}")
    print(f"Per-domain:")
    for dom in sorted(data["domain"].unique()):
        n = len(data[data["domain"] == dom])
        print(f"  {dom}: {n} runs")

    # ── RQ1: Skill vs No-skill ───────────────────────────────────────────
    print_header("RQ1: Skill Files vs. No-Skill Baseline")

    no_skill = data[data["condition"] == "none"]
    skill_both = data[data["condition"].isin(["markdown", "pseudocode"])]

    n_no = len(no_skill)
    n_skill = len(skill_both)
    fr_no = no_skill["failure_rate"].mean()
    fr_skill = skill_both["failure_rate"].mean()

    # Mann-Whitney U (one-tailed: no-skill > skill)
    u_stat, p_two = stats.mannwhitneyu(
        no_skill["failure_rate"].values,
        skill_both["failure_rate"].values,
        alternative="greater",
    )
    delta_rq1 = cliffs_delta(
        no_skill["failure_rate"].values,
        skill_both["failure_rate"].values,
    )
    reduction = fr_no / fr_skill if fr_skill > 0 else float("inf")

    print(f"\n  No skill:    N={n_no}, Mean FR = {fr_no*100:.1f}%")
    print(f"  Skill (both): N={n_skill}, Mean FR = {fr_skill*100:.1f}%")
    print(f"  Cliff's delta = {delta_rq1:.3f} ({magnitude(delta_rq1)})")
    print(f"  Mann-Whitney p = {p_two:.4f}" if p_two >= 0.001 else f"  Mann-Whitney p < 0.001")
    print(f"  Reduction multiplier: {reduction:.1f}x")
    print(f"  Effect (pp): {(fr_no - fr_skill)*100:.1f}pp")

    # Per-domain
    print("\n  Per-domain failure rates:")
    print(f"  {'Domain':<15} {'No skill':>10} {'Markdown':>10} {'Pseudocode':>10}")
    for dom in sorted(data["domain"].unique()):
        d = data[data["domain"] == dom]
        fr_none = d[d["condition"] == "none"]["failure_rate"].mean()
        fr_md = d[d["condition"] == "markdown"]["failure_rate"].mean()
        fr_pc = d[d["condition"] == "pseudocode"]["failure_rate"].mean()
        print(f"  {DOMAIN_LABELS[dom]:<15} {fr_none*100:>9.1f}% {fr_md*100:>9.1f}% {fr_pc*100:>9.1f}%")

    # Pooled
    fr_none_all = data[data["condition"] == "none"]["failure_rate"].mean()
    fr_md_all = data[data["condition"] == "markdown"]["failure_rate"].mean()
    fr_pc_all = data[data["condition"] == "pseudocode"]["failure_rate"].mean()
    print(f"  {'Pooled':<15} {fr_none_all*100:>9.1f}% {fr_md_all*100:>9.1f}% {fr_pc_all*100:>9.1f}%")

    # ── RQ2: Pseudocode vs Markdown ──────────────────────────────────────
    print_header("RQ2: Pseudocode vs. Markdown")

    md = data[data["condition"] == "markdown"]
    pc = data[data["condition"] == "pseudocode"]

    fr_md_pool = md["failure_rate"].mean()
    fr_pc_pool = pc["failure_rate"].mean()

    u_rq2, p_rq2 = stats.mannwhitneyu(
        md["failure_rate"].values,
        pc["failure_rate"].values,
        alternative="greater",
    )
    delta_rq2 = cliffs_delta(
        md["failure_rate"].values,
        pc["failure_rate"].values,
    )

    print(f"\n  Pooled:")
    print(f"    MD FR = {fr_md_pool*100:.1f}%, PC FR = {fr_pc_pool*100:.1f}%")
    print(f"    U = {u_rq2:.0f}, p = {p_rq2:.4f}" if p_rq2 >= 0.001 else f"    U = {u_rq2:.0f}, p < 0.001")
    print(f"    Cliff's delta = {delta_rq2:.3f} ({magnitude(delta_rq2)})")

    print(f"\n  Per-domain:")
    print(f"  {'Domain':<15} {'MD FR':>8} {'PC FR':>8} {'delta':>8} {'Mag':>8} {'p':>8}")
    for dom in sorted(data["domain"].unique()):
        d = data[data["domain"] == dom]
        md_d = d[d["condition"] == "markdown"]["failure_rate"].values
        pc_d = d[d["condition"] == "pseudocode"]["failure_rate"].values
        if len(md_d) == 0 or len(pc_d) == 0:
            continue
        fr_md_d = md_d.mean()
        fr_pc_d = pc_d.mean()
        delta_d = cliffs_delta(md_d, pc_d)
        _, p_d = stats.mannwhitneyu(md_d, pc_d, alternative="greater")
        sig = "*" if p_d < 0.05 else ""
        p_str = f"{p_d:.3f}" if p_d >= 0.001 else "< 0.001"
        print(f"  {DOMAIN_LABELS[dom]:<15} {fr_md_d*100:>7.1f}% {fr_pc_d*100:>7.1f}% {delta_d:>+8.3f} {magnitude(delta_d):>8} {p_str:>8}{sig}")

    # ── RQ3: Generalization ──────────────────────────────────────────────
    print_header("RQ3: Generalization Across Models and Families")

    # Cross-domain: mean delta, direction count, binomial test
    deltas_per_domain = []
    for dom in sorted(data["domain"].unique()):
        d = data[data["domain"] == dom]
        md_d = d[d["condition"] == "markdown"]["failure_rate"].values
        pc_d = d[d["condition"] == "pseudocode"]["failure_rate"].values
        if len(md_d) > 0 and len(pc_d) > 0:
            delta_d = cliffs_delta(md_d, pc_d)
            deltas_per_domain.append((dom, delta_d))

    mean_delta = np.mean([d for _, d in deltas_per_domain])
    n_positive = sum(1 for _, d in deltas_per_domain if d > 0)
    n_domains = len(deltas_per_domain)
    binom_p = stats.binomtest(n_positive, n_domains, 0.5).pvalue if n_domains > 0 else 1.0

    print(f"\n  Cross-domain consistency:")
    print(f"    Mean delta across {n_domains} domains: {mean_delta:+.3f} ({magnitude(mean_delta)})")
    print(f"    Positive direction: {n_positive}/{n_domains}")
    print(f"    Binomial test p = {binom_p:.2f}")

    # Cross-family
    print(f"\n  Cross-family analysis (Claude vs GLM):")
    print(f"  {'Family':<10} {'Domain':<15} {'delta':>8} {'p':>10} {'Mag':>8}")

    for family_name, family_models in [("Claude", CLAUDE_MODELS), ("GLM", GLM_MODELS)]:
        for dom in sorted(data["domain"].unique()):
            d = data[(data["domain"] == dom) & (data["model"].isin(family_models))]
            md_d = d[d["condition"] == "markdown"]["failure_rate"].values
            pc_d = d[d["condition"] == "pseudocode"]["failure_rate"].values
            if len(md_d) == 0 or len(pc_d) == 0:
                print(f"  {family_name:<10} {DOMAIN_LABELS[dom]:<15} {'N/A':>8} {'N/A':>10} {'N/A':>8}")
                continue
            delta_d = cliffs_delta(md_d, pc_d)
            try:
                _, p_d = stats.mannwhitneyu(md_d, pc_d, alternative="two-sided")
                p_str = f"{p_d:.3f}" if p_d >= 0.001 else "< 0.001"
            except ValueError:
                p_str = "N/A"
            sig = "*" if p_str != "N/A" and p_d < 0.05 else ""
            print(f"  {family_name:<10} {DOMAIN_LABELS[dom]:<15} {delta_d:>+8.3f} {p_str:>10}{sig} {magnitude(delta_d):>8}")

    # Frontier models
    print(f"\n  Frontier models (Opus 4.6 and GLM-5):")
    print(f"  {'Model':<15} {'MD FR':>8} {'PC FR':>8} {'delta (pp)':>10} {'Rel. reduction':>15}")
    for m in ["opus", "glm-5"]:
        d = data[data["model"] == m]
        md_fr = d[d["condition"] == "markdown"]["failure_rate"].mean()
        pc_fr = d[d["condition"] == "pseudocode"]["failure_rate"].mean()
        delta_pp = (md_fr - pc_fr) * 100
        rel_red = (md_fr - pc_fr) / md_fr * 100 if md_fr > 0 else 0
        delta_c = cliffs_delta(
            d[d["condition"] == "markdown"]["failure_rate"].values,
            d[d["condition"] == "pseudocode"]["failure_rate"].values,
        )
        print(f"  {MODEL_LABELS[m]:<15} {md_fr*100:>7.1f}% {pc_fr*100:>7.1f}% {delta_pp:>+9.1f}pp {rel_red:>14.0f}%")
        print(f"    Cliff's delta = {delta_c:.3f} ({magnitude(delta_c)})")

    # ── RQ4: Token Efficiency ────────────────────────────────────────────
    print_header("RQ4: Token Efficiency (Skill File Line Counts)")

    skill_lines = {
        "chart":      {"markdown": 159, "pseudocode": 219},
        "dockerfile": {"markdown": 214, "pseudocode": 295},
        "sql":        {"markdown": 203, "pseudocode": 235},
        "terraform":  {"markdown": 269, "pseudocode": 349},
    }

    md_lines = [v["markdown"] for v in skill_lines.values()]
    pc_lines = [v["pseudocode"] for v in skill_lines.values()]
    print(f"\n  Average lines across 4 domains:")
    print(f"    Markdown:   {np.mean(md_lines):.0f} lines")
    print(f"    Pseudocode: {np.mean(pc_lines):.0f} lines")

    print(f"\n  Per-domain:")
    for dom in sorted(skill_lines.keys()):
        sl = skill_lines[dom]
        print(f"    {DOMAIN_LABELS[dom]:<15} MD={sl['markdown']:>3}, PC={sl['pseudocode']:>3}")

    # ── RQ5: Variability / Reliability ──────────────────────────────────
    print_header("RQ5: Variability Analysis (Pseudocode Tightens Distributions)")

    from variability_analysis import (
        compute_hdi_comparison,
        compute_levene,
        compute_threshold_rates,
        compute_bootstrap_hdi_of_mean,
    )

    skill_data = data[data["condition"].isin(["markdown", "pseudocode"])].copy()

    # Per-model analysis
    print("\n  --- Per-model analysis ---")

    hdi_model = compute_hdi_comparison(skill_data, "model", "markdown", "pseudocode")
    print("\n  90% HDI width comparison (per model):")
    print(f"  {'Model':<12} {'HDI_MD':>10} {'HDI_PC':>10} {'Narrowing':>10} {'% Change':>10}")
    for _, r in hdi_model.iterrows():
        label = MODEL_LABELS.get(r["group"], r["group"])
        print(f"  {label:<12} {r['hdi_width_a']*100:>9.1f}% {r['hdi_width_b']*100:>9.1f}% {r['narrowing']*100:>+9.1f}pp {r['pct_change']:>9.0f}%")

    thresh_model = compute_threshold_rates(skill_data, "model", "markdown", "pseudocode", threshold=0.10)
    print(f"\n  P(FR < 10%) per model:")
    print(f"  {'Model':<12} {'P(MD)':>8} {'P(PC)':>8} {'Diff':>8}")
    for _, r in thresh_model.iterrows():
        label = MODEL_LABELS.get(r["group"], r["group"])
        p_md = r[f"P(FR<0.1)_markdown"]
        p_pc = r[f"P(FR<0.1)_pseudocode"]
        diff = r["difference"]
        print(f"  {label:<12} {p_md*100:>7.1f}% {p_pc*100:>7.1f}% {diff*100:>+7.1f}pp")

    levene_model = compute_levene(skill_data, "model", "markdown", "pseudocode")
    print(f"\n  Levene's test (per model):")
    print(f"  {'Model':<12} {'F':>8} {'p':>10} {'Var ratio':>10}")
    for _, r in levene_model.iterrows():
        label = MODEL_LABELS.get(r["group"], r["group"])
        p_str = f"{r['p']:.3f}" if r["p"] >= 0.001 else "< 0.001"
        sig = "*" if r["p"] < 0.05 else ""
        print(f"  {label:<12} {r['F']:>8.2f} {p_str:>10}{sig} {r['var_ratio']:>10.2f}")

    boot_model = compute_bootstrap_hdi_of_mean(skill_data, "model", "markdown", "pseudocode")
    print(f"\n  Bootstrap 95% HDI of mean (per model):")
    print(f"  {'Model':<12} {'MD [lo, hi]':>20} {'PC [lo, hi]':>20} {'Width narrow':>12}")
    for _, r in boot_model.iterrows():
        label = MODEL_LABELS.get(r["group"], r["group"])
        md_range = f"[{r['hdi_lo_a']*100:.1f}, {r['hdi_hi_a']*100:.1f}]"
        pc_range = f"[{r['hdi_lo_b']*100:.1f}, {r['hdi_hi_b']*100:.1f}]"
        print(f"  {label:<12} {md_range:>20} {pc_range:>20} {r['width_narrowing']*100:>+11.1f}pp")

    # Per-domain analysis
    print("\n  --- Per-domain analysis ---")

    hdi_domain = compute_hdi_comparison(skill_data, "domain", "markdown", "pseudocode")
    print("\n  90% HDI width comparison (per domain):")
    print(f"  {'Domain':<15} {'HDI_MD':>10} {'HDI_PC':>10} {'Narrowing':>10} {'% Change':>10}")
    for _, r in hdi_domain.iterrows():
        label = DOMAIN_LABELS.get(r["group"], r["group"])
        print(f"  {label:<15} {r['hdi_width_a']*100:>9.1f}% {r['hdi_width_b']*100:>9.1f}% {r['narrowing']*100:>+9.1f}pp {r['pct_change']:>9.0f}%")

    levene_domain = compute_levene(skill_data, "domain", "markdown", "pseudocode")
    print(f"\n  Levene's test (per domain):")
    print(f"  {'Domain':<15} {'F':>8} {'p':>10} {'Var ratio':>10}")
    for _, r in levene_domain.iterrows():
        label = DOMAIN_LABELS.get(r["group"], r["group"])
        p_str = f"{r['p']:.3f}" if r["p"] >= 0.001 else "< 0.001"
        sig = "*" if r["p"] < 0.05 else ""
        print(f"  {label:<15} {r['F']:>8.2f} {p_str:>10}{sig} {r['var_ratio']:>10.2f}")

    # Pooled Levene
    vals_md = skill_data[skill_data["condition"] == "markdown"]["failure_rate"].values
    vals_pc = skill_data[skill_data["condition"] == "pseudocode"]["failure_rate"].values
    f_pooled, p_pooled = stats.levene(vals_md, vals_pc, center="median")
    var_md = np.var(vals_md, ddof=1)
    var_pc = np.var(vals_pc, ddof=1)
    p_pooled_str = f"{p_pooled:.3f}" if p_pooled >= 0.001 else "< 0.001"
    sig_pooled = "*" if p_pooled < 0.05 else ""
    print(f"\n  Pooled Levene's test:")
    print(f"    F = {f_pooled:.2f}, p = {p_pooled_str}{sig_pooled}")
    print(f"    Var(MD) = {var_md:.4f}, Var(PC) = {var_pc:.4f}, ratio = {var_md/var_pc:.2f}")

    # Summary
    n_narrower = sum(1 for _, r in hdi_model.iterrows() if r["narrowing"] > 0)
    print(f"\n  KEY RQ5 NUMBERS:")
    print(f"    Models where PC has narrower 90% HDI: {n_narrower}/{len(hdi_model)}")
    print(f"    Pooled Levene F = {f_pooled:.2f}, p = {p_pooled_str}")
    print(f"    Pooled variance ratio (MD/PC) = {var_md/var_pc:.2f}")

    # ── Summary for LaTeX ────────────────────────────────────────────────
    print_header("Summary for LaTeX")

    total_runs = len(data)
    print(f"\n  Total runs: {total_runs}")
    print(f"  Domains: 4")
    print(f"  Models: 4")
    print(f"  Families: 2")

    # Per-model failure rates
    print(f"\n  Per-model pooled failure rates:")
    for m in MODEL_ORDER:
        d = data[data["model"] == m]
        for c in ["none", "markdown", "pseudocode"]:
            fr = d[d["condition"] == c]["failure_rate"].mean()
            print(f"    {MODEL_LABELS[m]:>12} {c:>12}: {fr*100:.1f}%")

    # All extraction failures
    print(f"\n  Per-domain rule counts:")
    rule_counts = {"chart": 15, "dockerfile": 13, "sql": 12, "terraform": 13}
    for dom in sorted(rule_counts.keys()):
        print(f"    {DOMAIN_LABELS[dom]:<15}: {rule_counts[dom]} rules")

    # Key paper numbers
    print(f"\n  KEY NUMBERS:")
    print(f"    RQ1: No-skill FR = {fr_no*100:.1f}%, Skill FR = {fr_skill*100:.1f}%")
    print(f"    RQ1: delta = {delta_rq1:.3f}, reduction = {reduction:.1f}x")
    print(f"    RQ2: MD FR = {fr_md_pool*100:.1f}%, PC FR = {fr_pc_pool*100:.1f}%")
    print(f"    RQ2: U = {u_rq2:.0f}, p = {p_rq2:.4f}, delta = {delta_rq2:.3f}")
    rel_pc = (fr_md_pool - fr_pc_pool) / fr_md_pool * 100 if fr_md_pool > 0 else 0
    print(f"    RQ2: Relative reduction = {rel_pc:.0f}%")

    # Skill-presence effect vs format effect
    skill_effect = fr_no - fr_skill
    format_effect = fr_md_pool - fr_pc_pool
    ratio = skill_effect / format_effect if format_effect > 0 else float("inf")
    print(f"    Skill-presence effect: {skill_effect*100:.1f}pp")
    print(f"    Format effect: {format_effect*100:.1f}pp")
    print(f"    Ratio: {ratio:.0f}x")


if __name__ == "__main__":
    main()
