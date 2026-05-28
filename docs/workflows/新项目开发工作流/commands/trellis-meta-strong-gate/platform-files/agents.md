<!-- workflow-embed-patch:trellis-meta-strong-gate -->

# Platform Agent Carriers

The current embedded workflow keeps the platform agent carrier files on disk as
baseline or compatibility surfaces, but it does **not** treat them as the live
execution path for normal implementation/checking.

## Current Policy

- Do **not** dispatch `trellis-research`, `trellis-implement`, or
  `trellis-check` as normal workflow steps in this installed workflow.
- The supported path is main-session execution plus workflow-state routing.
- Agent carrier files may still exist because they belong to the Trellis
  baseline, future compatibility, or uninstall/restore behavior.

Carrier presence is therefore not the same as carrier availability.

## What These Files Still Mean

If the user inspects platform agent directories, these files are best treated
as:

- baseline Trellis carrier definitions
- compatibility-retained surfaces
- possible future re-enable targets only after workflow policy changes

They are **not** the current source of truth for "how implementation/checking
should run today" in this installed workflow.

## Common Paths

| Platform | Carrier path | Current meaning in this workflow |
| --- | --- | --- |
| Claude Code | `.claude/agents/trellis-*.md` | Baseline/compatibility carrier, not the normal execution path |
| OpenCode | `.opencode/agents/trellis-*.md` | Baseline/compatibility carrier, not the normal execution path |
| Codex | `.codex/agents/trellis-*.toml` | Baseline/compatibility carrier, not the normal execution path |

Other Trellis platforms may generate similar files, but this workflow's managed
surface is limited to Claude Code, OpenCode, and Codex.

## If The User Wants To Change Execution Behavior

Use these edit points first:

1. `.trellis/workflow.md`
2. `.trellis/scripts/workflow/workflow-state.py`
3. the current platform's live entry carriers such as skills, commands, or
   workflow-state hooks

Only edit the platform agent files when the user explicitly wants to modify the
compatibility carrier itself or when the workflow policy is being deliberately
changed to re-enable that path.

## If The User Wants To Re-Enable Agent Paths

Treat that as a workflow-policy change, not as a one-file agent tweak.

You must verify in the same change:

- workflow stage routing
- workflow-state prompts and route metadata
- hook/plugin behavior around blocked subagent dispatch
- command/skill guidance that currently says to stay in the main session
- any install/upgrade checks that currently enforce the disabled state

Without those broader changes, editing the carrier file alone would create a
contradiction instead of a valid customization.
