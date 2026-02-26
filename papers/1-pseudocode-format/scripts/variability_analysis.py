#!/usr/bin/env python3
"""Variability analysis for A/B experiment datasets.

Provides HDI comparison, threshold‐rate analysis, Levene's test, and
bootstrap HDI‐of‐mean, plus a split‐violin figure for publication.

Works on any CSV with a numeric metric column, a binary condition column,
and a grouping column.

Usage (CLI):
    python scripts/variability_analysis.py \\
        --input data.csv \\
        --metric failure_rate \\
        --condition-col condition \\
        --condition-a markdown --condition-b pseudocode \\
        --group-col model \\
        --threshold 0.10 \\
        --output-dir paper/figures/
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd
from scipy import stats

# ── Matplotlib style (matches existing figures) ─────────────────────────────

_STYLE = {
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
}


# ── Analysis functions ───────────────────────────────────────────────────────


def compute_hdi(samples: np.ndarray, credibility: float = 0.90) -> tuple[float, float]:
    """Highest‐density interval for a 1‑D sample array.

    Uses the "shortest interval containing *credibility* of the data"
    approach (works well for unimodal, possibly skewed distributions).
    """
    samples = np.sort(samples)
    n = len(samples)
    interval_size = int(np.ceil(credibility * n))
    if interval_size >= n:
        return float(samples[0]), float(samples[-1])

    widths = samples[interval_size:] - samples[: n - interval_size]
    best = int(np.argmin(widths))
    return float(samples[best]), float(samples[best + interval_size])


def compute_hdi_comparison(
    df: pd.DataFrame,
    group_col: str,
    condition_a: str,
    condition_b: str,
    metric: str = "failure_rate",
    credibility: float = 0.90,
) -> pd.DataFrame:
    """Per‐group HDI width comparison between two conditions."""
    rows = []
    for group, gdf in df.groupby(group_col):
        for cond, label in [(condition_a, "a"), (condition_b, "b")]:
            vals = gdf.loc[gdf["condition"] == cond, metric].values
            if len(vals) < 2:
                lo, hi, width = np.nan, np.nan, np.nan
            else:
                lo, hi = compute_hdi(vals, credibility)
                width = hi - lo
            rows.append(
                {
                    "group": group,
                    f"hdi_lo_{label}": lo,
                    f"hdi_hi_{label}": hi,
                    f"hdi_width_{label}": width,
                }
            )

    # Merge a / b rows per group
    a_rows = [r for r in rows if "hdi_lo_a" in r]
    b_rows = [r for r in rows if "hdi_lo_b" in r]
    merged = []
    for a, b in zip(a_rows, b_rows):
        row = {**a, **b}
        wa = row["hdi_width_a"]
        wb = row["hdi_width_b"]
        row["narrowing"] = wa - wb
        row["pct_change"] = (wa - wb) / wa * 100 if wa and not np.isnan(wa) and wa != 0 else np.nan
        merged.append(row)

    return pd.DataFrame(merged)


def compute_threshold_rates(
    df: pd.DataFrame,
    group_col: str,
    condition_a: str,
    condition_b: str,
    metric: str = "failure_rate",
    threshold: float = 0.10,
) -> pd.DataFrame:
    """P(metric < threshold) per group and condition."""
    rows = []
    for group, gdf in df.groupby(group_col):
        vals_a = gdf.loc[gdf["condition"] == condition_a, metric].values
        vals_b = gdf.loc[gdf["condition"] == condition_b, metric].values
        p_a = (vals_a < threshold).mean() if len(vals_a) else np.nan
        p_b = (vals_b < threshold).mean() if len(vals_b) else np.nan
        rows.append(
            {
                "group": group,
                f"P(FR<{threshold})_{condition_a}": p_a,
                f"P(FR<{threshold})_{condition_b}": p_b,
                "difference": p_b - p_a if not (np.isnan(p_a) or np.isnan(p_b)) else np.nan,
            }
        )
    return pd.DataFrame(rows)


def compute_levene(
    df: pd.DataFrame,
    group_col: str,
    condition_a: str,
    condition_b: str,
    metric: str = "failure_rate",
) -> pd.DataFrame:
    """Levene's test (median variant) per group."""
    rows = []
    for group, gdf in df.groupby(group_col):
        vals_a = gdf.loc[gdf["condition"] == condition_a, metric].values
        vals_b = gdf.loc[gdf["condition"] == condition_b, metric].values
        if len(vals_a) < 2 or len(vals_b) < 2:
            rows.append({"group": group, "F": np.nan, "p": np.nan, "var_ratio": np.nan})
            continue
        f_stat, p_val = stats.levene(vals_a, vals_b, center="median")
        var_a = np.var(vals_a, ddof=1)
        var_b = np.var(vals_b, ddof=1)
        rows.append(
            {
                "group": group,
                "F": f_stat,
                "p": p_val,
                "var_a": var_a,
                "var_b": var_b,
                "var_ratio": var_a / var_b if var_b > 0 else np.nan,
            }
        )
    return pd.DataFrame(rows)


