# Experiment: Enterprise Software Decomposition

**Goal**: Determine optimal decomposition strategy and artifact format for LLM execution on real codebases

---

## 1. Hypotheses

### H1: Decomposition Strategy × Task Type Interaction

**Hypothesis**: Optimal decomposition depends on task type

| Task Type | Stack | Domain | Journey | Prediction |
|-----------|-------|--------|---------|------------|
| CRUD (add field) | **High** | Medium | Low | Stack wins |
| Workflow (state machine) | Low | **High** | Medium | Domain wins |
| Integration (API) | **High** | Low | Low | Stack wins |
| UI flow (multi-step) | Low | Medium | **High** | Journey wins |

**Eval objective**: `success_rate = tasks_with_passing_tests / total_tasks`

### H2: Artifact Format Impact

**Hypothesis**: Gherkin + OpenAPI + SQL outperforms other combinations

| Artifact Set | Prediction |
|--------------|------------|
| Natural language only | 50% success |
| Gherkin only | 65% success |
| Gherkin + OpenAPI | 75% success |
| **Gherkin + OpenAPI + SQL** | **85% success** |

**Eval objective**: `success_rate` per artifact set

### H3: Cross-Artifact Consistency

**Hypothesis**: Cross-reference validation catches errors before execution

| Validation Level | Error Detection Rate |
|------------------|---------------------|
| None | 0% (all errors reach execution) |
| Schema-only | 25% |
| Schema + Cross-ref | **60%** |

**Eval objective**: `errors_caught_at_validation / total_errors`

### H4: Step-Level Success Prediction

**Hypothesis**: Artifact quality predicts downstream success

| Metric | Correlation with Final Success |
|--------|-------------------------------|
| Gherkin parse success | r = 0.4 |
| OpenAPI schema validity | r = 0.6 |
| SQL migration success | r = 0.7 |
| **All three valid** | **r = 0.9** |

**Eval objective**: Correlation between intermediate validation and final success

---

## 2. Task Set (Concrete Examples)

### 2.1 CRUD Task

```yaml
task_id: crud_001
type: CRUD
description: "Add a 'phone_number' field to User model"
complexity: simple

input:
  - Existing User model (Prisma schema)
  - Existing User API endpoints
  - Existing User tests

expected_output:
  - Prisma schema updated with phone_number field
  - Migration file created
  - API endpoints accept/return phone_number
  - Tests updated for phone_number

decomposition_variants:
  stack:
    - step_1: Update Prisma schema
    - step_2: Create migration
    - step_3: Update API types
    - step_4: Update API handlers
    - step_5: Update tests
  
  domain:
    - step_1: Define User domain changes (phone_number as value object)
    - step_2: Implement User domain logic
    - step_3: Update all User-related code
    - step_4: Update tests
  
  journey:
    - step_1: User enters phone number (UI)
    - step_2: API validates phone number
    - step_3: Database stores phone number
    - step_4: User sees phone number in profile

eval_criteria:
  - Migration runs successfully
  - API accepts phone_number in POST/PATCH
  - API returns phone_number in GET
  - Tests pass
  - No breaking changes to existing fields
```

### 2.2 Workflow Task

```yaml
task_id: workflow_001
type: Workflow
description: "Add 'paused' state to Subscription lifecycle"
complexity: medium

input:
  - Existing Subscription model with states: [active, cancelled]
  - State transitions: active → cancelled
  - Billing logic tied to states

expected_output:
  - Subscription has 'paused' state
  - Transitions: active ↔ paused, paused → cancelled
  - Billing pauses when subscription is paused
  - Billing resumes when subscription is unpaused
  - UI shows pause/unpause buttons

decomposition_variants:
  stack:
    - step_1: Update DB schema (add paused state)
    - step_2: Update API endpoints
    - step_3: Update billing logic
    - step_4: Update UI
    - step_5: Update tests
  
  domain:
    - step_1: Define SubscriptionState value object
    - step_2: Define state machine transitions
    - step_3: Implement billing rules per state
    - step_4: Expose via API and UI
    - step_5: Update tests
  
  journey:
    - step_1: User clicks pause
    - step_2: System validates can pause
    - step_3: System pauses billing
    - step_4: User sees paused status
    - step_5: User clicks resume

eval_criteria:
  - State machine allows active → paused
  - State machine allows paused → active
  - Billing stops when paused
  - Billing resumes when unpaused
  - All existing tests still pass
  - New pause/unpause tests pass
```

