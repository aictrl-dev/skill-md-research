#!/usr/bin/env python3
"""
Evaluate experiment results: validate JSON, apply automated rule checks, output CSV.

Usage:
    python evaluate.py                  # Process all results in results/
    python evaluate.py results/foo.json # Process specific file(s)
"""

import csv
import json
import os
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
RESULTS_DIR = SCRIPT_DIR / "results"
OUTPUT_CSV = RESULTS_DIR / "scores.csv"

# ─── Token Usage Extraction ──────────────────────────────────────────────────

TOKEN_FIELDS = [
    "input_tokens",
    "output_tokens",
    "cache_read_tokens",
    "cache_write_tokens",
    "total_cost_usd",
]


def extract_token_usage(raw_output: str) -> dict:
    """Extract token usage from raw CLI output.

    Handles two formats:
    - Claude CLI: single JSON with usage.input_tokens etc. and total_cost_usd
    - Opencode CLI: JSONL with step_finish event containing part.tokens and part.cost

    Returns normalized dict with keys from TOKEN_FIELDS.
    Missing values are empty string (for CSV compatibility).
    """
    result = {k: "" for k in TOKEN_FIELDS}

    if not raw_output:
        return result

    # Try Claude CLI format: single JSON object
    try:
        cli = json.loads(raw_output)
        if isinstance(cli, dict) and "usage" in cli:
            usage = cli["usage"]
            result["input_tokens"] = usage.get("input_tokens", "")
            result["output_tokens"] = usage.get("output_tokens", "")
            result["cache_read_tokens"] = usage.get("cache_read_input_tokens", "")
            result["cache_write_tokens"] = usage.get("cache_creation_input_tokens", "")
            result["total_cost_usd"] = cli.get("total_cost_usd", "")
            return result
    except json.JSONDecodeError:
        pass

    # Try Opencode CLI format: JSONL with step_finish event
    if "\n" in raw_output and raw_output.lstrip().startswith("{"):
        for line in raw_output.strip().split("\n"):
            try:
                evt = json.loads(line)
                if isinstance(evt, dict) and evt.get("type") == "step_finish":
                    part = evt.get("part", {})
                    tokens = part.get("tokens", {})
                    cache = tokens.get("cache", {})
                    result["input_tokens"] = tokens.get("input", "")
                    result["output_tokens"] = tokens.get("output", "")
                    result["cache_read_tokens"] = cache.get("read", "")
                    result["cache_write_tokens"] = cache.get("write", "")
                    result["total_cost_usd"] = part.get("cost", "")
                    return result
            except (json.JSONDecodeError, KeyError):
                continue

    return result


# ─── Permission Denials Fallback ─────────────────────────────────────────────

def extract_from_permission_denials(raw_output: str) -> str | None:
    """Extract content from tool write attempts when model tried to write a file.

    Handles two formats:
    1. Claude CLI: single JSON with permission_denials[].tool_input.content
    2. Opencode CLI: JSONL with tool_use events where part.tool="write" and
       part.state.input.content contains the file content.

    Returns the extracted text content, or None if no useful content found.
    """
    if not raw_output:
        return None

    candidates = []

    # Format 1: Claude CLI JSON with permission_denials
    try:
        cli_response = json.loads(raw_output)
        if isinstance(cli_response, dict):
            denials = cli_response.get("permission_denials", [])
            for denial in denials:
                if denial.get("tool_name") != "Write":
                    continue
                tool_input = denial.get("tool_input") or {}
                content = tool_input.get("content", "")
                if isinstance(content, str) and len(content) > 20:
                    candidates.append(content)
    except json.JSONDecodeError:
        pass

    # Format 2: Opencode JSONL with tool_use write events
    if not candidates and "\n" in raw_output and raw_output.lstrip().startswith("{"):
        for line in raw_output.strip().split("\n"):
            try:
                evt = json.loads(line)
                if not isinstance(evt, dict) or evt.get("type") != "tool_use":
                    continue
                part = evt.get("part", {})
                if part.get("tool") != "write":
                    continue
                state = part.get("state", {})
                inp = state.get("input", {})
                content = inp.get("content", "")
                if isinstance(content, str) and len(content) > 20:
                    candidates.append(content)
            except (json.JSONDecodeError, KeyError):
                continue

    if not candidates:
        return None

    # Return the longest candidate (most complete output)
    return max(candidates, key=len)


# ─── JSON Extraction ─────────────────────────────────────────────────────────

