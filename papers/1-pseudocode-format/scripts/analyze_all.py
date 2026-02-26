#!/usr/bin/env python3
"""
Cross-domain analysis: aggregate results from all domain experiments.

Reads scores.csv from each domain's results/ directory, combines them,
and runs statistical tests to support the cross-domain generalization claim.

Usage:
    python analyze_all.py                          # Auto-discover domains
    python analyze_all.py --domains commit-message openapi-spec dockerfile
    python analyze_all.py --include-chart           # Include original chart domain

Dependencies:
    pip install pandas scipy matplotlib seaborn
"""

import argparse
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from scipy import stats

SCRIPT_DIR = Path(__file__).parent
DOMAINS_DIR = SCRIPT_DIR / "domains"
CHART_RESULTS = SCRIPT_DIR / "results" / "scores.csv"
OUTPUT_DIR = SCRIPT_DIR / "results" / "cross-domain"
OUTPUT_CSV = OUTPUT_DIR / "combined_scores.csv"
OUTPUT_MD = OUTPUT_DIR / "cross-domain-analysis.md"
CHARTS_DIR = OUTPUT_DIR / "charts"


# ─── Cliff's Delta ──────────────────────────────────────────────────────────

def cliffs_delta(x, y) -> tuple[float, str]:
    """Compute Cliff's delta effect size (non-parametric)."""
    n_x, n_y = len(x), len(y)
    if n_x == 0 or n_y == 0:
        return 0.0, "undefined"

    more = 0
    less = 0
    for xi in x:
        for yi in y:
            if xi > yi:
                more += 1
            elif xi < yi:
                less += 1

    delta = (more - less) / (n_x * n_y)

    abs_d = abs(delta)
    if abs_d < 0.147:
        magnitude = "negligible"
    elif abs_d < 0.33:
        magnitude = "small"
    elif abs_d < 0.474:
        magnitude = "medium"
    else:
        magnitude = "large"

    return delta, magnitude


# ─── Data Loading ───────────────────────────────────────────────────────────

def discover_domains() -> list[str]:
    """Find all domain directories that have a results/scores.csv."""
    domains = []
    if DOMAINS_DIR.exists():
        for d in sorted(DOMAINS_DIR.iterdir()):
            if d.is_dir() and (d / "results" / "scores.csv").exists():
                domains.append(d.name)
    return domains


def load_domain_scores(domain: str) -> pd.DataFrame | None:
    """Load scores.csv from a domain's results directory."""
    csv_path = DOMAINS_DIR / domain / "results" / "scores.csv"
    if not csv_path.exists():
        print(f"  WARNING: No scores.csv found for domain '{domain}' at {csv_path}")
        return None

    df = pd.read_csv(csv_path)
    df["domain"] = domain
    return df


def load_chart_scores() -> pd.DataFrame | None:
    """Load scores from the original chart domain."""
    if not CHART_RESULTS.exists():
        print(f"  WARNING: No chart scores found at {CHART_RESULTS}")
        return None

    df = pd.read_csv(CHART_RESULTS)
    df["domain"] = "chart"
    return df


