#!/usr/bin/env python3
"""
Statistical analysis of experiment results.

Reads scores.csv from evaluate.py, computes descriptive stats,
runs statistical tests, and generates summary charts + markdown report.

Usage:
    python analyze.py                      # Default: reads results/scores.csv
    python analyze.py results/scores.csv   # Explicit path

Dependencies:
    pip install pandas scipy matplotlib seaborn
"""

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from scipy import stats

SCRIPT_DIR = Path(__file__).parent
RESULTS_DIR = SCRIPT_DIR / "results"
DEFAULT_CSV = RESULTS_DIR / "scores.csv"
OUTPUT_MD = RESULTS_DIR / "analysis.md"
CHARTS_DIR = RESULTS_DIR / "charts"


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

    # Interpret magnitude
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


# ─── Descriptive Stats ───────────────────────────────────────────────────────

def descriptive_stats(df: pd.DataFrame) -> str:
    """Compute descriptive statistics by condition and model."""
    lines = ["## Descriptive Statistics\n"]

    # By condition
    lines.append("### Auto-Score by Condition\n")
    lines.append("| Condition | N | Mean | Std | Median | Min | Max |")
    lines.append("|-----------|---|------|-----|--------|-----|-----|")
    for cond in sorted(df["condition"].unique()):
        subset = df[df["condition"] == cond]["auto_score"]
        lines.append(
            f"| {cond} | {len(subset)} | {subset.mean():.2f} | {subset.std():.2f} "
            f"| {subset.median():.1f} | {subset.min()} | {subset.max()} |"
        )
    lines.append("")

    # By condition x model
    lines.append("### Auto-Score by Condition x Model\n")
    lines.append("| Model | none | markdown | pseudocode |")
    lines.append("|-------|------|----------|------------|")
    for model in sorted(df["model"].unique()):
        row = f"| {model} |"
        for cond in ["none", "markdown", "pseudocode"]:
            subset = df[(df["model"] == model) & (df["condition"] == cond)]["auto_score"]
            if len(subset) > 0:
                row += f" {subset.mean():.2f} (n={len(subset)}) |"
            else:
                row += " - |"
        lines.append(row)
    lines.append("")

    # JSON validity
    lines.append("### JSON Validity\n")
    lines.append("| Condition | Valid | Invalid | Rate |")
    lines.append("|-----------|-------|---------|------|")
    for cond in sorted(df["condition"].unique()):
        subset = df[df["condition"] == cond]
        valid = subset["json_valid"].sum()
        total = len(subset)
        rate = valid / total * 100 if total > 0 else 0
        lines.append(f"| {cond} | {valid} | {total - valid} | {rate:.0f}% |")
    lines.append("")

    return "\n".join(lines)


# ─── Statistical Tests ───────────────────────────────────────────────────────

