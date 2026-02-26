#!/usr/bin/env python3
"""Generate publication-quality figures for the arXiv paper.

Produces four figures:
  fig1 — Grouped bar chart: failure rate by condition (pooled + per-domain)
  fig2 — Heatmap: failure rate by model × condition
  fig3 — Forest plot: pseudocode advantage (pp) per model with bootstrap CIs
  fig4 — Split violin: failure rate distribution by model (markdown vs pseudocode)
"""

import sys
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

# Ensure scripts/ is importable
sys.path.insert(0, str(Path(__file__).resolve().parent))

# ── Paths ────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent

# Standard domains: use auto_score / scored_rules
STANDARD_DOMAINS = {
    "chart":      ROOT / "domains" / "chart" / "results-v2" / "scores_deep.csv",
    "dockerfile": ROOT / "domains" / "dockerfile" / "results" / "scores.csv",
    "sql":        ROOT / "domains" / "sql-query" / "results" / "scores.csv",
    "terraform":  ROOT / "domains" / "terraform" / "results" / "scores.csv",
}

GEMINI_CSV = ROOT.parent / "3-kpi-targets" / "gemini_scores.csv"

FIG_DIR = ROOT / "paper" / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

# ── Style ────────────────────────────────────────────────────────────────────
plt.rcParams.update({
    "font.family": "serif",
    "font.size": 9,
    "axes.labelsize": 10,
    "axes.titlesize": 10,
    "xtick.labelsize": 8.5,
    "ytick.labelsize": 8.5,
    "legend.fontsize": 8,
    "figure.dpi": 300,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.05,
})

CONDITION_ORDER = ["none", "markdown", "pseudocode"]
CONDITION_LABELS = {"none": "No skill", "markdown": "Markdown", "pseudocode": "Pseudocode"}
CONDITION_COLORS = {"none": "#bdbdbd", "markdown": "#6baed6", "pseudocode": "#2171b5"}

MODEL_ORDER = ["haiku", "opus", "glm-4.7", "glm-5", "gemini-3.1-pro-preview"]
MODEL_LABELS = {
    "haiku": "Haiku 4.5",
    "opus": "Opus 4.6",
    "glm-4.7": "GLM-4.7",
    "glm-5": "GLM-5",
    "gemini-3.1-pro-preview": "Gemini 3.1 Pro",
}
DOMAIN_LABELS = {
    "chart": "Chart",
    "dockerfile": "Dockerfile",
    "sql": "SQL (dbt)",
    "terraform": "Terraform",
}


def load_all() -> pd.DataFrame:
    """Load and unify scores from all four domains plus Gemini.

    Chart uses verdict-based scoring: failure_rate = fail_count / (pass_count + fail_count).
    Other domains use: failure_rate = 1 - auto_score / scored_rules.
    Extraction failures (scored_rules == 0 or pass+fail == 0) → failure_rate = 1.0.
    GLM-4.7-Flash is excluded.
    Gemini 3.1 Pro is loaded from a separate CSV.
    """
    frames = []
    for domain, path in STANDARD_DOMAINS.items():
        df = pd.read_csv(path)
        df["domain"] = domain
        df["model"] = df["model"].str.replace("zai-coding-plan/", "", regex=False)

        if domain == "chart":
            # Chart uses verdict-based pass_count / fail_count
            total = df["pass_count"] + df["fail_count"]
            df["failure_rate"] = np.where(
                total > 0,
                df["fail_count"] / total,
                1.0,
            )
        else:
            df["failure_rate"] = np.where(
                df["scored_rules"] > 0,
                1 - df["auto_score"] / df["scored_rules"],
                1.0,
            )

        frames.append(df)

    # Load Gemini data
    if GEMINI_CSV.exists():
        gdf = pd.read_csv(GEMINI_CSV)
        # Normalize domain: sql-query → sql
        gdf["domain"] = gdf["domain"].replace({"sql-query": "sql"})
        # Chart rows: use fail_count/(pass_count+fail_count) for failure rate
        chart_mask = gdf["domain"] == "chart"
        chart_total = gdf.loc[chart_mask, "pass_count"] + gdf.loc[chart_mask, "fail_count"]
        gdf.loc[chart_mask, "failure_rate"] = np.where(
            chart_total > 0,
            gdf.loc[chart_mask, "fail_count"] / chart_total,
            1.0,
        )
        # Non-chart rows: use 1 - auto_score/scored_rules
        non_chart = ~chart_mask
        gdf.loc[non_chart, "failure_rate"] = np.where(
            gdf.loc[non_chart, "scored_rules"] > 0,
            1 - gdf.loc[non_chart, "auto_score"] / gdf.loc[non_chart, "scored_rules"],
            1.0,
        )
        frames.append(gdf)
    else:
        print(f"WARNING: Gemini CSV not found at {GEMINI_CSV}", file=sys.stderr)

    data = pd.concat(frames, ignore_index=True)
    # Remove GLM-4.7-Flash
    data = data[data["model"] != "glm-4.7-flash"].reset_index(drop=True)
    return data