### 2.3 Integration Task

```yaml
task_id: integration_001
type: Integration
description: "Add Slack webhook notification for failed payments"
complexity: medium

input:
  - Existing payment processing
  - No Slack integration currently

expected_output:
  - Slack webhook configured
  - Failed payment triggers Slack notification
  - Notification contains: amount, user, error, timestamp
  - Rate limiting on notifications (max 10/minute)

decomposition_variants:
  stack:
    - step_1: Create SlackIntegration DB model
    - step_2: Create SlackService class
    - step_3: Integrate into payment failure handler
    - step_4: Add configuration endpoints
    - step_5: Add tests
  
  domain:
    - step_1: Define Notification domain
    - step_2: Define NotificationChannel interface
    - step_3: Implement SlackChannel
    - step_4: Wire up to Payment domain events
    - step_5: Add tests
  
  journey:
    - step_1: Payment fails
    - step_2: System queues notification
    - step_3: Notification sent to Slack
    - step_4: Admin sees notification

eval_criteria:
  - Slack webhook URL is configurable
  - Failed payment triggers HTTP POST to Slack
  - POST body contains required fields
  - Rate limiting enforced
  - Tests mock Slack API and pass
```

### 2.4 UI Flow Task

```yaml
task_id: uiflow_001
type: UI Flow
description: "Add multi-step checkout wizard"
complexity: medium

input:
  - Existing single-page checkout
  - Cart, payment, user models

expected_output:
  - Step 1: Review cart
  - Step 2: Enter shipping
  - Step 3: Enter payment
  - Step 4: Confirm order
  - Progress indicator
  - Back/forward navigation

decomposition_variants:
  stack:
    - step_1: Update DB for checkout state
    - step_2: Create checkout API endpoints
    - step_3: Create checkout components
    - step_4: Wire up navigation
    - step_5: Add tests
  
  domain:
    - step_1: Define CheckoutSession aggregate
    - step_2: Define checkout business rules
    - step_3: Implement checkout handlers
    - step_4: Build UI on top
    - step_5: Add tests
  
  journey:
    - step_1: User views cart (Step 1)
    - step_2: User enters shipping (Step 2)
    - step_3: User enters payment (Step 3)
    - step_4: User confirms (Step 4)
    - step_5: System creates order

eval_criteria:
  - All 4 steps are accessible
  - Progress indicator shows current step
  - Back button works
  - Data persists between steps
  - Order created on completion
  - E2E tests pass
```

---

## 3. Artifact Format Variants

### A1: Natural Language Only

```markdown
## Task: Add phone_number to User

1. Update the User model to include a phone_number field
2. Make sure the API can accept and return phone_number
3. Update the tests to cover phone_number
```

### A2: Gherkin Only

```gherkin
Feature: User phone number

  Scenario: User adds phone number
    Given a user exists
    When I update the user with phone_number "+1234567890"
    Then the user's phone_number should be "+1234567890"

  Scenario: Phone number is optional
    Given a user exists without phone_number
    When I get the user
    Then the response should succeed
```

### A3: Gherkin + OpenAPI

```gherkin
# Gherkin as above
```

```yaml
# openapi.yaml
paths:
  /users/{id}:
    patch:
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                phone_number:
                  type: string
                  pattern: '^\+[1-9]\d{1,14}$'
                  description: E.164 format
```

### A4: Gherkin + OpenAPI + SQL (Full)

```gherkin
# Gherkin as above
```

```yaml
# openapi.yaml as above
```

```sql
-- migration.sql
ALTER TABLE users ADD COLUMN phone_number VARCHAR(20);
CREATE INDEX idx_users_phone ON users(phone_number);
```

---

## 4. Evaluation Metrics

### 4.1 Primary Metrics

