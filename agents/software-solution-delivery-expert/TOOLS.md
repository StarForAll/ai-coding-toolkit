## Required Permissions

- `read`: YES — must inspect code, docs, configs, logs, and requirement inputs
- `write`: YES — must create plans, notes, specs, or delivery artifacts when
  asked
- `edit`: YES — must modify existing files when implementation or patch work is
  requested
- `glob`: YES — must locate relevant files quickly
- `grep`: YES — must search identifiers, errors, and repeated patterns
- `bash`: YES — should run targeted inspection, build, lint, test, or diff
  commands when relevant
- `websearch`: YES — required for latest-version, pricing, policy, security, or
  vendor-fact verification
- `webfetch`: YES — required to inspect cited live sources directly

## Recommended Permission Posture

- Prefer least privilege by default.
- If the target project treats this agent as planning-only, set write/edit
  permissions tighter.
- If the target project expects autonomous implementation, allow workspace file
  changes but keep production-impacting actions gated.

## Forbidden Operations

- destructive bulk deletion
- git history rewriting unless the user explicitly asks for it
- production deploys, live database mutations, or irreversible environment
  changes without explicit approval
- fabricating citations, versions, estimates, or verification results
- legal, tax, or financial guarantees presented as authoritative
- hiding material risk in order to make a project sound easier than it is

## Mapping Reminder

When adapting this source asset:

- Claude Code usually maps capability through `tools` and optional
  `permissionMode`
- OpenCode should prefer `permission`, not legacy `tools`
- Codex should express edit scope through `sandbox_mode`; extra doc/search
  access should be added only through currently supported config keys such as
  `mcp_servers` or `skills.config`
