# Evaluation Rubric: Chart Style Compliance

## Scoring Instructions

Each chart is scored on 15 binary criteria. Each criterion is either **PASS** (1 point) or **FAIL** (0 points).

**Total Score**: 0-15
**Pass Threshold**: >=13 (87%)

### Cross-Condition Scoring

The rubric is applied **identically** across all three conditions (no-skill, markdown, pseudocode). The same 15 rules are checked regardless of whether the model was given style instructions.

**No-skill baseline outputs**: These will typically score low (5-10 range) because the model was not given the 15 style rules. This is expected and is the whole point of the baseline — it measures what the model produces from training data alone. Common patterns in no-skill outputs:
- Titles may be labels ("GDP by Country") rather than sentences — **FAIL Rule 5**
- Source attribution may be missing or incomplete — **FAIL Rule 6**
- Colors may be rainbow/default palette — **FAIL Rule 1**
- No highlight or annotation — **FAIL Rules 2, 13**
- Chart may have all four spines — **FAIL Rule 10**

**Do not adjust scoring for baseline outputs.** The gap between baseline and skill conditions is the primary measurement of skill value (H1).

---

## Detailed Rubric

### COLOR RULES

#### Rule 1: Muted Palette
**PASS**: Uses blues, teals, grays, or similar professional tones
**FAIL**: Rainbow (ROYGBIV), neon, or overly saturated colors

| Example | Status | Reason |
|---------|--------|--------|
| `#1A476F, #2D7282, #5D666F` | PASS | Economist-style muted |
| `#FF0000, #00FF00, #0000FF` | FAIL | Primary RGB |
| `#FF69B4, #FFD700, #00CED1` | FAIL | Neon/bright |
| `#6366F1, #8B5CF6, #EC4899` | FAIL | Too saturated |

#### Rule 2: One Highlight
**PASS**: At most 2 related points highlighted, or 1 distinct point
**FAIL**: 3+ unrelated points highlighted, or no clear focus

| Example | Status | Reason |
|---------|--------|--------|
| China bar in red, others blue | PASS | Clear focus |
| USA+China both highlighted | PASS | Comparison pair |
| 3 bars in different accent colors | FAIL | No clear story |
| All bars same color | PASS | No highlight OK |

#### Rule 3: No Red + Green Together
**PASS**: Red and green not both used, or used with clear distinction
**FAIL**: Red and green as primary comparison colors

| Example | Status | Reason |
|---------|--------|--------|
| Red accent + blue primary | PASS | |
| Red and green both present | FAIL | Colorblind issue |
| Red accent only | PASS | |
| Green and blue only | PASS | |

#### Rule 4: Consistent Category Colors
**PASS**: Same category has same color throughout multi-chart series
**FAIL**: "USA" is blue in chart 1, red in chart 2

*Only applicable if evaluating multiple charts together. Default PASS for single chart.*

---

### TYPOGRAPHY RULES

#### Rule 5: Title is Full Sentence
**PASS**: Title states a finding, reads like a headline
**FAIL**: Title is just variable names or a label

| Example | Status | Reason |
|---------|--------|--------|
| "China's economy is 70% the size of America's" | PASS | Full sentence, states finding |
| "GDP Comparison by Country" | FAIL | Just describes data |
| "GDP by Country" | FAIL | Too short, not a sentence |
| "Why China's GDP matters for global trade" | PASS | Headline style |
| "Quarterly Revenue:" | FAIL | Ends with colon = label |

**Checklist**:
- [ ] Longer than 15 characters
- [ ] Does not end with ":"
- [ ] States a finding or insight
- [ ] Could appear as newspaper headline

#### Rule 6: Source Attribution Present
**PASS**: Source clearly visible at bottom
**FAIL**: No source, or source incomplete

| Example | Status | Reason |
|---------|--------|--------|
| "Source: IMF | Chart: aictrl.dev" | PASS | Complete |
| "Source: World Bank" | PASS | Minimum acceptable |
| "World Bank" | PASS | Implied source |
| No attribution | FAIL | Missing |
| "Data from various sources" | FAIL | Too vague |

#### Rule 7: Sans-Serif Font
**PASS**: Inter, Helvetica, Arial, system-ui, or similar
**FAIL**: Times New Roman, Georgia, or decorative fonts

**Check**: Look at axis labels and title. If they have serifs (small lines at ends of strokes), FAIL.

#### Rule 8: Data Labels for ≤8 Values
**PASS**: If ≤8 bars/points, they are labeled directly or axis is clear
**FAIL**: Only legend for small-N charts, labels illegible

| Scenario | Status |
|----------|--------|
| 5 bars with values shown on each | PASS |
| 5 bars with axis only, no legend | PASS |
| 5 bars with only legend | FAIL |
| 15 bars, no direct labels | PASS (too many to label) |

---

### AXIS RULES

#### Rule 9: Y=0 for Bar Charts
**PASS**: Bar chart y-axis starts at exactly 0
**FAIL**: Y-axis truncated, bars don't start from baseline

| Example | Status | Reason |
|---------|--------|--------|
| Y-axis: 0, 5, 10, 15, 20 | PASS | |
| Y-axis: 10, 15, 20, 25 | FAIL | Truncated |
| Y-axis: 0.1, 1, 10, 100 (log) | PASS | Log scale starts >0 OK |

**Note**: This rule only applies to BAR charts. Line charts can start at non-zero.

