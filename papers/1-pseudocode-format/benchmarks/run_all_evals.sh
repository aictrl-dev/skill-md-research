#!/usr/bin/env bash
# Reproduce all CSVs, statistics, and figures from raw JSON outputs.
#
# Usage:  bash benchmarks/run_all_evals.sh
# Run from:  papers/1-pseudocode-format/
#
# Prerequisites: Python 3.10+, pandas, numpy, scipy, matplotlib

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PAPER_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=== Skill-MD Reproducibility Pipeline ==="
echo "Paper root: $PAPER_ROOT"
echo

# Domain evaluators import shared helpers from scripts/evaluate.py
export PYTHONPATH="${PAPER_ROOT}/scripts:${PYTHONPATH:-}"

# ── Helper ────────────────────────────────────────────────────────────────────

run_eval() {
    local domain="$1" zip_dir="$2" eval_cmd="$3"
    echo "[$domain] Extracting raw outputs..."
    unzip -qo "$zip_dir/raw_outputs.zip" -d "$zip_dir/"
    echo "[$domain] Running evaluator..."
    eval "$eval_cmd"
    echo "[$domain] Cleaning up extracted JSONs..."
    # Remove only the JSONs that were in the zip (preserve scores CSVs and zip)
    (cd "$zip_dir" && unzip -l raw_outputs.zip | awk 'NR>3 && /\.json$/{print $NF}' | xargs -r rm -f)
}

# ── 1. Chart domain ──────────────────────────────────────────────────────────
# evaluate_deep.py reads from scripts/results/ and writes scores_deep.csv there.
# We extract to scripts/results/, run the evaluator, then copy the CSV to where
# generate_figures.py expects it (domains/chart/results-v2/).

echo "[chart] Extracting raw outputs..."
mkdir -p "$PAPER_ROOT/scripts/results"
unzip -qo "$PAPER_ROOT/domains/chart/results-v2/raw_outputs.zip" \
    -d "$PAPER_ROOT/scripts/results/"

echo "[chart] Running evaluator (evaluate_deep.py)..."
(cd "$PAPER_ROOT/scripts" && python3 evaluate_deep.py)

echo "[chart] Copying scores to domains/chart/results-v2/..."
cp "$PAPER_ROOT/scripts/results/scores_deep.csv" \
   "$PAPER_ROOT/domains/chart/results-v2/scores_deep.csv"

echo "[chart] Cleaning up extracted JSONs..."
(cd "$PAPER_ROOT/scripts/results" && \
 unzip -l "$PAPER_ROOT/domains/chart/results-v2/raw_outputs.zip" \
   | awk 'NR>3 && /\.json$/{print $NF}' | xargs -r rm -f)
echo

# ── 2. Dockerfile domain ─────────────────────────────────────────────────────
run_eval "dockerfile" \
    "$PAPER_ROOT/domains/dockerfile/results" \
    "(cd '$PAPER_ROOT/domains/dockerfile' && python3 evaluate_dockerfile.py)"
echo

# ── 3. SQL domain ────────────────────────────────────────────────────────────
run_eval "sql-query" \
    "$PAPER_ROOT/domains/sql-query/results" \
    "(cd '$PAPER_ROOT/domains/sql-query' && python3 evaluate_sql.py)"
echo

# ── 4. Terraform domain ──────────────────────────────────────────────────────
run_eval "terraform" \
    "$PAPER_ROOT/domains/terraform/results" \
    "(cd '$PAPER_ROOT/domains/terraform' && python3 evaluate_terraform.py)"
echo

# ── 5. Compute paper statistics ──────────────────────────────────────────────
echo "[stats] Computing paper statistics..."
python3 "$PAPER_ROOT/paper/compute_stats.py"
echo

# ── 6. Generate figures ──────────────────────────────────────────────────────
echo "[figures] Generating publication figures..."
python3 "$PAPER_ROOT/scripts/generate_figures.py"
echo

# ── Summary ───────────────────────────────────────────────────────────────────
echo "=== Done ==="
echo
echo "Output files:"
for f in \
    domains/chart/results-v2/scores_deep.csv \
    domains/dockerfile/results/scores.csv \
    domains/sql-query/results/scores.csv \
    domains/terraform/results/scores.csv \
    paper/figures; do
    if [ -e "$PAPER_ROOT/$f" ]; then
        echo "  [OK] $f"
    else
        echo "  [MISSING] $f"
    fi
done
