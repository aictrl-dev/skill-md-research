I'll explore the codebase to understand the Document model structure before designing the artifacts.
```gherkin
Feature: Document Word Count

  As a user
  I want documents to automatically track their word count
  So that I can filter, sort, and search documents by length

  Scenario: Calculate word count when creating a document
    Given I am an authenticated user
    When I create a document with title "Getting Started Guide"
    And the document text is "This is a comprehensive guide with fifteen words in total here"
    Then the document is created successfully
    And the document wordCount field equals 15
    And the word_count column in the database is set to 15

  Scenario: Update word count when document content changes
    Given I have an existing document with title "Draft Document"
    And the document text is "Short text" with wordCount 2
    When I update the document text to "This is an updated document with many more words in the content"
    Then the document is updated successfully
    And the document wordCount field equals 13
    And the word_count column in the database is updated to 13

  Scenario: Return word count in API response
    Given I have an existing document with wordCount of 42
    When I request the document info via documents.info endpoint
    Then the response includes a wordCount field with value 42
    And the response status is 200

  Scenario: Filter documents by minimum word count
    Given I have documents with word counts: 50, 100, 200, 500
    When I request documents list with minWordCount filter set to 100
    Then the response contains 3 documents
    And none of the returned documents have wordCount less than 100

  Scenario: Filter documents by maximum word count
    Given I have documents with word counts: 50, 100, 200, 500
    When I request documents list with maxWordCount filter set to 200
    Then the response contains 3 documents
    And none of the returned documents have wordCount greater than 200

  Scenario: Sort documents by word count ascending
    Given I have documents with word counts: 500, 50, 200, 100
    When I request documents list sorted by wordCount with direction ASC
    Then the documents are ordered by wordCount ascending
    And the first document has wordCount 50
    And the last document has wordCount 500

  Scenario: Sort documents by word count descending
    Given I have documents with word counts: 500, 50, 200, 100
    When I request documents list sorted by wordCount with direction DESC
    Then the documents are ordered by wordCount descending
    And the first document has wordCount 500
    And the last document has wordCount 50

  Scenario: Handle empty document content gracefully
    Given I am an authenticated user
    When I create a document with title "Empty Document"
    And the document text is empty string
    Then the document is created successfully
    And the document wordCount field equals 0

  Scenario: Handle document with whitespace-only content
    Given I am an authenticated user
    When I create a document with title "Whitespace Document"
    And the document text is "     \n\t   "
    Then the document is created successfully
    And the document wordCount field equals 0

  Scenario: Handle document with special characters and punctuation
    Given I am an authenticated user
    When I create a document with text "Hello, world! How are you? I'm fine... thanks!"
    Then the document is created successfully
    And the document wordCount equals 10

  Scenario: Handle document with multi-byte Unicode characters
    Given I am an authenticated user
    When I create a document with text "你好 世界 Hello world Bonjour le monde"
    Then the document is created successfully
    And the document wordCount equals 6

  Scenario: Store word count in document revisions for history tracking
    Given I have a document with wordCount 20
    When I create a revision of the document
    And update the document text to have wordCount 35
    Then a new revision is created
    And the revision stores the wordCount as 20
    And the current document has wordCount 35

  Scenario: Validate wordCount filter with negative number
    Given I am an authenticated user
    When I request documents list with minWordCount set to -10
    Then the request fails with validation error
    And the error message indicates wordCount must be non-negative

  Scenario: Validate wordCount filter with non-integer value
    Given I am an authenticated user
    When I request documents list with minWordCount set to 10.5
    Then the request fails with validation error
    And the error message indicates wordCount must be an integer

  Scenario: Database index improves query performance
    Given the database has 10,000 documents
    When I execute a query filtering by wordCount
    Then the query uses the documents_word_count_idx index
    And the query execution time is less than 100ms
```</arg_value></tool_call>

> build · glm-4.7

✱ Glob "**/document*.py" 0 matches
✱ Glob "**/api/**/*.py" 0 matches
✱ Glob "**/migrations/**/*.sql" 0 matches
✱ Glob "**/document*.js" 0 matches
✱ Glob "**/swagger*.yaml" 0 matches
✱ Glob "**/openapi*.yaml" 0 matches
→ Read .
→ Read prompts
→ Read tasks
→ Read codebase
→ Read tasks/outline_crud_001_word_count.md
✱ Glob "**/model*.py" in codebase · 0 matches
✱ Glob "**/models/**" in codebase · 100 matches
✱ Glob "**/*document*" in codebase · 50 matches
→ Read codebase/server/presenters/document.ts
→ Read codebase/server/routes/api/documents/documents.ts [limit=100]
→ Read codebase/server/models/Document.ts [limit=100]
→ Read codebase/server/routes/api/documents/schema.ts
✱ Glob "**/2025*.js" in codebase/server/migrations · 46 matches
→ Read codebase/server/migrations/20251125012929-add-popularity-score-to-documents.js
→ Read codebase/server/migrations/20260222000000-add-word-count-to-documents.js
