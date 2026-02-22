# Task Spec: Add Document Approval Workflow

**Task ID**: outline_workflow_001
**Type**: Workflow (State Machine)
**Codebase**: outline/outline
**Difficulty**: Medium
**Estimated Steps**: 6

---

## Description

Add a document approval workflow:
1. Documents can be submitted for approval by authors
2. Designated approvers can approve or reject documents
3. State transitions: `draft` → `pending_approval` → `approved` / `rejected`
4. Rejected documents can be resubmitted after revision
5. Notifications are sent to approvers and authors on state changes

---

## Current State

### Existing Models

| Model | Location | Relevance |
|-------|----------|-----------|
| `Document` | `server/models/Document.ts` | Has `publishedAt`, no approval state |
| `User` | `server/models/User.ts` | Users can be approvers |
| `Notification` | `server/models/Notification.ts` | Notification system exists |
| `UserMembership` | `server/models/UserMembership.ts` | Permission system |

### Files to Modify

| File | Purpose |
|------|---------|
| `server/models/Document.ts` | Add approval_state, approval workflow |
| `server/routes/api/documents/documents.ts` | Add approve/reject endpoints |
| `server/routes/api/documents/schema.ts` | Add approval schemas |
| `server/presenters/document.ts` | Include approval state in response |

### Files to Create

| File | Purpose |
|------|---------|
| `server/models/DocumentApproval.ts` | Approval records |
| `server/migrations/...add-document-approval.js` | DB migration |
| `server/commands/documentApprover.ts` | Approval logic |
| `server/routes/api/approvals/approvals.ts` | Approval API routes |

---

## Implementation Details

### Step 1: Database Migration

```javascript
// server/migrations/YYYYMMDDHHMMSS-add-document-approval.js
"use strict";

module.exports = {
  async up(queryInterface, Sequelize) {
    await queryInterface.sequelize.transaction(async (transaction) => {
      // Add approval state to documents
      await queryInterface.addColumn(
        "documents",
        "approval_state",
        {
          type: Sequelize.ENUM("draft", "pending_approval", "approved", "rejected"),
          defaultValue: "draft",
        },
        { transaction }
      );

      // Add rejection reason
      await queryInterface.addColumn(
        "documents",
        "rejection_reason",
        {
          type: Sequelize.TEXT,
          allowNull: true,
        },
        { transaction }
      );

      // Create document_approvals table
      await queryInterface.createTable(
        "document_approvals",
        {
          id: {
            type: Sequelize.UUID,
            primaryKey: true,
            defaultValue: Sequelize.UUIDV4,
          },
          documentId: {
            type: Sequelize.UUID,
            references: { model: "documents", key: "id" },
            onDelete: "CASCADE",
          },
          approverId: {
            type: Sequelize.UUID,
            references: { model: "users", key: "id" },
            onDelete: "CASCADE",
          },
          state: {
            type: Sequelize.ENUM("pending", "approved", "rejected"),
            defaultValue: "pending",
          },
          comment: {
            type: Sequelize.TEXT,
            allowNull: true,
          },
          createdAt: {
            type: Sequelize.DATE,
            allowNull: false,
          },
          updatedAt: {
            type: Sequelize.DATE,
            allowNull: false,
          },
        },
        { transaction }
      );

      // Add indexes
      await queryInterface.addIndex("document_approvals", ["documentId"], { transaction });
      await queryInterface.addIndex("document_approvals", ["approverId"], { transaction });
    });
  },

  async down(queryInterface, Sequelize) {
    await queryInterface.sequelize.transaction(async (transaction) => {
      await queryInterface.dropTable("document_approvals", { transaction });
      await queryInterface.removeColumn("documents", "rejection_reason", { transaction });
      await queryInterface.removeColumn("documents", "approval_state", { transaction });
      await queryInterface.sequelize.query(
        "DROP TYPE IF EXISTS enum_documents_approval_state;",
        { transaction }
      );
      await queryInterface.sequelize.query(
        "DROP TYPE IF EXISTS enum_document_approvals_state;",
        { transaction }
      );
    });
  },
};
```

### Step 2: DocumentApproval Model

