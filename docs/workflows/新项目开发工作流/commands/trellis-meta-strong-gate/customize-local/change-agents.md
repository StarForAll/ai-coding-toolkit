<!-- workflow-embed-patch:trellis-meta-strong-gate -->

# Change Compatibility Agent Carriers

In this installed workflow, `trellis-research`, `trellis-implement`, and
`trellis-check` are **not** the normal execution path. The workflow keeps those
agent carrier files only as baseline or compatibility surfaces.

## First Confirm The Real Goal

If the user says they want to:

- change the normal implementation path
- change whether implementation/checking uses the main session
- change whether blocked subagent routes can run

then start from:

1. `.trellis/workflow.md`
2. `.trellis/scripts/workflow/workflow-state.py`
3. the current platform's live hooks/skills/commands

Do **not** start from the agent files alone, because that would modify a
compatibility carrier without changing the workflow policy that currently keeps
it disabled.

## When Agent-File Editing Is Actually Appropriate

Editing the platform agent files is appropriate only when the user explicitly
wants one of these:

- inspect or document the retained compatibility carrier
- prepare a future re-enable design
- change the baseline carrier format itself for platforms that still ship it
- align agent-file wording with the current disabled-state contract

## Common Paths

| Platform | Path |
| --- | --- |
| Claude Code | `.claude/agents/trellis-*.md` |
| OpenCode | `.opencode/agents/trellis-*.md` |
| Codex | `.codex/agents/trellis-*.toml` |

Use the actual local files in the user project as authoritative.

## Safe Modification Principle

If the workflow still says "main-session-only", agent-file edits must preserve
that meaning instead of reopening the path silently.

Examples:

- OK: clarify that the carrier is compatibility-retained
- OK: document that live execution is routed elsewhere
- Not OK: rewrite the file so it looks like the current default execution path
  without also changing workflow policy, hooks, and route gating

## If The User Wants A Real Re-Enable

Treat that as a broader workflow-policy change. The change must include:

- route semantics
- blocked-dispatch hooks/plugins
- command/skill entry guidance
- install/upgrade validation

Without that larger bundle, the agent file alone is not the right edit target.
