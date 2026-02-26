[0m
> build · glm-4.7
[0m
### ARTIFACT 1: Gherkin

```gherkin
Feature: Document Approval
  Scenario: Submit for approval
    Given a document exists in draft state
    When the user submits the document for approval
    Then the document state changes to pending_approval
    And a notification is sent to assigned approvers

  Scenario: Approve document
    Given a document is in pending_approval state
    When an approver approves the document
    Then the document state changes to approved
    And a notification is sent to the document creator

  Scenario: Reject document
    Given a document is in pending_approval state
    When an approver rejects the document
    Then the document state changes to rejected
    And a notification is sent to the document creator
```

### ARTIFACT 2: OpenAPI

```yaml
openapi: 3.0.0
paths:
  /documents/{id}/approve:
    post:
      summary: Approve a pending document
      parameters:
        - name: id
          in: path
          required: true
          schema:
            type: string
      responses:
        '200':
          description: Document approved successfully
        '400':
          description: Document not in pending_approval state
        '404':
          description: Document not found

  /documents/{id}/reject:
    post:
      summary: Reject a pending document
      parameters:
        - name: id
          in: path
          required: true
          schema:
            type: string
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                reason:
                  type: string
      responses:
        '200':
          description: Document rejected successfully
        '400':
          description: Document not in pending_approval state
        '404':
          description: Document not found
```

### ARTIFACT 3: SQL Migration

```sql
ALTER TABLE documents ADD COLUMN approval_state VARCHAR(20) NOT NULL DEFAULT 'draft' CHECK (approval_state IN ('draft', 'pending_approval', 'approved', 'rejected'));

ALTER TABLE documents ADD COLUMN approved_by UUID REFERENCES users(id);
ALTER TABLE documents ADD COLUMN approved_at TIMESTAMP;
ALTER TABLE documents ADD COLUMN rejection_reason TEXT;

CREATE INDEX idx_documents_approval_state ON documents(approval_state);
```
