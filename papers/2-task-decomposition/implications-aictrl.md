# Implications for aictrl.dev: Planning & Validation Tooling

**Last updated**: 2026-02-21
**Audience**: Product development team
**Purpose**: Translate research findings into actionable product recommendations

---

## Executive Summary

The research strongly supports building **planning and validation tooling** that:

1. **Generates structured intermediate artifacts** (schemas, state machines, plans) before execution
2. **Validates each step** before proceeding to the next
3. **Caches and reuses** common transformation patterns
4. **Exposes failure points** through artifact inspection

---

## 1. Core Finding: Decomposition Improves Reliability

### Research Evidence

| Paper | Improvement | Key Insight |
|-------|-------------|-------------|
| MAKER | 0% error rate over 1M steps | Extreme decomposition + voting at each step |
| Lifecycle-Aware | +75% correctness | Intermediate artifacts compound quality |
| Divide-and-Conquer | +8.6% Pass@1 | CoT hits ceiling; decomposition breaks through |

### Product Implication

**aictrl.dev should generate plans as structured artifacts, not just execute tasks.**

```
Current (implicit):  User request → LLM → Output
Proposed (explicit): User request → Plan (artifact) → Validate → Execute → Output
```

---

## 2. What Kind of Intermediate Artifacts?

### Research Findings on Artifact Types

| Artifact Type | Use Case | Quality Impact | Source |
|---------------|----------|----------------|--------|
| **State machines** | Code/workflow generation | Highest impact | Lifecycle-Aware |
| **Schemas (JSON/YAML)** | Data transformation, visualization | Enables validation | SemanticALLI |
| **Prolog/logic rules** | Multi-hop reasoning | Outperforms CoT | π-CoT |
| **Code scaffolds** | Tool execution | Enables debugging | ToolCoder |
| **Summaries/outlines** | Long-context tasks | Enables compression | CLIPPER |

### Recommendation for aictrl.dev

**Generate artifact types based on task domain:**

| Domain | Artifact Type | Example |
|--------|---------------|---------|
| Data transformation | Schema definition | `{source_schema, target_schema, mapping_rules}` |
| Code generation | State machine + pseudocode | Flow diagram + step descriptions |
| Visualization | Chart spec (Vega-Lite) | JSON schema before rendering |
| API integration | Request/response schema | OpenAPI-style spec |
| SQL/query | Query plan | Table dependencies + column mapping |

---

## 3. Planning Tool Architecture

### Proposed Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     aictrl.dev Planning                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐              │
│  │  Intent  │───▶│   Plan   │───▶│  Review  │              │
│  │  Parser  │    │ Generator│    │  Agent   │              │
│  └──────────┘    └──────────┘    └──────────┘              │
│       │               │                │                     │
│       ▼               ▼                ▼                     │
│  ┌──────────────────────────────────────────────┐          │
│  │           Plan Artifact (structured)          │          │
│  │  - steps: [{type, input, output, validation}]│          │
│  │  - dependencies: DAG of step relationships    │          │
│  │  - schemas: input/output type definitions     │          │
│  │  - estimated_cost: tokens, time              │          │
│  └──────────────────────────────────────────────┘          │
│                          │                                   │
│                          ▼                                   │
│  ┌──────────────────────────────────────────────┐          │
│  │              Validation Layer                 │          │
│  │  - Schema validation (JSON Schema)            │          │
│  │  - Dependency cycle detection                 │          │
│  │  - Resource feasibility check                 │          │
│  │  - Security policy compliance                 │          │
│  └──────────────────────────────────────────────┘          │
│                          │                                   │
│                          ▼                                   │
│  ┌──────────────────────────────────────────────┐          │
│  │              Execution Engine                 │          │
│  │  - Step-by-step execution                     │          │
│  │  - Checkpointing at each step                 │          │
│  │  - Rollback on failure                        │          │
│  │  - Progress tracking                          │          │
│  └──────────────────────────────────────────────┘          │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Key Components

#### 3.1 Plan Generator

**Input**: User request (natural language)
**Output**: Structured plan artifact

```yaml
plan:
  id: plan_abc123
  intent: "Transform customer data from Salesforce to Stripe format"
  steps:
    - id: step_1
      type: schema_analysis
      input: { source: salesforce_customers }
      output: { schema: customer_schema_v1 }
      validation: json_schema_valid
      
    - id: step_2
      type: mapping_generation
      input: { source_schema: customer_schema_v1, target: stripe_customer }
      output: { mapping: field_mapping_v1 }
      depends_on: [step_1]
      validation: all_required_fields_mapped
      
    - id: step_3
      type: transformation_execution
      input: { data: salesforce_customers, mapping: field_mapping_v1 }
      output: { transformed: stripe_format_data }
      depends_on: [step_2]
      validation: output_schema_matches_target
```

