# Artifact Format: Full (Gherkin + OpenAPI + SQL)

Complete specification with behavior, API contract, and database schema.

## Format

### Part 1: Gherkin (Behavior)

```gherkin
Feature: [Feature Name]
  ...
```

### Part 2: OpenAPI (API Contract)

```yaml
openapi: 3.0.0
...
```

### Part 3: SQL (Database Schema)

```javascript
// Migration file
module.exports = {
  async up(queryInterface, Sequelize) { ... },
  async down(queryInterface, Sequelize) { ... }
};
```

## Example

### Gherkin

```gherkin
Feature: Document word count
  As a content author
  I want to see the word count of my documents
  So that I can track document length

  Scenario: Word count is calculated on save
    Given a document with content "Hello world test"
    When the document is saved
    Then the word_count column should be 3

  Scenario: Word count is returned in API response
    Given a document exists with id "doc-123"
    When I request GET /api/documents.info with id "doc-123"
    Then the response should include wordCount matching the database word_count

  Scenario: Word count is copied to revision
    Given a document with content "Test content"
    When the document is saved
    Then a revision should be created with the same word_count

  Scenario: Documents can be filtered by word count
    Given documents exist with word_counts [10, 50, 100]
    When I request /api/documents.list with minWordCount=50
    Then only documents with word_count >= 50 should be returned
```

### OpenAPI

```yaml
openapi: 3.0.0
info:
  title: Document Word Count API
  version: 1.0.0

paths:
  /api/documents.info:
    post:
      summary: Get document information
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/DocumentInfoRequest'
      responses:
        '200':
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/DocumentInfoResponse'

  /api/documents.list:
    post:
      summary: List documents
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                minWordCount:
                  type: integer
                  minimum: 0
                maxWordCount:
                  type: integer
                  minimum: 0
      responses:
        '200':
          content:
            application/json:
              schema:
                type: object
                properties:
                  data:
                    type: array
                    items:
                      $ref: '#/components/schemas/Document'

  /api/documents.update:
    post:
      summary: Update document
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                id:
                  type: string
                text:
                  type: string
                  description: Updating text recalculates wordCount
      responses:
        '200':
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/DocumentInfoResponse'

components:
  schemas:
    DocumentInfoRequest:
      type: object
      required:
        - id
      properties:
        id:
          type: string

    DocumentInfoResponse:
      type: object
      properties:
        data:
          $ref: '#/components/schemas/Document'

    Document:
      type: object
      properties:
        id:
          type: string
        title:
          type: string
        wordCount:
          type: integer
          minimum: 0
          description: Number of words in document content
        text:
          type: string
        createdAt:
          type: string
          format: date-time
        updatedAt:
          type: string
          format: date-time
```

### SQL Migration

```javascript
"use strict";

/** @type {import('sequelize-cli').Migration} */
module.exports = {
  async up(queryInterface, Sequelize) {
    await queryInterface.sequelize.transaction(async (transaction) => {
      // Add word_count to documents table
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

      // Add word_count to revisions table (for history)
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

      // Add index for filtering/sorting
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

## Cross-Artifact Validation

With full artifacts, we can validate:

1. **Gherkin → OpenAPI**: Scenario steps reference valid API endpoints
2. **OpenAPI → SQL**: API fields map to database columns
3. **End-to-end**: Gherkin scenarios test the full stack

## Pros
- Complete specification
- Full traceability from behavior to database
- Maximum validation coverage
- Clear contracts at every layer

## Cons
- Most verbose format
- Requires more upfront work
- Risk of over-specification
