## Required Permissions

- `read`: YES
- `write`: depends on whether the agent creates files
- `edit`: depends on whether the agent modifies existing files
- `glob`: usually YES
- `grep`: usually YES
- `bash`: optional
- `websearch`: YES if the agent handles time-sensitive tasks
- `webfetch`: YES if the agent must inspect cited live sources

## Forbidden Operations

- destructive bulk deletion
- inventing citations or “latest” claims without verification
- platform publishing actions unless explicitly required by the target project

## Mapping Reminder

When adapting this source asset:

- Claude Code usually maps capability through `tools`
- OpenCode should prefer `permission`
- Codex should express write scope through `sandbox_mode`
