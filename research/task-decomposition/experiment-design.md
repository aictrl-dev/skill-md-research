# Experiment Design: One-Shot vs. Chained Execution for Visualization

**Last updated**: 2026-02-21
**Purpose**: Test whether task decomposition produces better results than one-shot prompting

---

## 1. Research Question

**Does breaking chart generation into explicit steps with intermediate artifacts improve output quality compared to one-shot prompting?**

### Conditions to Compare

| Condition | Description | Steps |
|-----------|-------------|-------|
| **One-shot** | Single prompt with all instructions | 1. Generate chart directly |
| **Chained (3-step)** | Explicit decomposition | 1. Analyze data → 2. Choose chart type → 3. Generate spec |
| **Chained + Artifact** | Decomposition with structured artifacts | 1. Analyze → 2. Define schema (YAML) → 3. Implement |

---

## 2. Hypotheses

| ID | Hypothesis | Direction |
|----|------------|-----------|
| H1 | Chained execution produces higher rule compliance than one-shot | One-tailed |
| H2 | Chained + Artifact produces higher rule compliance than Chained (no artifact) | One-tailed |
| H3 | Chained execution enables better error diagnosis | Qualitative |
| H4 | Artifact caching reduces cost for similar requests | Two-tailed |

---

## 3. Experimental Design

### 3.1 Task Domain: Chart Specification (Vega-Lite)

Reuse existing infrastructure from `domains/chart/`:
- 3 complexity levels (simple, medium, complex)
- 15-rule evaluation rubric
- Automated + manual scoring

### 3.2 Conditions

| Condition | Prompt Structure | Intermediate Output |
|-----------|------------------|---------------------|
| **C1: One-shot** | All instructions in single prompt + task data | None |
| **C2: Chained** | Step 1: Analyze data characteristics | Natural language analysis |
| | Step 2: Choose chart type + rationale | NL chart selection |
| | Step 3: Generate Vega-Lite spec | JSON spec |
| **C3: Chained + Artifact** | Step 1: Analyze data → data profile schema | YAML artifact |
| | Step 2: Choose chart → chart schema | YAML artifact |
| | Step 3: Implement from schema | JSON spec |

### 3.3 Example Prompts

#### C1: One-Shot

```
You are a data visualization expert. Create a Vega-Lite chart specification for the following data.

Data: {gdp_data}

Rules:
1. Use appropriate chart type for comparison
2. Include proper axis labels
3. Use readable fonts (12pt minimum)
4. Apply accessible color palette
... (15 rules)

Output the complete Vega-Lite JSON specification.
```

#### C2: Chained

```
Step 1: Analyze the following data and describe its characteristics.
- Number of data points
- Data types (categorical, numerical, temporal)
- Distribution patterns
- Recommended visualization approaches

Data: {gdp_data}

[LLM OUTPUT: natural language analysis]

---

Step 2: Based on your analysis, choose the most appropriate chart type.
Explain your rationale.

[LLM OUTPUT: chart type + rationale]

---

Step 3: Generate a Vega-Lite specification implementing your chosen chart type.
Follow all 15 rules:
...

Data: {gdp_data}
Chart type: {output from Step 2}
```

#### C3: Chained + Artifact

```
Step 1: Analyze the data and output a YAML data profile.

Schema:
```yaml
data_profile:
  row_count: int
  columns:
    - name: str
      type: categorical | numerical | temporal
      unique_values: int (if categorical)
      min: float (if numerical)
      max: float (if numerical)
  relationships:
    - type: correlation | hierarchy | sequence
      columns: [str]
```

Data: {gdp_data}

[LLM OUTPUT: YAML artifact]

---

Step 2: Based on the data profile, choose and define the chart schema.

Schema:
```yaml
chart_schema:
  chart_type: bar | line | scatter | pie | ...
  mark: str
  encoding:
    x: {field, type, title}
    y: {field, type, title}
    color: {field, type} (optional)
    size: {field, type} (optional)
  rationale: str
```

[LLM OUTPUT: YAML artifact]

---

Step 3: Implement the chart specification from the schema.

Input:
- Data profile: {output from Step 1}
- Chart schema: {output from Step 2}

Output: Complete Vega-Lite JSON specification following all 15 rules.
```

### 3.4 Full Factorial

| Factor | Levels | Count |
|--------|--------|-------|
| Condition | 3 (one-shot, chained, chained+artifact) | 3 |
| Task | 3 (gdp, ai-models, cloud-revenue) | 3 |
| Model | 5 (haiku, opus, glm-4.7-flash, glm-4.7, glm-5) | 5 |
| Repetitions | 3 | 3 |

