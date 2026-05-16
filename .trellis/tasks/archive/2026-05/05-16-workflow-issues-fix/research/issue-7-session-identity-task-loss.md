# Research: Issue 7 - Without session identity, active task may be lost

- **Query**: Does task.py start in degraded mode lose the active-task pointer?
- **Scope**: Internal
- **Date**: 2026-05-16

## Findings

### How route Resolves Current Task

`workflow-state.py route` (lines 1051-1215) uses this resolution chain:

```
1. Explicit --task-dir argument? → Use it directly
2. resolve_active_task(repo_root) → Session runtime
   a. If active.task_path exists and not stale → Use it
   b. If stale → Return "repair_needed"
   c. If no task_path → Continue to degraded fallback
3. resolve_degraded_task_dir(repo_root) → Degraded fallback
   a. Only used when NO session file has any current_task pointer
   b. Reads .trellis/.runtime/degraded-active-task.json
   c. Falls through to next step if not found
4. No active task found →
   a. No tasks at all → "first_entry" (route to feasibility)
   b. Tasks exist but no pointer → "recovery_needed"
```

### Degraded Mode Mechanism

`resolve_degraded_task_dir()` (workflow-state.py:186-202):
```python
def resolve_degraded_task_dir(repo_root: Path) -> Path | None:
    if session_runtime_has_any_current_task(repo_root):
        # If any session file already carries a current_task pointer,
        # prefer explicit recovery instead of guessing from a degraded pointer.
        return None
    degraded_path = repo_root / ".trellis" / ".runtime" / "degraded-active-task.json"
    degraded = read_json(degraded_path)
    if not degraded:
        return None
    task_ref = degraded.get("current_task")
    ...
```

Key constraint: The degraded fallback is ONLY used when NO session file has any `current_task` pointer. If any session file exists (even with an empty or different pointer), the degraded path is skipped.

### Session Runtime Mechanism

`resolve_active_task()` is imported from `common.active_task`. The `session_runtime_has_any_current_task()` function (lines 172-183) scans `.trellis/.runtime/sessions/*.json` for any session with a non-empty `current_task` field.

### When Can the Task Be Lost?

The scenario described in the issue:

1. `task.py start` in "degraded mode" changes `task.json.status` to `in_progress`
2. But does NOT persist an active-task pointer in the session runtime
3. `workflow-state.py route` depends on `resolve_active_task()` to find the current task

**Analysis**: The degraded fallback (`degraded-active-task.json`) exists precisely for this scenario. If:
- No session files exist with a current_task pointer
- AND `degraded-active-task.json` exists with a valid task reference

Then `route` will find the task via the degraded path.

**However**: If `task.py start` does NOT write `degraded-active-task.json`, and there's no session runtime, then `route` falls through to "recovery_needed" with the message: "当前 session 未解析到 active task；请先明确当前任务或重新进入目标阶段".

### Existing Fallback Mechanisms

1. **`degraded-active-task.json`**: Explicit degraded pointer file
2. **`repair` subcommand**: Infers stage from artifacts when state is missing
3. **`recovery_needed` action**: Returns a JSON result indicating the user needs to manually re-select the task

### Source Files Involved

| File Path | Description |
|---|---|
| `docs/workflows/新项目开发工作流/commands/shell/workflow-state.py:186-202` | Degraded task resolution |
| `docs/workflows/新项目开发工作流/commands/shell/workflow-state.py:1077-1107` | Route's active task resolution chain |
| `docs/workflows/新项目开发工作流/commands/shell/workflow-state.py:172-183` | Session runtime check |
| `.trellis/scripts/common/active_task.py` (Trellis core, not in workflow source) | `resolve_active_task()` implementation |

## Verdict

**PARTIAL** -- The concern is partially valid but mitigated by design:

1. **The degraded fallback exists**: `resolve_degraded_task_dir()` reads `.trellis/.runtime/degraded-active-task.json` when no session has a current_task pointer.
2. **Recovery exists**: If all resolution paths fail, `route` returns `recovery_needed` with a clear message, and the `repair` subcommand can infer the stage from artifacts.
3. **Gap remains**: Whether `task.py start` actually writes `degraded-active-task.json` was not verifiable from the workflow source alone (it's in Trellis core's `task.py`, not in the workflow source). If `task.py start` does NOT write this file, then in a degraded scenario (no session runtime, task status advanced), the route would fall to `recovery_needed`.

The issue describes a real design tension: `task.json.status` can advance independently of the session-scoped active-task pointer. But the workflow has explicit fallback mechanisms for this scenario.

### Proposed Fix Scope

If `task.py start` does not write `degraded-active-task.json`:
1. `task.py start` (Trellis core, not workflow source): Should write `degraded-active-task.json` as a side effect when operating outside a session context.

If `task.py start` does write it:
2. This is a non-issue; the fallback works as designed.

## Caveats / Not Found

- `task.py start`'s implementation is in Trellis core (`.trellis/scripts/task.py`), which was not read in this research. The behavior of `task.py start` in degraded mode is assumed based on the issue description.
- The `recovery_needed` action is not a silent failure -- it explicitly tells the user to re-select the task. So the worst case is a minor UX inconvenience, not data loss.
