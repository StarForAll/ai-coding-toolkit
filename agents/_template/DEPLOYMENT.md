# Deployment Template

Use this file as a checklist when adapting a source agent into platform-specific wrappers.

## Refresh Policy

Add a short section explaining when the platform docs must be re-verified.

Recommended triggers:

- more than 90 days since the last verification
- the platform updates its agents / subagents / permissions docs
- the wrapper fails to parse or behaves differently from the current docs

## Claude Code

- Target path: `.claude/agents/<agent-id>.md`
- Format: Markdown + YAML frontmatter
- Minimum fields:
  - `name`
  - `description`

## OpenCode

- Target path: `.opencode/agents/<agent-id>.md`
- Format: Markdown + YAML frontmatter
- Recommended minimum fields:
  - `description`
  - `mode`
  - `permission`

## Codex

- Target path: `.codex/agents/<agent-id>.toml`
- Format: TOML
- Required fields:
  - `name`
  - `description`
  - `developer_instructions`

## Verification

- Can the platform discover the file?
- Can the agent access the intended tools?
- Does the agent correctly mark `[Evidence Gap]` when live verification is unavailable?
