#!/usr/bin/env python3
"""
Deep evaluator: all 15 rubric rules with structure-agnostic JSON search.

Three-valued verdicts per rule:
  pass   (1 pt) — evidence found that rule is satisfied
  fail   (0 pt) — evidence found that rule is violated
  absent (0 pt) — model didn't specify this aspect

Usage:
    python evaluate_deep.py                  # Process all results in results/
    python evaluate_deep.py results/foo.json # Process specific file(s)
"""

import colorsys
import csv
import json
import re
import sys
from pathlib import Path

# Reuse JSON extraction and token usage from existing evaluator
from evaluate import extract_json, extract_token_usage, TOKEN_FIELDS

SCRIPT_DIR = Path(__file__).parent
RESULTS_DIR = SCRIPT_DIR / "results"
OUTPUT_CSV = RESULTS_DIR / "scores_deep.csv"

# ─── Task Metadata ────────────────────────────────────────────────────────────

TASK_META = {
    "1": {"expected_type": "bar", "series_count": 1, "data_count": 5, "highlight_required": True},
    "2": {"expected_type": "line", "series_count": 1, "data_count": 8, "highlight_required": True},
    "3": {"expected_type": "line", "series_count": 3, "data_count": 8, "highlight_required": True},
}

# ─── Known Economist Palette ─────────────────────────────────────────────────

ECONOMIST_PALETTE = {
    "#1a476f", "#c74634", "#2d7282", "#e9c46a", "#5d666f", "#d0d0d0",
}

SERIF_FONTS = {
    "times", "times new roman", "georgia", "garamond", "palatino",
    "book antiqua", "baskerville", "cambria", "serif",
}

# ─── Structure-Agnostic Extractors ────────────────────────────────────────────

def deep_find(obj, keys, types=None):
    """Recursive DFS: collect values at any matching key name regardless of depth.

    Args:
        obj: JSON object to search
        keys: set of key names to match (case-insensitive)
        types: optional tuple of types to filter results
    Returns:
        list of (path, value) tuples
    """
    results = []
    keys_lower = {k.lower() for k in keys}

    def _walk(node, path):
        if isinstance(node, dict):
            for k, v in node.items():
                if k.lower() in keys_lower:
                    if types is None or isinstance(v, types):
                        results.append((f"{path}.{k}" if path else k, v))
                _walk(v, f"{path}.{k}" if path else k)
        elif isinstance(node, list):
            for i, item in enumerate(node):
                _walk(item, f"{path}[{i}]")

    _walk(obj, "")
    return results


def extract_all_hex_colors(obj):
    """Find every string matching #RRGGBB anywhere in the JSON tree."""
    colors = set()
    hex_re = re.compile(r"#[0-9a-fA-F]{6}\b")

    def _walk(node):
        if isinstance(node, str):
            for m in hex_re.finditer(node):
                colors.add(m.group(0).lower())
        elif isinstance(node, dict):
            for v in node.values():
                _walk(v)
        elif isinstance(node, list):
            for item in node:
                _walk(item)

    _walk(obj)
    return colors


def extract_title_text(obj):
    """Extract title text from various nesting patterns."""
    # Priority 1: dict-style title with "text" key (most explicit)
    for _, val in deep_find(obj, {"title"}, (dict,)):
        text = val.get("text", "")
        if isinstance(text, str) and len(text.strip()) > 5:
            return text.strip()

    # Priority 2: top-level or chart-level title string (skip axis titles)
    for path, val in deep_find(obj, {"title"}, (str,)):
        path_lower = path.lower()
        # Skip axis titles like "encoding.y.axis.title"
        if "axis" in path_lower or "encoding" in path_lower:
            continue
        if len(val.strip()) > 5:
            return val.strip()

    # Priority 3: any "text" key with substantial content
    for _, val in deep_find(obj, {"text"}, (str,)):
        if len(val.strip()) > 10:
            return val.strip()

    return ""


def extract_chart_type(obj):
    """Extract chart type from various JSON structures."""
    # Explicit chart_type / chartType
    for key in ["chart_type", "chartType"]:
        for _, val in deep_find(obj, {key}, (str,)):
            return val.lower()

    # type field — but only at chart level, not inside data items
    top_type = obj.get("type", "")
    if isinstance(top_type, str) and top_type.lower() in {"bar", "line", "scatter", "area", "pie"}:
        return top_type.lower()

    chart = obj.get("chart", {})
    if isinstance(chart, dict):
        ct = chart.get("type", "")
        if isinstance(ct, str) and ct:
            return ct.lower()

    # Vega-Lite: mark or mark.type
    mark = obj.get("mark", "")
    if isinstance(mark, str):
        return mark.lower()
    if isinstance(mark, dict):
        return mark.get("type", "").lower()

    return ""


