Fix GitHub issue #572: Add Move and Delete operations for Epic Tasks as MCP tools.

When restructuring epics (e.g., extracting stories into separate epics), there's no way to move or delete tasks via MCP tools. Orphaned tasks stay in the original epic and clutter the backlog.

**IMPORTANT: Use the aictrl MCP tools (code_search, code_context, code_plan, code_impact, code_deps, etc.) as your PRIMARY method for understanding the codebase before making changes. Do NOT read files manually until you've used the MCP tools to understand the architecture and find relevant code.**

Your task:

1. Use MCP tools to understand the task-epic-feature data model and how tasks are managed
2. Use MCP tools to find existing MCP tool patterns, StateManager interface, and Firestore implementation
3. Use MCP tools to understand the soft-delete cascade pattern and how features relate to tasks
4. Implement a `delete_task` MCP tool that safely removes a task (reject if actively claimed/in-progress, cascade soft-delete to features)
5. Implement a `move_task` MCP tool that moves a task between epics (update task + features epicId, handle broken dependencies, reject if in-progress)
6. Add the `moveTask` method to the StateManager interface and Firestore implementation

Follow all existing patterns you discover through the MCP tools. Do not modify any files beyond what's necessary.
