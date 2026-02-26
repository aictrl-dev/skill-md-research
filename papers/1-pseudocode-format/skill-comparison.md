# Skill Format Comparison: Chart Style Compliance

## Three Conditions

| Condition | Description | Lines | What It Tests |
|-----------|-------------|-------|---------------|
| No skill (baseline) | No style rules provided | 0 | Do skills help at all? |
| Markdown | Prose with tables and examples | 159 | Current industry standard |
| Pseudocode | Dataclasses, enums, `validate()` | 176 | Structured format hypothesis |

The markdown and pseudocode skills encode the **same 15 rules**. The no-skill baseline intentionally omits all style rules — low compliance is expected and demonstrates the value of skills.

---

## Semantic Equivalence Check (Markdown vs Pseudocode)

### Color (4 rules)
| # | Rule | Markdown | Pseudocode |
|---|------|----------|------------|
| 1 | Muted palette | Table + prose | `Color` enum |
| 2 | One highlight | "Highlight only ONE" | `highlight_count: int = 1` |
| 3 | No red+green | Explicit rule | `has_red and has_green` check |
| 4 | Consistent colors | "Same category = same color" | `category_colors: dict` |

### Typography (4 rules)
| # | Rule | Markdown | Pseudocode |
|---|------|----------|------------|
| 5 | Title = sentence | Good/Bad examples | `Title.text` validation |
| 6 | Source present | Required | `Source` dataclass |
| 7 | Sans-serif font | Explicit list | Implied in types |
| 8 | Labels for <=8 | Explicit rule | In checklist comment |

### Axes (4 rules)
| # | Rule | Markdown | Pseudocode |
|---|------|----------|------------|
| 9 | Y=0 for bars | MUST start at zero | `y_min != 0` violation |
| 10 | No top/right spine | Remove borders | `show_top_spine=False` |
| 11 | Gridlines subtle | `#D0D0D0` | `Color.GRID` |
| 12 | No redundant labels | Explicit rule | Checklist comment |

### Annotations (2 rules)
| # | Rule | Markdown | Pseudocode |
|---|------|----------|------------|
| 13 | Key insight called out | Add annotation | Checklist comment |
| 14 | Legend only if >3 | Explicit rule | Checklist comment |

### Layout (1 rule)
| # | Rule | Markdown | Pseudocode |
|---|------|----------|------------|
| 15 | Correct aspect ratio | 16:9 / 4:3 | `LayoutRules.violations()` |

---

## Format Characteristics

### No Skill (Baseline)
- **Structure**: None — just raw task data and a generic instruction
- **Style rules**: None provided
- **Expected outcome**: Model uses its training data defaults
- **Purpose**: Establishes whether skills add value beyond what the model already knows

### Markdown (159 lines)
- **Structure**: Headings, tables, bullet lists
- **Style**: Prose with examples
- **Enforcement**: Human-readable rules
- **Best for**: Human review, onboarding

### Pseudocode (176 lines)
- **Structure**: Dataclasses, enums, functions
- **Style**: Typed specifications with validation
- **Enforcement**: `validate()` returns violations
- **Best for**: Programmatic compliance checking

---

## Key Differences in Expression

| Concept | Markdown | Pseudocode |
|---------|----------|------------|
| Color palette | Table of hex values | `Enum` with values |
| Y-axis rule | "MUST start at zero" | `if y_min != 0: violation` |
| Validation | Checklist at end | `validate()` method |
| Chart type selection | Prose decision tree | `select_type()` function |

---

## Hypotheses

**H1 (Harness Effect)**: Skill conditions (md + pseudo) score higher than no-skill baseline, demonstrating that skills provide value beyond model defaults.

**H2 (Format Effect)**: Pseudocode produces equal or higher quality because:
- Types reduce ambiguity
- Enum constrains valid values
- Invariants are explicit

**H3 (Efficiency)**: Pseudocode produces fewer output tokens because:
- No repeated prose explanations
- Type system constrains output shape
- `validate()` method signals explicit contract

**H4 (Cross-model)**: Format effect holds across both model families (Claude + GLM).

---

## Files

```
docs/experiments/pseudo-code-skill/skills/
├── chart-style-markdown/SKILL.md    (159 lines)
└── chart-style-pseudocode/SKILL.md  (176 lines)
```
