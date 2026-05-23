# Research: Workflow Embedding Impact on Trellis Hooks/Commands/Skills

- **Query**: Depth analysis of how the "新项目开发工作流" embedding affects native trellis hooks, commands, and skills
- **Scope**: Internal (comparative file analysis)
- **Date**: 2026-05-23

## Findings

### 1. Hooks

#### Native Trellis Hooks (pure framework)

| File Path | Description |
|---|---|
| `.trellis/scripts/hooks/linear_sync.py` | Lifecycle hook syncing task events to Linear via `linearis` CLI; binds to `after_create`/`after_start`/`after_archive` |
| `.trellis/config.yaml` (hooks section) | Declares `after_create`/`after_start`/`after_finish`/`after_archive` as configurable lifecycle hooks |
| `workflow.md` (breadcrumb contract) | Defines 4 `[workflow-state:STATUS]` blocks: `no_task`, `planning`, `in_progress`, `completed` |
| `.trellis/spec/frontend/hook-guidelines.md` | Placeholder template for project hook conventions |

#### Workflow-Embedded Hooks (embedded framework)

The embedded framework does NOT add new hook files in `.trellis/scripts/hooks/`. Instead, it uses **6 runtime patcher scripts** that modify existing native hook/script behavior at install time:

| Patcher Script | Target | Description |
|---|---|---|
| `patch-inject-workflow-state.py` | `.claude/hooks/inject-workflow-state.py` + `.opencode/hooks/inject-workflow-state.js` | Replaces `get_active_task()` and `build_breadcrumb()` functions to route through `workflow-state.py route` instead of reading `task.json.status` directly |
| `patch-session-start-strong-gate.py` | `.claude/hooks/session-start.py` | Replaces `_get_task_status()` tail logic with `workflow-state.py route` delegation; removes legacy READY auto-continue instruction |
| `patch-task-start-strong-gate.py` | `.trellis/scripts/task.py` `cmd_start()` | Removes `planning -> in_progress` status flip; prints "skipping legacy status flip" instead |
| `patch-task-create-preserve-active.py` | `.trellis/scripts/common/task_store.py` | Adds `TRELLIS_PRESERVE_ACTIVE_TASK=1` guard so child task creation does not silently switch active task |
| `patch-task-status-view-strong-gate.py` | `.trellis/scripts/common/tasks.py` + `task_queue.py` + `task.py` | Replaces status display: `task.json.status` -> `workflow-state.json.stage`; adds `repair_needed` for missing state; adds `_workflow_display_extra` to task list output |
| `patch-workflow-phase.py` + `patch-workflow-phase-strong-gate.py` | `.trellis/scripts/common/workflow_phase.py` `get_step()` | Rejects legacy `#### X.Y` step lookups when strong-gate `workflow-state.json` is present |

Additionally, the embedded `workflow.md` **replaces** the 4 native breadcrumb blocks with **14** strong-gate breadcrumb blocks:

| Breadcrumb Key | Purpose | Native Equivalent |
|---|---|---|
| `feasibility` | First project assessment gate | NONE (new) |
| `brainstorm` | Requirement discovery and PRD iteration | `planning` (partial overlap) |
| `design` | Architecture and design document creation | NONE (new) |
| `plan` | Task decomposition and scheduling | NONE (new) |
| `implementation` | Code writing phase | `in_progress` (overlap) |
| `project-audit` | Full-project quality review | NONE (new) |
| `check` | Quality check against spec | NONE (new) |
| `review-gate` | Multi-CLI supplementary review | NONE (new) |
| `delivery` | Project handover and deployment | `completed` (partial overlap) |
| `awaiting_confirmation` | Confirmation boundary stop | NONE (new) |
| `awaiting_confirmation_with_blockers` | Confirmation with blockers | NONE (new) |
| `blocked` | Do not continue executing | NONE (new) |
| `context_needed` / `recovery_needed` / `repair_needed` / `embed_invalid` | Routing error states | NONE (new) |
| `workflow-state.route_failed` | Route helper failure | NONE (new) |

#### Hook Analysis: Overlap / Conflict / Coverage

1. **`linear_sync.py`** -- Identical in both; NOT modified by embedding. No conflict.

2. **`inject-workflow-state` hook (Python + JS)** -- **INVASIVE**: The patcher completely replaces `get_active_task()` and `build_breadcrumb()` function bodies. The original code read `task.json.status` to determine breadcrumb key; the patched code calls `workflow-state.py route` as subprocess, then maps route actions/stages to breadcrumb keys. This is a **full replacement** of the native breadcrumb routing logic, not an addition. Impact: HIGH -- the native `planning`/`in_progress`/`completed` status-to-breadcrumb mapping is completely superseded.