def compute_bootstrap_hdi_of_mean(
    df: pd.DataFrame,
    group_col: str,
    condition_a: str,
    condition_b: str,
    metric: str = "failure_rate",
    n_boot: int = 10_000,
    seed: int = 42,
) -> pd.DataFrame:
    """Bootstrap 95% HDI of the mean per group and condition."""
    rng = np.random.default_rng(seed)
    rows = []
    for group, gdf in df.groupby(group_col):
        for cond, label in [(condition_a, "a"), (condition_b, "b")]:
            vals = gdf.loc[gdf["condition"] == cond, metric].values
            if len(vals) < 2:
                rows.append(
                    {"group": group, f"mean_{label}": np.nan, f"hdi_lo_{label}": np.nan, f"hdi_hi_{label}": np.nan, f"hdi_width_{label}": np.nan}
                )
                continue
            boots = np.array(
                [rng.choice(vals, size=len(vals), replace=True).mean() for _ in range(n_boot)]
            )
            lo, hi = compute_hdi(boots, 0.95)
            rows.append(
                {
                    "group": group,
                    f"mean_{label}": vals.mean(),
                    f"hdi_lo_{label}": lo,
                    f"hdi_hi_{label}": hi,
                    f"hdi_width_{label}": hi - lo,
                }
            )

    a_rows = [r for r in rows if "mean_a" in r]
    b_rows = [r for r in rows if "mean_b" in r]
    merged = []
    for a, b in zip(a_rows, b_rows):
        row = {**a, **b}
        wa = row.get("hdi_width_a", np.nan)
        wb = row.get("hdi_width_b", np.nan)
        row["width_narrowing"] = wa - wb if not (np.isnan(wa) or np.isnan(wb)) else np.nan
        merged.append(row)
    return pd.DataFrame(merged)


# ── Figure function ──────────────────────────────────────────────────────────


