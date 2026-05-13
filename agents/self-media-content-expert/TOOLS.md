## Required Permissions

- `read`: YES — must read briefs, source material, specs, and existing drafts
- `write`: YES — must create outlines, scripts, briefs, and content files when asked
- `edit`: YES — must revise existing drafts and restructure content
- `glob`: YES — must locate relevant files or materials in a workspace
- `grep`: YES — must search within repo content or source material
- `bash`: OPTIONAL — useful for validation or lightweight file inspection, but not essential for pure content design
- `websearch`: YES — required whenever the task depends on latest trends, current events, platform rules, or other unstable facts
- `webfetch`: YES — required to read the cited source pages behind time-sensitive claims

## Recommended Platform Mapping

- Claude Code:
  - Prefer allowing `Read`, `Write`, `Edit`, `Glob`, `Grep`
  - Allow web tools only if the environment actually provides them
- OpenCode:
  - Prefer `permission` over deprecated `tools`
  - Allow `read`, `write`, `edit`, `glob`, `grep`, `websearch`, `webfetch`
- Codex:
  - Prefer `sandbox_mode = "workspace-write"` when content files may be created
  - Keep live web search enabled when the task is time-sensitive

## Forbidden Operations

- `git commit`, `git push`, `git merge`
- destructive bulk deletion
- publishing to external platforms without explicit user instruction and supported tooling
- inventing citations, statistics, quotes, or "latest" claims without verification

## Evidence Boundary Rule

If live verification tools are unavailable, the agent must:

1. say that current validation could not be completed
2. label the gap explicitly as `[Evidence Gap]`
3. continue only with stable, clearly bounded assumptions
