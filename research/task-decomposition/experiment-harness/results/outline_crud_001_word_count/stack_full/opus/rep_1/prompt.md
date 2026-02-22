# Task Spec: Add word_count to Documents

**Task ID**: outline_crud_001
**Type**: CRUD
**Codebase**: outline/outline
**Difficulty**: Simple
**Estimated Steps**: 5

---

## Description

Add a `word_count` field to the Document model that:
1. Is automatically calculated when document content changes
2. Is stored in the database for querying/sorting
3. Is returned in the Document API response
4. Can be used for filtering documents by length

---

## Current State

### Files to Modify

| File | Purpose | Lines to Modify |
|------|---------|-----------------|
| `server/models/Document.ts` | Document model definition | Add word_count column |
| `server/presenters/document.ts` | API response formatter | Include word_count in response |
| `server/routes/api/documents/schema.ts` | API validation schema | Add word_count to schema |
| `server/routes/api/documents/documents.ts` | API handlers | Use word_count in list/filter |

### Files to Create

| File | Purpose |
|------|---------|
| `server/migrations/YYYYMMDDHHMMSS-add-word-count-to-documents.js` | Database migration |

### Files to Update (Tests)

| File | Purpose |
|------|---------|
| `server/models/Document.test.ts` | Model unit tests |
| `server/routes/api/documents/documents.test.ts` | API integration tests |

---

## Implementation Details

### Step 1: Database Migration

**Create**: `server/migrations/YYYYMMDDHHMMSS-add-word-count-to-documents.js`

```javascript
"use strict";

/** @type {import('sequelize-cli').Migration} */
module.exports = {
  async up(queryInterface, Sequelize) {
    await queryInterface.sequelize.transaction(async (transaction) => {
      // Add word_count column to documents
      await queryInterface.addColumn(
        "documents",
        "word_count",
        {
          type: Sequelize.INTEGER,
          allowNull: false,
          defaultValue: 0,
        },
        { transaction }
      );

      // Add word_count column to revisions (for history)
      await queryInterface.addColumn(
        "revisions",
        "word_count",
        {
          type: Sequelize.INTEGER,
          allowNull: false,
          defaultValue: 0,
        },
        { transaction }
      );

      // Add index for sorting/filtering
      await queryInterface.addIndex("documents", ["word_count"], {
        name: "documents_word_count_idx",
        transaction,
      });
    });
  },

  async down(queryInterface, Sequelize) {
    await queryInterface.sequelize.transaction(async (transaction) => {
      await queryInterface.removeColumn("documents", "word_count", { transaction });
      await queryInterface.removeColumn("revisions", "word_count", { transaction });
      await queryInterface.removeIndex("documents", "documents_word_count_idx", { transaction });
    });
  },
};
```

### Step 2: Update Document Model

**File**: `server/models/Document.ts`

Add after line 348 (after `language` field):

```typescript
  /** The word count of the document content. */
  @Default(0)
  @Column(DataType.INTEGER)
  wordCount: number;
```

### Step 3: Add Word Count Calculation

**File**: `server/models/Document.ts` or `server/models/helpers/DocumentHelper.tsx`

Add a method to calculate word count from content:

```typescript
/**
 * Calculate the word count from document content.
 * 
 * @param content - The document content (ProsemirrorData or text)
 * @returns The number of words in the content
 */
static calculateWordCount(content: ProsemirrorData | string | null): number {
  if (!content) {
    return 0;
  }
  
  // If content is already text
  if (typeof content === "string") {
    return content.trim().split(/\s+/).filter(Boolean).length;
  }
  
  // If content is ProsemirrorData, extract text first
  const text = /* extract text from ProsemirrorData */;
  return text.trim().split(/\s+/).filter(Boolean).length;
}
```

Update the `BeforeSave` hook to calculate word count:

```typescript
@BeforeSave
static async calculateWordCountHook(document: Document) {
  document.wordCount = DocumentHelper.calculateWordCount(document.content);
}
```

### Step 4: Update API Presenter

**File**: `server/presenters/document.ts`

Add after line 65 (after `language`):

```typescript
    wordCount: document.wordCount,
```

### Step 5: Update API Schema (Optional - for filtering)

**File**: `server/routes/api/documents/schema.ts`

Add wordCount to filter schema if sorting/filtering is needed.

---

## Test Cases

### Unit Tests

**File**: `server/models/Document.test.ts`