#### Rule 10: No Top/Right Spine
**PASS**: Chart has only left and bottom borders (or none)
**FAIL**: Box around entire chart

| Visual | Status |
|--------|--------|
| Only left Y-axis line, bottom X-axis line | PASS |
| No axes at all (just gridlines) | PASS |
| Complete box around chart area | FAIL |
| Left, right, top, bottom all visible | FAIL |

#### Rule 11: Gridlines Subtle
**PASS**: Gridlines are light gray, not competing with data
**FAIL**: Gridlines are dark, thick, or distracting

| Example | Status |
|---------|--------|
| `#D0D0D0`, thin, dashed | PASS |
| `#000000`, solid | FAIL |
| No gridlines | PASS |
| `#E0E0E0`, thin | PASS |

#### Rule 12: No Redundant Labels
**PASS**: Each piece of info appears once
**FAIL**: Unit repeated on every bar, "Revenue" in title AND legend AND axis

| Example | Status |
|---------|--------|
| Title: "Cloud revenue", axis: "$B" | PASS |
| Title: "Cloud revenue ($B)", axis: "$B" | FAIL |
| Bars labeled "25.0", axis shows 25 | FAIL |

---

### ANNOTATION RULES

#### Rule 13: Key Insight Called Out
**PASS**: Annotation, highlight, or callout marks the main finding
**FAIL**: No visual emphasis on the story point

| Example | Status |
|---------|--------|
| Arrow pointing to crossover with text | PASS |
| One bar in accent color | PASS |
| Plain chart, no emphasis | FAIL for tasks requiring highlight |

**Note**: For tasks without explicit highlight requirement, PASS if chart is clear.

#### Rule 14: Legend Only If >3 Categories
**PASS**: ≤3 categories = direct labels, >3 = legend
**FAIL**: Legend for 2-category chart, no legend for 7-category chart

| Categories | Expectation |
|------------|-------------|
| 1 | No legend |
| 2 | Direct labels on data |
| 3 | Direct labels preferred, legend OK |
| 4+ | Legend required |

---

### LAYOUT RULES

#### Rule 15: Correct Aspect Ratio
**PASS**: Line charts wider than tall (16:9), bar charts ~4:3
**FAIL**: Square time series, extremely narrow charts

| Chart Type | Acceptable Ratio | Fail |
|------------|------------------|------|
| Line | 16:9, 2:1, 3:2 | 1:1, 1:2 |
| Bar | 4:3, 5:4, 3:2 | 1:2, 1:3 |
| Scatter | 1:1 OK | Extreme narrow |

**Check**: width > height for time series, height ≈ width for comparisons

---

## Scoring Worksheet

```
Chart ID: ____________
Evaluator: ____________
Date: ____________

COLOR (4 pts)
[ ] 1. Muted palette:      PASS / FAIL
[ ] 2. One highlight:      PASS / FAIL  
[ ] 3. No red+green:       PASS / FAIL
[ ] 4. Consistent colors:  PASS / FAIL

TYPOGRAPHY (4 pts)
[ ] 5. Title = sentence:   PASS / FAIL
[ ] 6. Source present:     PASS / FAIL
[ ] 7. Sans-serif font:    PASS / FAIL
[ ] 8. Labels for ≤8:      PASS / FAIL

AXES (4 pts)
[ ] 9. Y=0 for bars:       PASS / FAIL
[ ] 10. No top/right:      PASS / FAIL
[ ] 11. Subtle gridlines:  PASS / FAIL
[ ] 12. No redundancy:     PASS / FAIL

ANNOTATIONS (2 pts)
[ ] 13. Key insight:       PASS / FAIL
[ ] 14. Legend rule:       PASS / FAIL

LAYOUT (1 pt)
[ ] 15. Aspect ratio:      PASS / FAIL

TOTAL: ___ / 15

GRADE: A(15) B(13-14) C(11-12) F(≤10)

Notes:
_____________________________________
_____________________________________
```

---

## Inter-Rater Calibration

### Calibration Protocol

1. Both evaluators independently score 10 charts
2. Compare scores, calculate agreement rate
3. Discuss all disagreements
4. Calculate Cohen's kappa:

```
kappa = (observed_agreement - expected_agreement) / (1 - expected_agreement)
```

5. If kappa < 0.7:
   - Identify ambiguous rules
   - Add clarifying examples to rubric
   - Re-calibrate on 10 new charts
6. Proceed only when kappa >= 0.7

### Common Disagreement Sources

| Rule | Common Issue | Resolution |
|------|--------------|------------|
| 5 (Title) | What counts as "sentence"? | Must state finding, not describe |
| 8 (Labels) | When is axis "clear enough"? | If reader can identify value within 10%, OK |
| 13 (Insight) | What if no highlight requested? | PASS if task didn't specify |
| 15 (Ratio) | How precise? | Within 20% of target ratio |

---

## Edge Cases

### Q: What if chart uses dark mode?
A: Same rules apply. Colors should still be muted (not neon), gridlines subtle (not invisible).

### Q: What if data has extreme outliers?
A: Log scale is acceptable for line charts. Bar charts still require Y=0.

### Q: What if title is in another language?
A: Same structure rules apply. Should be full sentence, not label.

### Q: What if no annotation tool available?
A: PASS Rule 13 if highlight color is used to emphasize key point.

### Q: What about stacked bar charts?
A: Y=0 still required. Each segment should be distinguishable.
