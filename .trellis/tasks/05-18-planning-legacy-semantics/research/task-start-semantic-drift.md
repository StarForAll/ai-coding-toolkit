# Research: task.py create / start Semantic Drift in Embedded Workflow

- **Query**: Investigate the task.py create / task.py start semantic drift in the embedded workflow
- **Scope**: mixed (internal code + embedded project + source workflow)
- **Date**: 2026-05-18

## Findings

### 1. task.py create -- What It Actually Does

**File**: `/tmp/trellis-0.5.17-2/.trellis/scripts/common/task_store.py`

`cmd_create()` (line 145-318):

1. **Sets `status=planning`** on the new task.json (line 212): `"status": "planning"`
2. **Auto-activates the new task** (lines 270-297): When session identity is available, calls `set_active_task(rel_dir, repo_root)` so "the per-turn breadcrumb fires planning state."
   - Comment at line 270: `# Auto-activate the new task so the per-turn breadcrumb fires planning state.`
3. **Patched with preserve-parent-active** (line 277): `# [workflow-embed-patch:preserve-parent-active-task]`
   - When `TRELLIS_PRESERVE_ACTIVE_TASK=1` AND `args.parent` is truthy, skips auto-activate to keep parent as active task.
4. **Seeds implement.jsonl / check.jsonl** for sub-agent-capable platforms (lines 240-246)
5. **Prints "Next steps"** telling user to create prd.md then run `task.py start` (lines 301-312)

Key semantic: `create` sets `status=planning` and auto-activates. It does NOT set `status=in_progress`. The status flip to `in_progress` is `start`'s job.

### 2. task.py start -- What It Actually Does

**File**: `/tmp/trellis-0.5.17-2/.trellis/scripts/task.py`

`cmd_start()` (line 70-160):

**Normal path (session identity available, lines 137-157):**
1. Calls `set_active_task(task_dir, repo_root)` -- refreshes the per-session active-task pointer
2. Checks if task.json has `status == "planning"` (line 145)
3. **Strong-gate branch** (lines 146-147): If `workflow-state.json` exists in the task dir, PRINTS a warning and **SKIPS** the `planning -> in_progress` flip
4. **Legacy branch** (lines 148-151): If no `workflow-state.json`, FLIPS `status` from `planning` to `in_progress` in task.json

**Degraded path (no session identity, lines 95-135):**
1. Prints warning about degraded mode
2. Writes `.trellis/.runtime/degraded-active-task.json` fallback file (lines 112-121)
3. Same strong-gate check for status flip (lines 126-133)
4. Same legacy `planning -> in_progress` flip if no workflow-state.json (lines 130-133)

**Key semantic**: `start` does TWO things: (a) set/refresh active-task pointer, and (b) conditionally flip `task.json.status` from `planning` to `in_progress`. Under strong-gate, (b) is skipped when `workflow-state.json` exists.

### 3. The Strong-Gate Patch Applied to task.py

**Source patch file**: `/ops/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/commands/shell/patch-task-start-strong-gate.py`

This patch is applied by `_apply_patch_task_start()` in `install-workflow.py` (line 1419).

The patch modifies the original baseline `cmd_start()` code from:
```python
if data and data.get("status") == "planning":
    data["status"] = "in_progress"
    if write_json(task_json_path, data):
        print(colored("Status: planning -> in_progress", Colors.GREEN))
```

To:
```python
# [workflow-embed-patch:strong-gate-no-status-flip]
if data and data.get("status") == "planning":
    if (full_path / "workflow-state.json").is_file():
        print(colored("...skipping task.json status flip...", Colors.YELLOW))
    else:
        data["status"] = "in_progress"
        if write_json(task_json_path, data):
            print(colored("Status: planning -> in_progress", Colors.GREEN))
```

The patch is applied to BOTH occurrences of the status-flip code in `cmd_start()` (normal path at ~line 144, degraded path at ~line 126).