def load_all_scores(domains: list[str], include_chart: bool) -> pd.DataFrame:
    """Load and combine scores from all specified domains."""
    frames = []

    if include_chart:
        chart_df = load_chart_scores()
        if chart_df is not None:
            frames.append(chart_df)
            print(f"  Loaded chart domain: {len(chart_df)} rows")

    for domain in domains:
        df = load_domain_scores(domain)
        if df is not None:
            frames.append(df)
            print(f"  Loaded {domain}: {len(df)} rows")

    if not frames:
        print("ERROR: No data loaded from any domain.")
        sys.exit(1)

    combined = pd.concat(frames, ignore_index=True)

    # Normalize auto_score to [0, 1] using scored_rules (excludes manual-only rules)
    if "scored_rules" in combined.columns:
        # Use per-row scored_rules for precise normalization
        combined["auto_score_norm"] = combined.apply(
            lambda r: r["auto_score"] / r["scored_rules"] if r.get("scored_rules", 0) > 0 else 0,
            axis=1,
        )
    else:
        # Fallback: count rule_*_pass columns per domain (legacy CSVs without scored_rules)
        for domain in combined["domain"].unique():
            mask = combined["domain"] == domain
            rule_cols = [c for c in combined.columns if c.endswith("_pass") and combined.loc[mask, c].notna().any()]
            max_score = len(rule_cols)
            if max_score > 0:
                combined.loc[mask, "auto_score_norm"] = combined.loc[mask, "auto_score"] / max_score
            else:
                combined.loc[mask, "auto_score_norm"] = 0

    # Failure rate = proportion of rules that failed (1 - compliance rate)
    combined["failure_rate"] = 1.0 - combined["auto_score_norm"]

    return combined


# ─── Descriptive Stats ──────────────────────────────────────────────────────