```typescript
describe("wordCount", () => {
  it("should calculate word count on save", async () => {
    const document = await buildDocument({
      text: "Hello world this is a test",
    });
    expect(document.wordCount).toBe(6);
  });

  it("should update word count when content changes", async () => {
    const document = await buildDocument({
      text: "Initial content",
    });
    expect(document.wordCount).toBe(2);
    
    document.text = "Updated content with more words";
    await document.save();
    expect(document.wordCount).toBe(5);
  });

  it("should return 0 for empty content", async () => {
    const document = await buildDocument({
      text: "",
    });
    expect(document.wordCount).toBe(0);
  });
});
```

### API Tests

**File**: `server/routes/api/documents/documents.test.ts`

```typescript
describe("#documents.info with wordCount", () => {
  it("should include wordCount in response", async () => {
    const user = await buildUser();
    const document = await buildDocument({
      userId: user.id,
      teamId: user.teamId,
      text: "This is a test document",
    });
    const res = await server.post("/api/documents.info", {
      body: {
        token: user.getJwtToken(),
        id: document.id,
      },
    });
    const body = await res.json();
    expect(res.status).toEqual(200);
    expect(body.data.wordCount).toBe(5);
  });
});
```

---

## Evaluation Criteria

| Criterion | How to Verify | Pass Condition |
|-----------|---------------|----------------|
| Migration runs | `yarn db:migrate` | Exit code 0 |
| Column exists | Query database | `word_count` column in `documents` table |
| Model has field | TypeScript compiles | No type errors |
| Word count calculated | Create doc with text | wordCount matches actual word count |
| API returns field | GET /api/documents.info | Response includes `wordCount` |
| Tests pass | `yarn test server/models/Document.test.ts` | All tests pass |
| No regressions | `yarn test:server` | All existing tests pass |

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Word count accuracy | > 99% (match manual count) |
| Performance impact | < 10ms per document save |
| API response time | No measurable increase |
| Test coverage | New code > 80% covered |

---

## Decomposition Variants

### Stack Decomposition (Predicted Best)

```
Step 1: Create migration
  Input: None
  Output: migration file
  Validation: Migration file syntax correct

Step 2: Update Document model
  Input: migration
  Output: Document.ts with wordCount field
  Validation: TypeScript compiles

Step 3: Add calculation logic
  Input: Document.ts
  Output: DocumentHelper.calculateWordCount, BeforeSave hook
  Validation: Unit tests pass

Step 4: Update presenter
  Input: Document model
  Output: presenter with wordCount
  Validation: API returns wordCount

Step 5: Add tests
  Input: All changes
  Output: Test files
  Validation: All tests pass
```

### Domain Decomposition

```
Step 1: Define WordCount value object
  Input: Requirements
  Output: WordCount calculation logic
  Validation: Pure function tests

Step 2: Add to Document domain
  Input: WordCount logic
  Output: Document.wordCount field and behavior
  Validation: Domain model tests

Step 3: Add persistence (migration)
  Input: Domain model
  Output: Migration + model persistence
  Validation: DB round-trip works

Step 4: Expose via API
  Input: Domain + persistence
  Output: Presenter + routes
  Validation: API tests

Step 5: Integration tests
  Input: Full stack
  Output: E2E tests
  Validation: All tests pass
```

### Journey Decomposition

```
Step 1: User creates document (capture text)
  Input: User types content
  Output: Content captured
  Validation: Content stored

Step 2: System calculates count (preview)
  Input: Content
  Output: Live word count
  Validation: UI shows count

Step 3: User saves document
  Input: Content + user action
  Output: Persisted word count
  Validation: DB has count

Step 4: User views document
  Input: Document request
  Output: API response with wordCount
  Validation: UI shows count

Step 5: User filters by length
  Input: Filter request
  Output: Filtered results
  Validation: Correct filtering
```

---

## Commands to Run

```bash
# Create migration
yarn sequelize migration:create --name=add-word-count-to-documents

# Run migration
yarn db:migrate

# Run tests
yarn test server/models/Document.test.ts
yarn test server/routes/api/documents/documents.test.ts

# Type check
yarn tsc

# Lint
yarn lint
```

---

## References

- Existing similar field: `tasks` (calculated from content)
- Migration example: `server/migrations/20240617151506-add-icon-to-document.js`
- Model pattern: `server/models/Document.ts` lines 276-348
- Presenter pattern: `server/presenters/document.ts` lines 52-80
