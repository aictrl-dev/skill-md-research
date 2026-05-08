Fix GitHub issue #531: Add uniqueness validation for organization slugs.

When organizations are created, the slug is derived from the name but there is no uniqueness check. Two orgs named "Test Org" would both get slug `test-org`, causing routing conflicts since marketplace URLs and plugin install commands use the slug.

Fix this by:

1. In `server/state/firestore-manager.ts`, in the `createOrganization` method:
   - After generating the slug from the name, query Firestore to check if any existing organization already has that slug
   - If a collision is found, append a numeric suffix (e.g., `test-org-2`, `test-org-3`) by incrementing until a unique slug is found
   - Use the unique slug when creating the organization document

2. In `server/state/interface.ts`:
   - No interface change needed — the `createOrganization(name, ownerId)` signature stays the same, the uniqueness logic is internal

3. In `server/api/organization-routes.ts`:
   - No changes needed unless you want to add a specific error response for slug collisions (optional)

Follow all existing patterns: logger usage, error handling, Firestore query patterns, the existing slug generation logic. The `findOrgByShortId` function in `server/lib/org-utils.ts` already resolves slugs — do not modify it.

Do not modify any other files unless necessary for imports.
