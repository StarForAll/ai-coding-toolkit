# Research: Recovery Path and Error Message Precision in Embedded Workflow

- **Query**: Investigate the recovery path and error message precision issue in the embedded workflow at /tmp/trellis-0.5.17-2
- **Scope**: internal
- **Date**: 2026-05-18

## Findings

### Files Found

| File Path | Description |
|---|---|
| `/tmp/trellis-0.5.17-2/.trellis/scripts/workflow/workflow-state.py` | Embedded (deployed) copy, 2014 lines, identical to source |
| `/ops/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/commands/shell/workflow-state.py` | Source workflow-state.py, 2014 lines |
| `/tmp/trellis-0.5.17-2/.trellis/workflow.md` | Embedded workflow.md, 410 lines |
| `/ops/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/阶段状态机与强门禁协议.md` | Source protocol document |
| `/ops/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/commands/workflow_assets.py` | Asset registry including HELPER_SCRIPTS list |
| `/ops/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/commands/install-workflow.py` | Install script, `deploy_helper_scripts()` copies shell/*.py to target .trellis/scripts/workflow/ |

### Core Analysis: route Function Decision Tree and Error Messages

The `cmd_route` function (line 1581-1810) follows this decision tree. Every `_route_result` call emits a JSON object with `action`, `reason`, optional `target`, `stage`, `stage_status`, `blockers`, `warnings`, `profile_hint`.

#### Step 1: embed_invalid (line 1594-1597)
- Condition: `detect_embed_invalid()` returns non-None
- Action: `embed_invalid`
- Message: varies (library-lock missing, minimum asset pack missing, critical runtime patches missing)
- **Precision: GOOD** -- specific about what infrastructure is broken

#### Step 2: Resolve active task (line 1599-1681)

##### 2a. Stale active task (line 1609-1610)
- Condition: `active.stale == True`
- Action: `repair_needed`
- Message: `"Trellis 当前活动任务已失效: {active.task_path}"`
- **Precision: MODERATE** -- identifies WHICH task is stale, but does not distinguish "task was archived" from "task directory was moved" from "session pointer is stale because you switched tasks"

##### 2b. Unresolvable active task path (line 1613-1614)
- Condition: `resolve_task_ref()` returns None or not a dir
- Action: `repair_needed`
- Message: `"无法解析当前活动任务: {active.task_path}"`
- **Precision: MODERATE** -- identifies the path that failed, but does not explain WHY or what the user should do differently

##### 2c. No active task at all, degraded fallback exists (line 1618-1620)
- Condition: `active.task_path` is empty, but `resolve_degraded_task_dir()` succeeds
- Action: implicit (falls through to Step 3 using the degraded task)
- **Precision: N/A** -- silent fallback, no message to user about using degraded path

##### 2d. No active task, no degraded fallback, no tasks exist at all (line 1622-1674)
- Condition: no session active task, no degraded fallback, `.trellis/tasks/` has no task dirs
- Action: `first_entry`
- Message: `"当前 session 尚无 active task，首次进入 feasibility"` (or brainstorm if assessment allows)
- **Precision: GOOD** -- clear about what's happening

##### 2e. No active task, no degraded fallback, tasks DO exist (line 1676-1680)
- Condition: `.trellis/tasks/` has at least one task, but no session resolves an active task
- Action: `recovery_needed`
- Message: `"当前 session 未解析到 active task；请先明确当前任务或重新进入目标阶段"`
- **Precision: LOW** -- This is the KEY problem site. The message says "clarify your task or re-enter a stage" but the most common real cause is one of:
  1. User is on the PARENT task and should switch to a CHILD (leaf) task
  2. User's session pointer was cleared by a previous `task.py finish` but they want to continue working
  3. User started a new session and the old session's active task is gone
  The message gives no hint about WHICH task(s) exist, whether any are in a resumable state, or whether the issue is "wrong task context" vs "state is corrupted"

#### Step 3: Validate resolved task (line 1683-1707)

##### 3a. Task directory does not exist (line 1684-1685)
- Action: `repair_needed`
- Message: `"当前活动任务目录不存在"`
- **Precision: MODERATE** -- doesn't say which path or what happened

##### 3b. Missing workflow-state.json (line 1690-1692)
- Action: `repair_needed`
- Message: `"缺少 workflow-state.json"`
- **Precision: MODERATE** -- doesn't explain that this likely means the task was created before the workflow was installed, or that `workflow-state.py init` can fix it

##### 3c. State shape validation failed (line 1695-1707)
- Action: `repair_needed`
- Message: first error from `validate_state_shape()` (e.g., missing fields, invalid stage)
- **Precision: MODERATE** -- the first error is shown but the full list is in blockers; the message could be more helpful about what "repair" means

#### Step 4: Route by stage (line 1709-1810)

##### 4a. Parent task with children in leaf-required stage (line 1713-1717)
- Condition: `stage_requires_leaf(stage)` is True AND `task_data.children` is non-empty
- Action: `repair_needed`
- Message: `"当前 task 已有 children"`
- **Precision: LOW** -- This is another KEY problem site. The message says "this task has children" but does NOT explain:
  1. That the user needs to `task.py start <child-task>` to switch to a leaf task
  2. Which children exist and could be selected
  3. That this is NOT a state corruption -- it's a normal operational context issue
  The action is `repair_needed` which implies something is BROKEN, when really the user just needs to switch task context.

##### 4b. Stage awaiting_user_confirmation with blockers (line 1721-1731)
- Action: `awaiting_confirmation_with_blockers`
- Message: `"当前 stage={stage}, status=awaiting_user_confirmation 但仍存在 readiness blockers"`
- **Precision: GOOD** -- blockers list is included

##### 4c. Stage awaiting_user_confirmation, no blockers (line 1733-1740)
- Action: `awaiting_confirmation`
- Message: `"当前 stage={stage}, status=awaiting_user_confirmation"`
- **Precision: GOOD**

##### 4d. Readiness blockers but not awaiting confirmation (line 1743-1752)
- Action: `blocked` (for execution stages or plan) OR `repair_needed` (for other stages)
- Message: first readiness blocker
- **Precision: MODERATE** -- for non-execution/non-plan stages, the action is `repair_needed` when it's really a readiness issue (missing docs/files), not a state corruption. The misclassification makes it seem like the state is broken when it's just incomplete.

##### 4e. Execution stage reenter (line 1755-1790)
- Action: `blocked` or `reenter`
- **Precision: GOOD** -- clear about execution authorization status

##### 4f. Non-execution stage reenter (line 1793-1810)
- Action: `reenter`
- **Precision: GOOD** -- includes optional warnings

### The `cmd_set` Function Gates (line 1275-1330)

Four sequential gates, each with a specific rejection message:

1. **allowed_next_stages gate** (line 1289-1291):
   - Message: `"阶段切换被拒绝: {current} → {pending} 不在 allowed_next_stages {allowed} 中；如需强制切换请使用 --force"`
   - **Precision: GOOD**

2. **awaiting_user_confirmation gate** (line 1294-1297):
   - Message: `"阶段切换被拒绝: 进入 {pending} 前 stage_status 必须为 awaiting_user_confirmation；当前为 {current}。如需强制切换请使用 --force"`
   - **Precision: GOOD**

3. **execution_authorized gate** (line 1300-1304):
   - Message: `"阶段切换被拒绝: 进入 {pending} 前 checkpoints.execution_authorized 必须为 true（可在同一命令中通过 --execution-authorized true 设置）。如需强制切换请使用 --force"`
   - **Precision: GOOD**

4. **Stage transition gate validation** (line 1306-1315):
   - Message: per-gate error + `"阶段切换被拒绝: 门禁产物未齐；如需强制切换请使用 --force"`
   - **Precision: GOOD**

### Stage and Status Definitions

**STAGES** (line 71-84): feasibility, brainstorm, design, plan, implementation, test-first, project-audit, check, review-gate, finish-work, delivery, record-session

**STAGE_TRANSITIONS** (line 85-98): Defines the directed graph of allowed stage transitions.

**STAGE_STATUSES** (line 99-104): in_progress, blocked, awaiting_user_confirmation, completed

**EXECUTION_STAGES** (line 105): implementation, test-first

**COORDINATION_STAGES** (line 106): feasibility, brainstorm, design, plan

**LEAF_REQUIRED_STAGES** (line 107): STAGES - COORDINATION_STAGES (i.e., all execution and post-design stages)

### Key Functions for Error Generation

| Function | Line | Purpose |
|---|---|---|
| `validate_leaf_task` | 641 | Checks if a task with children is in a leaf-required stage |
| `validate_session_active_task` | 611 | Checks session runtime points to the right task |
| `collect_route_readiness_blockers` | 680 | Collects blockers for brainstorm, plan, execution stages |
| `collect_exit_gate_blockers` | 724 | Collects exit-gate completeness issues |
| `detect_embed_invalid` | 1527 | Checks install record and library lock integrity |
| `_route_result` | 1552 | Emits JSON route result with action/reason/blockers |
| `cmd_repair` | 1813 | Handles repair flow, differentiates manual_confirmation_required from repair_ready |

### workflow.md Recovery Guidance

The embedded `workflow.md` at `/tmp/trellis-0.5.17-2/.trellis/workflow.md`:

- **Does NOT distinguish** `recovery_needed` from `repair_needed` in user-facing text
- Line 76: Describes degraded mode recovery behavior for `task.py start`
- Line 230: Mentions `--force` to bypass for repair scenarios
- The `[workflow-state:no_task]` block (line 404-410) describes three options (A/A+/B/C) but does not explain what `recovery_needed` or `repair_needed` means when route returns them
- No guidance on "your session doesn't point to the right task" vs "your state file is actually corrupted"

### Source Protocol Document (阶段状态机与强门禁协议.md)

Key sections relevant to recovery:

- **Section 2** (line 19-53): "当前阶段的唯一判定链" -- describes the session -> active leaf task -> workflow-state.json chain, and explicitly states "无法解析时不允许识别当前阶段"
- **Line 43-46**: "active task 约束" -- says when session can't resolve, only "恢复当前任务 / 明确当前任务" branch is allowed
- **Line 49-53**: "叶子任务约束" -- says execution stages must be held by leaf tasks, and the session must be switched to the leaf task before entering execution
- **Section 4** (line 119-140): `/trellis:continue` boundaries -- lists the same recovery conditions but again does not distinguish "wrong context" from "broken state"

### Source vs Embedded: Identical

`diff` between embedded and source workflow-state.py produces no output -- they are byte-identical.

### Install Path

`deploy_helper_scripts()` in `install-workflow.py` (line 2573) copies files from `commands/shell/` to `.trellis/scripts/workflow/` on the target project. The `workflow-state.py` is listed in `HELPER_SCRIPTS` in `workflow_assets.py` (line 49).

## Problem Summary: All Imprecise Messages

### Site 1: Line 1676-1680 -- `recovery_needed` when tasks exist but session has no active task
- Current message: `"当前 session 未解析到 active task；请先明确当前任务或重新进入目标阶段"`
- Available context at this point: `repo_root`, knowledge that `.trellis/tasks/` contains at least one task dir with `task.json`
- What's missing: The function could enumerate which tasks exist, their statuses, and their current workflow stages. It could also check if ANY of those tasks are leaf tasks in an active stage, and suggest `task.py start <specific-task>`.

### Site 2: Line 1716 -- `repair_needed` when parent task has children
- Current message: `"当前 task 已有 children"`
- Available context: `task_data` (the full task.json), `stage` (the current workflow stage), `children` list
- What's missing: The function has the children list and could name them. It could explain that the user needs to `task.py start <child-name>` to switch to a leaf task. The action should arguably be `recovery_needed` (context issue) not `repair_needed` (state corruption).

### Site 3: Line 1609-1610 -- Stale active task
- Current message: `"Trellis 当前活动任务已失效: {active.task_path}"`
- Available context: `active.task_path`, `repo_root`, could check if the task was archived vs moved vs if there's a sibling task
- What's missing: Could check if the path points to an archived task (would be under `.trellis/archive/`) vs a non-existent path, and give different advice accordingly.

### Site 4: Line 1692 -- Missing workflow-state.json
- Current message: `"缺少 workflow-state.json"`
- Available context: `task_dir`, `repo_root`
- What's missing: Could suggest `workflow-state.py init <task-dir> --stage <stage>` as the fix, or explain that this typically happens when the task was created before the workflow was installed.

### Site 5: Line 1745-1752 -- Readiness blockers reported as `repair_needed`
- For non-execution, non-plan stages, readiness blockers produce `repair_needed` action
- The blockers are about missing docs/files, not state corruption
- This misclassifies "you haven't finished the current stage's deliverables" as "your state is broken"

### Distinction: `recovery_needed` vs `repair_needed`

In the current codebase:
- `recovery_needed` is used ONLY at line 1678 -- when session has no active task but tasks exist
- `repair_needed` is used at lines 1610, 1614, 1685, 1692, 1700, 1716, and 1747 -- covering stale task, unresolvable path, missing directory, missing state file, invalid state shape, parent-with-children, and readiness blockers
- The semantic difference is: `recovery_needed` = "you need to tell me which task to work on" vs `repair_needed` = "the state file is broken or the task is in an impossible configuration"
- BUT: "parent task with children" and "readiness blockers for non-execution stages" are NOT state corruption -- they are operational context issues. They should be `recovery_needed` or a new action like `context_needed`.

## Caveats / Not Found

- The `resolve_active_task()` function is imported from `common.active_task` -- its internal logic was not read (it's in the common module), so the exact conditions for `active.stale` are not documented here.
- The hook scripts (inject-workflow-state.py, session-start.py) were not examined for how they consume the route result -- they may have their own message interpretation layer.
- No test file for the route command's error messages was found; the test file at `commands/shell/test_workflow_state.py` was not examined for coverage of these specific paths.