### 4. The Preserve-Active Patch Applied to task_store.py

**Source patch file**: `/ops/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/commands/shell/patch-task-create-preserve-active.py`

Applied by `_apply_patch_task_create_preserve_active()` in `install-workflow.py` (line 1527).

Modifies the auto-activate block in `cmd_create()` to add an opt-in guard:
- When `TRELLIS_PRESERVE_ACTIVE_TASK=1` AND `--parent` is provided, skip auto-activate
- Otherwise, proceed with `resolve_context_key()` -> `set_active_task()` as before

### 5. task_queue.py -- Planning Status Queries

**File**: `/tmp/trellis-0.5.17-2/.trellis/scripts/common/task_queue.py`

- `list_pending_tasks()` (line 74-83): Hard-codes `list_tasks_by_status("planning", repo_root)`, mapping "pending" = "planning"
- This is a query-only module; it does not write status. It simply filters by `status == "planning"`
- No legacy breadcrumb references; no strong-gate awareness

### 6. workflow.md -- Documentation vs Implementation Analysis

**File**: `/tmp/trellis-0.5.17-2/.trellis/workflow.md`

**Current-task mechanism paragraph (line 76)**:
> `task.py start` always refreshes the active-task pointer for the current session; in strong-gate installs, if the active task already has `workflow-state.json`, patched `task.py start` does **not** treat `task.json.status` as the stage source of truth and may skip the legacy `planning -> in_progress` flip.

This accurately describes the patched behavior.

**no_task block (lines 404-410)**:
Line 407 (personal profile flow):
> (1) `task.py create "<title>"` -> (2) `trellis-brainstorm` -> (3) `task.py start <task-dir>`

Line 408:
> `task.py start` in this branch only persists or repairs the active-task pointer for the current session. It does **not** advance `workflow-state.json.stage`; stage changes must still be performed via `workflow-state.py set` after the current stage reaches `awaiting_user_confirmation`.

**Semantic drift identified**: The no_task block describes `task.py start` as "only persists or repairs the active-task pointer" -- but the ACTUAL code in `cmd_start()` still does the `planning -> in_progress` flip when `workflow-state.json` is NOT present. The documentation implies `start` never changes status, but in reality:

- **Without** `workflow-state.json` (e.g., early brainstorm before any stage is set, or non-strong-gate installs): `start` DOES flip `planning -> in_progress`
- **With** `workflow-state.json` (strong-gate installs after feasibility creates the state file): `start` does NOT flip status

The documentation at line 408 is accurate for strong-gate installs but incomplete -- it does not mention that the legacy flip still occurs when no `workflow-state.json` exists. This could mislead someone debugging a non-strong-gate scenario or a pre-feasibility flow.

### 7. Baseline vs Strong-Gate Workflow Task Mechanism Text

**Baseline version** (install-workflow.py lines 190-203):
> `task.py start` writes the same pointer (idempotent if already set) and flips `task.json.status` from `planning` to `in_progress`.

**Strong-gate version** (install-workflow.py lines 204-219):
> `task.py start` always refreshes the active-task pointer for the current session; in strong-gate installs, if the active task already has `workflow-state.json`, patched `task.py start` does **not** treat `task.json.status` as the stage source of truth and may skip the legacy `planning -> in_progress` flip.

The baseline text says `start` "flips status." The strong-gate text says `start` "may skip the flip." The embedded workflow.md (line 76) uses the strong-gate version.

### 8. Source Workflow Files Mapping

