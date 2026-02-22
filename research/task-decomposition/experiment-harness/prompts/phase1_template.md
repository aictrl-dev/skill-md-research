You are a software architect. Design this feature BEFORE implementation.

## Task
{TASK_DESCRIPTION}

## Output Requirements

Generate exactly THREE artifacts. Each must be complete and valid.

### 1. GHERKIN TEST SCENARIOS

Output a valid Gherkin feature file with at least 3 scenarios covering:
- Happy path
- Edge cases  
- Error handling

Start with: ```gherkin
End with: ```

### 2. OPENAPI SPECIFICATION

Output a valid OpenAPI 3.0 spec for the API changes.
Include request/response schemas for affected endpoints.

Start with: ```yaml
End with: ```

### 3. SQL MIGRATION

Output valid PostgreSQL migration with up and down sections.
Include column types, constraints, and indexes.

Start with: ```sql
End with: ```

## CRITICAL RULES

1. Output ALL THREE artifacts
2. Each artifact must be in a code block
3. Each artifact must be syntactically valid
4. DO NOT write implementation code
5. DO NOT skip any artifact

Now generate the three artifacts:
