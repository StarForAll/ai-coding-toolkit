# Research: Issue 3 - Strong gate state machine not connected to per-turn hook

- **Query**: Does the per-turn hook use workflow-state.json's stage, or only task.json.status?
- **Scope**: Internal
- **Date**: 2026-05-16

## Findings

### Core Discovery: Hook does NOT read workflow-state.json

The per-turn hook (`inject-workflow-state.py`) operates on a completely different data source than `workflow-state.py route`:

| Component | Data Source | What it reads |
|-----------|------------|---------------|
| `workflow-state.py route` | `task_dir/workflow-state.json` | `stage`, `stage_status`, `checkpoints`, `allowed_next_stages` |
| `inject-workflow-state.py` (hook) | `task_dir/task.json` | `id`, `status` (e.g. "planning", "in_progress") |

### Evidence Chain

1. **Hook reads only task.json** (`inject-workflow-state.py:169-193`):
   ```python
   def get_active_task(root, input_data) -> Optional[tuple[str, str, str]]:
       """Return (task_id, status, source) from the current active task."""
       ...
       task_json = task_dir / "task.json"
       data = json.loads(task_json.read_text(encoding="utf-8"))
       task_id = data.get("id") or task_dir.name
       status = data.get("status", "")
       return task_id, status, active.source
   ```
   The function returns `(task_id, status, source)` where `status` comes from `task.json.status`.

2. **Hook breadcrumb selection** (`inject-workflow-state.py:346-360`):
   ```python
   task = get_active_task(root, data)
   if task is None:
       no_task_key = resolve_breadcrumb_key("no_task", platform, config)
       breadcrumb = build_breadcrumb(None, "no_task", templates, ...)
   else:
       task_id, status, source = task
       status_key = resolve_breadcrumb_key(status, platform, config)
       breadcrumb = build_breadcrumb(task_id, status, templates, source, ...)
   ```
   The `status` here is `task.json.status`, NOT `workflow-state.json.stage`.

3. **Breadcrumb templates** (`inject-workflow-state.py:200-230`):
   Templates are loaded from `workflow.md` via `[workflow-state:STATUS]` tags. Available tags are:
   - `[workflow-state:no_task]`
   - `[workflow-state:planning]`
   - `[workflow-state:planning-inline]` (Codex inline mode)
   - `[workflow-state:in_progress]`
   - `[workflow-state:in_progress-inline]` (Codex inline mode)
   - `[workflow-state:completed]` (dead, never used)

4. **Codex inline mode mapping** (`inject-workflow-state.py:273-295`):
   When `platform == "codex"` and `dispatch_mode == "inline"`, the hook appends `-inline` to the status:
   - `planning` -> `planning-inline`
   - `in_progress` -> `in_progress-inline`
   For non-Codex platforms, the status is used as-is.

### workflow-state.json stage values vs task.json status values

**workflow-state.json stages** (from `workflow-state.py:60-73`):
`feasibility`, `brainstorm`, `design`, `plan`, `implementation`, `test-first`, `project-audit`, `check`, `review-gate`, `finish-work`, `delivery`, `record-session`

**task.json statuses** (from `task.py` conventions):
`planning`, `in_progress`, `completed`, `blocked`, etc.

**workflow.md tag names** (from embedded `/tmp/trellis-0.5.16-2/.trellis/workflow.md:121-126`):
`no_task`, `planning`, `in_progress`, `completed`

### The Disconnect

When `workflow-state.py route` detects the task is in stage `design` with `stage_status=in_progress`, the breadcrumb hook still reads `task.json.status` which could be just `planning` or `in_progress`. The hook has NO awareness of the fine-grained stage from `workflow-state.json`.

Result:
- Tasks in `design`/`plan`/`check` stages all get the same `in_progress` breadcrumb template
- Tasks in `feasibility`/`brainstorm` stages all get the same `planning` breadcrumb template
- The hook cannot differentiate between design-in-progress and plan-in-progress

### Source Files Involved

| File Path | Description |
|---|---|
| `docs/workflows/新项目开发工作流/commands/shell/workflow-state.py` | Strong-gate state machine; reads workflow-state.json |
| `docs/workflows/新项目开发工作流/commands/install-workflow.py` | Installs hooks; does not bridge stage to hook |
| `docs/workflows/新项目开发工作流/命令映射.md` | Defines stage mapping but does not address hook granularity |

Embedded target files (installed by `install-workflow.py`):
| File Path | Description |
|---|---|
| `.codex/hooks/inject-workflow-state.py` | Per-turn hook (Codex) |
| `.claude/hooks/inject-workflow-state.py` | Per-turn hook (Claude) |

### Related Specs

- `.trellis/spec/` — No spec currently governs the hook-to-stage bridge.

## Verdict

**REAL** -- The per-turn hook (`inject-workflow-state.py`) reads ONLY `task.json.status` to select breadcrumbs. It does NOT read `workflow-state.json`'s `stage` field. This means when the strong-gate state machine puts a task in `design`, `plan`, `check`, or `review-gate`, the hook still selects breadcrumbs based on the coarse `task.json.status` value (typically `planning` or `in_progress`). The workflow has 12 distinct stages but the hook only supports 3 breadcrumb states (`no_task`, `planning`, `in_progress`).

### Proposed Fix Scope

1. `inject-workflow-state.py` (both `.codex/hooks/` and `.claude/hooks/` copies): Add fallback logic to read `workflow-state.json`'s `stage` field when available, and use it to select a more specific breadcrumb.
2. `.trellis/workflow.md` (the embedded workflow.md in target projects): Add more `[workflow-state:STAGE]` tag blocks for the fine-grained stages (`design`, `plan`, `check`, etc.).
3. `install-workflow.py` (the installer): Ensure the updated hook is deployed correctly.

## Caveats / Not Found

- The hook's template loading from `workflow.md` is intentional single-source-of-truth design. Adding more tags is the clean approach.
- The hook file is written by `install-workflow.py` and is NOT under source control in the target project (it's generated). The source template lives in `commands/install-workflow.py` or a separate template mechanism.