| Embedded File | Source Equivalent |
|---|---|
| `.trellis/scripts/task.py` | Baseline from Trellis distribution; patched at install time |
| `.trellis/scripts/common/task_store.py` | Baseline from Trellis distribution; patched at install time |
| `.trellis/scripts/common/task_queue.py` | Baseline from Trellis distribution; no patch applied |
| `.trellis/scripts/common/active_task.py` | Baseline from Trellis distribution; no patch applied |
| `.trellis/workflow.md` | Built from baseline + patches injected by install-workflow.py |
| Patch: strong-gate no-status-flip | `docs/workflows/.../commands/shell/patch-task-start-strong-gate.py` |
| Patch: preserve-parent-active | `docs/workflows/.../commands/shell/patch-task-create-preserve-active.py` |
| Patch: workflow.md content | `docs/workflows/.../commands/workflow-patch-projectization.md` |
| Patch: workflow.md no_task block | Extracted from `workflow-patch-projectization.md` via `<!-- workflow-projectization-no-task-patch -->` marker |
| Patch: workflow.md mechanism paragraph | Replaced by `_replace_workflow_task_mechanism()` in install-workflow.py |

### 9. Install Workflow Patch Application Order (relevant patches)

From `install-workflow.py`:
1. `_apply_patch_task_start()` (line 1419) -- patches `task.py` with strong-gate no-status-flip
2. `_apply_patch_task_create_preserve_active()` (line 1527) -- patches `common/task_store.py` with preserve-parent-active
3. `_replace_workflow_task_mechanism()` (line 1066) -- replaces baseline mechanism paragraph in workflow.md
4. `inject_workflow_no_task_patch()` (line 1276) -- replaces baseline no_task block in workflow.md
5. `inject_workflow_breadcrumb_patch()` (line 1329) -- injects strong-gate breadcrumb blocks
6. `inject_workflow_phase_index_patch()` (line 1197) -- replaces Phase Index section
7. `_apply_patch_workflow_phase()` -- patches `workflow_phase.py` with strong-gate redirect

### 10. Semantic Drift Summary

| Aspect | What Docs Say | What Code Actually Does |
|---|---|---|
| `task.py create` status | Creates task with `status=planning` | Correct: line 212 sets `"status": "planning"` |
| `task.py create` auto-activate | Auto-sets per-session active-task pointer | Correct: lines 290-295, `set_active_task()` |
| `task.py start` primary purpose | "persists or repairs the active-task pointer" (no_task block, line 408) | Partially correct: it sets active-task pointer AND conditionally flips status |
| `task.py start` status flip (strong-gate) | "may skip the legacy `planning -> in_progress` flip" (line 76) | Correct: skips when `workflow-state.json` exists (lines 126, 146) |
| `task.py start` status flip (legacy) | Not mentioned in no_task block | Still flips `planning -> in_progress` when no `workflow-state.json` (lines 130-133, 149-151) |
| `task.py start` and stage advancement | "does **not** advance `workflow-state.json.stage`" (line 408) | Correct: `start` never touches `workflow-state.json` |
| `task.py start` as "stage transition" | Some older docs/use may treat start as stage transition | Start is NOT a stage transition; only `workflow-state.py set` advances stages |

**Key drift**: The no_task block's description of `task.py start` as "only persists or repairs the active-task pointer" omits the conditional status flip. This is accurate for strong-gate installs where `workflow-state.json` exists (feasibility creates it), but is misleading for:
- Pre-feasibility moments where `task.py start` runs before `workflow-state.json` is created
- Non-strong-gate installs (if any exist)
- Debugging scenarios where someone traces through `cmd_start()` and sees the flip logic

## Caveats / Not Found

- No baseline (unpatched) `task.py` was found in the main repo at `/ops/projects/personal/ai-coding-toolkit/` -- the baseline is apparently distributed via the Trellis package and patched only at the target project. The source patch files and install-workflow.py are the canonical source of truth for understanding the delta.
- The `start-patch-phase-router.md` and `start-skill-patch-phase-router.md` files describe the old `status=planning/in_progress` routing as "deprecated" but do not describe what `task.py start` does to status -- they describe the start SKILL (trellis-start/continue), not the `task.py start` command.
- `task_queue.py`'s `list_pending_tasks()` still maps "pending" to `"planning"` status, which is a minor naming inconsistency but not a functional drift since `task.json.status` retains "planning" under strong-gate until explicitly changed.