def extract_source_text(obj):
    """Extract source attribution text from various locations."""
    # Direct source string
    for path, val in deep_find(obj, {"source"}, (str,)):
        val = val.strip()
        # Skip Vega-Lite $schema-like URLs
        if val and not val.startswith("http") and len(val) > 3:
            return val

    # source.data, source.text
    for _, val in deep_find(obj, {"source"}, (dict,)):
        for sub_key in ["data", "text"]:
            sub = val.get(sub_key, "")
            if isinstance(sub, str) and len(sub.strip()) > 3:
                return sub.strip()

    # metadata.source
    meta = obj.get("metadata", {})
    if isinstance(meta, dict):
        src = meta.get("source", "")
        if isinstance(src, str) and len(src.strip()) > 3:
            return src.strip()

    return ""


def extract_font_families(obj):
    """Find all font family strings anywhere in the tree."""
    fonts = set()
    for _, val in deep_find(obj, {"family", "fontFamily", "font_family", "labelFont", "titleFont"}, (str,)):
        fonts.add(val.strip().lower())
    return fonts


def extract_aspect_ratio(obj):
    """Extract aspect ratio as width/height float, or None."""
    # Explicit aspect_ratio or aspectRatio string like "16:9"
    for _, val in deep_find(obj, {"aspect_ratio", "aspectRatio"}, (str,)):
        parts = val.split(":")
        if len(parts) == 2:
            try:
                return float(parts[0]) / float(parts[1])
            except (ValueError, ZeroDivisionError):
                pass

    # Width and height at any depth
    widths = deep_find(obj, {"width"}, (int, float))
    heights = deep_find(obj, {"height"}, (int, float))

    if widths and heights:
        w = widths[0][1]
        h = heights[0][1]
        if h > 0:
            return w / h

    return None


def extract_spine_config(obj):
    """Extract spine/border configuration.

    Returns dict with keys: top, right, bottom, left
    Values: True (enabled), False (disabled), None (unspecified)
    """
    config = {"top": None, "right": None, "bottom": None, "left": None}
    found = False

    # Pattern 1: spines: {top: false, right: false, ...}
    for _, val in deep_find(obj, {"spines"}, (dict,)):
        for side in config:
            if side in val:
                config[side] = bool(val[side])
                found = True

    # Pattern 2: removeSpines: ["top", "right"] or removedElements
    for _, val in deep_find(obj, {"removeSpines", "removedElements", "hideSpines"}, (list,)):
        for item in val:
            if isinstance(item, str) and item.lower() in config:
                config[item.lower()] = False
                found = True

    # Pattern 3: show_top_spine, show_right_spine in style
    for key in ["show_top_spine", "show_right_spine", "show_bottom_spine", "show_left_spine"]:
        side = key.replace("show_", "").replace("_spine", "")
        for _, val in deep_find(obj, {key}, (bool,)):
            config[side] = val
            found = True

    # Pattern 4: Vega-Lite style: view.stroke: null (removes border box)
    for _, val in deep_find(obj, {"view"}, (dict,)):
        if val.get("stroke") is None or val.get("stroke") == "transparent":
            config["top"] = False
            config["right"] = False
            found = True

    # Pattern 5: axis spine: false at axes.y.spine or axes.x.spine
    for _, val in deep_find(obj, {"spine"}, (bool,)):
        found = True  # At least there's some spine config

    if not found:
        return None
    return config


def extract_gridline_colors(obj):
    """Extract gridline color values."""
    colors = set()
    for _, val in deep_find(obj, {"gridColor", "gridline_color", "grid_color"}, (str,)):
        if re.match(r"#[0-9a-fA-F]{6}", val):
            colors.add(val.lower())

    # Nested: gridlines.color
    for _, val in deep_find(obj, {"gridlines"}, (dict,)):
        c = val.get("color", "")
        if isinstance(c, str) and re.match(r"#[0-9a-fA-F]{6}", c):
            colors.add(c.lower())

    return colors


def extract_annotations(obj):
    """Find annotations at any depth — supports list or dict with insight_annotation."""
    for _, val in deep_find(obj, {"annotations"}, (list,)):
        if val:
            return val

    # Typed structure: annotations.insight_annotation (string)
    for _, val in deep_find(obj, {"annotations"}, (dict,)):
        insight = val.get("insight_annotation", "")
        if isinstance(insight, str) and len(insight) > 3:
            return [{"text": insight}]

    # Standalone insight_annotation key
    for _, val in deep_find(obj, {"insight_annotation"}, (str,)):
        if len(val) > 3:
            return [{"text": val}]

    return []


