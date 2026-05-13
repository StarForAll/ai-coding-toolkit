# Platform Agent Compatibility Research

Date: 2026-05-13

## Scope

Verify current official agent/subagent configuration surfaces for:

- Claude Code
- Codex
- OpenCode

Goal: keep the new `agents/<id>/` source asset accurate for cross-platform
adaptation without actually installing wrappers in this repository.

## Sources

- Claude Code official docs:
  - https://code.claude.com/docs/en/sub-agents
- Codex official docs:
  - https://developers.openai.com/codex/subagents
- OpenCode official docs:
  - https://opencode.ai/docs/agents/
  - https://opencode.ai/docs/permissions

## Findings

### Claude Code

- Project-scoped subagents live under `.claude/agents/`.
- Subagents are Markdown files with YAML frontmatter plus Markdown body.
- `name` and `description` are required.
- Current supported optional frontmatter includes `tools`, `disallowedTools`,
  `model`, `permissionMode`, `maxTurns`, `skills`, `mcpServers`, `hooks`,
  `memory`, `background`, `effort`, `isolation`, `color`, `initialPrompt`.
- Plugins cannot use `hooks`, `mcpServers`, or `permissionMode`, but project
  subagents can.
- Files added directly on disk require a session restart to load.

Implication for source assets:

- Keep `SYSTEM.md` platform-neutral.
- Put Claude-specific capability tuning only in deployment guidance.

### Codex

- Project-scoped custom agents live under `.codex/agents/`.
- Each custom agent is one standalone TOML file.
- Required fields are:
  - `name`
  - `description`
  - `developer_instructions`
- Current documented optional fields include:
  - `nickname_candidates`
  - `model`
  - `model_reasoning_effort`
  - `sandbox_mode`
  - `mcp_servers`
  - `skills.config`
- Global spawned-agent controls remain under `[agents]` in `.codex/config.toml`.
- Custom agent file format may still evolve as authoring/sharing matures.

Implication for source assets:

- Use top-level TOML keys in wrapper examples.
- Avoid overcommitting to optional fields in the source asset unless they are
  truly role-defining.

### OpenCode

- Project-scoped Markdown agents live under `.opencode/agents/`.
- Markdown filename becomes the agent name.
- `description` is required.
- `mode` defaults to `all`; set `mode: subagent` when the wrapper should only
  act as a subagent.
- `permission` is the recommended current control surface.
- Legacy `tools` config is deprecated as of `v1.1.1` and kept only for
  backward compatibility.
- `model`, `temperature`, `steps`, `hidden`, `task permissions`, `top_p`, and
  additional config fields are available depending on use case.

Implication for source assets:

- Wrapper examples should prefer `permission` rather than `tools`.
- For this repository's source layer, document OpenCode identity as
  filename-derived instead of adding a pseudo-`name` field.

## Cross-Platform Convergence Rules

1. Shared role definition belongs in `SYSTEM.md`.
2. Role description belongs in `README.md`; wrappers can derive short platform
   descriptions from it.
3. Permission/sandbox/model differences belong in `DEPLOYMENT.md`.
4. If a future platform change affects required fields, update:
   - the agent's `README.md`
   - the agent's `DEPLOYMENT.md`
   - `.trellis/spec/agents/index.md` if the change affects the repository-wide
     source/deploy contract

## Current Risk Notes

- Claude Code and Codex both expose richer optional fields than the existing
  minimal template in `agents/_template/DEPLOYMENT.md`.
- Codex official docs now clearly document optional custom-agent fields beyond
  the older minimal examples already present in this repo.
- OpenCode docs explicitly deprecate legacy `tools`, so new wrapper examples
  should not teach `tools` as the default path.