def extract_json(raw_output: str) -> tuple[dict | None, str | None]:
    """Extract chart JSON from raw output.

    The raw_output is the full Claude CLI JSON response. The chart spec
    is embedded in the 'result' field, typically wrapped in markdown fences.
    """
    if not raw_output:
        return None, "empty output"

    # Step 0: If raw_output is opencode JSONL (newline-delimited JSON events),
    # extract text from the "text" event type
    text_to_search = raw_output
    if '\n' in raw_output and raw_output.lstrip().startswith('{'):
        lines = raw_output.strip().split('\n')
        text_parts = []
        is_jsonl = False
        for line in lines:
            try:
                evt = json.loads(line)
                if isinstance(evt, dict) and 'type' in evt and 'sessionID' in evt:
                    is_jsonl = True
                    if evt['type'] == 'text':
                        text_parts.append(evt['part']['text'])
            except (json.JSONDecodeError, KeyError):
                continue
        if is_jsonl:
            text_to_search = '\n'.join(text_parts) if text_parts else ""

    # Step 1: If raw_output is a Claude CLI JSON response, extract the 'result' field
    cli_response = None
    try:
        cli_response = json.loads(raw_output)
        if isinstance(cli_response, dict) and "result" in cli_response:
            text_to_search = cli_response["result"]
    except json.JSONDecodeError:
        pass

    # Step 1b: Check permission_denials for chart JSON (Write tool denials contain
    # the chart spec in tool_input.content when model tried to write a file)
    if cli_response and isinstance(cli_response, dict):
        for denial in cli_response.get("permission_denials", []):
            content = (denial.get("tool_input") or {}).get("content", "")
            if isinstance(content, str) and len(content) > 50:
                try:
                    obj = json.loads(content)
                    if isinstance(obj, dict) and ("chart_type" in obj or "title" in obj):
                        return obj, None
                except json.JSONDecodeError:
                    pass

    # Step 2: Try extracting from markdown code fences (most common)
    patterns = [
        r"```json\s*\n(.*?)\n\s*```",
        r"```\s*\n(.*?)\n\s*```",
    ]
    for pattern in patterns:
        match = re.search(pattern, text_to_search, re.DOTALL)
        if match:
            try:
                obj = json.loads(match.group(1))
                if isinstance(obj, dict):
                    return obj, None
            except json.JSONDecodeError:
                continue

    # Step 3: Try direct parse
    try:
        obj = json.loads(text_to_search)
        if isinstance(obj, dict):
            return obj, None
    except json.JSONDecodeError:
        pass

    # Step 4: Try finding first { ... } block
    brace_start = text_to_search.find("{")
    if brace_start >= 0:
        depth = 0
        for i in range(brace_start, len(text_to_search)):
            if text_to_search[i] == "{":
                depth += 1
            elif text_to_search[i] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        obj = json.loads(text_to_search[brace_start : i + 1])
                        if isinstance(obj, dict):
                            return obj, None
                    except json.JSONDecodeError:
                        break

    return None, "could not extract valid JSON"


# ─── Schema Validation ───────────────────────────────────────────────────────

def validate_schema(chart: dict) -> tuple[bool, list[str]]:
    """Check that essential chart fields are present (flexible naming)."""
    errors = []

    # Title: accept title, title.text, or chart.title
    has_title = False
    if "title" in chart:
        has_title = True
    if not has_title:
        errors.append("missing title field")

    # Source: accept source, source.data, metadata.source
    has_source = False
    if "source" in chart:
        has_source = True
    elif isinstance(chart.get("metadata"), dict) and "source" in chart["metadata"]:
        has_source = True
    elif isinstance(chart.get("config"), dict):
        # Vega-Lite puts source in config or as text annotation
        has_source = True  # be lenient with Vega-Lite specs
    if not has_source:
        errors.append("missing source field")

    # Chart type: accept chart_type, chartType, type, mark, mark.type
    has_type = False
    for key in ["chart_type", "chartType", "type"]:
        if key in chart:
            has_type = True
            break
    if not has_type:
        # Vega-Lite uses "mark" or "mark.type"
        mark = chart.get("mark")
        if mark is not None:
            has_type = True
    if not has_type:
        errors.append("missing chart type field")

    # Data: accept data, series, datasets, or Vega-Lite data.values
    has_data = False
    if "data" in chart or "series" in chart:
        has_data = True
    elif isinstance(chart.get("data"), dict) and "values" in chart["data"]:
        has_data = True
    if not has_data:
        errors.append("missing data field")

    return len(errors) == 0, errors


# ─── Automated Rule Checks ──────────────────────────────────────────────────
#
# Rules that can be checked programmatically from JSON output:
#   Rule 5:  Title is full sentence (>20 chars, doesn't end with ":")
#   Rule 6:  Source field present and non-empty
#   Rule 9:  Y-axis min = 0 for bar charts
#   Rule 10: No top/right spine flags
#   Rule 15: Aspect ratio appropriate for chart type

def _extract_title_text(chart: dict) -> str:
    """Extract title text from various JSON structures."""
    title = chart.get("title", {})
    if isinstance(title, str):
        return title
    if isinstance(title, dict):
        return title.get("text", "")
    # Vega-Lite: chart.title can be absent, check config
    return ""


