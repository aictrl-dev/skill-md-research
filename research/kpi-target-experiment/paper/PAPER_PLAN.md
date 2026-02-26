# Paper Plan: Motivation Framing in LLM Agents

## Target: arXiv submission (CS.CL - Computation and Language)

## Working Title
"Motivation Framing Improves LLM Agent Performance: KPI Targets and Historical Context Increase Output Quality by 17.6%"

## Abstract (200-250 words)
[To write after all results are in]

Key points to cover:
- Problem: LLMs don't naturally allocate effort based on task difficulty
- Solution: Motivation framing with KPI targets and historical context
- Method: A/B test across 4 models, 2 domains, 3 task complexities
- Results: +17.6% quality improvement, effect larger for weaker models
- Implication: Goal-setting theory applies to AI agents

---

## Section 1: Introduction (~800 words)

### 1.1 Motivation
- LLMs apply uniform effort regardless of task difficulty (cite adaptive reasoning survey)
- Unlike humans, LLMs don't respond to challenge or ambitious goals
- Question: Can motivation framing change LLM behavior?

### 1.2 Background
- Test-time compute scaling shows more effort = better outcomes
- But effort allocation is not adaptive to task needs
- Human motivation research: ambitious goals improve performance (Locke & Latham)

### 1.3 Contribution
- First study on motivation framing for LLM agents
- Novel intervention: KPI targets + historical performance context
- Empirical validation across multiple models and domains

---

## Section 2: Related Work (~600 words)

### 2.1 Test-Time Compute and Effort Allocation
- Best-of-N scaling
- Adaptive computation
- Chain-of-thought and reasoning effort

### 2.2 Prompt Engineering for Performance
- Role prompting
- Few-shot examples
- Self-consistency

### 2.3 Motivation and Goal-Setting Theory
- Human motivation literature
- Goal difficulty and performance
- Gap: No prior work on goal-setting for AI

---

## Section 3: Method (~1000 words)

### 3.1 Intervention Design
- KPI target: "97% compliance"
- Historical context: baseline, skill-enhanced, top-performer scores
- Rule-specific guidance: focus attention on low-baseline rules

### 3.2 Experimental Design
- Conditions: markdown (control) vs markdown+target (treatment)
- Domains: SQL Query (dbt), Chart (visualization)
- Models: haiku, opus, glm-4.7, glm-5
- Tasks: 3 complexity levels per domain
- Repetitions: 5 per cell

### 3.3 Domains and Evaluation
- SQL: 14 rules for dbt analytics pipelines
- Chart: 15 rules for visualization specifications
- Automated evaluation (no manual review)

### 3.4 Hypotheses
- H1: Target improves scores
- H2: Target increases tokens (effort)
- H3: Effect larger for weaker models

---

## Section 4: Results (~1200 words)

### 4.1 Primary Finding: Quality Improvement
- Overall: +17.6% improvement
- Table: Per-model results
- Statistical significance tests

### 4.2 Effort Allocation
- Token usage changes
- Variation by model
- glm-4.7: efficiency gain (quality up, tokens flat)

### 4.3 Model-Level Analysis
- haiku: +16% quality, +21% tokens
- opus: +12% quality, +11% tokens
- glm-4.7: +28% quality, +3% tokens (best efficiency)
- glm-5: +15% quality, +72% tokens

### 4.4 Task Complexity Effects
- Simple vs medium vs complex tasks
- Interaction with model capability

### 4.5 Domain Comparison
- SQL results (complete)
- Chart results (pending)

---

## Section 5: Discussion (~800 words)

### 5.1 Mechanism: Focus vs Effort
- Some models increase effort (more tokens)
- Some models improve focus (same tokens, better quality)
- Individual variation analogous to human goal-setting

### 5.2 Implications for AI Engineering
- Motivation framing as a prompt engineering technique
- Cost-quality trade-offs vary by model
- Recommended for weaker models / harder tasks

### 5.3 Limitations
- Single intervention design
- Two domains only
- 4 models tested
- Ceiling effects in some tasks

### 5.4 Future Work
- Optimal target levels (80% vs 90% vs 97%)
- Alternative framings (competition, loss aversion)
- Multi-domain replication

---

## Section 6: Conclusion (~200 words)

- Summary of findings
- Broader implications
- Call for further research

---

## Appendices

### A: Full Intervention Text
- KPI context template
- Domain-specific variants

### B: Evaluation Rubrics
- SQL: 14 rules detailed
- Chart: 15 rules detailed

### C: Raw Results
- Per-run scores
- Statistical tables

---

## Figures (planned)

1. **Figure 1**: Score comparison (bar chart)
2. **Figure 2**: Token vs Score trade-off (scatter)
3. **Figure 3**: Per-model breakdown (grouped bars)
4. **Figure 4**: Task complexity interaction (line chart)

---

## Tables (planned)

1. **Table 1**: Experiment design (conditions x models x tasks)
2. **Table 2**: Primary results (per-model scores)
3. **Table 3**: Token usage changes
4. **Table 4**: Statistical significance tests

---

## Timeline

| Task | Status | Owner |
|------|--------|-------|
| SQL experiments | ✓ Complete | - |
| Chart experiments | In progress | Auto |
| Paper outline | ✓ Draft | - |
| Abstract | Pending | - |
| Introduction | Pending | - |
| Method | Pending | - |
| Results (SQL) | Ready to write | - |
| Results (Chart) | Pending data | - |
| Discussion | Pending | - |
| Figures | Pending | - |
| Final review | Pending | - |

---

## Submission Checklist

- [ ] Abstract under 250 words
- [ ] All figures readable in B&W
- [ ] References formatted for arXiv
- [ ] No identifying information (blind review if applicable)
- [ ] Supplementary materials linked
