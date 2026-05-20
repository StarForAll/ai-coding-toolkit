<!-- workflow-embed-patch:trellis-meta-strong-gate -->

# Change Local Hooks

Hooks/plugins are the automation layer that connects a platform to Trellis. In strong-gate projects, edit the platform's actual carrier rather than assuming every CLI uses Claude-style hook paths.

## Read These Files First

1. Target platform settings/config:
   - Claude Code: `.claude/settings.json`
   - OpenCode: `.opencode/package.json`
   - Codex: `.codex/hooks.json`
2. Target platform hook/plugin directory:
   - Claude Code: `.claude/hooks/`
   - OpenCode: `.opencode/plugins/`
   - Codex: `.codex/hooks/`
3. `.trellis/scripts/common/active_task.py`
4. `.trellis/scripts/common/session_context.py`
5. `.trellis/workflow.md`

## Common Carrier Types

| Carrier | Purpose |
| --- | --- |
| session-start | Optional overview when a session starts, resets, or compacts. |
| workflow-state | Emits the current strong-gate stage plus route metadata on each user input. |
| sub-agent context | Injects PRD/spec/research before implementation/check/research agents start. |
| shell session bridge | Lets shell commands inherit the same Trellis session identity. |

## Modification Steps

1. Find the registration in the current platform settings/config.
2. Confirm the registered hook/plugin path exists.
3. Read the carrier implementation and identify its inputs, outputs, and `.trellis/scripts/` dependencies.
4. Modify the carrier behavior.
5. If routing or stage semantics change, synchronize `.trellis/workflow.md` and `workflow-state.py` in the same change.

## Example: Change New-Session Injection Content

First find the platform carrier for the current target:

```text
Claude Code: .claude/settings.json -> .claude/hooks/session-start.py
OpenCode: .opencode/package.json -> .opencode/plugins/session-start.js
Codex: .codex/hooks.json -> .codex/hooks/session-start.py
```

If the carrier ultimately calls `.trellis/scripts/get_context.py` or `session_context.py`, editing the local Trellis script is usually more robust than hard-coding content directly inside the hook/plugin wrapper.

## Example: Agent Did Not Read JSONL

First confirm:

```bash
python3 ./.trellis/scripts/task.py current --source
python3 ./.trellis/scripts/task.py validate <task>
```

If the task and JSONL are correct, determine whether the platform uses hook/plugin push or agent pull. For hook/plugin push, edit the matching `inject-subagent-context` carrier; for agent pull, edit the agent file.

## Notes

- Settings/config files handle registration; hook/plugin files handle behavior. Inspect both together.
- Different platforms support different carrier shapes. Do not directly copy Claude hook paths into OpenCode or Codex guidance.
- Hooks/plugins should read project-local `.trellis/`; they should not depend on Trellis upstream source paths.
- Carrier failures should surface visible errors so AI does not silently lose context.
