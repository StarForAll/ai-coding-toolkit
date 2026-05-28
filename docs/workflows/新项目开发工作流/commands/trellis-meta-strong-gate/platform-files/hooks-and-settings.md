<!-- workflow-embed-patch:trellis-meta-strong-gate -->

# Hooks And Settings

Hooks/settings are the entry layer that connects a platform to Trellis. In strong-gate projects, they must wire the actual carrier that emits the current stage and task context.

## Settings Responsibilities

settings/config files usually register:

- optional session-start carrier: injects a Trellis overview when a session starts or resets.
- per-turn workflow-state carrier: emits the current strong-gate stage on each user input.
- compatibility carrier context: injects task context when a retained agent
  carrier is explicitly used.
- shell/session bridge: lets shell commands see the same Trellis session identity.
- platform plugin or extension entry points.

## Common Files

| Platform | settings/config |
| --- | --- |
| Claude Code | `.claude/settings.json` |
| Cursor | `.cursor/hooks.json` |
| Codex | `.codex/hooks.json`, `.codex/config.toml` |
| OpenCode | `.opencode/package.json`, `.opencode/plugins/*` |

Whether these files exist depends on which `trellis init --<platform>` surfaces the project has.

## Hook Script Types

| Script | Purpose |
| --- | --- |
| `session-start.py` | Optional session-start overview when that platform wires the event. |
| `inject-workflow-state.py` | Emits the current stage template plus route metadata such as `action`, `status`, and `blockers`. |
| `inject-subagent-context.py` | Injects PRD, JSONL context, and related spec/research for retained compatibility carriers when they are explicitly used. |
| `inject-shell-session-context.py` | Lets shell commands inherit Trellis session identity. |

## Modification Principles

1. **Settings wire things up; hooks define behavior.** If only the hook changes, the platform may never call it.
2. **Confirm the live carrier first.** Some projects use SessionStart, some use turn-level hooks, and some use both.
3. **Strong-gate routing must be route-based.** The workflow-state carrier may still choose a stage template, but its source of truth must be `workflow-state.py route`, not `task.json.status`, and it must not hide blocker/repair actions.
4. **Errors must be visible.** If a carrier is missing or inactive, surface which context was not injected.

## Troubleshooting Path

If the user says "AI did not read Trellis state":

1. Check whether the platform settings register the carrier the project actually uses.
2. Check whether the corresponding hook/plugin file exists.
3. Manually run the `.trellis/scripts/get_context.py`, `task.py current --source`, or `workflow-state.py route` command that the carrier depends on.
4. Check whether active task state exists in `.trellis/.runtime/sessions/`.
5. Check whether the platform shell passes session identity.

For Codex specifically, `.codex/hooks.json` plus `inject-workflow-state.py` is the usual managed path in this workflow; treat `session-start.py` as optional unless the target project explicitly wires it.