def statistical_tests(df: pd.DataFrame) -> str:
    """Run hypothesis tests."""
    lines = ["## Statistical Tests\n"]

    # Only use runs with valid JSON
    valid = df[df["json_valid"]].copy()

    if len(valid) == 0:
        lines.append("No valid results to analyze.\n")
        return "\n".join(lines)

    # H1: Skills vs No-skill (harness effect)
    lines.append("### H1: Harness Effect (Skills vs No-Skill)\n")
    skill_scores = valid[valid["condition"].isin(["markdown", "pseudocode"])]["auto_score"]
    none_scores = valid[valid["condition"] == "none"]["auto_score"]

    if len(skill_scores) > 0 and len(none_scores) > 0:
        u_stat, p_value = stats.mannwhitneyu(
            skill_scores, none_scores, alternative="greater"
        )
        delta, magnitude = cliffs_delta(skill_scores.tolist(), none_scores.tolist())
        lines.append(f"- Mann-Whitney U = {u_stat:.1f}, p = {p_value:.4f}")
        lines.append(f"- Cliff's delta = {delta:.3f} ({magnitude})")
        lines.append(f"- Skill mean = {skill_scores.mean():.2f}, No-skill mean = {none_scores.mean():.2f}")
        sig = "significant" if p_value < 0.05 else "not significant"
        lines.append(f"- **Result: {sig}** (alpha=0.05, one-tailed)\n")
    else:
        lines.append("- Insufficient data for this test\n")

    # H2: Pseudocode vs Markdown (format effect)
    lines.append("### H2: Format Effect (Pseudocode vs Markdown)\n")
    pseudo_scores = valid[valid["condition"] == "pseudocode"]["auto_score"]
    md_scores = valid[valid["condition"] == "markdown"]["auto_score"]

    if len(pseudo_scores) > 0 and len(md_scores) > 0:
        u_stat, p_value = stats.mannwhitneyu(
            pseudo_scores, md_scores, alternative="greater"
        )
        delta, magnitude = cliffs_delta(pseudo_scores.tolist(), md_scores.tolist())
        lines.append(f"- Mann-Whitney U = {u_stat:.1f}, p = {p_value:.4f}")
        lines.append(f"- Cliff's delta = {delta:.3f} ({magnitude})")
        lines.append(f"- Pseudocode mean = {pseudo_scores.mean():.2f}, Markdown mean = {md_scores.mean():.2f}")
        sig = "significant" if p_value < 0.05 else "not significant"
        lines.append(f"- **Result: {sig}** (alpha=0.05, one-tailed)\n")
    else:
        lines.append("- Insufficient data for this test\n")

    # H4: Cross-model (does format effect hold across families?)
    lines.append("### H4: Cross-Model Consistency\n")

    # Determine model families
    valid["family"] = valid["model"].apply(
        lambda m: "claude" if m in ("haiku", "opus") else "glm"
    )

    for family in sorted(valid["family"].unique()):
        fam_data = valid[valid["family"] == family]
        pseudo = fam_data[fam_data["condition"] == "pseudocode"]["auto_score"]
        md = fam_data[fam_data["condition"] == "markdown"]["auto_score"]

        if len(pseudo) > 0 and len(md) > 0:
            u_stat, p_value = stats.mannwhitneyu(
                pseudo, md, alternative="two-sided"
            )
            delta, magnitude = cliffs_delta(pseudo.tolist(), md.tolist())
            lines.append(f"**{family.upper()}**: U={u_stat:.1f}, p={p_value:.4f}, "
                         f"delta={delta:.3f} ({magnitude})")
        else:
            lines.append(f"**{family.upper()}**: Insufficient data")
    lines.append("")

    # Pass rate chi-squared
    lines.append("### Pass Rate (Schema Valid) by Condition\n")

    contingency = pd.crosstab(valid["condition"], valid["schema_valid"])
    if contingency.shape == (3, 2):
        chi2, p_value, dof, expected = stats.chi2_contingency(contingency)
        lines.append(f"- Chi-squared = {chi2:.2f}, df = {dof}, p = {p_value:.4f}")
        sig = "significant" if p_value < 0.05 else "not significant"
        lines.append(f"- **Result: {sig}**\n")
    else:
        lines.append("- Cannot compute chi-squared (insufficient categories)\n")

    return "\n".join(lines)


# ─── Charts ──────────────────────────────────────────────────────────────────