#### 3.2 Validation Layer

**Per-step validation** (from R-LAM paper):
- Schema conformance
- Type checking
- Business rule compliance
- Security policy

**Cross-step validation**:
- Dependency cycle detection
- Resource feasibility
- Timeout estimation

#### 3.3 Execution Engine

**From MAKER paper**: Checkpointing + voting at each step

```python
for step in plan.steps:
    artifact = execute_step(step)
    
    if validate(artifact, step.validation_rules):
        checkpoint(step, artifact)
    else:
        # Retry with alternative approach
        artifact = retry_with_feedback(step, validation_errors)
        
        if not validate(artifact):
            rollback_to_checkpoint(step - 1)
            request_human_input(step)
```

---

## 4. Validation Tool Architecture

### Research Support

| Paper | Validation Approach | Result |
|-------|---------------------|--------|
| π-CoT | Prolog queries as verifiable artifacts | Outperforms RAG/CoT |
| R-LAM | Structured action schemas + provenance | Enables audit/replay |
| ToolCoder | Error traceback for systematic debugging | Higher task success |

### Validation Capabilities

#### 4.1 Schema Validation

```yaml
validation:
  type: json_schema
  spec:
    type: object
    required: [customer_id, email]
    properties:
      customer_id:
        type: string
        pattern: "^cus_[a-zA-Z0-9]+$"
      email:
        type: string
        format: email
```

#### 4.2 Business Rule Validation

```yaml
validation:
  type: custom_rules
  rules:
    - name: no_pii_in_logs
      check: "output.logs | contains_pii | not"
    - name: required_fields_mapped
      check: "output.mapping | keys | contains_all(target.required_fields)"
```

#### 4.3 Security Policy Validation

```yaml
validation:
  type: security_policy
  policies:
    - no_external_api_calls_without_auth
    - no_raw_secrets_in_output
    - rate_limit_compliance
```

---

## 5. Caching & Reuse (Cost Reduction)

### Research Support

**SemanticALLI**: 83% cache hit rate on intermediate representations

### Implementation

```yaml
cache:
  # Cache intermediate artifacts, not just final outputs
  enabled: true
  
  artifacts:
    - type: schema_analysis
      key: hash(source_data_structure)
      ttl: 24h
      
    - type: mapping_generation
      key: hash(source_schema + target_schema)
      ttl: 168h  # 1 week
      
    - type: transformation_code
      key: hash(mapping + target_format)
      ttl: 720h  # 30 days
```

### Cost Savings

| Scenario | Without Caching | With Caching | Savings |
|----------|-----------------|--------------|---------|
| Repeated transformation | 3 LLM calls | 1 LLM call | 66% |
| Similar data structures | 3 LLM calls | 2 LLM calls | 33% |
| Same target schema | 2 LLM calls | 0 LLM calls | 100% |

---

## 6. Failure Debugging & Recovery

### Research Support

| Paper | Approach | Benefit |
|-------|----------|---------|
| MOSAIC | Consolidated Context Window | Reduces hallucination |
| VIGIL | Emotional representation + RBT diagnosis | Self-healing |
| ERL | Erase-and-regenerate faulty steps | Prevents error propagation |

### Debugging Workflow

```
Failure at Step 3: transformation_execution
    │
    ├── 1. Identify failure point (which validation failed?)
    │
    ├── 2. Inspect intermediate artifacts
    │   ├── Input artifact (from Step 2)
    │   ├── Execution trace
    │   └── Validation errors
    │
    ├── 3. Determine root cause
    │   ├── Bad input? → Retry Step 2
    │   ├── Bad execution? → Retry Step 3 with feedback
    │   ├── Bad plan? → Regenerate plan
    │
    └── 4. Apply fix
        ├── Automatic: retry with error context
        └── Manual: request human input
```

---

## 7. Product Features to Build

### Phase 1: Foundation (2-4 weeks)

| Feature | Description | Research Basis |
|---------|-------------|----------------|
| **Plan Generator** | Generate structured plan from NL request | TMK Framework |
| **Schema Validator** | JSON Schema validation for artifacts | R-LAM |
| **Step Executor** | Execute plan step-by-step with checkpointing | MAKER |

### Phase 2: Reliability (4-6 weeks)

| Feature | Description | Research Basis |
|---------|-------------|----------------|
| **Artifact Cache** | Cache intermediate representations | SemanticALLI |
| **Retry Engine** | Retry failed steps with error context | ERL |
| **Rollback** | Revert to last successful checkpoint | R-LAM |