def _bootstrap_ci(values, n_boot=5000, seed=42, ci=95):
    """Return (mean, lo, hi) bootstrap CI."""
    rng = np.random.default_rng(seed)
    mean = values.mean()
    boots = np.array([rng.choice(values, size=len(values), replace=True).mean()
                      for _ in range(n_boot)])
    alpha = (100 - ci) / 2
    lo, hi = np.percentile(boots, [alpha, 100 - alpha])
    return mean, lo, hi


# ── Figure 1 ─────────────────────────────────────────────────────────────────

def fig1_condition_bars(data: pd.DataFrame):
    """Grouped bar chart: failure rate by condition, pooled + per-domain."""
    groups = ["Pooled", "Chart", "Dockerfile", "SQL (dbt)", "Terraform"]
    domain_map = {"Pooled": None, "Chart": "chart", "Dockerfile": "dockerfile",
                  "SQL (dbt)": "sql", "Terraform": "terraform"}

    fig, ax = plt.subplots(figsize=(6.5, 3.2))
    x = np.arange(len(groups))
    width = 0.24

    for i, cond in enumerate(CONDITION_ORDER):
        means, lo_err, hi_err = [], [], []
        for group in groups:
            dom = domain_map[group]
            subset = data if dom is None else data[data["domain"] == dom]
            fr = subset[subset["condition"] == cond]["failure_rate"].values
            mean, lo, hi = _bootstrap_ci(fr)
            means.append(mean * 100)
            lo_err.append((mean - lo) * 100)
            hi_err.append((hi - mean) * 100)

        yerr = np.array([lo_err, hi_err])
        ax.bar(x + (i - 1) * width, means, width,
               label=CONDITION_LABELS[cond],
               color=CONDITION_COLORS[cond],
               edgecolor="white", linewidth=0.5,
               yerr=yerr, capsize=2, error_kw={"linewidth": 0.7})

    ax.set_ylabel("Failure rate (%)")
    ax.set_xticks(x)
    ax.set_xticklabels(groups)
    ax.set_ylim(0, 70)
    ax.legend(loc="upper left", frameon=True, edgecolor="#cccccc")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.yaxis.grid(True, linestyle="--", alpha=0.3)
    ax.set_axisbelow(True)

    fig.savefig(FIG_DIR / "fig1_condition_bars.pdf")
    fig.savefig(FIG_DIR / "fig1_condition_bars.png")
    plt.close(fig)
    print("  fig1_condition_bars.pdf")


# ── Figure 2 ─────────────────────────────────────────────────────────────────

def fig2_model_heatmap(data: pd.DataFrame):
    """Heatmap: failure rate by model (rows) × condition (cols), pooled."""
    models = MODEL_ORDER
    conds = CONDITION_ORDER

    matrix = np.zeros((len(models), len(conds)))
    for i, m in enumerate(models):
        for j, c in enumerate(conds):
            subset = data[(data["model"] == m) & (data["condition"] == c)]
            matrix[i, j] = subset["failure_rate"].mean() * 100

    fig, ax = plt.subplots(figsize=(4.0, 3.6))
    im = ax.imshow(matrix, cmap="RdYlGn_r", aspect="auto", vmin=0, vmax=65)

    ax.set_xticks(range(len(conds)))
    ax.set_xticklabels([CONDITION_LABELS[c] for c in conds])
    ax.set_yticks(range(len(models)))
    ax.set_yticklabels([MODEL_LABELS[m] for m in models])

    for i in range(len(models)):
        for j in range(len(conds)):
            val = matrix[i, j]
            color = "white" if val > 40 else "black"
            ax.text(j, i, f"{val:.1f}%", ha="center", va="center",
                    fontsize=8, color=color, fontweight="bold")

    # White dividers between families: Claude (0-1), GLM (2-3), Gemini (4)
    ax.axhline(y=1.5, color="white", linewidth=2.5)
    ax.axhline(y=3.5, color="white", linewidth=2.5)

    cbar = fig.colorbar(im, ax=ax, shrink=0.8, pad=0.02)
    cbar.set_label("Failure rate (%)", fontsize=8)
    cbar.ax.tick_params(labelsize=7)

    fig.savefig(FIG_DIR / "fig2_model_heatmap.pdf")
    fig.savefig(FIG_DIR / "fig2_model_heatmap.png")
    plt.close(fig)
    print("  fig2_model_heatmap.pdf")