**Total runs: 3 × 3 × 5 × 3 = 135 runs**

---

## 4. Metrics

### 4.1 Primary: Rule Compliance

**Dependent variable**: `failure_rate = 1 - (rules_passed / 15)`

Evaluate on same 15-rule rubric as existing experiments.

### 4.2 Secondary Metrics

| Metric | How Measured |
|--------|--------------|
| Total tokens | Sum of input + output tokens |
| Latency | Wall-clock time per condition |
| Artifact validity | Schema conformance (C3 only) |
| Error recovery | Can failure be diagnosed from intermediate output? |
| Cost | Tokens × price |

### 4.3 Qualitative Analysis

For failed outputs:
1. Can we identify which step failed? (C2, C3 only)
2. Is the intermediate artifact valid? (C3 only)
3. Can we fix by retrying only the failed step? (C2, C3 only)

---

## 5. Analysis Plan

### 5.1 Statistical Tests

**Primary comparison**: One-way ANOVA on failure_rate across 3 conditions

**Pairwise comparisons** (with Bonferroni correction):
1. C2 vs C1 (does chaining help?)
2. C3 vs C2 (do artifacts help?)
3. C3 vs C1 (does full decomposition help?)

### 5.2 Effect Sizes

- Cohen's d for pairwise comparisons
- Target: d > 0.5 (medium effect)

### 5.3 Subgroup Analysis

- By task complexity (simple vs medium vs complex)
- By model capability (economy vs frontier)
- By model family (Claude vs GLM)

---

## 6. Expected Outcomes

### Based on Literature

| Hypothesis | Expected Result | Confidence |
|------------|-----------------|------------|
| H1: C2 > C1 | Chaining improves compliance | Medium |
| H2: C3 > C2 | Artifacts improve compliance | Medium |
| H3: Better diagnosis | C3 enables step-level debugging | High |
| H4: Cost reduction | Caching works for similar data | Medium |

### Potential Surprises

1. **One-shot is competitive for frontier models**: Larger models may not need decomposition
2. **Overhead outweighs benefit**: Chaining costs may exceed quality gains
3. **Artifacts add friction**: Schema conformance may reduce flexibility

---

## 7. Implementation

### 7.1 Runner Script

```bash
# Run all conditions
./scripts/run-decomposition-experiment.sh --all

# Run single condition
./scripts/run-decomposition-experiment.sh --condition chained-artifact --task gdp --model haiku
```

### 7.2 File Structure

```
domains/chart/
  decomposition-experiment/
    prompts/
      one-shot.md
      chained.md
      chained-artifact.md
    results/
      one-shot/
        task1_model1_rep1.json
        ...
      chained/
        ...
      chained-artifact/
        ...
    artifacts/  # Intermediate outputs for C3
      task1_model1_rep1/
        data_profile.yaml
        chart_schema.yaml
    analyze_decomposition.py
```

### 7.3 Evaluation

```python
# Analyze results
python domains/chart/decomposition-experiment/analyze_decomposition.py

# Output:
# - failure_rate by condition
# - token consumption by condition
# - statistical significance tests
# - artifact validity analysis
```

---

## 8. Timeline

| Phase | Duration | Deliverable |
|-------|----------|-------------|
| Prompt design | 1 day | 3 prompt templates |
| Runner implementation | 1 day | run-decomposition-experiment.sh |
| Data collection | 1 day | 135 result files |
| Evaluation | 0.5 day | Scored results |
| Analysis | 0.5 day | Statistical report |
| **Total** | **4 days** | |

---

## 9. Success Criteria

| Outcome | Action |
|---------|--------|
| C3 significantly outperforms C1 (p < 0.05, d > 0.5) | Adopt chained+artifact approach for aictrl.dev |
| C2 ≈ C1 (no difference) | Skip artifacts, but may still chain for debugging |
| C3 > C2 > C1 (gradient) | Full decomposition recommended |
| Frontier models show no benefit | Recommend decomposition for economy models only |

---

## 10. Extensions

If results are promising:

1. **Test on other domains**: SQL generation, code generation
2. **Optimize decomposition granularity**: 2-step vs 3-step vs 5-step
3. **Implement caching**: Measure cost savings from artifact reuse
4. **Build plan editor**: Allow users to modify intermediate artifacts before execution
