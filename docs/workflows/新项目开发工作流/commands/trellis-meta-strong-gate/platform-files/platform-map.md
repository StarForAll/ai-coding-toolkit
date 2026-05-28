<!-- workflow-embed-patch:trellis-meta-strong-gate -->

# Platform File Map

This page still lists common Trellis file locations by platform, but for this
installed workflow the existence of a carrier path does not automatically mean
that the carrier is part of the active execution path.

## Matrix

| Platform | CLI flag | Main directory | Skill directory | Agent directory | Hooks/extensions |
| --- | --- | --- | --- | --- | --- |
| Claude Code | `--claude` | `.claude/` | `.claude/skills/` | `.claude/agents/` | `.claude/hooks/` + `.claude/settings.json` |
| OpenCode | `--opencode` | `.opencode/` | `.opencode/skills/` | `.opencode/agents/` | `.opencode/plugins/` |
| Codex | `--codex` | `.codex/` | `.agents/skills/` | `.codex/agents/` | `.codex/hooks/` + `.codex/hooks.json` |

Other Trellis platforms may generate similar directories, but this workflow's
managed surface is limited to Claude Code, OpenCode, and Codex.

## Current Capability Groups In This Workflow

### Generated Agent Carriers

Claude Code, OpenCode, and Codex may still have generated
`trellis-research` / `trellis-implement` / `trellis-check` carrier files.

In this installed workflow, those files are:

- baseline or compatibility-retained carriers
- not the normal execution path
- not the first edit target for current implementation/check behavior

If the user wants to change current workflow behavior, start from:

1. `.trellis/workflow.md`
2. active workflow-state hooks/plugins
3. installed stage skills/commands

Use the agent directory only when the user is explicitly modifying the retained
carrier itself or intentionally planning a broader re-enable.

### Main-Session Execution

The supported execution path in this installed workflow is main-session-first,
even on platforms that still generate agent carrier files.

That means:

- carrier existence does not imply dispatch is allowed
- blocked-subagent hooks/plugins may still exist and are part of the contract
- stage guidance and workflow-state routing are the live authority

### Shared `.agents/skills/`

`.agents/skills/` remains a shared skill carrier, but its presence does not
mean that platform agent files are active. Distinguish shared skills from
platform agent carriers.

## Decision Rules

1. User specified a platform: inspect that platform's actual settings and live
   carriers first.
2. User wants current execution behavior: edit workflow/hook/skill/command
   surfaces before touching retained agent carriers.
3. User explicitly wants the retained carrier or a future re-enable: then read
   the platform agent directory too.