# ── Figure 3 ─────────────────────────────────────────────────────────────────

def fig3_pseudocode_advantage(data: pd.DataFrame):
    """Forest plot: Markdown FR − Pseudocode FR per model, with bootstrap CIs."""
    models = MODEL_ORDER
    fig, ax = plt.subplots(figsize=(5.5, 3.4))

    for i, m in enumerate(models):
        md_fr = data[(data["model"] == m) & (data["condition"] == "markdown")]["failure_rate"].values
        pc_fr = data[(data["model"] == m) & (data["condition"] == "pseudocode")]["failure_rate"].values

        if len(md_fr) == 0 or len(pc_fr) == 0:
            continue

        delta = md_fr.mean() - pc_fr.mean()

        rng = np.random.default_rng(42)
        boot_deltas = []
        for _ in range(5000):
            b_md = rng.choice(md_fr, size=len(md_fr), replace=True).mean()
            b_pc = rng.choice(pc_fr, size=len(pc_fr), replace=True).mean()
            boot_deltas.append(b_md - b_pc)
        lo, hi = np.percentile(boot_deltas, [2.5, 97.5])

        color = "#2171b5" if delta > 0 else "#d94801"
        ax.errorbar(delta * 100, i,
                    xerr=[[abs(delta - lo) * 100], [(hi - delta) * 100]],
                    fmt="o", color=color, markersize=7, capsize=4,
                    linewidth=1.5, markeredgecolor="white", markeredgewidth=0.5)
        # Value label
        ax.text(delta * 100 + (hi - delta) * 100 + 0.5, i,
                f"{delta*100:+.1f}pp", va="center", fontsize=7, color=color)

    ax.axvline(x=0, color="#999999", linestyle="--", linewidth=0.8)
    ax.set_yticks(range(len(models)))
    ax.set_yticklabels([MODEL_LABELS[m] for m in models])
    ax.set_xlabel("Pseudocode advantage (pp)\n(Markdown FR $-$ Pseudocode FR)")
    ax.invert_yaxis()
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.xaxis.grid(True, linestyle="--", alpha=0.3)
    ax.set_axisbelow(True)

    # Right-side annotation
    ax.annotate("$\\leftarrow$ Markdown better  |  Pseudocode better $\\rightarrow$",
                xy=(0.5, 1.02), xycoords="axes fraction",
                ha="center", fontsize=7, color="#666666")

    fig.savefig(FIG_DIR / "fig3_pseudocode_advantage.pdf")
    fig.savefig(FIG_DIR / "fig3_pseudocode_advantage.png")
    plt.close(fig)
    print("  fig3_pseudocode_advantage.pdf")


# ── Figure 4 ─────────────────────────────────────────────────────────────────

def fig4_variance_violin(data: pd.DataFrame):
    """Split violin: failure rate distribution by model (markdown vs pseudocode)."""
    from variability_analysis import plot_violin_comparison

    skill_data = data[data["condition"].isin(["markdown", "pseudocode"])].copy()
    fig = plot_violin_comparison(
        skill_data,
        group_col="model",
        condition_a="markdown",
        condition_b="pseudocode",
        metric="failure_rate",
        group_order=MODEL_ORDER,
        group_labels=MODEL_LABELS,
        condition_labels={"markdown": "Markdown", "pseudocode": "Pseudocode"},
        threshold_line=0.10,
        output_path=FIG_DIR / "fig4_variance_violin.pdf",
    )
    plt.close(fig)


# ── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Loading data...")
    data = load_all()
    print(f"  {len(data)} runs across {data['domain'].nunique()} domains")
    print(f"  Models: {sorted(data['model'].unique())}")
    print(f"  Conditions: {sorted(data['condition'].unique())}")
    print(f"  Per-domain counts:")
    for dom in sorted(data['domain'].unique()):
        n = len(data[data['domain'] == dom])
        print(f"    {dom}: {n} runs")
    print()
    print("Generating figures...")
    fig1_condition_bars(data)
    fig2_model_heatmap(data)
    fig3_pseudocode_advantage(data)
    fig4_variance_violin(data)
    print()
    print("Done. Figures saved to paper/figures/")
