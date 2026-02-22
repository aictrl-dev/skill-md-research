# Quick Reference: Task Decomposition Research

## Research Question

**Does breaking tasks into intermediate artifacts improve LLM execution quality?**

---

## Key Findings from Literature

| Paper | Finding | Impact |
|-------|---------|--------|
| MAKER | Extreme decomposition + voting → 0% errors over 1M steps | Reliability |
| Lifecycle-Aware | Intermediate artifacts → +75% correctness | Quality |
| SemanticALLI | Cache intermediate representations → 83% hit rate | Cost |
| Divide-and-Conquer | DAC reasoning → +8.6% over CoT | Quality ceiling |

---

## Hypotheses to Test

| ID | Hypothesis | Prediction |
|----|------------|------------|
| H1 | Stack decomposition wins for CRUD | Stack > Domain > Journey |
| H2 | Domain decomposition wins for workflows | Domain > Stack > Journey |
| H3 | Journey decomposition wins for UI flows | Journey > Domain > Stack |
| H4 | Full artifacts (Gherkin+API+SQL) best for CRUD/Integration | Full > Gherkin+API > Gherkin > NL |
| H5 | Gherkin-only best for UI flows | Gherkin > Full (less overhead) |

---

## Experiment Design

| Dimension | Values |
|-----------|--------|
| **Tasks** | 4 (CRUD, Workflow, Integration, UI) |
| **Decompositions** | 3 (stack, domain, journey) |
| **Artifact formats** | 4 (nl, gherkin, gherkin_api, full) |
| **Models** | 3 (economy, mid, frontier) |
| **Reps** | 3 |
| **Total** | 432 runs |

---

## Task Quick Reference

### outline_crud_001: Add word_count
- **Type**: CRUD
- **Best Decomp**: Stack (DB → Model → API → Presenter)
- **Best Artifacts**: Full (Gherkin + OpenAPI + SQL)
- **Files**: `Document.ts`, presenter, migration

### outline_workflow_001: Approval Workflow
- **Type**: Workflow (State Machine)
- **Best Decomp**: Domain (ApprovalState, transitions, commands)
- **Best Artifacts**: Full
- **Files**: `Document.ts`, `DocumentApproval.ts`, API endpoints

### outline_integration_001: Slack Webhook
- **Type**: Integration
- **Best Decomp**: Stack (Service → Types → API → Tests)
- **Best Artifacts**: Gherkin + API
- **Files**: `SlackWebhookService.ts`, API endpoint

### outline_uiflow_001: Creation Wizard
- **Type**: UI Flow
- **Best Decomp**: Journey (User actions → System responses)
- **Best Artifacts**: Gherkin only
- **Files**: `DocumentWizard/`, `DocumentWizardStore.ts`

---

## Decomposition Strategies

### Stack (Layer-by-Layer)
```
DB → Model → API → UI
```
**Best for**: CRUD, integrations

### Domain (Bounded Contexts)
```
Define domain → Implement rules → Wire infrastructure
```
**Best for**: Workflows, state machines

### Journey (User Actions)
```
User action → System response → Next action
```
**Best for**: UI flows, wizards

---

## Artifact Formats

| Format | Components | Verifiability |
|--------|------------|---------------|
| `nl` | Natural language | Low |
| `gherkin` | Scenarios | Medium (parser) |
| `gherkin_api` | + OpenAPI spec | High |
| `full` | + SQL migration | Highest |

---

## Quick Commands

```bash
# Single run
./run-decomposition-experiment.sh \
  --task outline_crud_001_word_count \
  --decomposition stack \
  --artifacts full \
  --rep 1

# Pilot (test run)
./run-decomposition-experiment.sh --pilot

# Full experiment
./run-decomposition-experiment.sh --full

# Dry run (see what would run)
./run-decomposition-experiment.sh --full --dry-run
```

---

## Evaluation Metrics

```python
success = (
    tests_pass AND           # yarn test
    migration_runs AND       # yarn db:migrate  
    api_works AND            # endpoints respond
    artifact_consistency AND # Gherkin → API → SQL aligned
)
```

---

## Files Structure

```
research/task-decomposition/
├── README.md                    # Overview
├── literature-review.md         # Academic research
├── implications-aictrl.md       # Product recommendations
├── enterprise-decomposition.md  # Epic/Story breakdown
├── experiment-design.md         # Visualization experiment
├── experiment-enterprise.md     # Enterprise experiment
├── codebase-selection.md        # Codebase analysis
│
└── experiment-harness/
    ├── README.md
    ├── codebase/                # Outline (cloned)
    ├── tasks/                   # 4 task specs
    ├── prompts/                 # Decomposition + artifact prompts
    ├── scripts/                 # Runner + evaluator
    └── results/                 # Experiment outputs
```

---

## Product Implications for aictrl.dev

1. **Planning tool**: Generate structured plans before execution
2. **Validation tool**: Verify artifacts at each step
3. **Caching**: Reuse intermediate representations
4. **Debugging**: Inspect failed steps, not just final output

See `implications-aictrl.md` for detailed recommendations.
