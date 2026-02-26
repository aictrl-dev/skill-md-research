# Domain Decomposition Strategy

Decompose the task by **bounded context/domain**, isolating business logic:

## Domain Identification

1. Identify the core domain concepts involved
2. Define bounded contexts for each concept
3. Establish relationships between contexts
4. Implement each context independently

## Principles

- Each domain is a bounded context with clear boundaries
- Domains communicate through well-defined interfaces
- Business logic lives in the domain, not in layers
- Infrastructure is secondary to domain logic

## Step Template

```
Step N: [Domain] - [Description]
Context: [Bounded context name]
Entities: [Core entities in this context]
Rules: [Business rules to implement]
Output: [Domain artifacts + infrastructure]
```

## Example

For "Add document approval workflow":

```
Step 1: Define Approval domain
  Context: DocumentApproval
  Entities: ApprovalRequest, Approval, Rejection
  Rules: 
    - Only pending documents can be approved
    - Approvers must have permission
    - Approval is final
  Output: ApprovalState enum, Approval aggregate

Step 2: Implement Approval logic
  Context: DocumentApproval
  Rules:
    - State transitions: draft → pending → approved/rejected
    - Notifications on state change
  Output: ApprovalService, state machine

Step 3: Wire to Document domain
  Context: Document
  Rules:
    - Document has one ApprovalState
    - State affects document visibility
  Output: Document-Approval relationship

Step 4: Expose via API
  Context: API (thin layer)
  Output: /documents/:id/approve endpoint

Step 5: Build UI
  Context: UI (thin layer)
  Output: Approval buttons, status display
```

## When to Use

- Business workflow implementations
- State machine logic
- Multi-entity interactions
- Domain-specific validations
- Complex business rules
