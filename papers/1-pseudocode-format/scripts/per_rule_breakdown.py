#!/usr/bin/env python3
"""Per-rule pass rate breakdown by condition (none, markdown, pseudocode) across 4 domains."""

import pandas as pd
import re
import sys

pd.set_option("display.max_rows", 200)
pd.set_option("display.width", 160)
pd.set_option("display.max_colwidth", 40)

import os

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PAPER1_ROOT = os.path.dirname(_SCRIPT_DIR)  # papers/1-pseudocode-format/
_DOMAINS_DIR = os.path.join(_PAPER1_ROOT, "domains")

DOMAINS = {
    "chart": os.path.join(_DOMAINS_DIR, "chart", "results-v2", "scores_deep.csv"),
    "dockerfile": os.path.join(_DOMAINS_DIR, "dockerfile", "results", "scores.csv"),
    "sql-query": os.path.join(_DOMAINS_DIR, "sql-query", "results", "scores.csv"),
    "terraform": os.path.join(_DOMAINS_DIR, "terraform", "results", "scores.csv"),
}

EXCLUDE_MODELS = {"glm-4.7-flash"}


def load_and_clean(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    # Strip prefix from model column
    df["model"] = df["model"].str.replace("zai-coding-plan/", "", regex=False)
    # Exclude models
    df = df[~df["model"].isin(EXCLUDE_MODELS)].copy()
    return df


def analyse_chart(df: pd.DataFrame) -> pd.DataFrame:
    """Chart domain uses rule_NN_verdict with values pass/fail/absent."""
    verdict_cols = sorted([c for c in df.columns if c.endswith("_verdict")])
    rows = []
    for col in verdict_cols:
        # Extract rule name like rule_01
        rule_name = col.replace("_verdict", "")
        # Convert to binary: pass=1, fail=0, absent=NaN (exclude absent from mean)
        series = df[col].map({"pass": 1.0, "fail": 0.0, "absent": float("nan")})
        temp = df[["condition"]].copy()
        temp["val"] = series
        grouped = temp.groupby("condition")["val"].mean() * 100
        rows.append({
            "rule": rule_name,
            "none": grouped.get("none", float("nan")),
            "markdown": grouped.get("markdown", float("nan")),
            "pseudocode": grouped.get("pseudocode", float("nan")),
        })
    return pd.DataFrame(rows)


def analyse_bool_pass(df: pd.DataFrame) -> pd.DataFrame:
    """Dockerfile and Terraform: columns ending with _pass that are boolean True/False."""
    pass_cols = sorted([c for c in df.columns if c.endswith("_pass")])
    rows = []
    for col in pass_cols:
        rule_name = col.replace("_pass", "")
        series = df[col].astype(float)
        temp = df[["condition"]].copy()
        temp["val"] = series.values
        grouped = temp.groupby("condition")["val"].mean() * 100
        rows.append({
            "rule": rule_name,
            "none": grouped.get("none", float("nan")),
            "markdown": grouped.get("markdown", float("nan")),
            "pseudocode": grouped.get("pseudocode", float("nan")),
        })
    return pd.DataFrame(rows)


def analyse_sql(df: pd.DataFrame) -> pd.DataFrame:
    """SQL domain: mix of _pass (boolean) and _rate (float 0-1) columns."""
    # Rate columns (already 0-1 scale)
    rate_cols = sorted([c for c in df.columns if re.match(r"rule_\d+_\w+_rate$", c)])
    # Pass columns (boolean)
    pass_cols = sorted([c for c in df.columns if re.match(r"rule_\d+_\w+_pass$", c)])

    rows = []
    for col in rate_cols:
        rule_name = col.replace("_rate", "")
        series = df[col].astype(float)
        temp = df[["condition"]].copy()
        temp["val"] = series.values
        grouped = temp.groupby("condition")["val"].mean() * 100
        rows.append({
            "rule": rule_name,
            "none": grouped.get("none", float("nan")),
            "markdown": grouped.get("markdown", float("nan")),
            "pseudocode": grouped.get("pseudocode", float("nan")),
        })
    for col in pass_cols:
        rule_name = col.replace("_pass", "")
        series = df[col].astype(float)
        temp = df[["condition"]].copy()
        temp["val"] = series.values
        grouped = temp.groupby("condition")["val"].mean() * 100
        rows.append({
            "rule": rule_name,
            "none": grouped.get("none", float("nan")),
            "markdown": grouped.get("markdown", float("nan")),
            "pseudocode": grouped.get("pseudocode", float("nan")),
        })
    return pd.DataFrame(rows)


def print_domain_table(domain: str, result_df: pd.DataFrame):
    result_df["delta_pc_minus_md"] = result_df["pseudocode"] - result_df["markdown"]
    print(f"\n{'='*90}")
    print(f"  DOMAIN: {domain.upper()}")
    print(f"{'='*90}")
    header = f"{'Rule':<40} {'None%':>7} {'MD%':>7} {'PC%':>7} {'PC-MD':>7}"
    print(header)
    print("-" * 90)
    for _, row in result_df.iterrows():
        none_val = f"{row['none']:.1f}" if pd.notna(row["none"]) else "n/a"
        md_val = f"{row['markdown']:.1f}" if pd.notna(row["markdown"]) else "n/a"
        pc_val = f"{row['pseudocode']:.1f}" if pd.notna(row["pseudocode"]) else "n/a"
        delta = row["delta_pc_minus_md"]
        delta_str = f"{delta:+.1f}" if pd.notna(delta) else "n/a"
        print(f"{row['rule']:<40} {none_val:>7} {md_val:>7} {pc_val:>7} {delta_str:>7}")
    print()


def main():
    all_results = {}  # domain -> DataFrame with columns [rule, none, markdown, pseudocode, delta]

    for domain, path in DOMAINS.items():
        print(f"Loading {domain} from {path} ...")
        df = load_and_clean(path)
        conditions = df["condition"].unique()
        models = df["model"].unique()
        print(f"  Conditions: {sorted(conditions)}")
        print(f"  Models: {sorted(models)}")
        print(f"  Rows: {len(df)}")

        if domain == "chart":
            result = analyse_chart(df)
        elif domain == "sql-query":
            result = analyse_sql(df)
        else:
            result = analyse_bool_pass(df)

        result["delta_pc_minus_md"] = result["pseudocode"] - result["markdown"]
        all_results[domain] = result
        print_domain_table(domain, result)

    # =========================================================================
    # Highlight summary
    # =========================================================================
    print("\n" + "=" * 90)
    print("  HIGHLIGHT SUMMARY: BIGGEST PSEUDOCODE vs MARKDOWN DELTAS")
    print("=" * 90)

    all_rows = []
    for domain, result_df in all_results.items():
        for _, row in result_df.iterrows():
            all_rows.append({
                "domain": domain,
                "rule": row["rule"],
                "none": row["none"],
                "markdown": row["markdown"],
                "pseudocode": row["pseudocode"],
                "delta": row["delta_pc_minus_md"],
            })
    combined = pd.DataFrame(all_rows).dropna(subset=["delta"])
    combined = combined.sort_values("delta", ascending=False)

    print("\n--- Top 10: Pseudocode BEATS Markdown (largest positive delta) ---")
    top = combined.head(10)
    header = f"{'Domain':<14} {'Rule':<40} {'MD%':>7} {'PC%':>7} {'PC-MD':>7}"
    print(header)
    print("-" * 90)
    for _, r in top.iterrows():
        print(f"{r['domain']:<14} {r['rule']:<40} {r['markdown']:7.1f} {r['pseudocode']:7.1f} {r['delta']:+7.1f}")

    print("\n--- Top 10: Markdown BEATS Pseudocode (largest negative delta) ---")
    bottom = combined.tail(10).sort_values("delta")
    print(header)
    print("-" * 90)
    for _, r in bottom.iterrows():
        print(f"{r['domain']:<14} {r['rule']:<40} {r['markdown']:7.1f} {r['pseudocode']:7.1f} {r['delta']:+7.1f}")

    # =========================================================================
    # Cross-domain aggregate
    # =========================================================================
    print("\n" + "=" * 90)
    print("  CROSS-DOMAIN AGGREGATE: Mean pass rate by condition")
    print("=" * 90)
    for domain, result_df in all_results.items():
        avg_none = result_df["none"].mean()
        avg_md = result_df["markdown"].mean()
        avg_pc = result_df["pseudocode"].mean()
        avg_delta = result_df["delta_pc_minus_md"].mean()
        none_str = f"{avg_none:.1f}" if pd.notna(avg_none) else "n/a"
        print(f"  {domain:<14}  None={none_str:>5}%  MD={avg_md:.1f}%  PC={avg_pc:.1f}%  delta(PC-MD)={avg_delta:+.1f}pp")

    # Grand average
    all_deltas = combined["delta"]
    print(f"\n  Grand mean delta (PC - MD) across all {len(combined)} rules: {all_deltas.mean():+.2f}pp")
    print(f"  Rules where PC > MD: {(all_deltas > 0).sum()} / {len(all_deltas)}")
    print(f"  Rules where MD > PC: {(all_deltas < 0).sum()} / {len(all_deltas)}")
    print(f"  Rules tied:          {(all_deltas == 0).sum()} / {len(all_deltas)}")


if __name__ == "__main__":
    main()