```typescript
// server/models/DocumentApproval.ts
import {
  Column,
  Table,
  ForeignKey,
  BelongsTo,
  DataType,
  IsIn,
} from "sequelize-typescript";
import Document from "./Document";
import User from "./User";
import ParanoidModel from "./base/ParanoidModel";

@Table({ tableName: "document_approvals" })
class DocumentApproval extends ParanoidModel {
  @IsIn({ args: [["pending", "approved", "rejected"]] })
  @Column(DataType.STRING)
  state: "pending" | "approved" | "rejected";

  @Column(DataType.TEXT)
  comment: string | null;

  @ForeignKey(() => Document)
  @Column(DataType.UUID)
  documentId: string;

  @BelongsTo(() => Document, "documentId")
  document: Document;

  @ForeignKey(() => User)
  @Column(DataType.UUID)
  approverId: string;

  @BelongsTo(() => User, "approverId")
  approver: User;
}

export default DocumentApproval;
```

### Step 3: Update Document Model

```typescript
// Add to server/models/Document.ts

// Add enum type
export type ApprovalState = "draft" | "pending_approval" | "approved" | "rejected";

// Add columns
@Column(
  DataType.ENUM("draft", "pending_approval", "approved", "rejected")
)
approvalState: ApprovalState;

@Column(DataType.TEXT)
rejectionReason: string | null;

// Add relationship
@HasMany(() => DocumentApproval, "documentId")
approvals: DocumentApproval[];

// Add state transition method
async submitForApproval(approverIds: string[]): Promise<void> {
  if (this.approvalState !== "draft") {
    throw new Error("Only draft documents can be submitted for approval");
  }
  
  this.approvalState = "pending_approval";
  await this.save();
  
  // Create approval records
  for (const approverId of approverIds) {
    await DocumentApproval.create({
      documentId: this.id,
      approverId,
      state: "pending",
    });
  }
}

async approve(approverId: string, comment?: string): Promise<void> {
  if (this.approvalState !== "pending_approval") {
    throw new Error("Document is not pending approval");
  }
  
  const approval = await DocumentApproval.findOne({
    where: { documentId: this.id, approverId },
  });
  
  if (!approval) {
    throw new Error("User is not an approver for this document");
  }
  
  approval.state = "approved";
  approval.comment = comment || null;
  await approval.save();
  
  // Check if all approvals complete
  const pending = await DocumentApproval.count({
    where: { documentId: this.id, state: "pending" },
  });
  
  if (pending === 0) {
    this.approvalState = "approved";
    await this.save();
  }
}

async reject(approverId: string, reason: string): Promise<void> {
  if (this.approvalState !== "pending_approval") {
    throw new Error("Document is not pending approval");
  }
  
  this.approvalState = "rejected";
  this.rejectionReason = reason;
  await this.save();
  
  // Mark all pending approvals as rejected
  await DocumentApproval.update(
    { state: "rejected", comment: reason },
    { where: { documentId: this.id, state: "pending" } }
  );
}
```

### Step 4: API Endpoints

```typescript
// server/routes/api/documents/documents.ts

// Submit for approval
router.post(
  "documents.submit",
  auth(),
  validate(T.DocumentsSubmitSchema),
  transaction(),
  async (ctx: APIContext) => {
    const { id, approverIds } = ctx.input;
    const document = await Document.findByPk(id);
    
    authorize(ctx.state.user, "submit", document);
    
    await document.submitForApproval(approverIds);
    
    // Send notifications to approvers
    for (const approverId of approverIds) {
      await Notification.create({
        event: "documents.approval_requested",
        userId: approverId,
        documentId: document.id,
      });
    }
    
    ctx.body = { data: presentDocument(ctx, document) };
  }
);

// Approve document
router.post(
  "documents.approve",
  auth(),
  validate(T.DocumentsApproveSchema),
  transaction(),
  async (ctx: APIContext) => {
    const { id, comment } = ctx.input;
    const document = await Document.findByPk(id);
    
    authorize(ctx.state.user, "approve", document);
    
    await document.approve(ctx.state.user.id, comment);
    
    ctx.body = { data: presentDocument(ctx, document) };
  }
);

// Reject document
router.post(
  "documents.reject",
  auth(),
  validate(T.DocumentsRejectSchema),
  transaction(),
  async (ctx: APIContext) => {
    const { id, reason } = ctx.input;
    const document = await Document.findByPk(id);
    
    authorize(ctx.state.user, "reject", document);
    
    await document.reject(ctx.state.user.id, reason);
    
    ctx.body = { data: presentDocument(ctx, document) };
  }
);
```