def extract_legend_config(obj):
    """Extract legend configuration. Returns: True (shown), False (hidden), None (unspecified)."""
    # Explicit legend: null or legend: false
    for _, val in deep_find(obj, {"legend"}, (type(None), bool)):
        if val is None or val is False:
            return False

    for _, val in deep_find(obj, {"showLegend", "show_legend"}, (bool,)):
        return val

    # Legend dict
    for _, val in deep_find(obj, {"legend"}, (dict,)):
        show = val.get("show", val.get("visible", True))
        return bool(show)

    return None


def count_data_points(obj):
    """Count data points in the chart."""
    # data[] array
    data = obj.get("data", None)
    if isinstance(data, list) and data:
        return len(data)

    # data.values[] (Vega-Lite)
    if isinstance(data, dict):
        vals = data.get("values", [])
        if isinstance(vals, list):
            return len(vals)

    # Nested: chart.data
    chart = obj.get("chart", {})
    if isinstance(chart, dict):
        d = chart.get("data", [])
        if isinstance(d, list):
            return len(d)

    # series[0].data[]
    series = obj.get("series", [])
    if isinstance(series, list) and series:
        first = series[0]
        if isinstance(first, dict):
            sd = first.get("data", [])
            if isinstance(sd, list):
                return len(sd)

    return 0


def count_series(obj):
    """Count distinct data series."""
    series = obj.get("series", [])
    if isinstance(series, list) and series:
        return len(series)

    # Multi-column data: count numeric fields in first data row
    data = obj.get("data", [])
    if isinstance(data, list) and data and isinstance(data[0], dict):
        numeric_fields = [k for k, v in data[0].items()
                         if isinstance(v, (int, float)) and k.lower() not in
                         {"index", "id", "row", "highlight"}]
        if numeric_fields:
            return len(numeric_fields)

    # Vega-Lite data.values
    if isinstance(data, dict):
        vals = data.get("values", [])
        if isinstance(vals, list) and vals and isinstance(vals[0], dict):
            numeric_fields = [k for k, v in vals[0].items()
                             if isinstance(v, (int, float)) and k.lower() not in
                             {"index", "id", "row", "highlight"}]
            if numeric_fields:
                return len(numeric_fields)

    return 0


def extract_highlight_info(obj):
    """Check for highlight/accent data points."""
    highlights = []

    # data[].highlight: true
    for _, val in deep_find(obj, {"highlight"}, (bool,)):
        if val:
            highlights.append("data_flag")

    # Typed structure: colors.highlight_count >= 1 and colors.highlight_color present
    for _, val in deep_find(obj, {"highlight_count"}, (int,)):
        if val >= 1:
            highlights.append("typed_highlight_count")
    for _, val in deep_find(obj, {"highlight_color"}, (str,)):
        if val and len(val) > 3:
            highlights.append("typed_highlight_color")

    # Distinct colors in data items
    data_colors = set()
    data = obj.get("data", [])
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                c = item.get("color", "")
                if isinstance(c, str) and c:
                    data_colors.add(c.lower())
    if isinstance(data, dict):
        for item in data.get("values", []):
            if isinstance(item, dict):
                c = item.get("color", "")
                if isinstance(c, str) and c:
                    data_colors.add(c.lower())

    return highlights, data_colors


def extract_data_labels_config(obj):
    """Check if data labels are configured."""
    # labels config — match bool, dict, or non-empty list
    for _, val in deep_find(obj, {"labels", "dataLabels", "data_labels", "bar_values"}, (bool, dict, list)):
        if isinstance(val, list) and len(val) > 0:
            return True
        if isinstance(val, (bool, dict)):
            return True

    # Vega-Lite: layer with text mark
    for _, val in deep_find(obj, {"layer"}, (list,)):
        for item in val:
            if isinstance(item, dict):
                mark = item.get("mark", {})
                if isinstance(mark, dict) and mark.get("type") == "text":
                    return True
                if mark == "text":
                    return True

    return False


