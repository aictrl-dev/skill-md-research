Fix GitHub issue #477: Add a `delete_feature` MCP tool.

There is no MCP tool to delete a feature. When acceptance criteria need correction after a feature has been promoted past "draft", there's no way to remove and recreate it.

Add a new `delete_feature` tool to the existing MCP tools. It should:

1. Accept `feature_id` (required string) as input
2. Validate the feature exists
3. Validate the parent task is NOT actively claimed or in-progress (safety check) — if the task is claimed, reject with a workflow error
4. Call the existing `deleteFeature` method on StateManager (soft-delete is already implemented)
5. Broadcast the update via WebSocket
6. Return a success response with the deleted feature ID and parent task ID

Follow the exact same patterns as other tools in the same file:
- Add to the `definitions` array with proper inputSchema
- Add a case to the `handle` function switch
- Use `validateSessionOrgAccess` for authorization
- Use `jsonResponse`/`errorResponse`/`workflowErrorResponse` helpers
- Extract args with proper TypeScript types

Do not modify any other files unless necessary for imports.