3. **`session-start` hook** -- **INVASIVE**: The patcher replaces the `_get_task_status()` tail after `task_status = task_data.get("status")`. The original code used PLANNING/READY/COMPLETED status routing; the patched code delegates to `workflow-state.py route` and surfaces STRONG-GATE status. Also removes "If a task is READY, execute its Next required action without asking" instruction. Impact: HIGH -- startup behavior fundamentally changed; no longer auto-continues on READY.

4. **`task.py cmd_start()`** -- **INVASIVE**: The original code flips `task.json.status` from `planning` to `in_progress` on `task.py start`. The patched code **skips this flip entirely**, printing a yellow warning instead. This means `task.json.status` stays at `planning` indefinitely under strong-gate; `workflow-state.json.stage` becomes the only progress indicator. Impact: HIGH -- breaks any downstream tool that reads `task.json.status` to determine progress phase.

5. **`task_store.py cmd_create()`** -- **SUPPLEMENTARY**: Adds a conditional guard (`TRELLIS_PRESERVE_ACTIVE_TASK=1`) to prevent active-task switching when creating child tasks. The original auto-activate still runs when the guard is not set. Impact: LOW -- additive, no overlap.

6. **`tasks.py` / `task_queue.py` / `task.py` (status views)** -- **INVASIVE**: Replaces raw `task.json.status` display with `workflow-state.json.stage` display. The `_display_status()` function returns `repair_needed` when `workflow-state.json` is missing, which is a **breaking change** -- previously, a task with `status=planning` and no `workflow-state.json` would display as "planning"; now it displays as "repair_needed". Impact: HIGH -- any task not initialized with `workflow-state.json` will show as broken.

7. **`workflow_phase.py get_step()`** -- **INVASIVE**: Rejects legacy `#### X.Y` step lookups when a strong-gate stage is detected. Returns empty string instead of the step content. Impact: MEDIUM -- `get_context.py --mode phase --step X.Y` stops working for strong-gate projects.

---

### 2. Commands

#### Native Trellis Commands (from `workflow.md` Skill Routing)

| Command | Purpose |
|---|---|
| `brainstorm` | Requirement exploration (maps to `trellis-brainstorm` skill) |
| `check` | Quality check (maps to `trellis-check` skill / sub-agent) |
| `continue` | Resume current task phase |
| `finish-work` | Archive task + record session |
| `start` | Start/activate task |
| `implement` | (Sub-agent dispatch, maps to `trellis-implement`) |
| `update-spec` | (Maps to `trellis-update-spec` skill) |
| `break-loop` | (Maps to `trellis-break-loop` skill) |
| `before-dev` | (Maps to `trellis-before-dev` skill) |

#### Workflow-Embedded Commands (from `workflow-installed.json`)

Per `workflow-installed.json`, the embedding defines:

**overlay_commands** (replace native behavior):
- `brainstorm` -- overlays native `trellis-brainstorm` with stage-gated version
- `check` -- overlays native `trellis-check` with stage-gated version

**added_commands** (new commands):
- `feasibility`
- `design`
- `plan`
- `project-audit`
- `review-gate`
- `delivery`

**disabled_commands** (native commands explicitly disabled):
- `parallel` -- replaced with `parallel-disabled.md` stub

**patched_baseline_commands** (native commands whose behavior is modified):
- `continue` -- patched via `start-patch-phase-router.md` to use `workflow-state.py route` instead of `status=planning`/`status=in_progress` routing
- `finish-work` -- patched via `finish-work-patch-projectization.md` to add code quality checklist

**patched_codex_skills**:
- `trellis-continue`, `trellis-finish-work`, `trellis-start`

**patched_shared_docs**:
- `workflow.md` -- the entire Phase Index section is replaced

**critical_runtime_patches**:
- `inject-workflow-state`, `session-start-strong-gate`, `task-start-strong-gate`, `task-create-preserve-active`, `task-status-view-strong-gate`, `workflow-phase-strong-gate`

#### Command Analysis: Overlap / Conflict / Coverage

1. **`brainstorm`** -- **OVERLAY**: The workflow's `brainstorm.md` replaces the native `trellis-brainstorm` skill. The native version is a generic requirements discovery tool; the workflow version adds stage-gate validation, `assessment.md` bootstrapping, and execution-card awareness. Impact: MEDIUM -- extended functionality but the underlying skill is replaced.