def extract_units_locations(obj):
    """Find where units/format strings appear (title, axis, labels)."""
    locations = set()
    title = extract_title_text(obj)

    # Common unit patterns
    unit_patterns = [r"\$", r"USD", r"billion", r"trillion", r"%", r"bn", r"B\b"]
    unit_re = re.compile("|".join(unit_patterns), re.IGNORECASE)

    if title and unit_re.search(title):
        locations.add("title")

    # Check subtitle
    for _, val in deep_find(obj, {"subtitle"}, (str,)):
        if unit_re.search(val):
            locations.add("subtitle")

    # Check axis labels
    for _, val in deep_find(obj, {"label", "tickFormat", "format"}, (str,)):
        if unit_re.search(val):
            locations.add("axis")

    # Check data labels
    for _, val in deep_find(obj, {"labels", "dataLabels"}, (dict,)):
        fmt = val.get("format", "")
        if isinstance(fmt, str) and unit_re.search(fmt):
            locations.add("labels")

    # Check axis title
    for path, val in deep_find(obj, {"title"}, (str,)):
        if "axis" in path.lower() or "y" in path.lower() or "x" in path.lower():
            if unit_re.search(val):
                locations.add("axis")

    return locations


# ─── Color Analysis Utilities ─────────────────────────────────────────────────

def hex_to_hsl(hex_color):
    """Convert #RRGGBB to (hue_degrees, saturation_0_1, lightness_0_1)."""
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i:i+2], 16) / 255.0 for i in (0, 2, 4))
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    return h * 360, s, l


def is_muted(hex_color):
    """Check if a color is muted (low saturation or low lightness)."""
    if hex_color.lower() in ECONOMIST_PALETTE:
        return True
    h, s, l = hex_to_hsl(hex_color)
    return s < 0.7 or l < 0.45


def is_neon_or_primary(hex_color):
    """Check if a color is neon/rainbow/primary RGB."""
    h, s, l = hex_to_hsl(hex_color)
    # Primary RGB: very high saturation + specific hues
    if s > 0.85 and l > 0.4:
        return True
    # Pure primary checks
    hex_lower = hex_color.lower().lstrip("#")
    primaries = {"ff0000", "00ff00", "0000ff", "ffff00", "ff00ff", "00ffff"}
    if hex_lower in primaries:
        return True
    return False


def is_red_family(hex_color):
    """Hue 0-30 or 330-360, saturation > 0.3."""
    h, s, _ = hex_to_hsl(hex_color)
    return s > 0.3 and (h <= 30 or h >= 330)


def is_green_family(hex_color):
    """Hue 90-150, saturation > 0.3."""
    h, s, _ = hex_to_hsl(hex_color)
    return s > 0.3 and 90 <= h <= 150


def is_light_color(hex_color):
    """Check if a color has lightness > 70%."""
    _, _, l = hex_to_hsl(hex_color)
    return l > 0.7


def is_sans_serif(font_str):
    """Check if a font string specifies sans-serif fonts."""
    lower = font_str.lower()
    for serif in SERIF_FONTS:
        # Match whole word: "serif" should not match "sans-serif"
        if serif == "serif":
            # Check for standalone "serif" not preceded by "sans-"
            if re.search(r"(?<!sans-)(?<!sans )\bserif\b", lower):
                return False
        elif serif in lower:
            return False
    return True


# ─── 15 Rule Checkers ─────────────────────────────────────────────────────────
# Each returns (verdict, detail) where verdict is "pass", "fail", or "absent"

def rule_01_muted_palette(chart, meta):
    """All data colors have low saturation or match Economist palette."""
    colors = extract_all_hex_colors(chart)
    # Filter out near-white, near-black, and obvious background/grid colors
    data_colors = set()
    for c in colors:
        _, s, l = hex_to_hsl(c)
        if l > 0.9 or l < 0.05:
            continue  # background/text colors
        if c in {"#d0d0d0", "#e0e0e0", "#f5f5f5", "#f0f0f0", "#cccccc", "#999999", "#333333", "#1a1a1a"}:
            continue  # grid/text/bg colors
        data_colors.add(c)

    if not data_colors:
        return "absent", "no data colors found"

    bad = [c for c in data_colors if is_neon_or_primary(c)]
    if bad:
        return "fail", f"neon/primary colors: {', '.join(bad)}"

    non_muted = [c for c in data_colors if not is_muted(c)]
    if non_muted:
        return "fail", f"saturated colors: {', '.join(non_muted)}"

    return "pass", f"{len(data_colors)} muted colors"


def rule_02_one_highlight(chart, meta):
    """At most 2 related points highlighted or accent-colored."""
    highlights, data_colors = extract_highlight_info(chart)

    # Count accent/distinct colors
    if data_colors and len(data_colors) > 1:
        # Multiple distinct colors in data — some may be highlights
        # Up to 2 distinct highlight colors is fine
        non_gray = [c for c in data_colors if not c.startswith("#5d") and not c.startswith("#d0")]
        if len(non_gray) > 2:
            return "fail", f"{len(non_gray)} distinct accent colors in data"

    # Count highlight flags
    if len(highlights) > 2:
        return "fail", f"{len(highlights)} data points flagged as highlight"

    annotations = extract_annotations(chart)
    if highlights or annotations or data_colors:
        return "pass", "highlight/accent present and <=2"

    return "absent", "no highlight data found"


