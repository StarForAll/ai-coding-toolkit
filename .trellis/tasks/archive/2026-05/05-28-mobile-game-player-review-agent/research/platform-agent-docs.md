# Research: Platform Agent Docs

- **Query**: Verify current official documentation for Claude Code, OpenCode,
  and Codex custom agent/subagent wrapper fields needed for a cross-CLI agent
  deployment guide.
- **Scope**: external
- **Date**: 2026-05-28

## Findings

### Claude Code

- Official page checked: `https://code.claude.com/docs/en/sub-agents.md`
- Project-scoped subagents are Markdown files under `.claude/agents/`.
- Subagent files use YAML frontmatter followed by the system prompt body.
- `name` and `description` are required frontmatter fields.
- Optional fields include tool controls and richer wrapper concerns such as
  `tools`, `disallowedTools`, `model`, `permissionMode`, `maxTurns`,
  `skills`, `mcpServers`, `hooks`, `memory`, `background`, `effort`,
  `isolation`, `color`, and `initialPrompt`.
- Source `SYSTEM.md` should remain wrapper-agnostic; these fields belong in
  `DEPLOYMENT.md` or generated platform files.

### OpenCode

- Official pages checked:
  - `https://dev.opencode.ai/docs/agents/`
  - `https://dev.opencode.ai/docs/permissions/`
- Project Markdown agents live under `.opencode/agents/`; filename becomes the
  agent name.
- Markdown agents use frontmatter plus a prompt body.
- `description` is required; `mode: subagent` should be used for subagent use.
- `permission` is the current preferred field for tool control.
- The legacy `tools` boolean config is deprecated as of `v1.1.1`, though still
  supported for compatibility.
- Permission actions are `allow`, `ask`, and `deny`; `edit` gates write/edit/
  patch-style file modification.

### Codex

- Official page checked: `https://developers.openai.com/codex/multi-agent/`
- Project-scoped custom agents live under `.codex/agents/`.
- Each standalone custom agent file is TOML.
- Required fields are `name`, `description`, and `developer_instructions`.
- Supported optional custom-agent/config keys include `nickname_candidates`,
  `model`, `model_reasoning_effort`, `sandbox_mode`, `mcp_servers`, and
  `skills.config`.
- Codex subagents inherit the current sandbox policy unless the custom agent
  explicitly overrides it.

## Constraints For This Task

- The new mobile-game agent should be authored in `agents/<id>/` as source.
- `SYSTEM.md` must not contain Claude frontmatter, OpenCode frontmatter, or
  Codex TOML.
- Wrapper templates in `DEPLOYMENT.md` should prefer:
  - Claude Code: `.claude/agents/mobile-game-player-reviewer.md`
  - OpenCode: `.opencode/agents/mobile-game-player-reviewer.md`
  - Codex: `.codex/agents/mobile-game-player-reviewer.toml`
- Deployment notes should include a refresh policy because platform fields are
  version-sensitive.