### Phase 3: Intelligence (6-8 weeks)

| Feature | Description | Research Basis |
|---------|-------------|----------------|
| **Plan Reviewer** | Second agent reviews plan before execution | MOSAIC |
| **Failure Analyzer** | Auto-diagnose failure root cause | VIGIL |
| **Plan Optimizer** | Merge redundant steps, optimize DAG | Divide-and-Conquer |

---

## 8. Metrics to Track

### Quality Metrics

| Metric | Definition | Target |
|--------|------------|--------|
| Plan validity rate | % of plans that pass validation | > 95% |
| Step success rate | % of steps that complete without error | > 90% |
| End-to-end success | % of requests completed successfully | > 85% |
| Artifact reuse rate | % of cached artifacts reused | > 50% |

### Cost Metrics

| Metric | Definition | Target |
|--------|------------|--------|
| Tokens per request | Total tokens consumed | Reduce 30% via caching |
| LLM calls per request | Number of API calls | < 5 for simple tasks |
| Cache hit rate | % of cache lookups that succeed | > 60% |

### Reliability Metrics

| Metric | Definition | Target |
|--------|------------|--------|
| Recovery rate | % of failures that auto-recover | > 70% |
| MTTR | Mean time to recovery | < 30s |
| Rollback rate | % of requests requiring rollback | < 10% |

---

## 9. Competitive Differentiation

### How This Differs from Current Approaches

| Approach | Current Tools | aictrl.dev (Proposed) |
|----------|---------------|----------------------|
| **Planning** | Implicit (LLM decides internally) | Explicit (structured artifact) |
| **Validation** | Output-only | Per-step + cross-step |
| **Debugging** | Black box | White box (inspect artifacts) |
| **Caching** | Response-only | Intermediate artifacts |
| **Recovery** | Restart from scratch | Rollback + retry |

### Key Differentiator: **Verifiable Intermediate Artifacts**

Users can:
1. See the plan before execution
2. Validate each step independently
3. Debug failures at the artifact level
4. Cache and reuse transformation logic

---

## 10. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **Over-decomposition** (too many steps) | Medium | Latency, cost | Auto-merge similar steps |
| **Artifact complexity** (hard to validate) | Low | User confusion | Use standard schemas (JSON Schema, OpenAPI) |
| **Cache invalidation** | Medium | Stale results | TTL + hash-based keys |
| **Plan divergence** (plan != execution) | Medium | Trust issues | Runtime validation + alerts |

---

## 11. Next Steps

1. **Prototype**: Build plan generator for 1-2 domains (data transformation, visualization)
2. **Validate**: Run A/B test comparing one-shot vs. planned execution
3. **Measure**: Track quality, cost, and latency metrics
4. **Iterate**: Add caching, retry, and debugging features

---

## Appendix: Example Use Cases

### A. Data Transformation (Salesforce → Stripe)

**Without planning**:
```
User: "Transform my Salesforce customer data to Stripe format"
LLM: [generates transformation code]
Result: ❌ Missing field mappings, wrong format
```

**With planning**:
```yaml
Plan:
  1. Analyze Salesforce schema → Artifact: {schema: ...}
  2. Map to Stripe schema → Artifact: {mapping: ...}  
  3. Generate transformation → Artifact: {code: ...}
  4. Validate output → Artifact: {validation_result: ...}
  5. Execute → Result: ✓
```

### B. Visualization Generation

**Without planning**:
```
User: "Create a bar chart showing revenue by region"
LLM: [generates chart spec]
Result: ❌ Wrong chart type, missing labels
```

**With planning**:
```yaml
Plan:
  1. Analyze data characteristics → Artifact: {data_profile: ...}
  2. Choose chart type → Artifact: {chart_type: bar, rationale: ...}
  3. Generate spec → Artifact: {vega_lite_spec: ...}
  4. Validate spec → Artifact: {validation: ...}
  5. Render → Result: ✓
```

### C. SQL Query Generation

**Without planning**:
```
User: "Get monthly revenue by product category"
LLM: [generates SQL]
Result: ❌ Wrong JOIN, missing aggregation
```

**With planning**:
```yaml
Plan:
  1. Parse intent → Artifact: {entities: [revenue, product, month], aggregations: [sum]}
  2. Map to tables → Artifact: {table_mapping: ...}
  3. Build query plan → Artifact: {join_graph: ..., aggregation_steps: ...}
  4. Generate SQL → Artifact: {sql: ...}
  5. Validate → Artifact: {syntax_check: ✓, schema_check: ✓}
  6. Execute → Result: ✓
```
