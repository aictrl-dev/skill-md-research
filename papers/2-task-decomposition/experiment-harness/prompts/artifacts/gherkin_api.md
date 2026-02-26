# Artifact Format: Gherkin + OpenAPI

Combine behavioral specification (Gherkin) with API contract (OpenAPI).

## Format

### Part 1: Gherkin (Behavior)

```gherkin
Feature: [Feature Name]
  ...
```

### Part 2: OpenAPI (API Contract)

```yaml
openapi: 3.0.0
info:
  title: [Feature] API
  version: 1.0.0
paths:
  /endpoint:
    get:
      ...
```

## Example

### Gherkin

```gherkin
Feature: Document word count
  As a content author
  I want to see the word count of my documents
  So that I can track document length

  Scenario: Word count is returned in API response
    Given a document exists with id "doc-123"
    And the document has content "Hello world"
    When I request GET /api/documents.info with id "doc-123"
    Then the response status should be 200
    And the response should include wordCount: 2

  Scenario: Word count is updated on document update
    Given a document exists with id "doc-123"
    When I request POST /api/documents.update with:
      | id      | doc-123          |
      | text    | Updated content  |
    Then the response status should be 200
    And the document wordCount should be 2
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
              type: object
              required:
                - id
              properties:
                id:
                  type: string
                  description: Document ID
      responses:
        '200':
          description: Document information
          content:
            application/json:
              schema:
                type: object
                properties:
                  data:
                    $ref: '#/components/schemas/Document'

  /api/documents.update:
    post:
      summary: Update document
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required:
                - id
              properties:
                id:
                  type: string
                text:
                  type: string
                  description: Document content (affects wordCount)
      responses:
        '200':
          description: Updated document
          content:
            application/json:
              schema:
                type: object
                properties:
                  data:
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
        wordCount:
          type: integer
          description: Number of words in the document content
          minimum: 0
        text:
          type: string
        createdAt:
          type: string
          format: date-time
        updatedAt:
          type: string
          format: date-time
```

## Pros
- Testable behavior (Gherkin)
- API contract (OpenAPI)
- Can validate API conformance
- Enables mock servers

## Cons
- Missing database schema
- No data layer specification
- Still needs translation to implementation