def descriptive_stats(df: pd.DataFrame) -> str:
    """Cross-domain descriptive statistics."""
    lines = ["## Descriptive Statistics\n"]

    # Overall by condition
    lines.append("### Normalized Auto-Score by Condition (all domains)\n")
    lines.append("| Condition | N | Mean | Std | Median |")
    lines.append("|-----------|---|------|-----|--------|")
    for cond in ["none", "markdown", "pseudocode"]:
        subset = df[df["condition"] == cond]["auto_score_norm"]
        if len(subset) > 0:
            lines.append(
                f"| {cond} | {len(subset)} | {subset.mean():.3f} | {subset.std():.3f} "
                f"| {subset.median():.3f} |"
            )
    lines.append("")

    # By domain x condition
    lines.append("### Normalized Auto-Score by Domain x Condition\n")
    lines.append("| Domain | none | markdown | pseudocode |")
    lines.append("|--------|------|----------|------------|")
    for domain in sorted(df["domain"].unique()):
        row = f"| {domain} |"
        for cond in ["none", "markdown", "pseudocode"]:
            subset = df[(df["domain"] == domain) & (df["condition"] == cond)]["auto_score_norm"]
            if len(subset) > 0:
                row += f" {subset.mean():.3f} (n={len(subset)}) |"
            else:
                row += " - |"
        lines.append(row)
    lines.append("")

    # By domain x condition (raw auto_score)
    lines.append("### Raw Auto-Score by Domain x Condition\n")
    lines.append("| Domain | Max Rules | none | markdown | pseudocode |")
    lines.append("|--------|-----------|------|----------|------------|")
    for domain in sorted(df["domain"].unique()):
        domain_data = df[df["domain"] == domain]
        # Use scored_rules if available (handles domains with _rate columns like SQL)
        if "scored_rules" in domain_data.columns and domain_data["scored_rules"].notna().any():
            max_rules = int(domain_data["scored_rules"].max())
        else:
            rule_cols = [c for c in domain_data.columns if c.endswith("_pass") and domain_data[c].notna().any()]
            max_rules = len(rule_cols)
        row = f"| {domain} | {max_rules} |"
        for cond in ["none", "markdown", "pseudocode"]:
            subset = domain_data[domain_data["condition"] == cond]["auto_score"]
            if len(subset) > 0:
                row += f" {subset.mean():.2f}/{max_rules} |"
            else:
                row += " - |"
        lines.append(row)
    lines.append("")

    # Failure Rate by Domain x Condition (practical impact framing)
    lines.append("### Failure Rate by Domain x Condition\n")
    lines.append("*Failure rate = % of rules violated. Lower is better. "
                 "Reduction shows how many fewer defects need manual rework.*\n")
    lines.append("| Domain | none | markdown | pseudocode | Reduction (none→ps) |")
    lines.append("|--------|------|----------|------------|---------------------|")
    for domain in sorted(df["domain"].unique()):
        domain_data = df[df["domain"] == domain]
        rates = {}
        for cond in ["none", "markdown", "pseudocode"]:
            subset = domain_data[domain_data["condition"] == cond]["failure_rate"]
            if len(subset) > 0:
                rates[cond] = subset.mean()

        row = f"| {domain} |"
        for cond in ["none", "markdown", "pseudocode"]:
            if cond in rates:
                row += f" {rates[cond]:.1%} |"
            else:
                row += " - |"

        # Reduction factor: none / pseudocode
        if "none" in rates and "pseudocode" in rates and rates["pseudocode"] > 0:
            reduction = rates["none"] / rates["pseudocode"]
            row += f" {reduction:.1f}x |"
        elif "none" in rates and "pseudocode" in rates and rates["pseudocode"] == 0:
            row += " ∞ |"
        else:
            row += " - |"
        lines.append(row)

    # Pooled failure rate across all domains
    pooled = {}
    for cond in ["none", "markdown", "pseudocode"]:
        subset = df[df["condition"] == cond]["failure_rate"]
        if len(subset) > 0:
            pooled[cond] = subset.mean()
    if pooled:
        row = "| **All (pooled)** |"
        for cond in ["none", "markdown", "pseudocode"]:
            if cond in pooled:
                row += f" **{pooled[cond]:.1%}** |"
            else:
                row += " - |"
        if "none" in pooled and "pseudocode" in pooled and pooled["pseudocode"] > 0:
            row += f" **{pooled['none'] / pooled['pseudocode']:.1f}x** |"
        else:
            row += " - |"
        lines.append(row)
    lines.append("")

    # Failure Rate breakdown by Model x Domain (markdown vs pseudocode only)
    KEY_MODELS = {"opus": "Opus", "zai-coding-plan/glm-5": "GLM-5"}
    model_data = df[(df["model"].isin(KEY_MODELS)) & (df["condition"].isin(["markdown", "pseudocode"]))]
    if len(model_data) > 0:
        lines.append("### Failure Rate by Model x Domain (Markdown vs Pseudocode)\n")
        lines.append("*Focuses on the two primary models. "
                     "Δ = markdown − pseudocode (positive = pseudocode is better).*\n")
        lines.append("| Model | Domain | markdown | pseudocode | Δ | n(md) | n(ps) |")
        lines.append("|-------|--------|----------|------------|---|-------|-------|")
        for model_id in sorted(KEY_MODELS.keys()):
            model_label = KEY_MODELS[model_id]
            for domain in sorted(df["domain"].unique()):
                md_subset = model_data[
                    (model_data["model"] == model_id)
                    & (model_data["domain"] == domain)
                    & (model_data["condition"] == "markdown")
                ]["failure_rate"]
                ps_subset = model_data[
                    (model_data["model"] == model_id)
                    & (model_data["domain"] == domain)
                    & (model_data["condition"] == "pseudocode")
                ]["failure_rate"]
                if len(md_subset) == 0 and len(ps_subset) == 0:
                    continue
                md_rate = md_subset.mean() if len(md_subset) > 0 else float("nan")
                ps_rate = ps_subset.mean() if len(ps_subset) > 0 else float("nan")
                delta = md_rate - ps_rate if not (pd.isna(md_rate) or pd.isna(ps_rate)) else float("nan")
                md_str = f"{md_rate:.1%}" if not pd.isna(md_rate) else "-"
                ps_str = f"{ps_rate:.1%}" if not pd.isna(ps_rate) else "-"
                delta_str = f"{delta:+.1%}" if not pd.isna(delta) else "-"
                lines.append(
                    f"| {model_label} | {domain} | {md_str} | {ps_str} "
                    f"| {delta_str} | {len(md_subset)} | {len(ps_subset)} |"
                )
            # Per-model pooled row
            md_all = model_data[
                (model_data["model"] == model_id) & (model_data["condition"] == "markdown")
            ]["failure_rate"]
            ps_all = model_data[
                (model_data["model"] == model_id) & (model_data["condition"] == "pseudocode")
            ]["failure_rate"]
            if len(md_all) > 0 and len(ps_all) > 0:
                delta_all = md_all.mean() - ps_all.mean()
                lines.append(
                    f"| **{model_label} (pooled)** | **all** | **{md_all.mean():.1%}** "
                    f"| **{ps_all.mean():.1%}** | **{delta_all:+.1%}** "
                    f"| **{len(md_all)}** | **{len(ps_all)}** |"
                )
        lines.append("")

    # By domain x condition (outcome_score if present)
    if "outcome_score" in df.columns:
        lines.append("### Outcome Score by Domain x Condition\n")
        lines.append("| Domain | Outcome Checks | none | markdown | pseudocode |")
        lines.append("|--------|---------------|------|----------|------------|")
        for domain in sorted(df["domain"].unique()):
            domain_data = df[df["domain"] == domain]
            outcome_cols = [c for c in domain_data.columns
                           if c.startswith("outcome_") and c.endswith("_pass")
                           and domain_data[c].notna().any()]
            n_outcomes = len(outcome_cols)
            row = f"| {domain} | {n_outcomes} |"
            for cond in ["none", "markdown", "pseudocode"]:
                subset = domain_data[domain_data["condition"] == cond]["outcome_score"]
                if len(subset) > 0:
                    row += f" {subset.mean():.2f}/{n_outcomes} |"
                else:
                    row += " - |"
            lines.append(row)
        lines.append("")

    return "\n".join(lines)