def check_rule_5_title(chart: dict) -> tuple[bool, str]:
    """Rule 5: Title is a full sentence."""
    text = _extract_title_text(chart)

    if not text:
        return False, "title text is empty"
    if len(text) < 20:
        return False, f"title too short ({len(text)} chars < 20)"
    if text.rstrip().endswith(":"):
        return False, "title ends with colon (label, not sentence)"

    return True, "ok"


def check_rule_6_source(chart: dict) -> tuple[bool, str]:
    """Rule 6: Source attribution present and non-empty."""
    # Direct source field
    source = chart.get("source")
    if source is not None:
        if isinstance(source, str) and len(source.strip()) > 0:
            return True, "ok"
        if isinstance(source, dict):
            data = source.get("data", source.get("text", ""))
            if isinstance(data, str) and len(data.strip()) > 0:
                return True, "ok"

    # metadata.source
    metadata = chart.get("metadata", {})
    if isinstance(metadata, dict):
        src = metadata.get("source", "")
        if isinstance(src, str) and len(src.strip()) > 0:
            return True, "ok"

    # Vega-Lite config or layer annotations
    config = chart.get("config", {})
    if isinstance(config, dict):
        # Check for source in subtitle or annotations
        title = chart.get("title", {})
        if isinstance(title, dict):
            subtitle = title.get("subtitle", "")
            if isinstance(subtitle, str) and "source" in subtitle.lower():
                return True, "ok (in subtitle)"

    return False, "source field missing or empty"


def _get_chart_type(chart: dict) -> str:
    """Extract chart type from various JSON structures."""
    for key in ["chart_type", "chartType", "type"]:
        val = chart.get(key, "")
        if isinstance(val, str) and val:
            return val.lower()
    # Vega-Lite: mark field
    mark = chart.get("mark", "")
    if isinstance(mark, str):
        return mark.lower()
    if isinstance(mark, dict):
        return mark.get("type", "").lower()
    return ""


def check_rule_9_y_zero(chart: dict) -> tuple[bool, str]:
    """Rule 9: Y-axis starts at 0 for bar charts."""
    chart_type = _get_chart_type(chart)
    if chart_type != "bar":
        return True, "n/a (not bar chart)"

    # Check y_axis, axes.y, scales.y, encoding.y
    y_axis = chart.get("y_axis", chart.get("yAxis", {}))
    if not isinstance(y_axis, dict):
        axes = chart.get("axes", {})
        if isinstance(axes, dict):
            y_axis = axes.get("y", {})

    if isinstance(y_axis, dict):
        y_min = y_axis.get("min", y_axis.get("beginAtZero"))
        if y_min is not None:
            if y_min == True or y_min == 0:
                return True, "ok (y starts at 0)"
            if isinstance(y_min, (int, float)) and y_min != 0:
                return False, f"bar chart y_min={y_min}, should be 0"

    # Vega-Lite: check encoding.y.scale.zero
    encoding = chart.get("encoding", {})
    if isinstance(encoding, dict):
        y_enc = encoding.get("y", {})
        if isinstance(y_enc, dict):
            scale = y_enc.get("scale", {})
            if isinstance(scale, dict) and scale.get("zero") == False:
                return False, "bar chart scale.zero=false"

    return True, "needs_review (no explicit y config)"


def check_rule_10_spines(chart: dict) -> tuple[bool, str]:
    """Rule 10: No top/right spine."""
    # Check for explicit spine config
    spines = chart.get("spines", {})
    if isinstance(spines, dict):
        if spines.get("top", False) or spines.get("right", False):
            return False, "top/right spine enabled"

    # Check style/layout for border/spine info
    style = chart.get("style", {})
    if isinstance(style, dict):
        if style.get("show_top_spine", False) or style.get("show_right_spine", False):
            return False, "top/right spine enabled in style"

    # Most outputs won't have explicit spine config — needs manual review
    return True, "needs_review (no explicit spine config)"


def check_rule_15_aspect(chart: dict) -> tuple[bool, str]:
    """Rule 15: Aspect ratio appropriate for chart type."""
    chart_type = chart.get("chart_type", "").lower()
    layout = chart.get("layout", {})
    if not isinstance(layout, dict):
        return True, "needs_review (no layout)"

    width = layout.get("width")
    height = layout.get("height")
    if width is None or height is None:
        # Check for aspect_ratio field
        ratio = layout.get("aspect_ratio")
        if ratio:
            return True, f"aspect_ratio specified: {ratio}"
        return True, "needs_review (no dimensions)"

    if height == 0:
        return False, "height is 0"

    ratio = width / height
    if chart_type == "line" and ratio < 1.2:
        return False, f"line chart ratio {ratio:.2f} < 1.2 (should be wider)"
    if chart_type == "bar" and ratio < 0.8:
        return False, f"bar chart ratio {ratio:.2f} < 0.8"

    return True, f"ratio={ratio:.2f}"


