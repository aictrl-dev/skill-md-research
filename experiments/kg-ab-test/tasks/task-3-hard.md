Fix GitHub issue #572: Add Move and Delete operations for Epic Tasks as MCP tools.

When restructuring epics (e.g., extracting stories into separate epics), there's no way to move or delete tasks via MCP tools. Orphaned tasks stay in the original epic and clutter the backlog.

Implement the following:

### 1. `delete_task` MCP tool

Add to the existing epic MCP tools file. It should:
- Accept `task_id` (required string)
- Validate the task exists
- Safety check: reject if task status is `active` or `review` (i.e., someone is working on it), or if it's claimed by a session
- Call the existing `deleteTask` method on StateManager (soft-delete already cascades to features)
- Update the parent epic's task counts
- Broadcast the update via WebSocket
- Return success with deleted task ID, epic ID, and count of cascaded features

### 2. `move_task` MCP tool

Add to the same file. It should:
- Accept `task_id` (required string) and `target_epic_id` (required string)
- Validate both the task and target epic exist
- Safety check: reject if task is `active`, `review`, or claimed
- Validate the target epic belongs to the same organization
- Move the task: update the task's `epicId` to the target epic
- Move all associated features: update their `epicId` references too
- Handle dependency references: if the task has `dependsOn` entries pointing to tasks in the OLD epic, log a warning (don't block the move, but inform the user which dependencies may be broken)
- Update task counts on both the source and target epics
- Broadcast updates via WebSocket for both epics
- Return success with moved task ID, source epic ID, target epic ID, and feature count

### 3. StateManager changes

- In `server/state/interface.ts`: add `moveTask(taskId: string, targetEpicId: string): Promise<EpicTask>` to the IStateManager interface
- In `server/state/firestore-manager.ts`: implement `moveTask` — use a Firestore batch to atomically update the task's `epicId` and all its features' `epicId` fields

### Patterns to follow

- Use the same MCP tool definition structure (definitions array, handle switch case)
- Use `validateSessionOrgAccess` for authorization
- Use `jsonResponse`/`errorResponse`/`workflowErrorResponse` helpers
- Use the project's logger for warnings about broken dependencies
- Follow the existing soft-delete cascade pattern from `deleteTask`
- Use Firestore transactions or batched writes for atomicity

Do not modify any files beyond what's described above unless necessary for imports.
