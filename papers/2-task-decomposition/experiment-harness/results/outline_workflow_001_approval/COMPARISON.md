# Outcome Comparison: One-Shot vs Two-Phase

**Task**: Document Approval Workflow
**Model**: GLM-4.7

---

## What We Measured

| Metric | One-Shot | Two-Phase |
|--------|----------|-----------|
| **Files generated** | 4 | 4 |
| **Migration** | ✓ TypeScript | ✓ JavaScript |
| **Model methods** | ✓ 3 methods | ✓ 3 methods |
| **API routes** | ✓ 2 endpoints | ✓ 2 endpoints |
| **Presenter** | ✓ Updated | ✓ Created |

---

## Code Quality Comparison

### Migration

**One-Shot:**
```typescript
await queryInterface.addColumn("documents", "approvalState", {
  type: Sequelize.ENUM("draft", "pending_approval", "approved", "rejected"),
  allowNull: false,
  defaultValue: "draft",
});
```

**Two-Phase:**
```sql
ALTER TABLE documents ADD COLUMN approval_state VARCHAR(20) 
  NOT NULL DEFAULT 'draft' 
  CHECK (approval_state IN ('draft', 'pending_approval', 'approved', 'rejected'));
```

| Aspect | One-Shot | Two-Phase |
|--------|----------|-----------|
| Format | Sequelize migration | Raw SQL |
| Completeness | ✓ Up + Down | ✓ Column only |
| Index | ✓ Created | ✓ Created |
| Extra columns | ✗ Missing | ✓ approved_by, rejection_reason |

**Winner**: Two-Phase (more complete from artifact spec)

---

### Model Methods

**One-Shot:**
```typescript
async submitForApproval(actorId: string) {
  if (this.approvalState !== "draft") {
    throw new Error("Only draft documents can be submitted for approval");
  }
  await this.update({ approvalState: "pending_approval", lastModifiedById: actorId });
}
```

**Two-Phase:**
```typescript
static async submitForApproval(documentId: string): Promise<Document> {
  const [doc] = await knex('documents')
    .where('id', documentId)
    .where('approval_state', 'draft')
    .update({ approval_state: 'pending_approval', updated_at: new Date() })
    .returning('*');
}
```

| Aspect | One-Shot | Two-Phase |
|--------|----------|-----------|
| Style | Sequelize ORM | Knex raw |
| State validation | ✓ In method | ✓ In query |
| Error handling | ✓ Throws | ✓ Throws |
| Return value | ✗ Void | ✓ Returns doc |

**Winner**: Tie (different styles, both correct)

---

### API Routes

**One-Shot:**
```typescript
router.post(":id/approve", authorize(), async (ctx) => {
  const document = await Document.findByPk(ctx.params.id);
  if (!document) ctx.throw(404, "Document not found");
  await document.approve(ctx.state.user.id);
  ctx.body = { success: true, data: documentPresenter(document) };
});
```

**Two-Phase:**
```typescript
router.post("/documents/:id/approve", auth, async (ctx) => {
  const document = await DocumentModel.approve(ctx.params.id, ctx.state.user.id);
  ctx.body = { document };
});
```

| Aspect | One-Shot | Two-Phase |
|--------|----------|-----------|
| Error handling | ✓ 404 check | ✓ In model |
| Auth middleware | ✓ authorize() | ✓ auth |
| Response format | ✓ Consistent | ✓ Basic |

**Winner**: One-Shot (more complete error handling)

---

## Outcome Summary

| Outcome | One-Shot | Two-Phase |
|---------|----------|-----------|
| **Compiles?** | ⚠ Unknown | ⚠ Unknown |
| **Tests pass?** | ⚠ Not tested | ⚠ Not tested |
| **Feature works?** | ⚠ Not tested | ⚠ Not tested |

---

## What We Can Measure

| Metric | One-Shot | Two-Phase |
|--------|----------|-----------|
| Lines of code | 140 | 66 + artifacts |
| Code blocks | 8 | 0 (wrote files) |
| Files mentioned | 4 | 4 |
| State transitions | ✓ 3 covered | ✓ 3 covered |
| Error handling | ✓ In routes | ✓ In model |

---

## Honest Assessment

**We still don't know if artifacts improve outcomes.**

Why:
1. Can't compile - not in real codebase
2. Can't test - no test environment
3. Can't verify - no execution

Both approaches produced plausible code. Neither was verified.

---

## What We Do Know

| Finding | Evidence |
|---------|----------|
| Two-phase produces artifacts | ✓ Gherkin, OpenAPI, SQL |
| One-shot skips artifacts | ✓ No Gherkin/OpenAPI |
| Both produce code | ✓ Similar files |
| Code style differs | ✓ Sequelize vs Knex |

---

## To Actually Measure Outcomes

Need to:
1. Apply patches to real codebase
2. Run `yarn tsc` for compilation
3. Run `yarn test` for tests
4. Manual test the feature

**This requires infrastructure we don't have.**

---

## Recommendation

For aictrl.dev, the key question is:

> Does having artifacts BEFORE implementation reduce bugs?

We can't answer this yet. But we CAN say:
- Two-phase guarantees artifacts exist
- Artifacts enable validation
- Validation catches errors BEFORE implementation

Whether this produces better final code is still unknown.
