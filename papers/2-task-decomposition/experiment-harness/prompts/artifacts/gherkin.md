# Artifact Format: Gherkin Only

Describe behavior using Gherkin syntax (Given/When/Then).

## Format

```gherkin
Feature: [Feature Name]
  [Feature description]

  Scenario: [Scenario 1]
    Given [initial context]
    When [action]
    Then [expected outcome]

  Scenario: [Scenario 2]
    Given [initial context]
    When [action]
    Then [expected outcome]
```

## Example

```gherkin
Feature: Document word count
  As a content author
  I want to see the word count of my documents
  So that I can track document length

  Scenario: Word count is calculated on save
    Given I am editing a document
    And the document has content "Hello world test"
    When I save the document
    Then the word_count should be 3

  Scenario: Word count is displayed in document list
    Given a document exists with content "This is a test document"
    When I view the documents list
    Then I should see word count "5" for the document

  Scenario: Word count updates when content changes
    Given a document exists with content "Initial"
    When I update the content to "Initial content extended"
    Then the word_count should be 3

  Scenario: Empty document has zero word count
    Given I create a new document
    And the content is empty
    When I save the document
    Then the word_count should be 0

  Scenario Outline: Word count for different content lengths
    Given a document with content "<content>"
    When I save the document
    Then the word_count should be <count>

    Examples:
      | content              | count |
      | One                  | 1     |
      | Two words            | 2     |
      | Three words here     | 3     |
```

## Pros
- Executable with test frameworks (Cypress, Playwright)
- Human-readable
- Encourages behavior-first thinking
- Can be validated with Gherkin parser

## Cons
- Doesn't specify implementation
- Missing API/DB contracts
- Needs translation to code