# ─── Main Evaluation ─────────────────────────────────────────────────────────

AUTOMATED_CHECKS = {
    "rule_5_title": check_rule_5_title,
    "rule_6_source": check_rule_6_source,
    "rule_9_y_zero": check_rule_9_y_zero,
    "rule_10_spines": check_rule_10_spines,
    "rule_15_aspect": check_rule_15_aspect,
}

CSV_FIELDS = [
    "run_id",
    "model",
    "condition",
    "task",
    "task_complexity",
    "rep",
    "duration_ms",
    *TOKEN_FIELDS,
    "json_valid",
    "json_error",
    "schema_valid",
    "schema_errors",
    "rule_5_title_pass",
    "rule_5_title_detail",
    "rule_6_source_pass",
    "rule_6_source_detail",
    "rule_9_y_zero_pass",
    "rule_9_y_zero_detail",
    "rule_10_spines_pass",
    "rule_10_spines_detail",
    "rule_15_aspect_pass",
    "rule_15_aspect_detail",
    "auto_score",
    "needs_manual_review",
]


def evaluate_run(result_file: Path) -> dict:
    """Evaluate a single run result file."""
    with open(result_file) as f:
        result = json.load(f)

    row = {
        "run_id": result.get("run_id", result_file.stem),
        "model": result.get("model", ""),
        "condition": result.get("condition", ""),
        "task": result.get("task", ""),
        "task_complexity": result.get("task_complexity", ""),
        "rep": result.get("rep", ""),
        "duration_ms": result.get("duration_ms", ""),
    }

    # Extract token usage and JSON from raw output
    raw = result.get("raw_output", "")
    row.update(extract_token_usage(raw))

    chart, json_error = extract_json(raw)

    row["json_valid"] = chart is not None
    row["json_error"] = json_error or ""

    if chart is None:
        # Can't check anything else
        row["schema_valid"] = False
        row["schema_errors"] = json_error
        for name in AUTOMATED_CHECKS:
            row[f"{name}_pass"] = False
            row[f"{name}_detail"] = "no valid JSON"
        row["auto_score"] = 0
        row["needs_manual_review"] = False
        return row

    # Schema validation
    schema_ok, schema_errors = validate_schema(chart)
    row["schema_valid"] = schema_ok
    row["schema_errors"] = "; ".join(schema_errors) if schema_errors else ""

    # Automated rule checks
    auto_score = 0
    needs_review = False
    for name, check_fn in AUTOMATED_CHECKS.items():
        passed, detail = check_fn(chart)
        row[f"{name}_pass"] = passed
        row[f"{name}_detail"] = detail
        if passed:
            auto_score += 1
        if "needs_review" in detail:
            needs_review = True

    row["auto_score"] = auto_score
    row["needs_manual_review"] = needs_review

    return row


def main():
    # Determine which files to process
    if len(sys.argv) > 1:
        files = [Path(f) for f in sys.argv[1:] if f.endswith(".json")]
    else:
        if not RESULTS_DIR.exists():
            print(f"No results directory found at {RESULTS_DIR}")
            sys.exit(1)
        files = sorted(RESULTS_DIR.glob("*.json"))
        # Exclude scores.csv and other non-result files
        files = [f for f in files if f.name != "scores.csv"]

    if not files:
        print("No result files found.")
        sys.exit(1)

    print(f"Evaluating {len(files)} result files...")

    rows = []
    for f in files:
        try:
            row = evaluate_run(f)
            rows.append(row)
        except Exception as e:
            print(f"  ERROR processing {f.name}: {e}")

    # Write CSV
    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(OUTPUT_CSV, "w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    # Summary
    json_valid = sum(1 for r in rows if r["json_valid"])
    schema_valid = sum(1 for r in rows if r["schema_valid"])
    needs_review = sum(1 for r in rows if r["needs_manual_review"])

    print(f"\nResults written to {OUTPUT_CSV}")
    print(f"  Total runs: {len(rows)}")
    print(f"  JSON valid: {json_valid}/{len(rows)}")
    print(f"  Schema valid: {schema_valid}/{len(rows)}")
    print(f"  Needs manual review: {needs_review}/{len(rows)}")

    # Auto-score summary by condition
    print("\nAuto-score by condition (max 5 automatable rules):")
    conditions = {}
    for r in rows:
        cond = r["condition"]
        if cond not in conditions:
            conditions[cond] = []
        conditions[cond].append(r["auto_score"])

    for cond in sorted(conditions):
        scores = conditions[cond]
        avg = sum(scores) / len(scores) if scores else 0
        print(f"  {cond}: mean={avg:.1f}, n={len(scores)}")


if __name__ == "__main__":
    main()
