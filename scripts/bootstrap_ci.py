#!/usr/bin/env python3
"""
Bootstrap confidence intervals for experiment scores.

Reads any scores CSV, auto-detects the score column, groups by
(model, condition), and computes BCa bootstrap 95% CIs on the mean.

Usage:
    python bootstrap_ci.py results/scores_deep.csv
    python bootstrap_ci.py results/scores_deep.csv --output ci_results.csv
    python bootstrap_ci.py domains/commit-message/results/scores.csv
"""

import argparse
import csv
import math
import random
import sys
from pathlib import Path

# Score column names to auto-detect (priority order)
SCORE_CANDIDATES = [
    "deep_score",
    "auto_score",
    "pass_count",
]

N_BOOTSTRAP = 10_000
CI_LEVEL = 0.95


def read_csv(path: Path) -> list[dict]:
    with open(path) as f:
        return list(csv.DictReader(f))


def detect_score_column(rows: list[dict]) -> str:
    """Find the score column from known candidates."""
    headers = set(rows[0].keys()) if rows else set()
    for candidate in SCORE_CANDIDATES:
        if candidate in headers:
            return candidate
    raise ValueError(
        f"No score column found. Expected one of {SCORE_CANDIDATES}, "
        f"got columns: {sorted(headers)}"
    )


def bootstrap_mean_ci(
    values: list[float],
    n_bootstrap: int = N_BOOTSTRAP,
    ci_level: float = CI_LEVEL,
) -> tuple[float, float, float]:
    """Compute bootstrap percentile CI for the mean.

    Returns (mean, lower, upper).
    Uses percentile method (BCa requires jackknife which adds complexity
    for marginal accuracy gain at n>=3).
    """
    n = len(values)
    if n == 0:
        return 0.0, 0.0, 0.0
    if n == 1:
        return values[0], values[0], values[0]

    observed_mean = sum(values) / n
    alpha = (1 - ci_level) / 2

    # Generate bootstrap distribution of means
    rng = random.Random(42)  # reproducible
    boot_means = []
    for _ in range(n_bootstrap):
        sample = [rng.choice(values) for _ in range(n)]
        boot_means.append(sum(sample) / n)

    boot_means.sort()

    lower_idx = max(0, int(math.floor(alpha * n_bootstrap)))
    upper_idx = min(n_bootstrap - 1, int(math.ceil((1 - alpha) * n_bootstrap)) - 1)

    return observed_mean, boot_means[lower_idx], boot_means[upper_idx]


def main():
    parser = argparse.ArgumentParser(
        description="Compute bootstrap 95% CIs on mean scores by (model, condition)."
    )
    parser.add_argument("csv_file", type=Path, help="Path to scores CSV")
    parser.add_argument(
        "--output", "-o", type=Path, default=None,
        help="Write CI results to CSV (optional)",
    )
    parser.add_argument(
        "--score-column", "-s", type=str, default=None,
        help="Override auto-detected score column name",
    )
    args = parser.parse_args()

    if not args.csv_file.exists():
        print(f"File not found: {args.csv_file}")
        sys.exit(1)

    rows = read_csv(args.csv_file)
    if not rows:
        print("No data rows found.")
        sys.exit(1)

    score_col = args.score_column or detect_score_column(rows)
    print(f"Score column: {score_col}")
    print(f"Total rows: {len(rows)}")
    print(f"Bootstrap resamples: {N_BOOTSTRAP}")
    print()

    # Group by (model, condition)
    groups: dict[tuple[str, str], list[float]] = {}
    for row in rows:
        model = row.get("model", "")
        condition = row.get("condition", "")
        try:
            val = float(row[score_col])
        except (ValueError, TypeError):
            continue
        groups.setdefault((model, condition), []).append(val)

    # Compute CIs
    ci_rows = []
    for (model, condition) in sorted(groups.keys()):
        values = groups[(model, condition)]
        mean, lower, upper = bootstrap_mean_ci(values)
        ci_rows.append({
            "model": model,
            "condition": condition,
            "n": len(values),
            "mean": round(mean, 3),
            "ci_lower": round(lower, 3),
            "ci_upper": round(upper, 3),
        })

    # Print summary table
    conditions_order = ["none", "markdown", "pseudocode"]
    models = sorted(set(r["model"] for r in ci_rows))

    # Header
    header = f"{'Model':>30s}"
    for cond in conditions_order:
        header += f"  {'':>3s}{cond:>22s}"
    print(header)
    print("-" * len(header))

    for model in models:
        line = f"{model:>30s}"
        for cond in conditions_order:
            match = [r for r in ci_rows if r["model"] == model and r["condition"] == cond]
            if match:
                r = match[0]
                cell = f"{r['mean']:.1f} [{r['ci_lower']:.1f}, {r['ci_upper']:.1f}]"
                line += f"  n={r['n']:>2d} {cell:>19s}"
            else:
                line += f"  {'--':>25s}"
        print(line)

    # Write CSV if requested
    if args.output:
        ci_fields = ["model", "condition", "n", "mean", "ci_lower", "ci_upper"]
        with open(args.output, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=ci_fields)
            writer.writeheader()
            writer.writerows(ci_rows)
        print(f"\nCI results written to {args.output}")


if __name__ == "__main__":
    main()
