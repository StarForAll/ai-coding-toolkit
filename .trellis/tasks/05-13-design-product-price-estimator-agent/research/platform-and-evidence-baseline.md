# Platform And Evidence Baseline

Date verified: 2026-05-13

## Research Question

What current platform constraints matter for authoring a reusable source-layer
 agent that can later be adapted to Claude Code, OpenCode, and Codex, while
 enforcing live verification for time-sensitive software pricing work?

## Sources

- Claude Code subagents:
  `https://code.claude.com/docs/en/sub-agents`
- Codex custom agents:
  `https://developers.openai.com/codex/subagents`
- OpenCode agents:
  `https://opencode.ai/docs/agents/`
- OpenCode permissions:
  `https://opencode.ai/docs/permissions`

## Verified Findings

### Claude Code

- Project-scoped agents live under `.claude/agents/`.
- Files are Markdown with YAML frontmatter plus a Markdown body.
- Required frontmatter fields are `name` and `description`.
- The body becomes the system prompt.
- Current optional frontmatter is broader than older templates and includes
  fields such as `tools`, `disallowedTools`, `model`, `permissionMode`,
  `maxTurns`, `skills`, `mcpServers`, `hooks`, `memory`, `background`,
  `effort`, `isolation`, `color`, and `initialPrompt`.

### Codex

- Personal agents live under `~/.codex/agents/`; project-scoped agents live
  under `.codex/agents/`.
- Each custom agent is a standalone TOML file.
- Required fields are `name`, `description`, and `developer_instructions`.
- Optional fields inherit from the parent session when omitted; the current
  official page explicitly names `nickname_candidates`, `model`,
  `model_reasoning_effort`, `sandbox_mode`, `mcp_servers`, and
  `skills.config`.
- The agent file behaves like a configuration layer for spawned sessions, so
  source-agent docs should avoid inventing unsupported TOML keys.

### OpenCode

- Project-scoped agents live under `.opencode/agents/`; global agents live
  under `~/.config/opencode/agents/`.
- Markdown agent files use frontmatter plus a Markdown prompt body.
- The file name becomes the agent name.
- `description` is required.
- `mode` supports `primary`, `subagent`, or `all`; default is `all`.
- `permission` is the current preferred capability model.
- OpenCode also supports optional fields such as `model`, `temperature`,
  `steps`, `hidden`, `disable`, `top_p`, and JSON-based `opencode.json`
  declarations in addition to Markdown agent files.
- The legacy `tools` config is deprecated and kept for backward compatibility.
- `permission.edit` covers file modifications including write/edit/patch.
- Permission rules for tools such as `bash`, `websearch`, and `webfetch` can be
  simple actions or more granular object rules.

## Design Implications For This Agent

1. The reusable source asset should stay platform-agnostic in `SYSTEM.md`.
2. `DEPLOYMENT.md` should own current wrapper guidance and field drift notes.
3. OpenCode guidance must prefer `permission`, not legacy `tools`.
4. Codex guidance must stick to currently confirmed TOML keys only.
5. The agent's core behavior must treat pricing-related current facts as live
   evidence problems, not stable-knowledge problems.

## Live-Evidence Contract For Pricing Work

The pricing-focused agent should require live verification before presenting the
 following as facts:

- LLM / API vendor pricing
- cloud or hosting pricing
- SMS, email, payments, storage, and vector database pricing
- marketplace or app store commissions and fees
- competitor pricing pages
- regional labor-rate or contractor-rate benchmarks
- exchange rates
- time-sensitive security, compliance, or policy costs

If the environment cannot verify these, the agent must return `[Evidence Gap]`
instead of pretending the facts are current.
