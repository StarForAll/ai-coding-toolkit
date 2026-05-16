# Research: Issue 2 - First entry bypasses feasibility

- **Query**: Does the Codex per-turn hook bypass feasibility by injecting no_task block's A/B/C rules instead of routing to feasibility?
- **Scope**: Internal
- **Date**: 2026-05-16

## Findings

### Files Found

| File Path | Description |
|---|---|
| `/ops/.../commands/shell/workflow-state.py` (lines 1080-1160) | Route logic in workflow-state.py |
| `/tmp/trellis-0.5.16-2/.trellis/workflow.md` (lines 158-162) | no_task breadcrumb block |
| `/tmp/trellis-0.5.16-2/.claude/hooks/inject-workflow-state.py` | Claude hook -- identical to Codex hook |
| `/tmp/trellis-0.5.16-2/.codex/hooks/inject-workflow-state.py` | Codex hook -- identical to Claude hook |

### Analysis

#### workflow-state.py route logic (line 1099-1100)

When no task exists and no tasks have been created yet:
```python
if not has_any_task:
    _route_result("feasibility", "first_entry", "当前 session 尚无 active task，首次进入 feasibility")
```

This correctly returns `action=first_entry, target=feasibility`. The `/trellis:continue` command correctly routes this to `/trellis:feasibility`.

#### Hook behavior (both Claude and Codex hooks are identical)

The hook's `main()` function (line 328-387):
1. Resolves active task via `get_active_task()`
2. If no task found (`task is None`): builds breadcrumb with status `"no_task"`
3. The breadcrumb key is resolved via `resolve_breadcrumb_key("no_task", platform, config)`
4. On Codex with inline mode, this becomes `"no_task-inline"` (which does NOT exist in workflow.md, so it falls back to `"no_task"`)
5. The hook reads the `[workflow-state:no_task]` block from workflow.md and injects it

#### The no_task breadcrumb block (workflow.md lines 158-162)

```
[workflow-state:no_task]
No active task.
**A Direct answer** — pure Q&A...
**B Create a task** — Entry sequence: (1) load `feasibility` skill ... (2) if assessment allows, load `trellis-brainstorm` skill ...
**C Inline change** ...
[/workflow-state:no_task]
```

This block DOES mention feasibility as step (1) in option B. So the hook IS injecting text that says "load feasibility first."

#### The Codex bootstrap notice (hook lines 85-99)

For Codex with no active task, the hook also injects `CODEX_NO_TASK_BOOTSTRAP_NOTICE` which says:
> "route the user's request per the <workflow-state> A/B/C rules below."

This explicitly refers to the A/B/C rules in the no_task breadcrumb.

### Verdict: PARTIAL

**What works correctly:**
1. `workflow-state.py route` correctly returns `feasibility` as the first_entry target
2. The `/trellis:continue` command correctly routes `first_entry` to `/trellis:feasibility`
3. The `no_task` breadcrumb DOES mention feasibility as the first step (option B, step 1)

**The actual gap:**
1. The hook injects the `no_task` block on EVERY user turn when there is no active task -- not just when `/trellis:continue` is called
2. The `no_task` block presents THREE options (A/B/C) with feasibility buried inside option B's sub-step
3. For a first-time user who just describes work, the AI sees the A/B/C triage and may choose option B but skip to `task.py create + trellis-brainstorm` (the old flow), especially because:
   - Option B says "load feasibility skill to evaluate" but the **heading** says "Create a task"
   - A model might focus on the "Create a task" heading and jump to brainstorm
4. The Codex bootstrap notice explicitly says "route per A/B/C rules" -- reinforcing the triage rather than routing to feasibility
5. There is no `no_task-inline` tag in workflow.md, so Codex inline mode falls back to the same `no_task` block

**Key distinction:** The `workflow-state.py route` command and `/trellis:continue` command DO correctly route to feasibility. But the **per-turn hook injection** (which fires on every user prompt, not just on `/trellis:continue`) presents the old A/B/C triage that can lead to bypassing feasibility.

### Source files involved

- `docs/workflows/新项目开发工作流/commands/shell/workflow-state.py` -- route logic is correct
- The workflow.md template's `[workflow-state:no_task]` block -- the triage text buries feasibility inside option B
- The hook source (`inject-workflow-state.py`) -- generated from shared source; correctly reads workflow.md

### Proposed fix scope

1. **workflow.md `[workflow-state:no_task]` block**: Consider restructuring to make feasibility the explicit first step, rather than burying it inside option B. For example, the first instruction could be "If no assessment.md exists, route to feasibility first" before presenting A/B/C.
2. **Codex bootstrap notice**: Consider updating to mention feasibility as the default first step for new work, not just "route per A/B/C rules."

## Caveats / Not Found

- The issue is not that feasibility is absent from the hook output -- it IS mentioned. The issue is that it's buried inside a multi-option triage where a model might skip it.
- This only affects the per-turn hook path, not the `/trellis:continue` command path.
