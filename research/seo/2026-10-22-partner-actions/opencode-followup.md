Following up on the automated stale-PR closure: we maintain aictrl and would like this existing ecosystem submission reconsidered.

The public package is now `@aictrl/opencode@1.2.0` on the `latest` tag. It installs 17 portable engineering skills for tasks such as spec review, code review and root-cause analysis, with optional OAuth-connected aictrl workflows. The source and setup are at https://github.com/aictrl-dev/skills.

A fresh isolated check of that exact npm version passed clean project install, repeat install and uninstall. Repeat install preserved identical files; uninstall preserved an unrelated skill and MCP configuration. No model run, account login or connected workflow was needed for this installer check.

I checked the current English Ecosystem page and aictrl is absent. The original proposal is a single Plugins-table row; its older package/count details need updating for the current release. Would you be willing to reopen this PR for that update and review? We can refresh the row against current `dev`.
