## Required Permissions

- `read`: YES — must inspect briefs, specs, contracts, docs, cost inputs, and
  technical scope material
- `write`: YES — must create estimate notes, quote drafts, pricing tables, or
  decision memos when asked
- `edit`: YES — must update existing pricing or proposal files when the task is
  tied to an existing workspace artifact
- `glob`: YES — must locate relevant files quickly
- `grep`: YES — must search requirements, dependencies, scope items, and prior
  estimate references
- `bash`: YES — should run targeted inspection or validation commands when
  local project evidence affects scope or delivery cost
- `websearch`: YES — required for latest vendor pricing, market benchmarks,
  competitor pricing, platform fees, and current policy verification
- `webfetch`: YES — required to inspect cited live pricing pages and primary
  sources directly

## Recommended Permission Posture

- Prefer least privilege by default.
- If the target project uses this agent only for pricing analysis, write/edit
  permissions can be tighter.
- If the target project expects estimate artifacts to be produced directly in
  the repo, allow workspace file changes but keep production-impacting actions
  gated.

## Forbidden Operations

- destructive bulk deletion
- git history rewriting unless the user explicitly asks for it
- production deploys, live billing changes, or irreversible environment changes
  without explicit approval
- fabricating citations, prices, exchange rates, cost tables, or verification
  results
- presenting legal, tax, accounting, or procurement guarantees as authoritative
- hiding assumption-sensitive pricing risk in order to make a quote sound more
  certain than it is

## Mapping Reminder

When adapting this source asset:

- Claude Code usually maps capability through `tools` and optional
  `permissionMode`
- OpenCode should prefer `permission`, not legacy `tools`; note that
  `permission.edit` covers write/edit/patch style file modification as one
  merged capability
- Codex should express edit scope through `sandbox_mode`; web search and fetch
  are not declared through standalone agent keys, so live-web behavior depends
  on the parent session or attached MCP/doc-search capabilities that the target
  project actually enables
