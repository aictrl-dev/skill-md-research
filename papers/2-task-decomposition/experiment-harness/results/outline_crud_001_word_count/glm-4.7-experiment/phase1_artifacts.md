### ARTIFACT 1: Gherkin (REQUIRED)
```gherkin
Feature: Word Count
  Scenario: Word count auto-calculates when document content changes
    Given a document exists with content "Hello world"
    When the document content is updated to "Hello world this is a test"
    Then the word_count field should be 7
    And the word_count should be stored in the database
    And the API response should include the word_count field

  Scenario: Word count allows filtering documents
    Given multiple documents exist with different word counts
    When requesting documents filtered by word_count greater than 5
    Then only documents with word_count greater than 5 are returned

  Scenario: Word count allows sorting documents
    Given multiple documents exist with different word counts
    When requesting documents sorted by word_count descending
    Then documents are returned in order of highest to lowest word count
```

### ARTIFACT 2: OpenAPI (REQUIRED)
```yaml
openapi: 3.0.0
info:
  title: Documents API
  version: 1.0.0
paths:
  /documents:
    get:
      summary: List documents
      parameters:
        - name: sort_by
          in: query
          schema:
            type: string
            enum: [word_count, -word_count, created_at, -created_at]
        - name: word_count_min
          in: query
          schema:
            type: integer
        - name: word_count_max
          in: query
          schema:
            type: integer
      responses:
        '200':
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/Document'
    post:
      summary: Create document
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                title:
                  type: string
                content:
                  type: string
      responses:
        '201':
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Document'
  /documents/{id}:
    get:
      summary: Get document
      parameters:
        - name: id
          in: path
          required: true
          schema:
            type: string
      responses:
        '200':
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Document'
    put:
      summary: Update document
      parameters:
        - name: id
          in: path
          required: true
          schema:
            type: string
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                title:
                  type: string
                content:
                  type: string
      responses:
        '200':
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Document'
components:
  schemas:
    Document:
      type: object
      properties:
        id:
          type: string
        title:
          type: string
        content:
          type: string
        word_count:
          type: integer
          description: Number of words in the document content
          readOnly: true
        created_at:
          type: string
          format: date-time
        updated_at:
          type: string
          format: date-time
      required:
        - id
        - title
        - content
        - word_count
```

### ARTIFACT 3: SQL Migration (REQUIRED)
```sql
-- Migration: Add word_count to documents
-- Up
ALTER TABLE documents ADD COLUMN word_count INTEGER NOT NULL DEFAULT 0;

-- Create index for filtering by word_count
CREATE INDEX idx_documents_word_count ON documents(word_count);

-- Down
-- DROP INDEX IF EXISTS idx_documents_word_count;
-- ALTER TABLE documents DROP COLUMN word_count;
```
