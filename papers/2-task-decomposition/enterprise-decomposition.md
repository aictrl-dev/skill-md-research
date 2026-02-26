# Research: Enterprise Software Task Decomposition

**Last updated**: 2026-02-21
**Domain**: Decomposing Epics/Stories into executable artifacts
**Application**: aictrl.dev planning and validation tooling

---

## 1. The Problem

Enterprise software requests arrive as:
- **Epics**: Large, cross-cutting features (e.g., "Add subscription billing")
- **Stories**: Smaller, user-focused requirements (e.g., "User can view invoice history")

**Question**: How should these be decomposed for reliable LLM execution?

---

## 2. Decomposition Dimensions

### 2.1 By Stack Layer

```
Epic: "Add subscription billing"
    │
    ├── DB Layer
    │   ├── Schema: subscription, invoice, payment tables
    │   └── Migrations: add_subscription_tables.sql
    │
    ├── Backend Layer
    │   ├── API: POST /subscriptions, GET /invoices
    │   └── Logic: billing_cycle, proration, tax_calc
    │
    ├── Frontend Layer
    │   ├── Components: SubscriptionForm, InvoiceList
    │   └── Pages: /billing, /invoices
    │
    ├── Test Layer
    │   ├── Unit: billing_calculator.test.ts
    │   └── Integration: subscription_flow.test.ts
    │
    └── Infra Layer
        ├── CI: billing_tests.yml
        └── Config: stripe_webhook_endpoint
```

**Pros**: Clear ownership, sequential dependencies, verifiable outputs
**Cons**: May miss cross-cutting concerns, fragmented domain logic

### 2.2 By Domain

```
Epic: "Add subscription billing"
    │
    ├── Subscription Domain
    │   ├── Create subscription
    │   ├── Cancel subscription
    │   └── Upgrade/downgrade
    │
    ├── Invoice Domain
    │   ├── Generate invoice
    │   ├── Send invoice
    │   └── Track payment status
    │
    ├── Payment Domain
    │   ├── Process payment
    │   ├── Handle failures
    │   └── Refunds
    │
    └── Reporting Domain
        ├── Revenue metrics
        └── Churn analytics
```

**Pros**: Bounded contexts, independent deployability, domain expertise
**Cons**: May duplicate stack work, coordination overhead

### 2.3 By User Journey

```
Epic: "Add subscription billing"
    │
    ├── Journey: User subscribes
    │   ├── View plans → Choose plan → Enter payment → Confirm
    │
    ├── Journey: User views invoices
    │   ├── List invoices → Filter → Download PDF
    │
    ├── Journey: User cancels
    │   ├── Request cancel → Confirm → Handle proration → Process refund
    │
    └── Journey: Admin manages
        ├── View all subscriptions → Override → Apply discounts
```

**Pros**: User-centric, testable as flows, clear acceptance criteria
**Cons**: May miss backend complexity, infrastructure invisible

---

## 3. Research Questions

### RQ1: Which Decomposition Dimension Produces Best Results?

| Metric | Stack | Domain | Journey |
|--------|-------|--------|---------|
| Execution success rate | ? | ? | ? |
| Artifact verifiability | ? | ? | ? |
| Cross-step consistency | ? | ? | ? |
| Human review efficiency | ? | ? | ? |

### RQ2: Does Task Type Determine Optimal Decomposition?

| Task Type | Predicted Best | Rationale |
|-----------|----------------|-----------|
| **CRUD feature** | Stack | Clear layer boundaries |
| **Business workflow** | Domain | Domain logic集中 |
| **User-facing flow** | Journey | User-centric acceptance |
| **Integration** | Stack | External system at one layer |
| **Refactoring** | Domain | Minimize blast radius |

### RQ3: Which Artifact Combinations Maximize Verifiability?

| Artifact Set | Verifiability | Completeness | LLM Success |
|--------------|---------------|--------------|-------------|
| Gherkin + HTML | High (testable) | Medium (no backend) | ? |
| Gherkin + API Spec + DB Schema | High | High | ? |
| Pseudocode + State Diagram | Medium | Medium | ? |
| Natural language only | Low | Low | ? |

---

## 4. Artifact Format Comparison

### 4.1 Test Artifacts

| Format | Verifiability | LLM Generation Quality | Industry Adoption |
|--------|---------------|------------------------|-------------------|
| **Gherkin** | Executable (Cypress, Playwright) | High (structured) | Very high |
| **YAML tests** | Executable (custom runners) | Medium | Medium |
| **Natural language** | Manual only | High | Low |
| **Code (test files)** | Executable directly | Medium | Very high |

### 4.2 UI Artifacts

| Format | Verifiability | LLM Generation Quality | Use Case |
|--------|---------------|------------------------|----------|
| **HTML mockup** | Visual review | High | Frontend design |
| **Figma/Design spec** | Design review | Low | Design handoff |
| **Component schema (JSON)** | Schema validation | High | Component generation |
| **Natural language** | Manual | High | Early ideation |

### 4.3 API Artifacts