def rule_03_no_red_green(chart, meta):
    """Red-family and green-family not both in data colors."""
    colors = extract_all_hex_colors(chart)
    # Filter to likely data colors
    data_colors = set()
    for c in colors:
        _, s, l = hex_to_hsl(c)
        if l > 0.9 or l < 0.05:
            continue
        if c in {"#d0d0d0", "#e0e0e0", "#f5f5f5", "#f0f0f0", "#cccccc", "#999999", "#333333", "#1a1a1a"}:
            continue
        data_colors.add(c)

    if not data_colors:
        return "absent", "no colors to evaluate"

    has_red = any(is_red_family(c) for c in data_colors)
    has_green = any(is_green_family(c) for c in data_colors)

    if has_red and has_green:
        reds = [c for c in data_colors if is_red_family(c)]
        greens = [c for c in data_colors if is_green_family(c)]
        return "fail", f"red ({', '.join(reds)}) + green ({', '.join(greens)}) both present"

    return "pass", "no red+green conflict"


def rule_04_consistent_colors(chart, meta):
    """Auto-pass for single chart evaluation."""
    return "pass", "single chart (auto-pass)"


def rule_05_title_sentence(chart, meta):
    """Title is >20 chars, not a label, contains insight."""
    text = extract_title_text(chart)

    if not text:
        return "absent", "no title found"

    if len(text) < 20:
        return "fail", f"title too short ({len(text)} chars): '{text}'"

    if text.rstrip().endswith(":"):
        return "fail", f"title ends with colon (label style): '{text}'"

    # Check for insight words vs. pure label
    label_patterns = [
        r"^[A-Z][A-Za-z\s]+ by [A-Z]",  # "GDP by Country"
        r"^[A-Z][A-Za-z\s]+ of [A-Z]",  # "Comparison of Economies"
        r"^[A-Z][A-Za-z\s]+ for [A-Z]",
    ]
    insight_words = {"remain", "overtook", "surpass", "grew", "decline", "lead",
                     "gap", "largest", "smallest", "most", "dominat", "ahead",
                     "behind", "slower", "faster", "exceed", "near", "close",
                     "catching", "roughly", "approximately", "almost", "still",
                     "despite", "while", "although", "but", "yet", "however",
                     "significantly", "doubled", "tripled", "half", "twice",
                     "why", "how", "matter", "impact", "shift", "chang",
                     "continu", "emerg", "fall", "rise", "climb", "drop",
                     "surge", "plummet", "stag"}

    text_lower = text.lower()
    has_insight = any(w in text_lower for w in insight_words)

    # If >30 chars, likely a sentence even without insight words
    if len(text) > 30 or has_insight:
        return "pass", f"insight title ({len(text)} chars)"

    # Short-ish without clear insight — likely a label
    is_label = any(re.match(p, text) for p in label_patterns)
    if is_label:
        return "fail", f"label-style title: '{text}'"

    return "pass", f"title present ({len(text)} chars)"


def rule_06_source_present(chart, meta):
    """Source attribution present and non-vague."""
    source = extract_source_text(chart)

    if not source:
        return "absent", "no source field found anywhere"

    vague = {"various sources", "multiple sources", "see references", "internet", "online"}
    if source.lower().strip() in vague:
        return "fail", f"vague source: '{source}'"

    return "pass", f"source: '{source[:60]}'"


def rule_07_sans_serif(chart, meta):
    """All font strings are sans-serif families."""
    fonts = extract_font_families(chart)

    if not fonts:
        return "absent", "no font specified"

    bad = [f for f in fonts if not is_sans_serif(f)]
    if bad:
        return "fail", f"serif fonts: {', '.join(bad)}"

    return "pass", f"sans-serif: {', '.join(list(fonts)[:3])}"


def rule_08_data_labels(chart, meta):
    """Labels config present for <=8 data points."""
    n_points = count_data_points(chart)
    has_labels = extract_data_labels_config(chart)

    if n_points == 0:
        return "absent", "can't determine data count"

    if n_points <= 8:
        if has_labels:
            return "pass", f"{n_points} points with labels configured"
        return "fail", f"{n_points} points but no label config"

    # >8 points — labels not required
    return "pass", f"{n_points} points (>8, labels optional)"


