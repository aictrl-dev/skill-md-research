# Artifact Format: Natural Language Only

Describe each step and its implementation in natural language prose.

## Format

For each step, provide:

```markdown
## Step N: [Step Name]

### What to do
[Describe the implementation in plain English]

### Expected outcome
[Describe what success looks like]

### Notes
[Any additional context or edge cases]
```

## Example

```markdown
## Step 1: Add word_count column to documents table

### What to do
Create a new database migration that adds a word_count column to the documents table. 
The column should be an integer with a default value of 0. Also add the same column 
to the revisions table for history tracking. Create an index on this column for 
efficient sorting.

### Expected outcome
After running the migration, both documents and revisions tables have a word_count 
column. The migration should be reversible.

### Notes
Use the existing migration pattern from other migrations in the codebase. Make sure 
to wrap changes in a transaction.
```

## Pros
- Easy to write and understand
- Flexible, no strict format
- Good for exploration

## Cons
- Hard to validate automatically
- Ambiguity in specifications
- No type safety
