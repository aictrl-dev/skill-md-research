Based on the task requirements, I'll generate the three artifacts for the `word_count` feature. These are designed to be implementation-agnostic but follow standard patterns for a REST API backed by PostgreSQL.

## 1. GHERKIN TEST SCENARIOS

```gherkin
Feature: Document Word Count Calculation and Retrieval
  As a user of the document API
  I want word counts to be automatically calculated and available for filtering
  So that I can organize and query documents by length

  Background:
    Given a Document API endpoint at /documents
    And the database is empty

  Scenario: Word count is calculated on document creation
    When I create a document with content "Hello world from the API"
    Then the document word_count should be 5
    And the word_count is persisted in the database

  Scenario: Word count updates when document content changes
    Given a document with content "Initial content here"
    And the word_count is 3
    When I update the document content to "This is a much longer content update with more words"
    Then the document word_count should be 10
    And the updated word_count is persisted in the database

  Scenario: Word count handles empty content
    When I create a document with empty content ""
    Then the document word_count should be 0
    And the document is retrievable

  Scenario: Word count handles whitespace-only content
    When I create a document with content "   \n  \t  "
    Then the document word_count should be 0

  Scenario: Word count is returned in API response
    When I create a document with content "Sample document content"
    And I retrieve the document via GET /documents/{id}
    Then the response includes a word_count field with value 3

  Scenario: Filter documents by word count range
    Given documents exist with the following word counts:
      | content                      | expected_count |
      | "One two three"              | 3              |
      | "Four five"                  | 2              |
      | "A longer document with text" | 5             |
    When I query GET /documents?min_word_count=3&max_word_count=5
    Then I receive 2 documents
    And the word_counts are 3 and 5

  Scenario: Sort documents by word count ascending
    Given documents with word counts: [5, 2, 8, 3]
    When I query GET /documents?sort=word_count&order=asc
    Then documents are returned in order: [2, 3, 5, 8]

  Scenario: Sort documents by word count descending
    Given documents with word counts: [5, 2, 8, 3]
    When I query GET /documents?sort=word_count&order=desc
    Then documents are returned in order: [8, 5, 3, 2]

  Scenario: Word count handles punctuation correctly
    When I create a document with content "Hello, world! How are you?"
    Then the document word_count should be 5

  Scenario: Word count handles special characters and numbers
    When I create a document with content "Test 123 with @special #chars and symbols!"
    Then the document word_count should be 9

  Scenario: Bulk document creation maintains accurate word counts
    When I create 100 documents with varying content lengths
    And I query for documents with word_count > 50
    Then the word_count values match the actual content word counts
    And query performance is acceptable (< 100ms)

  Scenario: Error handling when word count query parameter is invalid
    When I query GET /documents?min_word_count=invalid
    Then I receive a 400 Bad Request error
    And the error message indicates invalid query parameter

  Scenario: Null content is handled gracefully
    When I create a document with null content
    Then the word_count is set to 0
    Or a validation error is returned indicating content is required
```

## 2. OPENAPI SPECIFICATION

```yaml
openapi: 3.0.3
info:
  title: Document API
  version: 2.1.0
  description: API for managing documents with automatic word count calculation

servers:
  - url: https://api.example.com/v1
    description: Production server
  - url: http://localhost:8000/v1
    description: Local development server

paths:
  /documents:
    post:
      summary: Create a new document
      operationId: createDocument
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/CreateDocumentRequest'
      responses:
        '201':
          description: Document created successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/DocumentResponse'
        '400':
          $ref: '#/components/responses/BadRequest'
        '500':
          $ref: '#/components/responses/InternalServerError'

    get:
      summary: List documents with filtering and sorting
      operationId: listDocuments
      parameters:
        - name: min_word_count
          in: query
          description: Minimum word count for filtering
          schema:
            type: integer
            minimum: 0
          example: 10
        - name: max_word_count
          in: query
          description: Maximum word count for filtering
          schema:
            type: integer
            minimum: 0
          example: 100
        - name: sort
          in: query
          description: Field to sort by
          schema:
            type: string
            enum: [created_at, updated_at, word_count, title]
          example: word_count
        - name: order
          in: query
          description: Sort order
          schema:
            type: string
            enum: [asc, desc]
            default: asc
          example: asc
        - name: limit
          in: query
          description: Maximum number of results
          schema:
            type: integer
            minimum: 1
            maximum: 100
            default: 20
        - name: offset
          in: query
          description: Number of results to skip
          schema:
            type: integer
            minimum: 0
            default: 0
      responses:
        '200':
          description: List of documents
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/DocumentListResponse'
        '400':
          $ref: '#/components/responses/BadRequest'
        '500':
          $ref: '#/components/responses/InternalServerError'

  /documents/{documentId}:
    get:
      summary: Get a single document by ID
      operationId: getDocument
      parameters:
        - name: documentId
          in: path
          required: true
          description: Unique document identifier
          schema:
            type: string
            format: uuid
      responses:
        '200':
          description: Document retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/DocumentResponse'
        '404':
          $ref: '#/components/responses/NotFound'
        '500':
          $ref: '#/components/responses/InternalServerError'

    patch:
      summary: Update document content
      operationId: updateDocument
      parameters:
        - name: documentId
          in: path
          required: true
          description: Unique document identifier
          schema:
            type: string
            format: uuid
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/UpdateDocumentRequest'
      responses:
        '200':
          description: Document updated successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/DocumentResponse'
        '400':
          $ref: '#/components/responses/BadRequest'
        '404':
          $ref: '#/components/responses/NotFound'
        '500':
          $ref: '#/components/responses/InternalServerError'

    delete:
      summary: Delete a document
      operationId: deleteDocument
      parameters:
        - name: documentId
          in: path
          required: true
          description: Unique document identifier
          schema:
            type: string
            format: uuid
      responses:
        '204':
          description: Document deleted successfully
        '404':
          $ref: '#/components/responses/NotFound'
        '500':
          $ref: '#/components/responses/InternalServerError'

components:
  schemas:
    CreateDocumentRequest:
      type: object
      required:
        - title
        - content
      properties:
        title:
          type: string
          minLength: 1
          maxLength: 255
          example: "My Document"
        content:
          type: string
          minLength: 0
          example: "This is the document content."
        tags:
          type: array
          items:
            type: string
          example: ["important", "review"]

    UpdateDocumentRequest:
      type: object
      properties:
        title:
          type: string
          minLength: 1
          maxLength: 255
          example: "Updated Title"
        content:
          type: string
          minLength: 0
          example: "Updated document content."
        tags:
          type: array
          items:
            type: string
          example: ["updated"]

    DocumentResponse:
      type: object
      required:
        - id
        - title
        - content
        - word_count
        - created_at
        - updated_at
      properties:
        id:
          type: string
          format: uuid
          example: "550e8400-e29b-41d4-a716-446655440000"
        title:
          type: string
          example: "My Document"
        content:
          type: string
          example: "This is the document content."
        word_count:
          type: integer
          minimum: 0
          description: Automatically calculated number of words in the document
          example: 5
        tags:
          type: array
          items:
            type: string
          example: ["important"]
        created_at:
          type: string
          format: date-time
          example: "2026-02-22T10:30:00Z"
        updated_at:
          type: string
          format: date-time
          example: "2026-02-22T11:45:00Z"

    DocumentListResponse:
      type: object
      required:
        - data
        - pagination
      properties:
        data:
          type: array
          items:
            $ref: '#/components/schemas/DocumentResponse'
        pagination:
          type: object
          required:
            - total
            - limit
            - offset
          properties:
            total:
              type: integer
              example: 150
            limit:
              type: integer
              example: 20
            offset:
              type: integer
              example: 0
            has_more:
              type: boolean
              example: true

    Error:
      type: object
      required:
        - code
        - message
      properties:
        code:
          type: string
          example: "INVALID_REQUEST"
        message:
          type: string
          example: "The request contains invalid parameters"
        details:
          type: object
          example: { "field": "min_word_count", "reason": "must be a non-negative integer" }

  responses:
    BadRequest:
      description: Bad request - invalid parameters
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/Error'
    NotFound:
      description: Resource not found
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/Error'
    InternalServerError:
      description: Internal server error
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/Error'
```

## 3. SQL MIGRATION