def rule_09_y_zero_bars(chart, meta):
    """Bar chart with explicit min=0."""
    chart_type = extract_chart_type(chart)

    if chart_type != "bar":
        return "pass", f"n/a (chart type: {chart_type or 'unknown'})"

    # Check for explicit y min / y_min / domain / scale.zero
    for _, val in deep_find(chart, {"min", "y_min"}, (int, float)):
        if val == 0:
            return "pass", "y min=0"
        return "fail", f"y min={val}, should be 0"

    # domain: [0, ...]
    for _, val in deep_find(chart, {"domain"}, (list,)):
        if val and val[0] == 0:
            return "pass", "y domain starts at 0"
        if val and isinstance(val[0], (int, float)) and val[0] != 0:
            return "fail", f"y domain starts at {val[0]}"

    # Vega-Lite: scale.zero
    for _, val in deep_find(chart, {"zero"}, (bool,)):
        if val:
            return "pass", "scale.zero=true"
        return "fail", "scale.zero=false"

    # beginAtZero
    for _, val in deep_find(chart, {"beginAtZero"}, (bool,)):
        if val:
            return "pass", "beginAtZero=true"
        return "fail", "beginAtZero=false"

    return "absent", "bar chart with no explicit y-axis config"


def rule_10_no_top_right_spine(chart, meta):
    """Top and right spines explicitly removed."""
    config = extract_spine_config(chart)

    if config is None:
        return "absent", "no spine config found"

    top = config.get("top")
    right = config.get("right")

    if top is False and right is False:
        return "pass", "top+right spines removed"

    if top is True or right is True:
        sides = []
        if top is True:
            sides.append("top")
        if right is True:
            sides.append("right")
        return "fail", f"spine enabled: {', '.join(sides)}"

    # Partial config — at least something was specified
    if top is False or right is False:
        return "pass", "spine removal partially specified"

    return "absent", "spine config exists but unclear"


def rule_11_subtle_gridlines(chart, meta):
    """Grid color lightness > 70%."""
    grid_colors = extract_gridline_colors(chart)

    if not grid_colors:
        # Check for gridOpacity or gridDash (implies subtle gridlines)
        for _, val in deep_find(chart, {"gridOpacity"}, (int, float)):
            if val <= 0.5:
                return "pass", f"grid opacity={val} (subtle)"
            return "fail", f"grid opacity={val} (not subtle)"

        # No gridlines at all — acceptable
        for _, val in deep_find(chart, {"gridlines"}, (bool,)):
            if val is False:
                return "pass", "gridlines disabled"

        return "absent", "no grid color specified"

    dark = [c for c in grid_colors if not is_light_color(c)]
    if dark:
        return "fail", f"dark grid colors: {', '.join(dark)}"

    return "pass", f"subtle grid colors: {', '.join(grid_colors)}"


def rule_12_no_redundant_labels(chart, meta):
    """Unit doesn't appear in 3+ locations (title AND axis AND labels)."""
    locations = extract_units_locations(chart)

    if len(locations) < 2:
        return "absent", f"unit in {len(locations)} location(s) — insufficient data"

    if len(locations) >= 3:
        return "fail", f"unit appears in {len(locations)} places: {', '.join(sorted(locations))}"

    return "pass", f"unit in {len(locations)} locations: {', '.join(sorted(locations))}"


def rule_13_key_insight(chart, meta):
    """Annotations or highlights present (all tasks require them)."""
    annotations = extract_annotations(chart)
    highlights, data_colors = extract_highlight_info(chart)

    if annotations:
        return "pass", f"{len(annotations)} annotation(s)"

    if highlights:
        return "pass", f"{len(highlights)} highlight flag(s)"

    # Check for distinct accent colors in data (implicit highlight)
    if len(data_colors) > 1:
        return "pass", f"accent colors in data: {', '.join(list(data_colors)[:3])}"

    # Series with distinct colors count as visual emphasis
    series = chart.get("series", [])
    if isinstance(series, list) and series:
        return "pass", "series with color differentiation"

    return "fail", "no annotations, highlights, or emphasis found"


def rule_14_legend(chart, meta):
    """<=3 series without legend, or >3 with legend."""
    n_series = count_series(chart)
    legend = extract_legend_config(chart)

    if n_series == 0:
        return "absent", "can't determine series count"

    if n_series <= 3:
        if legend is False or legend is None:
            return "pass", f"{n_series} series, no legend (correct)"
        if legend is True:
            # 3 series with legend is acceptable per rubric
            if n_series == 3:
                return "pass", f"3 series with legend (acceptable)"
            return "fail", f"{n_series} series with legend (should use direct labels)"

    # >3 series
    if legend is True:
        return "pass", f"{n_series} series with legend (correct)"
    if legend is False:
        return "fail", f"{n_series} series without legend"

    return "absent", f"{n_series} series, legend config unclear"