2. **`check`** -- **OVERLAY**: The workflow's `check.md` replaces the native `trellis-check` skill. The workflow version adds `check-quality.py` integration, project-specific verification commands, and stage-gate transition awareness. Impact: MEDIUM -- extended functionality but the underlying skill is replaced.

3. **`continue`** -- **PATCHED**: The `start-patch-phase-router.md` replaces native Steps 1-4 (Load Current Context, Load Phase Index, Decide Where You Are, Load Specific Step) with `workflow-state.py route`-based routing. Impact: HIGH -- the entire phase navigation logic is replaced.

4. **`finish-work`** -- **PATCHED**: The `finish-work-patch-projectization.md` adds code quality checklist requirements before archive. Impact: LOW -- additive warning, does not replace core behavior.

5. **`start`** -- **PATCHED**: The `start-skill-patch-phase-router.md` replaces Steps 1-4 of the `trellis-start` skill with strong-gate routing. Impact: HIGH -- the entire phase navigation logic is replaced.

6. **`parallel`** -- **DISABLED**: Replaced with a stub command that says "parallel is disabled in this workflow". Impact: MEDIUM -- removes a native capability.

7. **New commands** (`feasibility`, `design`, `plan`, `project-audit`, `review-gate`, `delivery`) -- **SUPPLEMENTARY**: These are entirely new workflow stages with no native equivalents. No overlap.

---

### 3. Skills

#### Native Trellis Skills (from `workflow.md` Skill Routing)

| Skill | Purpose |
|---|---|
| `trellis-brainstorm` | Interactive requirements discovery |
| `trellis-implement` | Sub-agent for code implementation |
| `trellis-check` | Quality check sub-agent |
| `trellis-research` | Research sub-agent |
| `trellis-before-dev` | Pre-development spec loading (inline mode) |
| `trellis-update-spec` | Spec update after task completion |
| `trellis-break-loop` | Debug retrospective for recurring issues |

#### Workflow-Embedded Skills

The workflow embeds skills through command `.md` files (not a separate skills/ directory). The mapping is:

| Workflow Command | Skill Mapping | Relationship to Native |
|---|---|---|
| `feasibility` | New skill (no native equivalent) | SUPPLEMENTARY |
| `brainstorm` | Replaces `trellis-brainstorm` | OVERLAY |
| `design` | New skill (no native equivalent) | SUPPLEMENTARY |
| `plan` | New skill (no native equivalent) | SUPPLEMENTARY |
| `check` | Replaces `trellis-check` | OVERLAY |
| `project-audit` | New skill (no native equivalent) | SUPPLEMENTARY |
| `review-gate` | New skill (no native equivalent) | SUPPLEMENTARY |
| `delivery` | New skill (no native equivalent) | SUPPLEMENTARY |

The workflow does NOT embed:
- `trellis-implement` -- this sub-agent skill is still used inside the `implementation` stage
- `trellis-before-dev` -- still used for inline dispatch mode
- `trellis-update-spec` -- still used in Phase 3.3
- `trellis-break-loop` -- still used for debug retrospective
- `trellis-research` -- still used for research in Phase 1.2

#### Skill Analysis: Overlap / Conflict / Coverage

1. **`brainstorm` overlaying `trellis-brainstorm`** -- The workflow version extends the native skill with: `assessment.md` bootstrapping, execution-card obligations, watermark/ownership proof awareness, and stage-gate transition protocol. The core brainstorm loop (one question at a time, research before asking, update prd.md immediately) is preserved. Impact: MEDIUM -- additive features but the skill entry point is replaced.

2. **`check` overlaying `trellis-check`** -- The workflow version adds: `check-quality.py` script integration, frozen verification matrix execution, `workflow-state.py set` for stage transition, delivery/control validation. The core check logic (review against spec, run lint/typecheck, fix issues) is preserved. Impact: MEDIUM -- additive features but the skill entry point is replaced.

3. **No other skills are overlapped** -- `trellis-implement`, `trellis-before-dev`, `trellis-update-spec`, `trellis-break-loop`, `trellis-research` remain unchanged and are still referenced in the embedded `workflow.md`.

---

### 4. Overall Assessment

#### Nature of Embedding: Primarily INVASIVE

The workflow embedding is **NOT purely supplementary**. While it adds 6 new commands (`feasibility`, `design`, `plan`, `project-audit`, `review-gate`, `delivery`) that are genuinely new capabilities, the core runtime behavior is fundamentally altered:

| Aspect | Native Trellis | Embedded Workflow | Change Type |
|---|---|---|---|
| Task progress source of truth | `task.json.status` (`planning`/`in_progress`/`completed`) | `workflow-state.json.stage` (9 stages) | **Replacement** |
| Breadcrumb routing | `task.json.status` -> one of 4 tags | `workflow-state.py route` -> one of 14+ tags | **Replacement** |
| `task.py start` behavior | Flips `planning` -> `in_progress` | No status flip; prints warning | **Behavior removal** |
| Session startup | Auto-continue on READY | No auto-continue; delegates to route | **Behavior removal** |
| Phase step lookup | `get_context.py --mode phase --step X.Y` works | Disabled when strong-gate stage detected | **Capability removal** |
| Task list status display | Shows `planning`/`in_progress` | Shows stage name from `workflow-state.json` | **Replacement** |
| Pending task list | `status=planning` subset | All non-archived tasks | **Semantic change** |
| `parallel` command | Available | Disabled with stub | **Capability removal** |

#### Specific Redundancy / Conflict Items

1. **File**: `.trellis/scripts/task.py` (line 111-131 in embedded)
   **Issue**: `cmd_start()` no longer flips `task.json.status`, making `task.json.status` stale at `planning` forever
   **Impact**: HIGH -- any external tool or script reading `task.json.status` to determine task phase will get stale/wrong information

2. **File**: `.trellis/scripts/common/tasks.py` (added lines 23-67 in embedded)
   **Issue**: `_display_status()` returns `repair_needed` when `workflow-state.json` is missing, even for tasks with valid `task.json.status`
   **Impact**: HIGH -- pre-existing tasks created before the workflow was embedded will appear "broken" in task lists until manually initialized with `workflow-state.json`

3. **File**: `.trellis/scripts/common/workflow_phase.py` (added lines 108-149 in embedded)
   **Issue**: `get_step()` rejects all `#### X.Y` step lookups when strong-gate stage is present, returning empty string
   **Impact**: MEDIUM -- the `--mode phase --step` context mode becomes non-functional for strong-gate projects

4. **File**: `.trellis/workflow.md` (complete replacement of Phase Index section)
   **Issue**: The entire native 3-phase model (Plan/Execute/Finish) with 4 breadcrumb blocks is replaced with a 9-stage model with 14+ breadcrumb blocks
   **Impact**: HIGH -- the native workflow contract documented in `workflow-state-contract.md` no longer applies; AI agents reading `workflow.md` get completely different instructions

5. **File**: `inject-workflow-state.py` / `inject-workflow-state.js` (modified by patcher at install time)
   **Issue**: `get_active_task()` and `build_breadcrumb()` functions completely replaced; original functions that read `task.json.status` are gone
   **Impact**: HIGH -- the native breadcrumb resolution chain is severed; uninstalling the workflow would require restoring original hook files from backup

6. **File**: `session-start.py` (modified by patcher at install time)
   **Issue**: `_get_task_status()` tail replaced with `workflow-state.py route` delegation; READY auto-continue removed
   **Impact**: HIGH -- session startup behavior fundamentally different; AI no longer auto-continues tasks

7. **File**: `.trellis/scripts/common/task_queue.py` (line 83 modified in embedded)
   **Issue**: `list_pending()` now returns ALL non-archived tasks instead of `status=planning` subset
   **Impact**: MEDIUM -- semantic change; "pending" meaning changes from "not yet started" to "any active task"

8. **File**: `parallel` command (disabled via `parallel-disabled.md`)
   **Issue**: Native parallel/worktree dispatch capability is removed
   **Impact**: MEDIUM -- users who relied on parallel task execution lose this capability

9. **File**: `brainstorm.md` / `check.md` (overlay commands)
   **Issue**: Replace native `trellis-brainstorm` and `trellis-check` skill entry points
   **Impact**: MEDIUM -- the underlying skills still work but the entry points now have stage-gate validation and additional obligations that may block or redirect the user

## Caveats / Not Found

- No standalone `hooks/` directory was found under the workflow source (`docs/workflows/新项目开发工作流/hooks/`). The workflow does not ship its own hook files; instead, it uses patcher scripts that modify existing native hooks at install time.
- No standalone `skills/` directory was found under the workflow source. Skills are embedded via command `.md` files.
- The `.trellis/.backup-original/workflow.md` in the embedded project contains the original (pre-embedding) workflow.md, confirming that the installer preserves a backup.
- The `workflow-installed.json` is the most comprehensive record of what the embedding changed; it lists overlay_commands, added_commands, disabled_commands, patched_baseline_commands, and critical_runtime_patches.