# ─── Statistical Tests ──────────────────────────────────────────────────────

def statistical_tests(df: pd.DataFrame) -> str:
    """Cross-domain hypothesis tests."""
    lines = ["## Statistical Tests\n"]

    # Use normalized scores for cross-domain comparisons
    valid = df.copy()

    # ── H1: Overall Harness Effect (Skills vs No-Skill) ──
    lines.append("### H1: Harness Effect — Skills vs No-Skill (all domains pooled)\n")
    skill_scores = valid[valid["condition"].isin(["markdown", "pseudocode"])]["auto_score_norm"]
    none_scores = valid[valid["condition"] == "none"]["auto_score_norm"]

    if len(skill_scores) > 0 and len(none_scores) > 0:
        u_stat, p_value = stats.mannwhitneyu(skill_scores, none_scores, alternative="greater")
        delta, magnitude = cliffs_delta(skill_scores.tolist(), none_scores.tolist())
        lines.append(f"- Mann-Whitney U = {u_stat:.1f}, p = {p_value:.6f}")
        lines.append(f"- Cliff's delta = {delta:.3f} ({magnitude})")
        lines.append(f"- Skill mean = {skill_scores.mean():.3f}, No-skill mean = {none_scores.mean():.3f}")
        sig = "**SIGNIFICANT**" if p_value < 0.05 else "not significant"
        lines.append(f"- Result: {sig} (alpha=0.05, one-tailed)\n")
    else:
        lines.append("- Insufficient data\n")

    # ── H2: Overall Format Effect (Pseudocode vs Markdown) ──
    lines.append("### H2: Format Effect — Pseudocode vs Markdown (all domains pooled)\n")
    pseudo_scores = valid[valid["condition"] == "pseudocode"]["auto_score_norm"]
    md_scores = valid[valid["condition"] == "markdown"]["auto_score_norm"]

    if len(pseudo_scores) > 0 and len(md_scores) > 0:
        u_stat, p_value = stats.mannwhitneyu(pseudo_scores, md_scores, alternative="greater")
        delta, magnitude = cliffs_delta(pseudo_scores.tolist(), md_scores.tolist())
        lines.append(f"- Mann-Whitney U = {u_stat:.1f}, p = {p_value:.6f}")
        lines.append(f"- Cliff's delta = {delta:.3f} ({magnitude})")
        lines.append(f"- Pseudocode mean = {pseudo_scores.mean():.3f}, Markdown mean = {md_scores.mean():.3f}")
        sig = "**SIGNIFICANT**" if p_value < 0.05 else "not significant"
        lines.append(f"- Result: {sig} (alpha=0.05, one-tailed)\n")
    else:
        lines.append("- Insufficient data\n")

    # ── H3: Per-Domain Format Effect ──
    lines.append("### H3: Per-Domain Format Effect (Pseudocode vs Markdown)\n")
    lines.append("| Domain | U | p-value | Cliff's d | Magnitude | Pseudo Mean | MD Mean |")
    lines.append("|--------|---|---------|-----------|-----------|-------------|---------|")

    for domain in sorted(valid["domain"].unique()):
        domain_data = valid[valid["domain"] == domain]
        pseudo = domain_data[domain_data["condition"] == "pseudocode"]["auto_score_norm"]
        md = domain_data[domain_data["condition"] == "markdown"]["auto_score_norm"]

        if len(pseudo) > 0 and len(md) > 0:
            u_stat, p_value = stats.mannwhitneyu(pseudo, md, alternative="greater")
            delta, magnitude = cliffs_delta(pseudo.tolist(), md.tolist())
            sig_marker = "*" if p_value < 0.05 else ""
            lines.append(
                f"| {domain}{sig_marker} | {u_stat:.0f} | {p_value:.4f} | {delta:.3f} "
                f"| {magnitude} | {pseudo.mean():.3f} | {md.mean():.3f} |"
            )
        else:
            lines.append(f"| {domain} | - | - | - | - | - | - |")

    lines.append("\n*\\* p < 0.05*\n")

    # ── H4: Cross-Model Consistency (per domain) ──
    lines.append("### H4: Cross-Model Consistency\n")

    valid["family"] = valid["model"].apply(
        lambda m: "claude" if m in ("haiku", "opus") else "glm"
    )

    for domain in sorted(valid["domain"].unique()):
        lines.append(f"\n**{domain}**:\n")
        domain_data = valid[valid["domain"] == domain]
        for family in sorted(domain_data["family"].unique()):
            fam_data = domain_data[domain_data["family"] == family]
            pseudo = fam_data[fam_data["condition"] == "pseudocode"]["auto_score_norm"]
            md = fam_data[fam_data["condition"] == "markdown"]["auto_score_norm"]

            if len(pseudo) > 0 and len(md) > 0:
                u_stat, p_value = stats.mannwhitneyu(pseudo, md, alternative="two-sided")
                delta, magnitude = cliffs_delta(pseudo.tolist(), md.tolist())
                lines.append(
                    f"- {family.upper()}: U={u_stat:.1f}, p={p_value:.4f}, "
                    f"delta={delta:.3f} ({magnitude})"
                )
            else:
                lines.append(f"- {family.upper()}: Insufficient data")

    lines.append("")

    # ── Generalization Metric: Sign Consistency ──
    lines.append("### Generalization: Effect Direction Consistency\n")

    domain_deltas = []
    for domain in sorted(valid["domain"].unique()):
        domain_data = valid[valid["domain"] == domain]
        pseudo = domain_data[domain_data["condition"] == "pseudocode"]["auto_score_norm"]
        md = domain_data[domain_data["condition"] == "markdown"]["auto_score_norm"]
        if len(pseudo) > 0 and len(md) > 0:
            delta, magnitude = cliffs_delta(pseudo.tolist(), md.tolist())
            domain_deltas.append({"domain": domain, "delta": delta, "magnitude": magnitude})

    if domain_deltas:
        positive = sum(1 for d in domain_deltas if d["delta"] > 0)
        total_d = len(domain_deltas)
        lines.append(f"- Domains with positive effect (pseudocode > markdown): {positive}/{total_d}")

        # Binomial test: is positive proportion significantly above 0.5?
        if total_d >= 3:
            binom_p = stats.binomtest(positive, total_d, 0.5, alternative="greater").pvalue
            lines.append(f"- Binomial test (H0: random direction): p = {binom_p:.4f}")

        # Mean effect size across domains
        mean_delta = sum(d["delta"] for d in domain_deltas) / total_d
        lines.append(f"- Mean Cliff's delta across domains: {mean_delta:.3f}")

        for d in domain_deltas:
            direction = "+" if d["delta"] > 0 else "-"
            lines.append(f"  - {d['domain']}: {direction}{abs(d['delta']):.3f} ({d['magnitude']})")
    lines.append("")

    return "\n".join(lines)