def generate_charts(df: pd.DataFrame) -> list[str]:
    """Generate summary charts. Returns list of chart filenames."""
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    valid = df[df["json_valid"]].copy()
    chart_files = []

    if len(valid) == 0:
        return chart_files

    # Style
    sns.set_theme(style="whitegrid", font_scale=1.1)
    palette = {"none": "#5D666F", "markdown": "#1A476F", "pseudocode": "#C74634"}

    # 1. Boxplot: Auto-score by condition
    fig, ax = plt.subplots(figsize=(8, 5))
    sns.boxplot(
        data=valid, x="condition", y="auto_score",
        order=["none", "markdown", "pseudocode"],
        palette=palette, ax=ax
    )
    ax.set_title("Auto-Score by Condition (5 automatable rules)")
    ax.set_xlabel("Condition")
    ax.set_ylabel("Auto-Score (0-5)")
    ax.set_ylim(-0.5, 5.5)
    fig.tight_layout()
    fname = "boxplot_condition.png"
    fig.savefig(CHARTS_DIR / fname, dpi=150)
    plt.close(fig)
    chart_files.append(fname)

    # 2. Heatmap: Auto-score by condition x model
    pivot = valid.pivot_table(
        values="auto_score", index="model", columns="condition",
        aggfunc="mean"
    )
    # Reorder columns
    col_order = [c for c in ["none", "markdown", "pseudocode"] if c in pivot.columns]
    pivot = pivot[col_order]

    fig, ax = plt.subplots(figsize=(8, 5))
    sns.heatmap(
        pivot, annot=True, fmt=".2f", cmap="YlOrRd_r",
        vmin=0, vmax=5, ax=ax, linewidths=0.5
    )
    ax.set_title("Mean Auto-Score by Model x Condition")
    fig.tight_layout()
    fname = "heatmap_model_condition.png"
    fig.savefig(CHARTS_DIR / fname, dpi=150)
    plt.close(fig)
    chart_files.append(fname)

    # 3. Bar chart: JSON validity rate by condition
    validity = valid.groupby("condition")["schema_valid"].mean().reset_index()
    validity.columns = ["condition", "rate"]

    fig, ax = plt.subplots(figsize=(6, 4))
    order = ["none", "markdown", "pseudocode"]
    colors = [palette.get(c, "#999") for c in order]
    validity_ordered = validity.set_index("condition").reindex(order).reset_index()
    ax.bar(validity_ordered["condition"], validity_ordered["rate"], color=colors)
    ax.set_title("Schema Validity Rate by Condition")
    ax.set_ylabel("Rate")
    ax.set_ylim(0, 1.1)
    for i, row in validity_ordered.iterrows():
        ax.text(i, row["rate"] + 0.02, f"{row['rate']:.0%}", ha="center")
    fig.tight_layout()
    fname = "bar_validity.png"
    fig.savefig(CHARTS_DIR / fname, dpi=150)
    plt.close(fig)
    chart_files.append(fname)

    # 4. Duration boxplot by condition (if available)
    if "duration_ms" in valid.columns and valid["duration_ms"].notna().any():
        fig, ax = plt.subplots(figsize=(8, 5))
        sns.boxplot(
            data=valid, x="condition", y="duration_ms",
            order=["none", "markdown", "pseudocode"],
            palette=palette, ax=ax
        )
        ax.set_title("Response Duration by Condition")
        ax.set_xlabel("Condition")
        ax.set_ylabel("Duration (ms)")
        fig.tight_layout()
        fname = "boxplot_duration.png"
        fig.savefig(CHARTS_DIR / fname, dpi=150)
        plt.close(fig)
        chart_files.append(fname)

    return chart_files


# ─── Report ──────────────────────────────────────────────────────────────────

def generate_report(df: pd.DataFrame, chart_files: list[str]) -> str:
    """Generate markdown analysis report."""
    lines = [
        "# Experiment Analysis Report\n",
        f"Generated from {len(df)} runs.\n",
    ]

    lines.append(descriptive_stats(df))
    lines.append(statistical_tests(df))

    # Charts section
    if chart_files:
        lines.append("## Charts\n")
        for fname in chart_files:
            lines.append(f"![{fname}](charts/{fname})\n")

    # Per-rule pass rates
    lines.append("## Individual Rule Pass Rates\n")
    rule_cols = [c for c in df.columns if c.endswith("_pass")]
    valid = df[df["json_valid"]]

    if len(valid) > 0 and rule_cols:
        lines.append("| Rule | none | markdown | pseudocode |")
        lines.append("|------|------|----------|------------|")
        for col in rule_cols:
            rule_name = col.replace("_pass", "")
            row = f"| {rule_name} |"
            for cond in ["none", "markdown", "pseudocode"]:
                subset = valid[valid["condition"] == cond][col]
                if len(subset) > 0:
                    rate = subset.mean() * 100
                    row += f" {rate:.0f}% |"
                else:
                    row += " - |"
            lines.append(row)
        lines.append("")

    return "\n".join(lines)


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    csv_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_CSV

    if not csv_path.exists():
        print(f"Scores CSV not found at {csv_path}")
        print("Run evaluate.py first to generate scores.csv")
        sys.exit(1)

    df = pd.read_csv(csv_path)
    print(f"Loaded {len(df)} rows from {csv_path}")

    # Generate charts
    chart_files = generate_charts(df)
    print(f"Generated {len(chart_files)} charts in {CHARTS_DIR}/")

    # Generate report
    report = generate_report(df, chart_files)
    OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_MD.write_text(report)
    print(f"Analysis report written to {OUTPUT_MD}")


if __name__ == "__main__":
    main()