def rule_15_aspect_ratio(chart, meta):
    """Line >= 1.2 w:h, bar 0.8-2.5."""
    ratio = extract_aspect_ratio(chart)
    chart_type = extract_chart_type(chart)

    if ratio is None:
        return "absent", "no dimensions found"

    if chart_type == "line":
        if ratio >= 1.2:
            return "pass", f"line chart ratio {ratio:.2f} >= 1.2"
        return "fail", f"line chart ratio {ratio:.2f} < 1.2 (should be wider)"

    if chart_type == "bar":
        if 0.8 <= ratio <= 2.5:
            return "pass", f"bar chart ratio {ratio:.2f} in [0.8, 2.5]"
        return "fail", f"bar chart ratio {ratio:.2f} outside [0.8, 2.5]"

    # Unknown chart type — just check it's not extreme
    if 0.5 <= ratio <= 3.0:
        return "pass", f"ratio {ratio:.2f} (acceptable)"
    return "fail", f"ratio {ratio:.2f} (extreme)"


# ─── Rule Registry ────────────────────────────────────────────────────────────

RULES = [
    ("rule_01", "muted_palette", rule_01_muted_palette),
    ("rule_02", "one_highlight", rule_02_one_highlight),
    ("rule_03", "no_red_green", rule_03_no_red_green),
    ("rule_04", "consistent_colors", rule_04_consistent_colors),
    ("rule_05", "title_sentence", rule_05_title_sentence),
    ("rule_06", "source_present", rule_06_source_present),
    ("rule_07", "sans_serif", rule_07_sans_serif),
    ("rule_08", "data_labels", rule_08_data_labels),
    ("rule_09", "y_zero_bars", rule_09_y_zero_bars),
    ("rule_10", "no_top_right_spine", rule_10_no_top_right_spine),
    ("rule_11", "subtle_gridlines", rule_11_subtle_gridlines),
    ("rule_12", "no_redundant_labels", rule_12_no_redundant_labels),
    ("rule_13", "key_insight", rule_13_key_insight),
    ("rule_14", "legend_rule", rule_14_legend),
    ("rule_15", "aspect_ratio", rule_15_aspect_ratio),
]

# ─── CSV Fields ───────────────────────────────────────────────────────────────

CSV_FIELDS = [
    "run_id", "model", "condition", "task", "task_complexity", "rep", "duration_ms",
    *TOKEN_FIELDS,
    "json_valid", "json_error",
]
for rule_id, rule_name, _ in RULES:
    CSV_FIELDS.append(f"{rule_id}_verdict")
    CSV_FIELDS.append(f"{rule_id}_detail")
CSV_FIELDS.extend(["pass_count", "fail_count", "absent_count",
                    "deep_score", "deep_score_pct", "coverage"])

# ─── Main Evaluation ─────────────────────────────────────────────────────────

def evaluate_run(result_file):
    """Evaluate a single run result file with all 15 deep rules."""
    with open(result_file) as f:
        result = json.load(f)

    row = {
        "run_id": result.get("run_id", result_file.stem),
        "model": result.get("model", ""),
        "condition": result.get("condition", ""),
        "task": str(result.get("task", "")),
        "task_complexity": result.get("task_complexity", ""),
        "rep": result.get("rep", ""),
        "duration_ms": result.get("duration_ms", ""),
    }

    task_id = row["task"]
    meta = TASK_META.get(task_id, {})

    # Extract token usage and JSON from raw output
    raw = result.get("raw_output", "")
    row.update(extract_token_usage(raw))

    chart, json_error = extract_json(raw)

    row["json_valid"] = chart is not None
    row["json_error"] = json_error or ""

    if chart is None:
        for rule_id, _, _ in RULES:
            row[f"{rule_id}_verdict"] = "absent"
            row[f"{rule_id}_detail"] = "no valid JSON"
        row["pass_count"] = 0
        row["fail_count"] = 0
        row["absent_count"] = 15
        row["deep_score"] = 0
        row["deep_score_pct"] = 0.0
        row["coverage"] = 0.0
        return row

    # Run all 15 rules
    pass_count = 0
    fail_count = 0
    absent_count = 0

    for rule_id, rule_name, check_fn in RULES:
        verdict, detail = check_fn(chart, meta)
        row[f"{rule_id}_verdict"] = verdict
        row[f"{rule_id}_detail"] = detail

        if verdict == "pass":
            pass_count += 1
        elif verdict == "fail":
            fail_count += 1
        else:
            absent_count += 1

    row["pass_count"] = pass_count
    row["fail_count"] = fail_count
    row["absent_count"] = absent_count
    row["deep_score"] = pass_count
    row["deep_score_pct"] = round(pass_count / 15, 3)
    row["coverage"] = round((pass_count + fail_count) / 15, 3)

    return row