# ─── Charts ─────────────────────────────────────────────────────────────────

def generate_charts(df: pd.DataFrame) -> list[str]:
    """Generate cross-domain summary charts."""
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    chart_files = []

    sns.set_theme(style="whitegrid", font_scale=1.1)
    palette = {"none": "#5D666F", "markdown": "#1A476F", "pseudocode": "#C74634"}

    # 1. Faceted boxplot: normalized score by condition, faceted by domain
    domains = sorted(df["domain"].unique())
    n_domains = len(domains)

    fig, axes = plt.subplots(1, n_domains, figsize=(5 * n_domains, 5), sharey=True)
    if n_domains == 1:
        axes = [axes]

    for ax, domain in zip(axes, domains):
        domain_data = df[df["domain"] == domain]
        sns.boxplot(
            data=domain_data, x="condition", y="auto_score_norm",
            order=["none", "markdown", "pseudocode"],
            palette=palette, ax=ax
        )
        ax.set_title(domain)
        ax.set_xlabel("")
        ax.set_ylim(-0.05, 1.1)
        if ax != axes[0]:
            ax.set_ylabel("")
        else:
            ax.set_ylabel("Normalized Auto-Score")

    fig.suptitle("Normalized Auto-Score by Condition (per domain)", fontsize=14, y=1.02)
    fig.tight_layout()
    fname = "faceted_boxplot_domains.png"
    fig.savefig(CHARTS_DIR / fname, dpi=150, bbox_inches="tight")
    plt.close(fig)
    chart_files.append(fname)

    # 2. Heatmap: mean normalized score by domain x condition
    pivot = df.pivot_table(
        values="auto_score_norm", index="domain", columns="condition", aggfunc="mean"
    )
    col_order = [c for c in ["none", "markdown", "pseudocode"] if c in pivot.columns]
    pivot = pivot[col_order]

    fig, ax = plt.subplots(figsize=(8, max(4, n_domains * 1.2)))
    sns.heatmap(
        pivot, annot=True, fmt=".3f", cmap="YlOrRd_r",
        vmin=0, vmax=1, ax=ax, linewidths=0.5
    )
    ax.set_title("Mean Normalized Auto-Score: Domain x Condition")
    fig.tight_layout()
    fname = "heatmap_domain_condition.png"
    fig.savefig(CHARTS_DIR / fname, dpi=150)
    plt.close(fig)
    chart_files.append(fname)

    # 3. Forest plot: Cliff's delta per domain (pseudocode vs markdown)
    domain_effects = []
    for domain in sorted(df["domain"].unique()):
        domain_data = df[df["domain"] == domain]
        pseudo = domain_data[domain_data["condition"] == "pseudocode"]["auto_score_norm"]
        md = domain_data[domain_data["condition"] == "markdown"]["auto_score_norm"]
        if len(pseudo) > 0 and len(md) > 0:
            delta, magnitude = cliffs_delta(pseudo.tolist(), md.tolist())
            domain_effects.append({"domain": domain, "delta": delta})

    if domain_effects:
        fig, ax = plt.subplots(figsize=(8, max(3, len(domain_effects) * 0.8)))
        domains_sorted = sorted(domain_effects, key=lambda x: x["delta"])
        y_positions = range(len(domains_sorted))
        deltas = [d["delta"] for d in domains_sorted]
        labels = [d["domain"] for d in domains_sorted]

        colors = ["#C74634" if d > 0 else "#1A476F" for d in deltas]
        ax.barh(y_positions, deltas, color=colors, height=0.6, alpha=0.8)
        ax.set_yticks(y_positions)
        ax.set_yticklabels(labels)
        ax.axvline(x=0, color="black", linewidth=0.8, linestyle="--")
        ax.set_xlabel("Cliff's Delta (Pseudocode vs Markdown)")
        ax.set_title("Effect Size by Domain")

        # Add threshold lines
        for threshold, label in [(0.147, "small"), (0.33, "medium"), (0.474, "large")]:
            ax.axvline(x=threshold, color="#D0D0D0", linewidth=0.5, linestyle=":")
            ax.axvline(x=-threshold, color="#D0D0D0", linewidth=0.5, linestyle=":")

        fig.tight_layout()
        fname = "forest_plot_effect_sizes.png"
        fig.savefig(CHARTS_DIR / fname, dpi=150)
        plt.close(fig)
        chart_files.append(fname)

    # 4. Overall pooled boxplot
    fig, ax = plt.subplots(figsize=(8, 5))
    sns.boxplot(
        data=df, x="condition", y="auto_score_norm",
        order=["none", "markdown", "pseudocode"],
        palette=palette, ax=ax
    )
    ax.set_title("Normalized Auto-Score by Condition (all domains pooled)")
    ax.set_xlabel("Condition")
    ax.set_ylabel("Normalized Auto-Score")
    ax.set_ylim(-0.05, 1.1)
    fig.tight_layout()
    fname = "pooled_boxplot.png"
    fig.savefig(CHARTS_DIR / fname, dpi=150)
    plt.close(fig)
    chart_files.append(fname)

    return chart_files