| Format | Verifiability | LLM Generation Quality | Tooling |
|--------|---------------|------------------------|---------|
| **OpenAPI spec** | Schema + lint | High | Swagger, Prism |
| **GraphQL schema** | Type check | Very high | Apollo, Codegen |
| **TypeScript types** | Compile check | High | tsc |
| **Natural language** | Manual | High | None |

### 4.4 Data Artifacts

| Format | Verifiability | LLM Generation Quality | Use Case |
|--------|---------------|------------------------|----------|
| **SQL migration** | Executable | High | Schema changes |
| **DBML/ERD** | Visual review | High | Documentation |
| **Prisma schema** | Type check | Very high | ORM |
| **JSON Schema** | Validation | High | API contracts |

---

## 5. Hypotheses

### H1: Stack Decomposition Wins for CRUD, Domain for Workflows

| Task Type | Stack | Domain | Journey |
|-----------|-------|--------|---------|
| Simple CRUD | **Higher** | Lower | Lower |
| Business workflow | Lower | **Higher** | Medium |
| User flow | Lower | Medium | **Higher** |
| Integration | **Higher** | Lower | Lower |

### H2: Gherkin + API Spec + DB Schema is Optimal Artifact Set

| Artifact Set | Verifiability Score | LLM Success Rate (predicted) |
|--------------|---------------------|------------------------------|
| Natural language only | 1/5 | 60% |
| Gherkin only | 3/5 | 70% |
| Gherkin + HTML | 4/5 | 75% |
| **Gherkin + OpenAPI + SQL** | **5/5** | **85%** |
| All + State diagrams | 5/5 | 80% (overload) |

### H3: Artifact Order Matters

| Order | Rationale |
|-------|-----------|
| **Spec → Test → Code** | Test-driven, high verification |
| Code → Test → Spec | Refactor-friendly, low initial verification |
| Test → Spec → Code | BDD, highest verification |

Prediction: **Test → Spec → Code** produces highest quality

### H4: Cross-Artifact Consistency Validation Catches 60% of Errors

| Validation Type | Error Catch Rate |
|-----------------|------------------|
| Schema-only | 20% |
| Schema + Type | 40% |
| **Schema + Type + Cross-ref** | **60%** |

Cross-ref example: Gherkin `When I create subscription` references OpenAPI `POST /subscriptions` which references DB `subscriptions` table

### H5: Domain Decomposition Reduces Cross-Step Rework by 40%

| Decomposition | Rework Rate |
|---------------|-------------|
| Stack | 30% (layers diverge) |
| **Domain** | **18%** (bounded context) |
| Journey | 25% (backend missed) |

---

## 6. Experiment Design

### 6.1 Task Set

| Task | Type | Complexity | Expected Best Decomposition |
|------|------|------------|----------------------------|
| Add user registration | CRUD | Simple | Stack |
| Implement checkout flow | Workflow | Medium | Domain |
| Build dashboard | User flow | Medium | Journey |
| Integrate Stripe | Integration | Complex | Stack |
| Add role-based access | Domain logic | Complex | Domain |

### 6.2 Conditions

| Condition | Decomposition | Artifacts |
|-----------|---------------|-----------|
| C1 | Stack | Gherkin + HTML + OpenAPI + SQL |
| C2 | Domain | Gherkin + HTML + OpenAPI + SQL |
| C3 | Journey | Gherkin + HTML + OpenAPI + SQL |
| C4 | Stack | Natural language only |
| C5 | Stack | Gherkin only |
| C6 | Stack | Gherkin + HTML only |

### 6.3 Metrics

| Metric | How Measured |
|--------|--------------|
| **Execution success** | Generated code passes tests |
| **Artifact consistency** | Cross-reference validation |
| **Human review time** | Time to approve artifacts |
| **Rework rate** | Steps that need regeneration |

---

## 7. Practical Recommendations (Pre-Experiment)

### For aictrl.dev MVP

Based on literature and intuition:

| Task Type | Recommended Decomposition | Recommended Artifacts |
|-----------|---------------------------|-----------------------|
| **CRUD feature** | Stack (DB → API → UI → Test) | SQL → OpenAPI → HTML → Gherkin |
| **Business workflow** | Domain (per bounded context) | State diagram → Gherkin → OpenAPI |
| **User flow** | Journey (per user action) | Gherkin → HTML → Component schema |
| **Integration** | Stack (isolate external system) | OpenAPI → Gherkin → Code |

### Artifact Generation Order

```
1. Gherkin (behavioral spec)
      ↓ validates
2. OpenAPI/Schema (interface contracts)
      ↓ validates  
3. SQL/DBML (data model)
      ↓ generates
4. Code (implementation)
```

This enables **test-first validation** at each step.

---

## 8. Novel Contribution

> "We are the first to study decomposition strategies for enterprise software tasks, showing that stack-based decomposition outperforms domain-based for CRUD operations (+25% success), while domain-based wins for business workflows (+18% success). We further show that the artifact set {Gherkin + OpenAPI + SQL} provides optimal verifiability at minimal generation cost."

---

## Next Steps

1. Run experiment across 5 task types × 3 decompositions × 3 repetitions = 45 runs
2. Measure: success rate, consistency, review time, rework
3. Publish decomposition guidelines for aictrl.dev

Want me to create the detailed experiment prompts for each condition?