def is_experiment_run(filename):
    """Check if a filename matches the experiment run naming pattern."""
    # Pattern: model_condition_taskN_repN.json
    return bool(re.match(r"^[a-z].*_(?:none|markdown|pseudocode)_task\d+_rep\d+\.json$", filename))


def main():
    # Determine which files to process
    if len(sys.argv) > 1:
        files = [Path(f) for f in sys.argv[1:] if f.endswith(".json")]
    else:
        if not RESULTS_DIR.exists():
            print(f"No results directory found at {RESULTS_DIR}")
            sys.exit(1)
        files = sorted(RESULTS_DIR.glob("*.json"))
        # Only include proper experiment runs (exclude pilots, tests, etc.)
        files = [f for f in files if is_experiment_run(f.name)]

    if not files:
        print("No result files found.")
        sys.exit(1)

    print(f"Evaluating {len(files)} result files with deep rules...")

    rows = []
    for f in files:
        try:
            row = evaluate_run(f)
            rows.append(row)
        except Exception as e:
            print(f"  ERROR processing {f.name}: {e}")

    # Write CSV
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_CSV, "w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nResults written to {OUTPUT_CSV}")
    print(f"Total runs evaluated: {len(rows)}")

    # ─── Summary Tables ───────────────────────────────────────────────────────

    # Build pivot: model x condition → list of scores
    pivot = {}  # (model, condition) → [deep_score, ...]
    coverage_pivot = {}
    models = set()
    conditions_order = ["none", "markdown", "pseudocode"]

    for r in rows:
        key = (r["model"], r["condition"])
        models.add(r["model"])
        pivot.setdefault(key, []).append(r["deep_score"])
        coverage_pivot.setdefault(key, []).append(r["coverage"])

    models = sorted(models)

    # Deep Score table
    print(f"\n{'Deep Score by Model x Condition (mean / 15):':}")
    header = f"{'':>30s}"
    for cond in conditions_order:
        header += f"  {cond:>12s}"
    print(header)

    for model in models:
        line = f"{model:>30s}"
        for cond in conditions_order:
            scores = pivot.get((model, cond), [])
            if scores:
                avg = sum(scores) / len(scores)
                line += f"  {avg:>10.1f}/15"
            else:
                line += f"  {'—':>12s}"
        print(line)

    # Coverage table
    print(f"\n{'Coverage (% of rules with explicit pass/fail):':}")
    print(header)

    for model in models:
        line = f"{model:>30s}"
        for cond in conditions_order:
            covs = coverage_pivot.get((model, cond), [])
            if covs:
                avg = sum(covs) / len(covs) * 100
                line += f"  {avg:>10.0f}%"
            else:
                line += f"  {'—':>12s}"
        print(line)

    # Per-rule verdict breakdown
    print(f"\n{'Per-rule verdicts (pass / fail / absent across all runs):':}")
    for rule_id, rule_name, _ in RULES:
        p = sum(1 for r in rows if r[f"{rule_id}_verdict"] == "pass")
        f_ = sum(1 for r in rows if r[f"{rule_id}_verdict"] == "fail")
        a = sum(1 for r in rows if r[f"{rule_id}_verdict"] == "absent")
        print(f"  {rule_id} {rule_name:>25s}:  pass={p:>3d}  fail={f_:>3d}  absent={a:>3d}")

    # Per-rule by condition
    print(f"\n{'Per-rule pass rate by condition:':}")
    rule_header = f"{'rule':>30s}"
    for cond in conditions_order:
        rule_header += f"  {cond:>12s}"
    print(rule_header)

    for rule_id, rule_name, _ in RULES:
        line = f"{rule_id} {rule_name:>24s}"
        for cond in conditions_order:
            cond_rows = [r for r in rows if r["condition"] == cond]
            if cond_rows:
                p = sum(1 for r in cond_rows if r[f"{rule_id}_verdict"] == "pass")
                rate = p / len(cond_rows) * 100
                line += f"  {rate:>10.0f}%"
            else:
                line += f"  {'—':>12s}"
        print(line)


if __name__ == "__main__":
    main()
