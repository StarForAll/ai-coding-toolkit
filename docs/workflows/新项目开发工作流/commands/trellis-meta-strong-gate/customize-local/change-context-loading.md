<!-- workflow-embed-patch:trellis-meta-strong-gate -->

# Change Local Context Loading

In this installed workflow, context loading still matters, but the live path is
split between main-session guidance and compatibility-retained agent carriers.

## Read These Files First

1. `.trellis/workflow.md`
2. `.trellis/scripts/get_context.py`
3. `.trellis/scripts/common/session_context.py`
4. `.trellis/scripts/common/task_context.py`
5. `.trellis/scripts/common/active_task.py`
6. current platform hooks, skills, or commands that are actually active
7. the current task's `implement.jsonl` / `check.jsonl`

## Common Needs And Edit Points

| Need | Edit point |
| --- | --- |
| Inject more/less information in new sessions | `session_context.py` or the platform session-start carrier |
| Change hints on each user input | `[workflow-state:STATUS]` blocks in `.trellis/workflow.md` plus route metadata carriers |
| Main-session implementation/checking lacks spec context | workflow instructions, JSONL contents, and the live workflow-state/skill carriers |
| Compatibility agent carrier did not read specs | `inject-subagent-context` or the retained agent prelude, but only if the request is explicitly about that compatibility carrier |
| Active task is lost | `active_task.py` and platform session identity propagation |
| Change JSONL validation rules | `task_context.py` |

## Important Boundary

Do not jump to agent-file edits just because `implement.jsonl` / `check.jsonl`
exist. In this workflow those JSONL manifests may still support retained agent
carriers, but the normal execution path is main-session-first.

Use agent-specific context-loading edits only when the user is intentionally
working on the compatibility carrier itself or designing a broader re-enable.
