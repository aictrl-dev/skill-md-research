# Stack Decomposition Strategy

Decompose the task by **stack layer**, from bottom to top:

## Layer Order

1. **Database Layer** - Schema changes, migrations, indexes
2. **Model Layer** - Domain models, business logic
3. **API Layer** - Routes, handlers, validation
4. **Service Layer** - Background jobs, integrations
5. **UI Layer** - Components, pages, styles

## Principles

- Each layer depends on the layers below it
- Changes flow from bottom (DB) to top (UI)
- Test each layer independently before moving up
- Keep each step focused on a single layer

## Step Template

```
Step N: [Layer] - [Description]
Input: [What you need from previous steps]
Output: [What this step produces]
Validation: [How to verify this step succeeded]
```

## Example

For "Add email field to User":

```
Step 1: Database - Add email column
  Input: None
  Output: migration.sql
  Validation: Migration runs successfully

Step 2: Model - Add email to User model
  Input: migration.sql
  Output: User.ts with email field
  Validation: TypeScript compiles

Step 3: API - Update user endpoints
  Input: User model
  Output: routes/users.ts updated
  Validation: API accepts email in requests

Step 4: UI - Show email in profile
  Input: API changes
  Output: Profile component updated
  Validation: UI displays email
```

## When to Use

- CRUD operations
- Feature additions
- Schema changes
- Integration with external systems
