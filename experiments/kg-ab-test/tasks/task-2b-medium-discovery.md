Fix GitHub issue #531: Add uniqueness validation for organization slugs.

When organizations are created, the slug is derived from the name but there is no uniqueness check. Two orgs with the same name get the same slug, causing routing conflicts.

**IMPORTANT: Use the aictrl MCP tools (code_search, code_context, code_plan, code_impact, domain_entity, architecture_overview, etc.) as your PRIMARY method for understanding the codebase before making changes. Do NOT read files manually until you've used the MCP tools to understand the architecture and find relevant code.**

Your task:
1. Use MCP tools to understand how organizations are created and where the slug is generated
2. Use MCP tools to find all code that depends on slug uniqueness (URL routing, lookups, etc.)
3. Add slug collision detection: if a slug already exists, append a numeric suffix (-2, -3, etc.)
4. Follow all existing patterns you discover through the MCP tools

Do not modify any files beyond what's necessary. Follow all existing code conventions.