def plot_violin_comparison(
    df: pd.DataFrame,
    group_col: str,
    condition_a: str,
    condition_b: str,
    metric: str = "failure_rate",
    group_order: Sequence[str] | None = None,
    group_labels: dict[str, str] | None = None,
    condition_labels: dict[str, str] | None = None,
    threshold_line: float | None = 0.10,
    output_path: str | Path | None = None,
) -> plt.Figure:
    """Split violin plot comparing two conditions across groups.

    Left half = condition_a, right half = condition_b.
    Jittered dots overlaid. Optional threshold line.
    """
    plt.rcParams.update(_STYLE)

    if group_order is None:
        group_order = sorted(df[group_col].unique())
    if group_labels is None:
        group_labels = {g: g for g in group_order}
    if condition_labels is None:
        condition_labels = {condition_a: condition_a, condition_b: condition_b}

    color_a = "#e6932f"  # Markdown orange
    color_b = "#2171b5"  # Pseudocode blue

    n_groups = len(group_order)
    fig, ax = plt.subplots(figsize=(6.5, 3.0))
    positions = np.arange(n_groups)
    rng = np.random.default_rng(42)

    for i, group in enumerate(group_order):
        gdf = df[df[group_col] == group]
        vals_a = gdf.loc[gdf["condition"] == condition_a, metric].values
        vals_b = gdf.loc[gdf["condition"] == condition_b, metric].values

        # Draw split violins
        for vals, side, color in [(vals_a, -1, color_a), (vals_b, 1, color_b)]:
            if len(vals) < 4:
                # Too few points for a violin — just draw dots
                jitter = rng.uniform(-0.05, 0.05, size=len(vals))
                ax.scatter(
                    i + side * 0.15 + jitter,
                    vals * 100,
                    color=color,
                    alpha=0.6,
                    s=18,
                    edgecolor="white",
                    linewidth=0.3,
                    zorder=5,
                )
                continue

            parts = ax.violinplot(
                vals * 100,
                positions=[i],
                widths=0.7,
                showmeans=False,
                showmedians=False,
                showextrema=False,
            )
            for pc in parts["bodies"]:
                # Clip to left or right half
                m = np.mean(pc.get_paths()[0].vertices[:, 0])
                if side == -1:
                    pc.get_paths()[0].vertices[:, 0] = np.clip(
                        pc.get_paths()[0].vertices[:, 0], -np.inf, m
                    )
                else:
                    pc.get_paths()[0].vertices[:, 0] = np.clip(
                        pc.get_paths()[0].vertices[:, 0], m, np.inf
                    )
                pc.set_facecolor(color)
                pc.set_edgecolor("none")
                pc.set_alpha(0.35)

            # Jittered dots
            jitter = rng.uniform(0.02, 0.18, size=len(vals)) * side
            ax.scatter(
                i + jitter,
                vals * 100,
                color=color,
                alpha=0.6,
                s=12,
                edgecolor="white",
                linewidth=0.3,
                zorder=5,
            )

        # Median markers
        if len(vals_a) > 0:
            ax.plot(i - 0.15, np.median(vals_a) * 100, "_", color=color_a,
                    markersize=12, markeredgewidth=2, zorder=6)
        if len(vals_b) > 0:
            ax.plot(i + 0.15, np.median(vals_b) * 100, "_", color=color_b,
                    markersize=12, markeredgewidth=2, zorder=6)

    # Threshold line
    if threshold_line is not None:
        ax.axhline(
            y=threshold_line * 100,
            color="#d62728",
            linestyle="--",
            linewidth=0.8,
            alpha=0.7,
            zorder=1,
        )
        ax.text(
            n_groups - 0.5,
            threshold_line * 100 + 1.2,
            f"{threshold_line*100:.0f}% threshold",
            ha="right",
            fontsize=7,
            color="#d62728",
            alpha=0.7,
        )

    ax.set_xticks(positions)
    ax.set_xticklabels([group_labels.get(g, g) for g in group_order])
    ax.set_ylabel("Failure rate (%)")
    ax.set_ylim(-2, max(df[metric].max() * 100 + 5, 50))
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.yaxis.grid(True, linestyle="--", alpha=0.3)
    ax.set_axisbelow(True)

    # Legend
    patch_a = mpatches.Patch(color=color_a, alpha=0.6, label=condition_labels[condition_a])
    patch_b = mpatches.Patch(color=color_b, alpha=0.6, label=condition_labels[condition_b])
    ax.legend(handles=[patch_a, patch_b], loc="upper right", frameon=True, edgecolor="#cccccc")

    fig.tight_layout()

    if output_path is not None:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output_path)
        # Also save PNG
        fig.savefig(output_path.with_suffix(".png"))
        print(f"  Saved: {output_path}")

    return fig


# ── Pretty-printing helpers ──────────────────────────────────────────────────


def _fmt_p(p: float) -> str:
    if np.isnan(p):
        return "N/A"
    return f"{p:.3f}" if p >= 0.001 else "< 0.001"


