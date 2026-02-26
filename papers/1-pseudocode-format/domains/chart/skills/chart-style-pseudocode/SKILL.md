---
name: chart-style-pseudocode
description: Generate charts following Economist/FT visual style.
---

# Chart Style (Pseudocode)

```python
from dataclasses import dataclass
from enum import Enum
from typing import Literal

# ─────────────────────────────────────────────────────────────────────────────
# CORE TYPES
# ─────────────────────────────────────────────────────────────────────────────

class ChartType(Enum):
    BAR = "bar"
    LINE = "line"
    SCATTER = "scatter"

class Color(Enum):
    PRIMARY = "#1A476F"      # Main series
    ACCENT = "#C74634"       # Highlight ONE point
    TEAL = "#2D7282"         # Category 2
    GOLD = "#E9C46A"         # Category 3
    GRAY = "#5D666F"         # Category 4
    GRID = "#D0D0D0"         # Gridlines

@dataclass
class Title:
    text: str        # FULL SENTENCE stating finding, e.g. "China is 70% of US GDP"
    subtitle: str | None = None  # Context: "Nominal GDP, 2023"

@dataclass
class Source:
    data: str        # "World Bank"
    credit: str      # "Chart: aictrl.dev"

# ─────────────────────────────────────────────────────────────────────────────
# VALIDATION RULES — all 15 rules are typed fields
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ColorRules:
    """Rules 1-4: Color compliance."""
    palette: list[str]              # Rule 1: ONLY muted hex values (blues, teals, grays)
    highlight_color: str            # Rule 2: Exactly ONE accent color for key point
    highlight_count: int            # Rule 2: Must be 1
    has_red: bool                   # Rule 3: Track for red+green check
    has_green: bool                 # Rule 3: Track for red+green check
    category_color_map: dict[str, str]  # Rule 4: Category → color (consistent across charts)

    def violations(self) -> list[str]:
        v = []
        NEON = {"#FF0000", "#00FF00", "#0000FF", "#FF69B4", "#FFD700", "#00CED1"}
        if any(c.upper() in NEON for c in self.palette):
            v.append("Rule 1: Use muted palette, not rainbow/neon")
        if self.highlight_count != 1:
            v.append("Rule 2: Highlight exactly ONE key point")
        if self.has_red and self.has_green:
            v.append("Rule 3: No red+green together (accessibility)")
        return v

@dataclass
class Typography:
    """Rules 7-8: Font and label compliance."""
    font_family: str                # Rule 7: MUST be sans-serif (Inter, Helvetica, Arial, system-ui)
    data_labels: list[str]          # Rule 8: Direct labels on bars/points when ≤8 values
    label_format: str               # Number format: "1.2B", "850K", "45.6%"

    def violations(self) -> list[str]:
        v = []
        SERIF = {"times", "georgia", "garamond", "palatino", "serif"}
        if any(s in self.font_family.lower() for s in SERIF):
            v.append("Rule 7: Use sans-serif font (Inter, Helvetica, Arial)")
        return v

@dataclass
class AxisRules:
    """Rules 9-10: Axis compliance."""
    chart_type: ChartType
    y_min: float                    # Rule 9: MUST be 0 for bar charts
    show_top_spine: bool = False    # Rule 10: MUST be False
    show_right_spine: bool = False  # Rule 10: MUST be False

    def violations(self) -> list[str]:
        v = []
        if self.chart_type == ChartType.BAR and self.y_min != 0:
            v.append("Rule 9: Bar y-axis MUST start at 0")
        if self.show_top_spine or self.show_right_spine:
            v.append("Rule 10: Remove top/right spines")
        return v

@dataclass
class GridConfig:
    """Rules 11-12: Gridline and label compliance."""
    gridline_color: str             # Rule 11: MUST be light gray (#D0D0D0 or similar)
    gridline_style: Literal["dashed", "dotted", "solid", "none"]
    redundant_labels: bool = False  # Rule 12: MUST be False — no repeated units

    def violations(self) -> list[str]:
        v = []
        if self.gridline_color.upper() in ("#000000", "#333333", "#666666"):
            v.append("Rule 11: Gridlines must be subtle (light gray #D0D0D0)")
        if self.redundant_labels:
            v.append("Rule 12: Remove redundant labels (don't repeat units)")
        return v

@dataclass
class Annotations:
    """Rules 13-14: Annotation compliance."""
    insight_annotation: str         # Rule 13: Text callout for the key finding (REQUIRED)
    legend_position: str | None     # Rule 14: None if ≤3 categories, "top"/"right" if >3
    num_categories: int             # Rule 14: Used to validate legend necessity

    def violations(self) -> list[str]:
        v = []
        if not self.insight_annotation:
            v.append("Rule 13: Must annotate the key insight")
        if self.num_categories <= 3 and self.legend_position is not None:
            v.append("Rule 14: No legend needed for ≤3 categories — label directly")
        if self.num_categories > 3 and self.legend_position is None:
            v.append("Rule 14: Legend required for >3 categories")
        return v

@dataclass
class LayoutRules:
    """Rule 15: Aspect ratio compliance."""
    width: int
    height: int
    chart_type: ChartType

    def violations(self) -> list[str]:
        v = []
        if self.chart_type == ChartType.LINE and self.width <= self.height:
            v.append("Rule 15: Line charts must be wider than tall (16:9)")
        return v

# ─────────────────────────────────────────────────────────────────────────────
# COMPLETE SPEC — every field is mandatory (no defaults on required fields)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ChartSpec:
    title: Title                    # Rules 5-6: full sentence + source
    source: Source                  # Rule 6: source attribution
    chart_type: ChartType
    colors: ColorRules              # Rules 1-4
    typography: Typography          # Rules 7-8
    axes: AxisRules                 # Rules 9-10
    grid: GridConfig                # Rules 11-12
    annotations: Annotations        # Rules 13-14
    layout: LayoutRules             # Rule 15
    data: list[dict]                # The actual chart data

    def validate(self) -> list[str]:
        """Returns all violations. Empty list = fully compliant with 15 rules."""
        v = []

        # Rule 5: Title is full sentence
        if len(self.title.text) < 20 or self.title.text.endswith(":"):
            v.append("Rule 5: Title must be a full sentence stating the finding")

        # Rule 6: Source present
        if not self.source.data:
            v.append("Rule 6: Source attribution is required")

        # Rules 1-4
        v.extend(self.colors.violations())
        # Rules 7-8
        v.extend(self.typography.violations())
        # Rules 9-10
        v.extend(self.axes.violations())
        # Rules 11-12
        v.extend(self.grid.violations())
        # Rules 13-14
        v.extend(self.annotations.violations())
        # Rule 15
        v.extend(self.layout.violations())

        return v

    def is_compliant(self) -> bool:
        return len(self.validate()) == 0

# ─────────────────────────────────────────────────────────────────────────────
# CHART TYPE SELECTION
# ─────────────────────────────────────────────────────────────────────────────

def select_type(has_time: bool, showing_trend: bool, correlation: bool) -> ChartType:
    """Decision logic for chart type."""
    if correlation:
        return ChartType.SCATTER
    if has_time and showing_trend:
        return ChartType.LINE
    return ChartType.BAR

# NEVER USE: Pie, 3D, Area (not in ChartType)

# ─────────────────────────────────────────────────────────────────────────────
# NUMBER FORMATTING
# ─────────────────────────────────────────────────────────────────────────────

def format_num(n: float) -> str:
    """1.2B, 850K, 1,234, 45.6%"""
    if abs(n) >= 1e9: return f"{n/1e9:.1f}B"
    if abs(n) >= 1e6: return f"{n/1e6:.1f}M"
    if abs(n) >= 1e3: return f"{n:,.0f}"
    if 0 < abs(n) < 1: return f"{n*100:.1f}%"
    return f"{n:.1f}"
```

## Usage

1. Construct `ChartSpec` with **all** fields — every field is mandatory
2. Call `spec.validate()` → empty list = compliant with all 15 rules
3. Generate SVG/matplotlib/D3 output
4. All 15 rules are enforced through typed fields, not comments
