---
name: update-paper-numbers
description: Systematically update all statistical numbers in a LaTeX paper after recomputing results, ensuring consistency across abstract, body, tables, and appendices.
---

# Update Paper Numbers

When experiment data changes (new domain, removed domain, rerun fixes), every number in the paper must be updated consistently. This skill ensures nothing is missed.

## Process

### Step 1: Recompute all statistics

Run the stats script and capture exact output:

```bash
python3 scripts/recompute_stats.py 2>&1 | tee /tmp/new_stats.txt
```

Save this output — every number in the paper must match it exactly.

### Step 2: Inventory all numbers in the paper

Search for every numeric claim:

```bash
# Find all percentage values
grep -n '[0-9]\+\.[0-9]\+\\%' paper/main.tex

# Find all run counts
grep -n '[0-9]\{3,\} runs\|[0-9]\{3,\} scored' paper/main.tex

# Find domain counts
grep -n 'four\|five\|six\|seven' paper/main.tex

# Find effect sizes
grep -n 'delta\|0\.[0-9]\{3\}' paper/main.tex

# Find p-values
grep -n 'p\s*[<>=]' paper/main.tex
```

### Step 3: Update in order

Work through the paper linearly to avoid missing references:

1. **Title and abstract** — run count, domain count, headline numbers
2. **Introduction** — domain list, key claims
3. **Methodology** — domain descriptions, rule counts, run counts
4. **Results tables** — every cell in Tables 1-N
5. **Results narrative** — inline numbers that reference table values
6. **Discussion** — derived claims (ratios, percentages, comparisons)
7. **Threats to validity** — any domain-specific caveats
8. **Conclusion** — summary numbers
9. **Appendix** — rule details, per-domain breakdowns

### Step 4: Verify consistency

After all edits:

```bash
# Compile
tectonic paper/main.tex

# Check for undefined references
tectonic paper/main.tex 2>&1 | grep -i "undefined"

# Verify no old numbers remain (e.g., if you changed from 666 to 630 runs)
grep -n '666' paper/main.tex  # should return nothing

# Verify no domain references remain if removed
grep -ci 'openapi' paper/main.tex  # should return 0
```

## Common Pitfalls

1. **Tables have two representations** — the `\begin{tabular}` data AND the narrative sentence that describes the table. Both must match.
2. **Derived numbers** — "3.5x reduction" is computed from two other numbers. If those change, the multiplier changes too.
3. **Relative claims** — "Dockerfile shows the smallest effect" may become false if a new domain is added or removed.
4. **Direction claims** — "all four domains show positive effect" must be verified against the actual data. Check binomial test p-value.
5. **Appendix rule counts** — if you add/remove a domain, update the rule count range (e.g., "12--15 rules").
6. **Bibliography** — if you add/remove content, some citations may become unused. Check: `grep -oP '\\cite\{[^}]+\}' paper/main.tex | sort -u`

## LaTeX Number Formatting

- Percentages: `34.0\%` (one decimal place for failure rates)
- Effect sizes: `$\delta = 0.183$` (three decimal places for Cliff's delta)
- p-values: `$p < 0.001$` for very small, `$p = 0.015$` for moderate
- Run counts: plain number, no formatting: `630 scored runs`
- Multipliers: `3.5$\times$` with math mode for the times symbol