def _print_table(title: str, df: pd.DataFrame) -> None:
    print(f"\n  {title}")
    print(f"  {'-' * 70}")
    col_widths = {c: max(len(c), df[c].apply(lambda x: len(f"{x:.3f}" if isinstance(x, float) else str(x))).max()) for c in df.columns}
    header = "  ".join(f"{c:>{max(w, 8)}}" for c, w in col_widths.items())
    print(f"  {header}")
    for _, row in df.iterrows():
        vals = []
        for c in df.columns:
            v = row[c]
            if isinstance(v, float):
                if c == "p":
                    vals.append(f"{_fmt_p(v):>8}")
                else:
                    vals.append(f"{v:>8.3f}")
            else:
                vals.append(f"{str(v):>8}")
        print(f"  {'  '.join(vals)}")


# ── CLI ──────────────────────────────────────────────────────────────────────


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Variability analysis for A/B experiment datasets.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--input", required=True, help="Path to CSV file")
    p.add_argument("--metric", default="failure_rate", help="Numeric metric column (default: failure_rate)")
    p.add_argument("--condition-col", default="condition", help="Condition column name (default: condition)")
    p.add_argument("--condition-a", required=True, help="Label for condition A (e.g. markdown)")
    p.add_argument("--condition-b", required=True, help="Label for condition B (e.g. pseudocode)")
    p.add_argument("--group-col", required=True, help="Grouping column (e.g. model)")
    p.add_argument("--group-order", nargs="*", default=None, help="Ordered list of group values")
    p.add_argument("--threshold", type=float, default=0.10, help="Quality threshold (default: 0.10)")
    p.add_argument("--output-dir", default=None, help="Directory to save figure (optional)")
    p.add_argument("--credibility", type=float, default=0.90, help="HDI credibility level (default: 0.90)")
    p.add_argument("--n-boot", type=int, default=10_000, help="Bootstrap resamples (default: 10000)")
    return p


def main(argv: Sequence[str] | None = None) -> None:
    args = build_parser().parse_args(argv)

    df = pd.read_csv(args.input)

    # Filter to only the two conditions of interest
    df = df[df[args.condition_col].isin([args.condition_a, args.condition_b])].copy()
    # Rename condition col if needed for internal consistency
    if args.condition_col != "condition":
        df = df.rename(columns={args.condition_col: "condition"})

    group_col = args.group_col
    ca, cb = args.condition_a, args.condition_b

    print("=" * 70)
    print(f"  Variability Analysis: {ca} vs {cb}")
    print(f"  Grouped by: {group_col}")
    print(f"  Metric: {args.metric}, Threshold: {args.threshold}")
    print(f"  N = {len(df)} runs")
    print("=" * 70)

    # 1. HDI comparison
    hdi_df = compute_hdi_comparison(df, group_col, ca, cb, args.metric, args.credibility)
    _print_table(f"HDI Comparison ({args.credibility*100:.0f}% HDI)", hdi_df)

    # 2. Threshold rates
    thresh_df = compute_threshold_rates(df, group_col, ca, cb, args.metric, args.threshold)
    _print_table(f"Threshold Rates (P(FR < {args.threshold}))", thresh_df)

    # 3. Levene's test
    levene_df = compute_levene(df, group_col, ca, cb, args.metric)
    _print_table("Levene's Test (variance homogeneity)", levene_df)

    # 4. Bootstrap HDI of mean
    boot_df = compute_bootstrap_hdi_of_mean(df, group_col, ca, cb, args.metric, args.n_boot)
    _print_table("Bootstrap 95% HDI of Mean", boot_df)

    # 5. Figure
    if args.output_dir:
        out = Path(args.output_dir) / "fig4_variance_violin.pdf"
        plot_violin_comparison(
            df,
            group_col,
            ca,
            cb,
            metric=args.metric,
            group_order=args.group_order,
            threshold_line=args.threshold,
            output_path=out,
        )
        plt.close("all")

    print("\nDone.")


if __name__ == "__main__":
    main()
