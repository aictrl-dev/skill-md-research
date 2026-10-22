# SWE-EVO article: UI-polish run

22 October 2026. Target: `http://127.0.0.5:3005/blog/swe-evo-analysis`. Scope: `article.swe-evo-review`. Product PR: [#6434](https://github.com/aictrl-dev/aictrl/pull/6434). Before source: `17948751108767e484c04ea97b969c1538dd350e`.

Used the installed aictrl `ui-polish` skill and its bundled `measure.cjs`, with the content profile, assets-only mode, scripts disabled, and the existing cookie banner hidden for measurement only. Phone 390×844; desktop 1366×900. No production tracking or cookie preferences were changed. Measurements concern the article, not unrelated header/footer controls.

## Result

| Measure | Before | After |
| --- | --- | --- |
| Errors | 1 grouped finding: five 17px section-link targets | 0 |
| Warnings | 1 grouped finding: four 12px labels | 0 |
| Informational findings | 1 grouped finding: six 12px kicker labels | 0 |
| Compare | — | Fixed 3; remaining 0; new 0 |
| Accepted exceptions | None | None |

One source-edit and re-measurement round. The result was inspected visually at both widths, including the complete article screenshots. Every numerical claim and source note is retained; the table of failure/remedy/evidence becomes a responsive four-case sequence. The only new copy reported by compare is the context-input line assembled from the preceding paragraph and decorative arrows. No bracketed placeholders or invented numbers were introduced.

## Before and after

| View | Before | After |
| --- | --- | --- |
| Desktop opening | [before](before/desktop.png) | [after](after/desktop.png) |
| Desktop full article | [before](before/desktop-scope.png) | [after](after/desktop-scope.png) |
| Phone opening | [before](before/phone.png) | [after](after/phone.png) |
| Phone full article | [before](before/phone-scope.png) | [after](after/phone-scope.png) |

Raw geometry/contrast/copy receipts: [before](before/measure.json), [after](after/measure.json). Same CLI flags and viewport sizes were used for both.

## Visual rubric

| Point | Before | After | Located problem and resolution |
| --- | --- | --- | --- |
| 1 Grid/alignment | Pass | Pass | Retained the shared reading-column edge. Diagram, chart and comparison panels align with the prose. |
| 2 Sizing | Fail | Pass | Tiny section links became padded 44px targets; mobile panels fill their column. |
| 3 Labels/units | Pass | Pass | Chart units, model/harness headings and source labels remain explicit. No form fields. |
| 4 Hierarchy/focal point | Fail | Pass | Oversized headline reduced; the takeaway, navigable sections and measured experiment are distinct visual anchors. |
| 5 Grouping/rhythm | Fail | Pass | Gray prose/table repetition replaced by context routes, prompt comparison panels, numbered procedure rows and failure→remedy→evidence sequences. |
| 6 Type | Fail | Pass | 12px labels increased to 14px; body remains 16px or larger on the phone. |
| 7 Colour/contrast | Fail | Pass | Before was readable but visually uniform. Restrained indigo structure, teal evidence/contract panels, purple skills and amber execution/readout notes provide meaning. All measured contrast checks pass. |
| 8 Controls/states | Fail | Pass | Section links gained adequate touch areas plus hover/focus treatment; links and anchors retain their destinations. No new controls or interaction state. |
| 9 Consistency | Pass | Pass | Existing brand palette, spacing tokens, sharp corners and border system retained. |
| 10a Where you are | Pass | Pass | Article title, descriptive section headings and byline remain. |
| 10b How much is left | Pass | Pass | Existing reading-time copy and section navigation retained; no new duration/progress claim. |
| 10c Whose service | Pass | Pass | aictrl brand and product disclosure retained. |
| 10d Why we ask | N/A | N/A | No sensitive information requested. |
| 10e Finished | Pass | Pass | No clipped text or debug content; measured overflow checks pass. |

The colour/rhythm assessment is an editorial design judgement, not a claim that zero mechanical findings guarantees an engaging article. Long-form prose remains between the figures; evidence and instructions remain visible rather than being hidden in collapsed sections.

## Changes by element

- Hero/takeaway/navigation: shorter visual headline, indigo divider and summary surface, larger touch targets.
- Research paragraph/context diagram: an attributed highlight and four routes using existing context/skill/execution concepts.
- Benchmark/experiment: clear column headers, tabular numerals, readout note and prominent two-configuration token comparison.
- Prompt/procedure: side-by-side panels on desktop, stacked on phone; numbered procedure rows with stronger labels.
- Failure guidance: four responsive sequences preserving all original failure, intervention and evidence sentences.

No unresolved design decision, accepted warning or placeholder remains. Shared-site chrome and unrelated pages are outside this article-only polish.