| Metric | Definition | Target |
|--------|------------|--------|
| **Execution Success** | `tests_pass AND schema_valid AND api_works` | > 80% |
| **Artifact Consistency** | Cross-references valid (Gherkin → API → DB) | > 90% |
| **Step Success Rate** | Individual steps pass validation | > 85% |

### 4.2 Secondary Metrics

| Metric | Definition | Target |
|--------|------------|--------|
| **Tokens consumed** | Total input + output tokens | Minimize |
| **Rework rate** | Steps requiring regeneration | < 20% |
| **Time to completion** | Wall-clock time | Minimize |
| **Human review time** | Time to approve artifacts | < 5 min |

### 4.3 Evaluation Script

```python
def evaluate_task_run(task_id, decomposition, artifacts, output_code):
    results = {}
    
    # 1. Artifact validation
    results['gherkin_valid'] = validate_gherkin(artifacts.gherkin)
    results['openapi_valid'] = validate_openapi(artifacts.openapi)
    results['sql_valid'] = validate_sql(artifacts.sql)
    
    # 2. Cross-artifact consistency
    results['consistency'] = check_consistency(
        artifacts.gherkin,
        artifacts.openapi,
        artifacts.sql
    )
    
    # 3. Code generation success
    results['code_generates'] = can_compile(output_code)
    results['tests_pass'] = run_tests(output_code)
    
    # 4. Integration test (on real codebase)
    results['integration_pass'] = run_integration_tests(task_id, output_code)
    
    # 5. Overall success
    results['success'] = (
        results['tests_pass'] and 
        results['integration_pass'] and
        results['consistency'] > 0.9
    )
    
    return results
```

---

## 5. Experiment Matrix

### Full Factorial

| Factor | Levels | Count |
|--------|--------|-------|
| Task | 4 (CRUD, Workflow, Integration, UI) | 4 |
| Decomposition | 3 (Stack, Domain, Journey) | 3 |
| Artifact Format | 4 (NL, Gherkin, G+API, Full) | 4 |
| Model | 3 (economy, mid, frontier) | 3 |
| Repetitions | 3 | 3 |

**Total: 4 × 3 × 4 × 3 × 3 = 432 runs**

### Reduced Design (Recommended)

Focus on key comparisons:

| Experiment | Conditions | Runs |
|------------|------------|------|
| **Exp 1**: Decomposition × Task Type | 4 tasks × 3 decomp × 3 reps | 36 |
| **Exp 2**: Artifact Format | 1 task × 4 formats × 3 models × 3 reps | 36 |
| **Exp 3**: Consistency Validation | 1 task × 2 validation levels × 3 reps | 6 |
| **Total** | | **78 runs** |

---

## 6. Required Infrastructure

### 6.1 Target Codebase

Need a real codebase with:
- Prisma schema
- REST/GraphQL API
- React frontend
- Test suite (unit + integration)

**Options**:
1. Use aictrl.dev codebase (internal)
2. Create a synthetic SaaS starter (full control)
3. Use open-source SaaS template

### 6.2 Evaluation Harness

```
experiment-harness/
  tasks/
    crud_001.yaml
    workflow_001.yaml
    integration_001.yaml
    uiflow_001.yaml
  
  codebase/
    [target codebase]
  
  runners/
    run_decomposition.py      # Execute decomposition strategy
    generate_artifacts.py     # Generate artifacts per format
    evaluate_output.py        # Run eval script
  
  results/
    [run outputs and scores]
```

---

## 7. Success Criteria

| Hypothesis | Success Threshold |
|------------|-------------------|
| H1: Task × Decomp interaction | p < 0.05, effect size > 0.5 |
| H2: Full artifacts win | Full > Gherkin-only by > 10pp |
| H3: Consistency catches 60% | Caught errors / total > 0.6 |
| H4: Artifact predicts success | r > 0.8 for all-three-valid |

---

## Next Steps

1. **Choose codebase**: aictrl.dev vs synthetic vs open-source?
2. **Define 4 tasks** with full input/output specs
3. **Build eval harness** for automated scoring
4. **Run reduced design** (78 runs)
5. **Analyze and publish**

Which codebase should we use?