```sql
-- Migration: Add word_count field to documents table
-- Version: 2026_02_22_001_add_word_count_to_documents
-- Description: Add automatically calculated word_count column to enable document filtering and sorting by content length

-- ============= UP =============

BEGIN TRANSACTION;

-- Add the word_count column with default value of 0
ALTER TABLE documents
ADD COLUMN word_count INTEGER NOT NULL DEFAULT 0;

-- Create an index on word_count for efficient filtering and sorting
CREATE INDEX idx_documents_word_count 
ON documents(word_count);

-- Create a compound index for range queries
CREATE INDEX idx_documents_word_count_created_at 
ON documents(word_count, created_at DESC);

-- Create a function to calculate word count from content
CREATE OR REPLACE FUNCTION calculate_word_count(content TEXT)
RETURNS INTEGER AS $$
BEGIN
  -- Handle NULL content
  IF content IS NULL OR content = '' THEN
    RETURN 0;
  END IF;
  
  -- Count words by splitting on whitespace
  -- This approach handles multiple spaces, tabs, newlines correctly
  RETURN (
    SELECT COUNT(*)::INTEGER
    FROM (
      SELECT TRIM(word) as word
      FROM regexp_split_to_table(TRIM(content), '\s+') as word
      WHERE TRIM(word) != ''
    ) t
  );
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Create a trigger to update word_count on INSERT
CREATE OR REPLACE FUNCTION update_document_word_count_on_insert()
RETURNS TRIGGER AS $$
BEGIN
  NEW.word_count := calculate_word_count(NEW.content);
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_documents_calculate_word_count_insert
BEFORE INSERT ON documents
FOR EACH ROW
EXECUTE FUNCTION update_document_word_count_on_insert();

-- Create a trigger to update word_count on UPDATE of content
CREATE OR REPLACE FUNCTION update_document_word_count_on_update()
RETURNS TRIGGER AS $$
BEGIN
  -- Only recalculate if content has changed
  IF OLD.content IS DISTINCT FROM NEW.content THEN
    NEW.word_count := calculate_word_count(NEW.content);
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_documents_calculate_word_count_update
BEFORE UPDATE ON documents
FOR EACH ROW
EXECUTE FUNCTION update_document_word_count_on_update();

-- Backfill existing documents with word counts
UPDATE documents
SET word_count = calculate_word_count(content)
WHERE word_count = 0;

-- Add constraint to ensure word_count is non-negative
ALTER TABLE documents
ADD CONSTRAINT ck_documents_word_count_non_negative
CHECK (word_count >= 0);

-- Update table statistics after bulk update
ANALYZE documents;

COMMIT;

-- ============= DOWN =============

BEGIN TRANSACTION;

-- Drop triggers
DROP TRIGGER IF EXISTS trg_documents_calculate_word_count_update ON documents;
DROP TRIGGER IF EXISTS trg_documents_calculate_word_count_insert ON documents;

-- Drop trigger functions
DROP FUNCTION IF EXISTS update_document_word_count_on_update();
DROP FUNCTION IF EXISTS update_document_word_count_on_insert();

-- Drop word count calculation function
DROP FUNCTION IF EXISTS calculate_word_count(TEXT);

-- Drop constraint
ALTER TABLE documents
DROP CONSTRAINT IF EXISTS ck_documents_word_count_non_negative;

-- Drop indexes
DROP INDEX IF EXISTS idx_documents_word_count_created_at;
DROP INDEX IF EXISTS idx_documents_word_count;

-- Remove the word_count column
ALTER TABLE documents
DROP COLUMN IF EXISTS word_count;

COMMIT;
```

---

## Summary

These three artifacts provide a complete feature design for `word_count`:

**Gherkin Tests** - Cover 12 scenarios including:
- Happy path (creation, updates, retrieval)
- Edge cases (empty content, whitespace, special characters)
- Query operations (filtering by range, sorting)
- Error handling (invalid parameters, null content)

**OpenAPI Spec** - Defines:
- POST /documents (create with auto word_count)
- GET /documents (list with min/max word_count filters and sorting)
- GET /documents/{id} (retrieve with word_count in response)
- PATCH /documents/{id} (update with word_count recalculation)
- DELETE /documents/{id}
- DocumentResponse schema includes word_count field

**SQL Migration** - Includes:
- word_count column with NOT NULL DEFAULT 0
- Indexes for efficient queries (single and compound)
- PL/pgSQL function to calculate word count using regex
- Triggers for automatic calculation on INSERT/UPDATE
- Backfill script for existing documents
- Non-negative constraint
- Proper rollback script
