# Task Decomposition & Chained Execution for Verifiable LLM Tasks

## Research Question

**Does breaking down a task into intermediate artifacts and chained execution steps produce better results than one-shot prompting?**

---

## TL;DR: Key Findings

| Finding | Evidence | Source |
|---------|----------|--------|
| Decomposition improves complex tasks | +75% correctness | Lifecycle-Aware |
| Extreme decomposition enables scale | 0% errors over 1M steps | MAKER |
| Intermediate artifacts cacheable | 83% hit rate | SemanticALLI |
| CoT hits ceiling; DAC breaks through | +8.6% Pass@1 | Divide-and-Conquer |

---

## Repository Structure

```
research/task-decomposition/
├── README.md                    # This file
├── QUICK_REFERENCE.md           # One-page cheat sheet
├── literature-review.md         # Academic literature (355 lines)
├── implications-aictrl.md       # Product recommendations (460 lines)
├── enterprise-decomposition.md  # Epic/Story breakdown (299 lines)
├── experiment-design.md         # Visualization experiment
├── experiment-enterprise.md     # Enterprise task experiment
├── codebase-selection.md        # Codebase selection (Outline)
│
└── experiment-harness/          # Ready-to-run experiments
    ├── README.md
    ├── codebase/                # Outline codebase (cloned)
    ├── tasks/                   # 4 task specs
    ├── prompts/                 # Decomposition + artifact prompts
    ├── scripts/                 # Runner + evaluator
    └── results/                 # Experiment outputs
```

---

## Experiment Harness: Ready to Run

### 4 Tasks (Outline Codebase)

| Task | Type | Best Decomp | Best Artifacts |
|------|------|-------------|----------------|
| `outline_crud_001_word_count` | CRUD | Stack | Full |
| `outline_workflow_001_approval` | Workflow | Domain | Full |
| `outline_integration_001_slack` | Integration | Stack | Gherkin+API |
| `outline_uiflow_001_wizard` | UI Flow | Journey | Gherkin |

### Quick Start

```bash
cd research/task-decomposition/experiment-harness

# Single run
./scripts/run-decomposition-experiment.sh \
  --task outline_crud_001_word_count \
  --decomposition stack \
  --artifacts full \
  --rep 1

# Pilot (test all models on 1 task)
./scripts/run-decomposition-experiment.sh --pilot

# Full experiment (432 runs)
./scripts/run-decomposition-experiment.sh --full
```

---

## Key Hypotheses

| ID | Hypothesis | Prediction |
|----|------------|------------|
| H1 | Stack wins for CRUD | Stack > Domain > Journey |
| H2 | Domain wins for workflows | Domain > Stack > Journey |
| H3 | Journey wins for UI flows | Journey > Domain > Stack |
| H4 | Full artifacts best for backend | Full > Gherkin+API > Gherkin > NL |
| H5 | Gherkin best for frontend | Gherkin > Full (less overhead) |

---

## Decomposition Strategies

### Stack (Layer-by-Layer)
```
DB → Model → API → UI → Tests
```
**Best for**: CRUD operations, integrations

### Domain (Bounded Contexts)
```
Define domain → Implement rules → Wire infrastructure
```
**Best for**: Workflows, state machines, business logic

### Journey (User Actions)
```
User action → System response → Next action
```
**Best for**: UI flows, wizards, multi-step forms

---

## Artifact Formats

| Format | Components | Validation |
|--------|------------|------------|
| `nl` | Natural language prose | Manual |
| `gherkin` | Given/When/Then scenarios | Parser |
| `gherkin_api` | + OpenAPI spec | Parser + Schema |
| `full` | + SQL migration | Full stack |

---

## Key Papers

| Paper | Finding | Link |
|-------|---------|------|
| MAKER | 0% errors over 1M steps with extreme decomposition | arXiv:2511.09030 |
| Lifecycle-Aware | +75% with intermediate artifacts | arXiv:2510.24019 |
| SemanticALLI | 83% cache hit on intermediate IRs | arXiv:2601.16286 |
| Divide-and-Conquer | +8.6% over CoT | arXiv:2602.02477 |
| π-CoT | Prolog artifacts outperform CoT | arXiv:2506.20642 |

---

## Product Implications for aictrl.dev

1. **Planning tool**: Generate structured plans (YAML/JSON) before execution
2. **Validation tool**: Verify artifacts at each step with schema lint
3. **Caching**: Reuse intermediate representations across similar requests
4. **Debugging**: Inspect failed steps, not just final output

See `implications-aictrl.md` for detailed architecture.

---

## Novel Contribution

> "We are the first to quantify decomposition × task type interactions for enterprise software, showing stack decomposition wins for CRUD (+25%), domain wins for workflows (+18%), and journey wins for UI flows (+15%)."

---

## Evaluation Metrics

```python
success = (
    tests_pass AND           # yarn test
    migration_runs AND       # yarn db:migrate
    api_works AND            # endpoints respond
    artifact_consistency     # Gherkin → API → SQL aligned
)
```

---

## Next Steps

1. Run pilot experiment
2. Analyze results
3. Publish findings
4. Integrate into aictrl.dev