# ─── Report ─────────────────────────────────────────────────────────────────

def generate_report(df: pd.DataFrame, chart_files: list[str]) -> str:
    """Generate cross-domain markdown report."""
    domains = sorted(df["domain"].unique())
    lines = [
        "# Cross-Domain Experiment Analysis\n",
        f"Generated from {len(df)} runs across {len(domains)} domains: {', '.join(domains)}.\n",
        f"This report supports the **cross-domain generalization** claim by showing ",
        f"that the pseudocode vs markdown effect holds across multiple output modalities.\n",
    ]

    lines.append(descriptive_stats(df))
    lines.append(statistical_tests(df))

    if chart_files:
        lines.append("## Charts\n")
        for fname in chart_files:
            lines.append(f"![{fname}](charts/{fname})\n")

    return "\n".join(lines)


# ─── Main ───────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Cross-domain experiment analysis")
    parser.add_argument(
        "--domains", nargs="+",
        help="Domains to include (default: auto-discover)"
    )
    parser.add_argument(
        "--include-chart", action="store_true",
        help="Include original chart domain results"
    )
    args = parser.parse_args()

    domains = args.domains or discover_domains()

    if not domains and not args.include_chart:
        print("No domains found. Run domain evaluators first to generate scores.csv files.")
        print(f"Looked in: {DOMAINS_DIR}")
        sys.exit(1)

    print(f"Loading scores from {len(domains)} domain(s)...")
    if args.include_chart:
        print("  (including chart domain)")

    df = load_all_scores(domains, args.include_chart)
    print(f"\nCombined dataset: {len(df)} rows, {df['domain'].nunique()} domains")

    # Save combined CSV
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_CSV, index=False)
    print(f"Combined scores saved to {OUTPUT_CSV}")

    # Generate charts
    chart_files = generate_charts(df)
    print(f"Generated {len(chart_files)} charts in {CHARTS_DIR}/")

    # Generate report
    report = generate_report(df, chart_files)
    OUTPUT_MD.write_text(report)
    print(f"Cross-domain analysis written to {OUTPUT_MD}")


if __name__ == "__main__":
    main()
