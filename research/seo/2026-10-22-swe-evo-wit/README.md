# SWE-EVO: WiT correction after visual feedback

22 October 2026. This supersedes the coloured context cards and failure-flow presentation in the [earlier UI-polish report](../2026-10-22-swe-evo-ui-polish/README.md). The owner rejected their arbitrary colour, accent borders, narrow text columns and highlighted evidence boxes despite a mechanically clean run. The requested direction is **Words in Table (WiT)**.

## Final presentation

- Context audit: a plain two-column text table with strong row labels and full-width horizontal separators. No coloured cards, connector or duplicated input banner.
- Failure guidance: three text columns with one header row. No arrows, repeated desktop headings or highlighted evidence column.
- Phone: labels stack above full-width descriptions, preserving table/row/cell semantics and explicit header relationships.
- Section eyebrow: **Our experiment**. The redundant date is removed there; source/methodology dates remain.

Existing research claims, decision descriptions, failure/remedy/evidence sentences and external destinations are preserved. There is no new scientific result or additional numerical claim.

## Measurements and screenshots

Used the installed aictrl ui-polish content profile with scripts disabled and assets-only loading at phone 390×844 and desktop 1366×900. The full article and both corrected sections report zero errors and zero warnings. Mechanical before/after remains zero→zero; the change addresses the owner's visual judgement, which those checks did not capture.

| Section | Desktop | Phone | Receipt |
| --- | --- | --- | --- |
| Instruction audit | [screenshot](context/desktop-scope.png) | [screenshot](context/phone-scope.png) | [measurements](context/measure.json) |
| Failure guidance | [screenshot](failures/desktop-scope.png) | [screenshot](failures/phone-scope.png) | [measurements](failures/measure.json) |

[Full article measurements](article-measure.json), [compare output](compare.txt). The existing cookie banner is hidden for measurements only. Component-only captures additionally hide the site navigation because sticky chrome otherwise overlays element screenshots. No site-navigation CSS, cookie preference or tracking policy was changed.

## Visual rubric correction

| Point | Rejected version | WiT revision |
| --- | --- | --- |
| Grid/alignment | Pass mechanically; narrow card columns | Shared text-column edges; wide descriptions |
| Sizing | Pass mechanically; excessive equal-height card boxes | Content-sized rows |
| Labels/units | Repeated failure headers | One desktop header row; mobile labels next to their content |
| Hierarchy/focal point | Decorative cards compete with the text | Row labels lead into the descriptions |
| Grouping/rhythm | Fail: repetitive panels and arrows | Plain rows and consistent separators |
| Type | Fail visually: short lines and frequent wraps | Normal article body size; wider line measure |
| Colour/contrast | Fail visually: arbitrary highlights | Plain text and neutral rules in both sections |
| Controls/states | Existing navigation unchanged | Existing navigation unchanged |
| Consistency | Pass mechanically; unsuitable pattern | Same WiT treatment in both sections |
| 10a Orientation | Existing headings present | Existing headings retained |
| 10b Length | Existing reading-time/navigation | Unchanged |
| 10c Service | Brand/disclosure visible | Unchanged |
| 10d Sensitive questions | N/A | N/A |
| 10e Finish | Measurement pass did not establish quality | Checked responsive screenshots; owner approval is not implied |

No placeholders or unresolved mechanical warnings. This records the implemented preference, not a claim that the owner has approved the result.