### Step 5: Update Presenter

```typescript
// server/presenters/document.ts

// Add to response object
const res = {
  // ... existing fields
  approvalState: document.approvalState,
  rejectionReason: document.rejectionReason,
  approvals: document.approvals?.map(presentApproval),
};
```

### Step 6: Add Policy

```typescript
// server/policies/document.ts

allow(User, "approve", Document, (user, document) => {
  // User must be in the document's approval list
  return document.approvals?.some(a => a.approverId === user.id);
});

allow(User, "reject", Document, (user, document) => {
  return document.approvals?.some(a => a.approverId === user.id);
});
```

---

## Test Cases

```typescript
// server/models/Document.test.ts

describe("Document Approval Workflow", () => {
  it("should submit document for approval", async () => {
    const author = await buildUser();
    const approver = await buildUser();
    const document = await buildDocument({
      userId: author.id,
      teamId: author.teamId,
    });
    
    expect(document.approvalState).toBe("draft");
    
    await document.submitForApproval([approver.id]);
    
    expect(document.approvalState).toBe("pending_approval");
  });

  it("should approve document", async () => {
    const approver = await buildUser();
    const document = await buildDocument({ approvalState: "pending_approval" });
    await DocumentApproval.create({
      documentId: document.id,
      approverId: approver.id,
      state: "pending",
    });
    
    await document.approve(approver.id);
    
    expect(document.approvalState).toBe("approved");
  });

  it("should reject document with reason", async () => {
    const approver = await buildUser();
    const document = await buildDocument({ approvalState: "pending_approval" });
    
    await document.reject(approver.id, "Needs revision");
    
    expect(document.approvalState).toBe("rejected");
    expect(document.rejectionReason).toBe("Needs revision");
  });

  it("should not allow invalid state transitions", async () => {
    const document = await buildDocument({ approvalState: "approved" });
    
    await expect(
      document.submitForApproval([uuid()])
    ).rejects.toThrow("Only draft documents");
  });
});
```

---

## Evaluation Criteria

| Criterion | How to Verify | Pass Condition |
|-----------|---------------|----------------|
| Migration runs | `yarn db:migrate` | Exit code 0 |
| State transitions work | Unit tests | All state tests pass |
| API endpoints work | Integration tests | POST /submit, /approve, /reject succeed |
| Notifications sent | Check notification records | Records exist after submit |
| Policy enforced | Unauthorized request rejected | 403 for non-approvers |
| Tests pass | `yarn test` | All tests pass |

---

## Decomposition Variants

### Stack (Predicted: Medium)

```
Step 1: DB - Create migration (approval_state, document_approvals table)
Step 2: Model - Create DocumentApproval model
Step 3: Model - Update Document with approval methods
Step 4: API - Add /submit, /approve, /reject endpoints
Step 5: Policy - Add approval permissions
Step 6: Tests - Add workflow tests
```

### Domain (Predicted: Best)

```
Step 1: Define ApprovalState enum and state machine rules
Step 2: Define DocumentApproval aggregate and invariants
Step 3: Implement approval commands (Submit, Approve, Reject)
Step 4: Add persistence (migration + model)
Step 5: Expose via API + policy
Step 6: Add tests
```

### Journey (Predicted: Medium)

```
Step 1: Author clicks "Submit for approval" → System validates, changes state
Step 2: Author selects approvers → System creates approval records, sends notifications
Step 3: Approver receives notification → Approver clicks to view document
Step 4: Approver approves/rejects → System updates state, notifies author
Step 5: Author sees result → If rejected, can resubmit
```

---

## Commands

```bash
# Create migration
yarn sequelize migration:create --name=add-document-approval

# Run migration
yarn db:migrate

# Run tests
yarn test server/models/Document.test.ts
yarn test server/routes/api/documents/documents.test.ts
```
