#!/usr/bin/env python3
"""Generate an HTML report analysing token usage across all experiment domains.

Reads scores CSV files from each domain, computes per-condition and per-model
statistics for tokens, cost, and duration, and writes a self-contained HTML
report to paper/token_usage_report.html.
"""

import os
import sys
import math
import numpy as np
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "paper" / "token_usage_report.html"

DOMAIN_CSVS = {
    "chart": ROOT / "domains" / "chart" / "results-v2" / "scores_deep.csv",
    "dockerfile": ROOT / "domains" / "dockerfile" / "results" / "scores.csv",
    "sql-query": ROOT / "domains" / "sql-query" / "results" / "scores.csv",
    "terraform": ROOT / "domains" / "terraform" / "results" / "scores.csv",
}

CONDITION_ORDER = ["none", "markdown", "pseudocode"]
CONDITION_LABELS = {"none": "No Skill File", "markdown": "Markdown", "pseudocode": "Pseudocode"}

MODEL_LABELS = {
    "haiku": "Claude Haiku",
    "opus": "Claude Opus",
    "zai-coding-plan/glm-4.7": "GLM-4.7",
    "zai-coding-plan/glm-4.7-flash": "GLM-4.7-flash",
    "zai-coding-plan/glm-5": "GLM-5",
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_all():
    """Load and concatenate all domain CSVs, adding a 'domain' column."""
    frames = []
    for domain, path in DOMAIN_CSVS.items():
        df = pd.read_csv(path)
        df["domain"] = domain
        frames.append(df)
    all_df = pd.concat(frames, ignore_index=True)

    # Compute total_input_tokens = input_tokens + cache_read + cache_write
    for col in ("cache_read_tokens", "cache_write_tokens"):
        if col not in all_df.columns:
            all_df[col] = 0
    all_df["cache_read_tokens"] = all_df["cache_read_tokens"].fillna(0)
    all_df["cache_write_tokens"] = all_df["cache_write_tokens"].fillna(0)
    all_df["input_tokens"] = all_df["input_tokens"].fillna(0)
    all_df["output_tokens"] = all_df["output_tokens"].fillna(0)
    all_df["total_cost_usd"] = all_df["total_cost_usd"].fillna(0)
    all_df["duration_ms"] = all_df["duration_ms"].fillna(0)

    all_df["total_input_tokens"] = (
        all_df["input_tokens"] + all_df["cache_read_tokens"] + all_df["cache_write_tokens"]
    )
    all_df["total_tokens"] = all_df["total_input_tokens"] + all_df["output_tokens"]
    all_df["duration_s"] = all_df["duration_ms"] / 1000.0

    return all_df


def fmt_int(v):
    if pd.isna(v):
        return "&mdash;"
    return f"{int(round(v)):,}"


def fmt_float(v, decimals=4):
    if pd.isna(v):
        return "&mdash;"
    return f"{v:,.{decimals}f}"


def fmt_pct(v, decimals=1):
    if pd.isna(v):
        return "&mdash;"
    return f"{v:+.{decimals}f}%"


def fmt_dur(v):
    """Format duration in seconds."""
    if pd.isna(v):
        return "&mdash;"
    return f"{v:,.1f}s"


def color_cell(val, low, high, reverse=False):
    """Return a background-color CSS string. Green=good, red=bad.
    If reverse=True, lower is better (cost/tokens)."""
    if pd.isna(val) or pd.isna(low) or pd.isna(high) or high == low:
        return ""
    t = (val - low) / (high - low)
    if reverse:
        t = 1 - t
    # t=1 is green, t=0 is red
    r = int(255 - t * 100)
    g = int(155 + t * 100)
    b = int(155 - t * 10)
    return f"background-color: rgba({r},{g},{b},0.25);"


def pct_change_vs_none(group_df, metric, group_col):
    """Compute % change of markdown and pseudocode vs none for a metric."""
    rows = []
    for group_val in group_df[group_col].unique():
        sub = group_df[group_df[group_col] == group_val]
        none_val = sub[sub["condition"] == "none"][metric].values
        if len(none_val) == 0:
            continue
        none_val = none_val[0]
        for cond in ["markdown", "pseudocode"]:
            cond_val = sub[sub["condition"] == cond][metric].values
            if len(cond_val) == 0:
                continue
            cond_val = cond_val[0]
            if none_val and none_val > 0:
                pct = ((cond_val - none_val) / none_val) * 100
            else:
                pct = float("nan")
            rows.append({group_col: group_val, "condition": cond, f"{metric}_pct_change": pct})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# HTML Generation
# ---------------------------------------------------------------------------

def generate_report(df):
    sections = []

    # ---- Summary stats ----
    n_runs = len(df)
    n_models = df["model"].nunique()
    n_domains = df["domain"].nunique()
    total_cost = df["total_cost_usd"].sum()
    total_tokens = df["total_tokens"].sum()
    mean_cost = df["total_cost_usd"].mean()

    # Key finding: compare conditions across all data
    cond_stats = df.groupby("condition").agg(
        mean_output=("output_tokens", "mean"),
        mean_input=("total_input_tokens", "mean"),
        mean_cost=("total_cost_usd", "mean"),
        mean_dur=("duration_s", "mean"),
        total_cost=("total_cost_usd", "sum"),
    ).reindex(CONDITION_ORDER)

    none_out = cond_stats.loc["none", "mean_output"]
    md_out = cond_stats.loc["markdown", "mean_output"]
    ps_out = cond_stats.loc["pseudocode", "mean_output"]
    md_out_pct = ((md_out - none_out) / none_out) * 100
    ps_out_pct = ((ps_out - none_out) / none_out) * 100

    none_cost = cond_stats.loc["none", "mean_cost"]
    md_cost = cond_stats.loc["markdown", "mean_cost"]
    ps_cost = cond_stats.loc["pseudocode", "mean_cost"]
    md_cost_pct = ((md_cost - none_cost) / none_cost) * 100
    ps_cost_pct = ((ps_cost - none_cost) / none_cost) * 100

    none_inp = cond_stats.loc["none", "mean_input"]
    md_inp = cond_stats.loc["markdown", "mean_input"]
    ps_inp = cond_stats.loc["pseudocode", "mean_input"]
    md_inp_pct = ((md_inp - none_inp) / none_inp) * 100
    ps_inp_pct = ((ps_inp - none_inp) / none_inp) * 100

    none_dur = cond_stats.loc["none", "mean_dur"]
    md_dur = cond_stats.loc["markdown", "mean_dur"]
    ps_dur = cond_stats.loc["pseudocode", "mean_dur"]
    md_dur_pct = ((md_dur - none_dur) / none_dur) * 100
    ps_dur_pct = ((ps_dur - none_dur) / none_dur) * 100

    findings = []
    findings.append(f"Markdown skill files increase mean output tokens by <strong>{md_out_pct:+.1f}%</strong> vs. no skill file.")
    findings.append(f"Pseudocode skill files increase mean output tokens by <strong>{ps_out_pct:+.1f}%</strong> vs. no skill file.")
    findings.append(f"Markdown increases mean cost by <strong>{md_cost_pct:+.1f}%</strong>; pseudocode by <strong>{ps_cost_pct:+.1f}%</strong>.")
    findings.append(f"Markdown increases total input tokens by <strong>{md_inp_pct:+.1f}%</strong>; pseudocode by <strong>{ps_inp_pct:+.1f}%</strong>.")
    findings.append(f"Markdown changes mean duration by <strong>{md_dur_pct:+.1f}%</strong>; pseudocode by <strong>{ps_dur_pct:+.1f}%</strong>.")

    sections.append(f"""
    <div class="summary-box">
        <h2>Executive Summary</h2>
        <div class="stat-grid">
            <div class="stat-card"><div class="stat-num">{n_runs:,}</div><div class="stat-label">Total Runs</div></div>
            <div class="stat-card"><div class="stat-num">{n_models}</div><div class="stat-label">Models</div></div>
            <div class="stat-card"><div class="stat-num">{n_domains}</div><div class="stat-label">Domains</div></div>
            <div class="stat-card"><div class="stat-num">${total_cost:.2f}</div><div class="stat-label">Total Cost</div></div>
            <div class="stat-card"><div class="stat-num">{total_tokens:,.0f}</div><div class="stat-label">Total Tokens</div></div>
            <div class="stat-card"><div class="stat-num">${mean_cost:.4f}</div><div class="stat-label">Mean Cost/Run</div></div>
        </div>
        <h3>Key Findings (All Domains Pooled)</h3>
        <ul class="findings">
            {''.join(f'<li>{f}</li>' for f in findings)}
        </ul>
    </div>
    """)

    # ---- Section 1: Per-Condition Token Usage (each domain) ----
    sections.append('<h2 id="per-condition">1. Per-Condition Token Usage by Domain</h2>')
    sections.append('<p>Mean values per run. "Total Input" = input_tokens + cache_read + cache_write (full prompt size). % change relative to "none" condition.</p>')

    for domain in sorted(df["domain"].unique()):
        ddf = df[df["domain"] == domain]
        stats = ddf.groupby("condition").agg(
            n=("output_tokens", "count"),
            mean_input=("total_input_tokens", "mean"),
            std_input=("total_input_tokens", "std"),
            mean_output=("output_tokens", "mean"),
            std_output=("output_tokens", "std"),
            mean_cost=("total_cost_usd", "mean"),
            std_cost=("total_cost_usd", "std"),
            mean_dur=("duration_s", "mean"),
            std_dur=("duration_s", "std"),
        ).reindex(CONDITION_ORDER)

        none_row = stats.loc["none"]
        rows_html = ""
        for cond in CONDITION_ORDER:
            r = stats.loc[cond]
            inp_pct = ((r["mean_input"] - none_row["mean_input"]) / none_row["mean_input"] * 100) if none_row["mean_input"] > 0 else float("nan")
            out_pct = ((r["mean_output"] - none_row["mean_output"]) / none_row["mean_output"] * 100) if none_row["mean_output"] > 0 else float("nan")
            cost_pct = ((r["mean_cost"] - none_row["mean_cost"]) / none_row["mean_cost"] * 100) if none_row["mean_cost"] > 0 else float("nan")
            dur_pct = ((r["mean_dur"] - none_row["mean_dur"]) / none_row["mean_dur"] * 100) if none_row["mean_dur"] > 0 else float("nan")

            pct_class = lambda p: "pct-pos" if p > 2 else ("pct-neg" if p < -2 else "pct-neutral")

            rows_html += f"""<tr>
                <td><strong>{CONDITION_LABELS.get(cond, cond)}</strong></td>
                <td>{int(r['n'])}</td>
                <td>{fmt_int(r['mean_input'])} <span class="std">&plusmn;{fmt_int(r['std_input'])}</span></td>
                <td class="{pct_class(inp_pct)}">{fmt_pct(inp_pct) if cond != 'none' else '&mdash;'}</td>
                <td>{fmt_int(r['mean_output'])} <span class="std">&plusmn;{fmt_int(r['std_output'])}</span></td>
                <td class="{pct_class(out_pct)}">{fmt_pct(out_pct) if cond != 'none' else '&mdash;'}</td>
                <td>${fmt_float(r['mean_cost'])}</td>
                <td class="{pct_class(cost_pct)}">{fmt_pct(cost_pct) if cond != 'none' else '&mdash;'}</td>
                <td>{fmt_dur(r['mean_dur'])}</td>
                <td class="{pct_class(dur_pct)}">{fmt_pct(dur_pct) if cond != 'none' else '&mdash;'}</td>
            </tr>"""

        sections.append(f"""
        <h3>{domain.title().replace('-', ' ')}</h3>
        <table>
            <thead><tr>
                <th>Condition</th><th>N</th>
                <th>Mean Input Tokens</th><th>&Delta;%</th>
                <th>Mean Output Tokens</th><th>&Delta;%</th>
                <th>Mean Cost (USD)</th><th>&Delta;%</th>
                <th>Mean Duration</th><th>&Delta;%</th>
            </tr></thead>
            <tbody>{rows_html}</tbody>
        </table>
        """)

    # ---- Section 2: Per-Model Token Usage ----
    sections.append('<h2 id="per-model">2. Per-Model Token Usage (All Domains Pooled)</h2>')

    model_stats = df.groupby("model").agg(
        n=("output_tokens", "count"),
        mean_input=("total_input_tokens", "mean"),
        mean_output=("output_tokens", "mean"),
        mean_cost=("total_cost_usd", "mean"),
        mean_dur=("duration_s", "mean"),
        total_cost=("total_cost_usd", "sum"),
    ).sort_values("mean_cost", ascending=False)

    rows_html = ""
    for model in model_stats.index:
        r = model_stats.loc[model]
        rows_html += f"""<tr>
            <td><strong>{MODEL_LABELS.get(model, model)}</strong></td>
            <td>{int(r['n'])}</td>
            <td>{fmt_int(r['mean_input'])}</td>
            <td>{fmt_int(r['mean_output'])}</td>
            <td>${fmt_float(r['mean_cost'])}</td>
            <td>${fmt_float(r['total_cost'], 2)}</td>
            <td>{fmt_dur(r['mean_dur'])}</td>
        </tr>"""

    sections.append(f"""
    <table>
        <thead><tr>
            <th>Model</th><th>N</th>
            <th>Mean Input</th><th>Mean Output</th>
            <th>Mean Cost</th><th>Total Cost</th>
            <th>Mean Duration</th>
        </tr></thead>
        <tbody>{rows_html}</tbody>
    </table>
    """)

    # Per-model per-condition breakdown
    sections.append('<h3>Per-Model x Condition Breakdown</h3>')
    for model in sorted(df["model"].unique()):
        mdf = df[df["model"] == model]
        stats = mdf.groupby("condition").agg(
            n=("output_tokens", "count"),
            mean_input=("total_input_tokens", "mean"),
            mean_output=("output_tokens", "mean"),
            mean_cost=("total_cost_usd", "mean"),
            mean_dur=("duration_s", "mean"),
        ).reindex(CONDITION_ORDER).dropna(how="all")

        if "none" not in stats.index:
            continue
        none_row = stats.loc["none"]
        rows_html = ""
        for cond in CONDITION_ORDER:
            if cond not in stats.index:
                continue
            r = stats.loc[cond]
            out_pct = ((r["mean_output"] - none_row["mean_output"]) / none_row["mean_output"] * 100) if none_row["mean_output"] > 0 else float("nan")
            cost_pct = ((r["mean_cost"] - none_row["mean_cost"]) / none_row["mean_cost"] * 100) if none_row["mean_cost"] > 0 else float("nan")
            pct_class = lambda p: "pct-pos" if p > 2 else ("pct-neg" if p < -2 else "pct-neutral")
            rows_html += f"""<tr>
                <td>{CONDITION_LABELS.get(cond, cond)}</td>
                <td>{int(r['n'])}</td>
                <td>{fmt_int(r['mean_input'])}</td>
                <td>{fmt_int(r['mean_output'])}</td>
                <td class="{pct_class(out_pct)}">{fmt_pct(out_pct) if cond != 'none' else '&mdash;'}</td>
                <td>${fmt_float(r['mean_cost'])}</td>
                <td class="{pct_class(cost_pct)}">{fmt_pct(cost_pct) if cond != 'none' else '&mdash;'}</td>
                <td>{fmt_dur(r['mean_dur'])}</td>
            </tr>"""

        sections.append(f"""
        <h4>{MODEL_LABELS.get(model, model)}</h4>
        <table class="compact">
            <thead><tr>
                <th>Condition</th><th>N</th><th>Mean Input</th><th>Mean Output</th><th>&Delta;% Out</th>
                <th>Mean Cost</th><th>&Delta;% Cost</th><th>Mean Duration</th>
            </tr></thead>
            <tbody>{rows_html}</tbody>
        </table>
        """)

    # ---- Section 3: Condition x Model Heatmap (Output Tokens) ----
    sections.append('<h2 id="heatmap">3. Output Tokens Heatmap: Model &times; Condition</h2>')
    sections.append('<p>Mean output tokens per run. Cell colour intensity indicates relative magnitude (darker = more tokens).</p>')

    for domain in sorted(df["domain"].unique()):
        ddf = df[df["domain"] == domain]
        pivot = ddf.pivot_table(values="output_tokens", index="model", columns="condition", aggfunc="mean")
        pivot = pivot.reindex(columns=CONDITION_ORDER)

        all_vals = pivot.values.flatten()
        all_vals = all_vals[~np.isnan(all_vals)]
        vmin, vmax = all_vals.min(), all_vals.max()

        header = "<tr><th>Model</th>" + "".join(f"<th>{CONDITION_LABELS.get(c,c)}</th>" for c in CONDITION_ORDER) + "</tr>"
        body = ""
        for model in sorted(pivot.index):
            cells = ""
            for cond in CONDITION_ORDER:
                val = pivot.loc[model, cond] if cond in pivot.columns else float("nan")
                intensity = (val - vmin) / (vmax - vmin) if not pd.isna(val) and vmax > vmin else 0
                bg = f"background-color: rgba(66,133,244,{0.1 + intensity * 0.5});"
                cells += f'<td style="{bg}">{fmt_int(val)}</td>'
            body += f"<tr><td><strong>{MODEL_LABELS.get(model, model)}</strong></td>{cells}</tr>"

        sections.append(f"""
        <h3>{domain.title().replace('-', ' ')}</h3>
        <table class="heatmap"><thead>{header}</thead><tbody>{body}</tbody></table>
        """)

    # Pooled heatmap
    pivot_all = df.pivot_table(values="output_tokens", index="model", columns="condition", aggfunc="mean")
    pivot_all = pivot_all.reindex(columns=CONDITION_ORDER)
    all_vals = pivot_all.values.flatten()
    all_vals = all_vals[~np.isnan(all_vals)]
    vmin, vmax = all_vals.min(), all_vals.max()

    header = "<tr><th>Model</th>" + "".join(f"<th>{CONDITION_LABELS.get(c,c)}</th>" for c in CONDITION_ORDER) + "<th>&Delta;% (md vs none)</th><th>&Delta;% (ps vs none)</th></tr>"
    body = ""
    for model in sorted(pivot_all.index):
        cells = ""
        for cond in CONDITION_ORDER:
            val = pivot_all.loc[model, cond] if cond in pivot_all.columns else float("nan")
            intensity = (val - vmin) / (vmax - vmin) if not pd.isna(val) and vmax > vmin else 0
            bg = f"background-color: rgba(66,133,244,{0.1 + intensity * 0.5});"
            cells += f'<td style="{bg}">{fmt_int(val)}</td>'
        none_v = pivot_all.loc[model, "none"] if "none" in pivot_all.columns else float("nan")
        md_v = pivot_all.loc[model, "markdown"] if "markdown" in pivot_all.columns else float("nan")
        ps_v = pivot_all.loc[model, "pseudocode"] if "pseudocode" in pivot_all.columns else float("nan")
        md_pct = ((md_v - none_v) / none_v * 100) if not pd.isna(none_v) and none_v > 0 else float("nan")
        ps_pct = ((ps_v - none_v) / none_v * 100) if not pd.isna(none_v) and none_v > 0 else float("nan")
        pct_class = lambda p: "pct-pos" if p > 2 else ("pct-neg" if p < -2 else "pct-neutral")
        cells += f'<td class="{pct_class(md_pct)}">{fmt_pct(md_pct)}</td>'
        cells += f'<td class="{pct_class(ps_pct)}">{fmt_pct(ps_pct)}</td>'
        body += f"<tr><td><strong>{MODEL_LABELS.get(model, model)}</strong></td>{cells}</tr>"

    sections.append(f"""
    <h3>All Domains Pooled</h3>
    <table class="heatmap"><thead>{header}</thead><tbody>{body}</tbody></table>
    """)

    # ---- Section 4: Cost Analysis ----
    sections.append('<h2 id="cost">4. Cost Analysis</h2>')

    # Total cost by condition and domain
    cost_pivot = df.pivot_table(values="total_cost_usd", index="domain", columns="condition", aggfunc="sum")
    cost_pivot = cost_pivot.reindex(columns=CONDITION_ORDER)
    cost_pivot.loc["ALL DOMAINS"] = cost_pivot.sum()

    header = "<tr><th>Domain</th>" + "".join(f"<th>{CONDITION_LABELS.get(c,c)}</th>" for c in CONDITION_ORDER) + "<th>Total</th></tr>"
    body = ""
    for domain in list(cost_pivot.index):
        row_total = cost_pivot.loc[domain].sum()
        cells = ""
        for cond in CONDITION_ORDER:
            val = cost_pivot.loc[domain, cond] if cond in cost_pivot.columns else 0
            cells += f"<td>${fmt_float(val, 2)}</td>"
        cells += f"<td><strong>${fmt_float(row_total, 2)}</strong></td>"
        cls = ' class="total-row"' if domain == "ALL DOMAINS" else ""
        body += f"<tr{cls}><td><strong>{domain}</strong></td>{cells}</tr>"

    sections.append(f"""
    <h3>Total Cost by Domain &times; Condition (USD)</h3>
    <table><thead>{header}</thead><tbody>{body}</tbody></table>
    """)

    # Mean cost per run by model x condition
    cost_run = df.pivot_table(values="total_cost_usd", index="model", columns="condition", aggfunc="mean")
    cost_run = cost_run.reindex(columns=CONDITION_ORDER)

    all_vals = cost_run.values.flatten()
    all_vals = all_vals[~np.isnan(all_vals)]
    vmin, vmax = all_vals.min(), all_vals.max()

    header = "<tr><th>Model</th>" + "".join(f"<th>{CONDITION_LABELS.get(c,c)}</th>" for c in CONDITION_ORDER) + "</tr>"
    body = ""
    for model in sorted(cost_run.index):
        cells = ""
        for cond in CONDITION_ORDER:
            val = cost_run.loc[model, cond] if cond in cost_run.columns else float("nan")
            # Color: green = cheap, red = expensive
            if not pd.isna(val) and vmax > vmin:
                t = (val - vmin) / (vmax - vmin)
                r_c = int(155 + t * 100)
                g_c = int(255 - t * 100)
                bg = f"background-color: rgba({r_c},{g_c},155,0.3);"
            else:
                bg = ""
            cells += f'<td style="{bg}">${fmt_float(val)}</td>'
        body += f"<tr><td><strong>{MODEL_LABELS.get(model, model)}</strong></td>{cells}</tr>"

    sections.append(f"""
    <h3>Mean Cost per Run: Model &times; Condition (USD)</h3>
    <table class="heatmap"><thead>{header}</thead><tbody>{body}</tbody></table>
    """)

    # ---- Section 4b: Claude-only Cost Analysis ----
    sections.append('<h3>Claude-Only Cost Analysis (Haiku + Opus)</h3>')
    sections.append('<p>Since GLM models report zero cost, this isolates cost effects for Claude models only.</p>')

    claude_df = df[df["model"].isin(["haiku", "opus"])]
    claude_cond = claude_df.groupby("condition").agg(
        n=("total_cost_usd", "count"),
        mean_cost=("total_cost_usd", "mean"),
        median_cost=("total_cost_usd", "median"),
        total_cost=("total_cost_usd", "sum"),
        mean_output=("output_tokens", "mean"),
        mean_input=("total_input_tokens", "mean"),
    ).reindex(CONDITION_ORDER)

    none_c = claude_cond.loc["none"]
    rows_html = ""
    for cond in CONDITION_ORDER:
        r = claude_cond.loc[cond]
        cost_pct = ((r["mean_cost"] - none_c["mean_cost"]) / none_c["mean_cost"] * 100) if none_c["mean_cost"] > 0 else float("nan")
        out_pct = ((r["mean_output"] - none_c["mean_output"]) / none_c["mean_output"] * 100) if none_c["mean_output"] > 0 else float("nan")
        inp_pct = ((r["mean_input"] - none_c["mean_input"]) / none_c["mean_input"] * 100) if none_c["mean_input"] > 0 else float("nan")
        pct_class_fn = lambda p: "pct-pos" if p > 2 else ("pct-neg" if p < -2 else "pct-neutral")
        rows_html += f"""<tr>
            <td><strong>{CONDITION_LABELS.get(cond, cond)}</strong></td>
            <td>{int(r['n'])}</td>
            <td>{fmt_int(r['mean_input'])}</td>
            <td class="{pct_class_fn(inp_pct)}">{fmt_pct(inp_pct) if cond != 'none' else '&mdash;'}</td>
            <td>{fmt_int(r['mean_output'])}</td>
            <td class="{pct_class_fn(out_pct)}">{fmt_pct(out_pct) if cond != 'none' else '&mdash;'}</td>
            <td>${fmt_float(r['mean_cost'])}</td>
            <td class="{pct_class_fn(cost_pct)}">{fmt_pct(cost_pct) if cond != 'none' else '&mdash;'}</td>
            <td>${fmt_float(r['total_cost'], 2)}</td>
        </tr>"""

    sections.append(f"""
    <table>
        <thead><tr>
            <th>Condition</th><th>N</th>
            <th>Mean Input</th><th>&Delta;%</th>
            <th>Mean Output</th><th>&Delta;%</th>
            <th>Mean Cost</th><th>&Delta;%</th>
            <th>Total Cost</th>
        </tr></thead>
        <tbody>{rows_html}</tbody>
    </table>
    """)

    # ---- Section 5: Duration Analysis ----
    sections.append('<h2 id="duration">5. Duration Analysis</h2>')
    sections.append("""<div class="note"><strong>Note on outliers:</strong> Some GLM-4.7-flash runs have extreme
    durations (up to ~66 minutes for a single run in Terraform). These outliers heavily skew the mean for the
    "none" condition. Median values are more robust. The apparent duration <em>decrease</em> with skill files
    in the Executive Summary is driven by these GLM outliers in the baseline.</div>""")

    for domain in sorted(df["domain"].unique()):
        ddf = df[df["domain"] == domain]
        stats = ddf.groupby("condition").agg(
            mean_dur=("duration_s", "mean"),
            median_dur=("duration_s", "median"),
            std_dur=("duration_s", "std"),
            p95_dur=("duration_s", lambda x: x.quantile(0.95)),
        ).reindex(CONDITION_ORDER)

        none_row = stats.loc["none"]
        rows_html = ""
        for cond in CONDITION_ORDER:
            r = stats.loc[cond]
            dur_pct = ((r["mean_dur"] - none_row["mean_dur"]) / none_row["mean_dur"] * 100) if none_row["mean_dur"] > 0 else float("nan")
            pct_class = lambda p: "pct-pos" if p > 2 else ("pct-neg" if p < -2 else "pct-neutral")
            rows_html += f"""<tr>
                <td>{CONDITION_LABELS.get(cond, cond)}</td>
                <td>{fmt_dur(r['mean_dur'])}</td>
                <td class="{pct_class(dur_pct)}">{fmt_pct(dur_pct) if cond != 'none' else '&mdash;'}</td>
                <td>{fmt_dur(r['median_dur'])}</td>
                <td>{fmt_dur(r['std_dur'])}</td>
                <td>{fmt_dur(r['p95_dur'])}</td>
            </tr>"""

        sections.append(f"""
        <h3>{domain.title().replace('-', ' ')}</h3>
        <table>
            <thead><tr><th>Condition</th><th>Mean</th><th>&Delta;%</th><th>Median</th><th>Std Dev</th><th>P95</th></tr></thead>
            <tbody>{rows_html}</tbody>
        </table>
        """)

    # Duration by model
    sections.append('<h3>Mean Duration by Model (All Domains)</h3>')
    dur_model = df.pivot_table(values="duration_s", index="model", columns="condition", aggfunc="mean")
    dur_model = dur_model.reindex(columns=CONDITION_ORDER)

    header = "<tr><th>Model</th>" + "".join(f"<th>{CONDITION_LABELS.get(c,c)}</th>" for c in CONDITION_ORDER) + "<th>&Delta;% (md)</th><th>&Delta;% (ps)</th></tr>"
    body = ""
    for model in sorted(dur_model.index):
        cells = ""
        for cond in CONDITION_ORDER:
            val = dur_model.loc[model, cond] if cond in dur_model.columns else float("nan")
            cells += f"<td>{fmt_dur(val)}</td>"
        none_v = dur_model.loc[model, "none"] if "none" in dur_model.columns else float("nan")
        md_v = dur_model.loc[model, "markdown"] if "markdown" in dur_model.columns else float("nan")
        ps_v = dur_model.loc[model, "pseudocode"] if "pseudocode" in dur_model.columns else float("nan")
        md_pct = ((md_v - none_v) / none_v * 100) if not pd.isna(none_v) and none_v > 0 else float("nan")
        ps_pct = ((ps_v - none_v) / none_v * 100) if not pd.isna(none_v) and none_v > 0 else float("nan")
        pct_class = lambda p: "pct-pos" if p > 2 else ("pct-neg" if p < -2 else "pct-neutral")
        cells += f'<td class="{pct_class(md_pct)}">{fmt_pct(md_pct)}</td>'
        cells += f'<td class="{pct_class(ps_pct)}">{fmt_pct(ps_pct)}</td>'
        body += f"<tr><td><strong>{MODEL_LABELS.get(model, model)}</strong></td>{cells}</tr>"

    sections.append(f"""
    <table><thead>{header}</thead><tbody>{body}</tbody></table>
    """)

    # ---- Section 6: Key Question Analysis ----
    sections.append('<h2 id="key-question">6. Key Question: Token Efficiency of Skill Files</h2>')
    sections.append("""<p><strong>Question:</strong> Do skill files (markdown/pseudocode) cost more input tokens
    (longer prompt) but produce shorter/more efficient outputs? Or do they produce longer outputs too?</p>""")

    # Per-domain analysis
    for domain in sorted(df["domain"].unique()):
        ddf = df[df["domain"] == domain]
        cond_stats = ddf.groupby("condition").agg(
            mean_input=("total_input_tokens", "mean"),
            mean_output=("output_tokens", "mean"),
            mean_cost=("total_cost_usd", "mean"),
            mean_dur=("duration_s", "mean"),
        ).reindex(CONDITION_ORDER)

        none = cond_stats.loc["none"]
        analysis_rows = ""
        for cond in ["markdown", "pseudocode"]:
            r = cond_stats.loc[cond]
            inp_d = ((r["mean_input"] - none["mean_input"]) / none["mean_input"] * 100)
            out_d = ((r["mean_output"] - none["mean_output"]) / none["mean_output"] * 100)
            cost_d = ((r["mean_cost"] - none["mean_cost"]) / none["mean_cost"] * 100)
            dur_d = ((r["mean_dur"] - none["mean_dur"]) / none["mean_dur"] * 100)

            # Determine narrative
            if out_d < -2:
                out_narrative = "shorter (more efficient)"
                out_icon = "good"
            elif out_d > 2:
                out_narrative = "longer"
                out_icon = "neutral"
            else:
                out_narrative = "similar"
                out_icon = "neutral"

            analysis_rows += f"""<tr>
                <td><strong>{CONDITION_LABELS[cond]}</strong></td>
                <td class="{'pct-pos' if inp_d > 2 else 'pct-neg' if inp_d < -2 else 'pct-neutral'}">{fmt_pct(inp_d)}</td>
                <td class="{'pct-neg' if out_d < -2 else 'pct-pos' if out_d > 2 else 'pct-neutral'}">{fmt_pct(out_d)}</td>
                <td class="{'pct-neg' if cost_d < -2 else 'pct-pos' if cost_d > 2 else 'pct-neutral'}">{fmt_pct(cost_d)}</td>
                <td class="{'pct-neg' if dur_d < -2 else 'pct-pos' if dur_d > 2 else 'pct-neutral'}">{fmt_pct(dur_d)}</td>
                <td>{out_narrative}</td>
            </tr>"""

        sections.append(f"""
        <h3>{domain.title().replace('-', ' ')}</h3>
        <table>
            <thead><tr><th>Condition</th><th>&Delta; Input</th><th>&Delta; Output</th><th>&Delta; Cost</th><th>&Delta; Duration</th><th>Output Verdict</th></tr></thead>
            <tbody>{analysis_rows}</tbody>
        </table>
        """)

    # Overall verdict
    overall_cond = df.groupby("condition").agg(
        mean_input=("total_input_tokens", "mean"),
        mean_output=("output_tokens", "mean"),
        mean_cost=("total_cost_usd", "mean"),
    ).reindex(CONDITION_ORDER)
    none_o = overall_cond.loc["none"]

    sections.append("""
    <h3>Overall Verdict</h3>
    <div class="verdict-box">
    """)

    for cond in ["markdown", "pseudocode"]:
        r = overall_cond.loc[cond]
        inp_d = ((r["mean_input"] - none_o["mean_input"]) / none_o["mean_input"] * 100)
        out_d = ((r["mean_output"] - none_o["mean_output"]) / none_o["mean_output"] * 100)
        cost_d = ((r["mean_cost"] - none_o["mean_cost"]) / none_o["mean_cost"] * 100)

        sections.append(f"""
        <p><strong>{CONDITION_LABELS[cond]}:</strong>
        Input tokens change: <span class="{'pct-pos' if inp_d > 0 else 'pct-neg'}">{fmt_pct(inp_d)}</span>,
        Output tokens change: <span class="{'pct-pos' if out_d > 0 else 'pct-neg'}">{fmt_pct(out_d)}</span>,
        Cost change: <span class="{'pct-pos' if cost_d > 0 else 'pct-neg'}">{fmt_pct(cost_d)}</span></p>
        """)

    sections.append("</div>")

    # ---- Section 7: Per-Domain Per-Model detailed tables ----
    sections.append('<h2 id="detailed">7. Detailed Per-Domain Per-Model Breakdown</h2>')

    for domain in sorted(df["domain"].unique()):
        ddf = df[df["domain"] == domain]
        sections.append(f'<h3>{domain.title().replace("-", " ")}</h3>')

        pivot = ddf.pivot_table(
            values=["total_input_tokens", "output_tokens", "total_cost_usd", "duration_s"],
            index="model",
            columns="condition",
            aggfunc="mean",
        )

        header = "<tr><th rowspan='2'>Model</th>"
        for cond in CONDITION_ORDER:
            header += f"<th colspan='4'>{CONDITION_LABELS.get(cond, cond)}</th>"
        header += "</tr><tr>"
        for _ in CONDITION_ORDER:
            header += "<th>Input</th><th>Output</th><th>Cost</th><th>Duration</th>"
        header += "</tr>"

        body = ""
        for model in sorted(pivot.index):
            cells = ""
            for cond in CONDITION_ORDER:
                try:
                    inp = pivot.loc[model, ("total_input_tokens", cond)]
                except KeyError:
                    inp = float("nan")
                try:
                    out = pivot.loc[model, ("output_tokens", cond)]
                except KeyError:
                    out = float("nan")
                try:
                    cost = pivot.loc[model, ("total_cost_usd", cond)]
                except KeyError:
                    cost = float("nan")
                try:
                    dur = pivot.loc[model, ("duration_s", cond)]
                except KeyError:
                    dur = float("nan")
                cells += f"<td>{fmt_int(inp)}</td><td>{fmt_int(out)}</td><td>${fmt_float(cost)}</td><td>{fmt_dur(dur)}</td>"
            body += f"<tr><td><strong>{MODEL_LABELS.get(model, model)}</strong></td>{cells}</tr>"

        sections.append(f"""
        <div class="table-scroll">
        <table class="compact"><thead>{header}</thead><tbody>{body}</tbody></table>
        </div>
        """)

    # ---- Assemble HTML ----
    content = "\n".join(sections)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Token Usage Analysis &mdash; Skill File Experiment</title>
<style>
    :root {{
        --bg: #fafbfc;
        --card-bg: #ffffff;
        --border: #e1e4e8;
        --text: #24292e;
        --text-secondary: #586069;
        --accent: #0366d6;
        --green: #28a745;
        --red: #d73a49;
        --orange: #e36209;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
        background: var(--bg);
        color: var(--text);
        line-height: 1.6;
        padding: 2rem;
        max-width: 1400px;
        margin: 0 auto;
    }}
    h1 {{
        font-size: 1.8rem;
        border-bottom: 2px solid var(--accent);
        padding-bottom: 0.5rem;
        margin-bottom: 1.5rem;
    }}
    h2 {{
        font-size: 1.4rem;
        margin-top: 2.5rem;
        margin-bottom: 1rem;
        color: var(--accent);
        border-bottom: 1px solid var(--border);
        padding-bottom: 0.3rem;
    }}
    h3 {{
        font-size: 1.15rem;
        margin-top: 1.5rem;
        margin-bottom: 0.5rem;
        color: var(--text);
    }}
    h4 {{
        font-size: 1.05rem;
        margin-top: 1rem;
        margin-bottom: 0.4rem;
        color: var(--text-secondary);
    }}
    p {{ margin-bottom: 0.8rem; color: var(--text-secondary); }}
    table {{
        width: 100%;
        border-collapse: collapse;
        margin-bottom: 1.5rem;
        background: var(--card-bg);
        border-radius: 6px;
        overflow: hidden;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
        font-size: 0.9rem;
    }}
    table.compact {{ font-size: 0.82rem; }}
    th, td {{
        padding: 0.55rem 0.75rem;
        text-align: right;
        border-bottom: 1px solid var(--border);
    }}
    th {{
        background: #f6f8fa;
        font-weight: 600;
        text-align: right;
        white-space: nowrap;
    }}
    td:first-child, th:first-child {{
        text-align: left;
    }}
    tr:hover {{ background: rgba(3,102,214,0.04); }}
    tr.total-row {{ background: #f0f4ff; font-weight: 600; }}
    .std {{ color: #999; font-size: 0.85em; }}
    .pct-pos {{ color: var(--red); font-weight: 600; }}
    .pct-neg {{ color: var(--green); font-weight: 600; }}
    .pct-neutral {{ color: var(--text-secondary); }}
    .summary-box {{
        background: var(--card-bg);
        border: 1px solid var(--border);
        border-radius: 8px;
        padding: 1.5rem;
        margin-bottom: 2rem;
        box-shadow: 0 1px 5px rgba(0,0,0,0.06);
    }}
    .stat-grid {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
        gap: 1rem;
        margin-bottom: 1.5rem;
    }}
    .stat-card {{
        text-align: center;
        padding: 1rem;
        background: #f6f8fa;
        border-radius: 6px;
        border: 1px solid var(--border);
    }}
    .stat-num {{
        font-size: 1.5rem;
        font-weight: 700;
        color: var(--accent);
    }}
    .stat-label {{
        font-size: 0.85rem;
        color: var(--text-secondary);
        margin-top: 0.2rem;
    }}
    .findings {{
        list-style: none;
        padding: 0;
    }}
    .findings li {{
        padding: 0.4rem 0;
        padding-left: 1.2rem;
        position: relative;
    }}
    .findings li::before {{
        content: "\\25B6";
        position: absolute;
        left: 0;
        color: var(--accent);
        font-size: 0.7rem;
        top: 0.55rem;
    }}
    .verdict-box {{
        background: #f0f7ff;
        border: 1px solid #c8e1ff;
        border-radius: 6px;
        padding: 1rem 1.5rem;
        margin: 1rem 0;
    }}
    .table-scroll {{
        overflow-x: auto;
    }}
    table.heatmap td {{
        font-weight: 600;
        text-align: center;
    }}
    table.heatmap th {{
        text-align: center;
    }}
    .nav {{
        position: sticky;
        top: 0;
        background: var(--bg);
        padding: 0.5rem 0;
        margin-bottom: 1rem;
        border-bottom: 1px solid var(--border);
        z-index: 100;
        font-size: 0.9rem;
    }}
    .nav a {{
        color: var(--accent);
        text-decoration: none;
        margin-right: 1.5rem;
    }}
    .nav a:hover {{ text-decoration: underline; }}
    .note {{
        background: #fffbdd;
        border: 1px solid #f9c513;
        border-radius: 4px;
        padding: 0.75rem 1rem;
        margin: 1rem 0;
        font-size: 0.9rem;
    }}
    footer {{
        margin-top: 3rem;
        padding-top: 1rem;
        border-top: 1px solid var(--border);
        color: var(--text-secondary);
        font-size: 0.85rem;
    }}
</style>
</head>
<body>

<h1>Token Usage Analysis &mdash; Skill File Experiment</h1>
<p>Generated from scores CSV data across 4 domains. Evaluates token efficiency for RQ4.</p>

<div class="nav">
    <a href="#per-condition">Per-Condition</a>
    <a href="#per-model">Per-Model</a>
    <a href="#heatmap">Heatmap</a>
    <a href="#cost">Cost</a>
    <a href="#duration">Duration</a>
    <a href="#key-question">Key Question</a>
    <a href="#detailed">Detailed</a>
</div>

<div class="note">
    <strong>Note on input tokens:</strong> For Claude models (Haiku, Opus), most prompt tokens appear as <code>cache_read_tokens</code> + <code>cache_write_tokens</code>,
    with <code>input_tokens</code> showing only the uncached portion. "Total Input" = input_tokens + cache_read + cache_write.
    For GLM models, all prompt tokens appear in <code>input_tokens</code>. Cost figures include all token types.
</div>

<div class="note">
    <strong>Note on cost data:</strong> GLM models (zai-coding-plan) report <code>total_cost_usd = 0</code> in all runs
    (likely self-hosted or cost not tracked by the CLI). Cost analysis is therefore meaningful only for Claude Haiku and Opus.
    Token counts and durations are available for all models.
</div>

{content}

<footer>
    Report generated on 2026-02-22 &bull; Data from {n_runs} experiment runs across {n_domains} domains and {n_models} models.
</footer>

</body>
</html>"""

    return html


def main():
    df = load_all()
    html = generate_report(df)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(html)
    print(f"Report written to {OUTPUT}")
    print(f"  Total runs: {len(df)}")
    print(f"  Domains: {sorted(df['domain'].unique())}")
    print(f"  Models: {sorted(df['model'].unique())}")


if __name__ == "__main__":
    main()
