# Audit Report

## Audit Boundary

- Workflow root: `docs/workflows/新项目开发工作流/`
- Runtime evidence project: `/tmp/trellis-0.5.17-2`
- Compatible anchor version: `0.5.17`
- Current Trellis version: `0.5.17`
- Version gate: `passed`

## Confirmed Issues

### 1. Parent task can still be written into leaf-only execution state

- Status: confirmed
- Evidence:
  - Installed/runtime helper still rejected leaf-only stages only in later validation/route, not in `cmd_set`.
  - Source `workflow-state.py` before patch lacked `validate_leaf_task()` enforcement in `cmd_set`.
- Validation action:
  - Static review of `docs/workflows/新项目开发工作流/commands/shell/workflow-state.py`
  - Added regression test `test_set_rejects_execution_stage_on_parent_task_with_children`
- Fix:
  - `cmd_set` now rejects any resulting leaf-required stage on a task with `children`.
  - Transition-gate path also checks the leaf constraint before write.

### 2. `repair` inferred stage from artifacts and could rebuild wrong semantics

- Status: confirmed
- Evidence:
  - `/tmp/trellis-0.5.17-2/.agents/skills/trellis-start/SKILL.md` hard-boundary text forbade inferring stage from task artifacts.
  - `/tmp/trellis-0.5.17-2/.trellis/scripts/workflow/workflow-state.py` `cmd_repair` inferred stage from `assessment.md`, `design/`, `task_plan.md`, `check.md`, `delivery/` and wrote `build_default_state()` on `--apply`.
- Validation action:
  - Static review of installed `/tmp` copies and source helper.
  - Replaced old inference tests with explicit-stage / recover-from-state tests.
- Fix:
  - `repair` no longer infers stage from task artifacts.
  - Recovery now supports:
    - valid current state → `ok`
    - broken state with preserved `stage` → `repair_ready`
    - explicit `--stage` → safe rebuild path
    - otherwise → `manual_confirmation_required`
  - Same-stage repair preserves recoverable semantic fields instead of blind reset.

### 3. Delivery / ownership / watermark validators were not attached to strong gates

- Status: confirmed
- Evidence:
  - Delivery docs required `delivery-control-validate.py`, `ownership-proof-validate.py`, `source-watermark-guard.py`.
  - Source `validate_delivery_gate()` only checked file presence plus two outsourcing files before patch.
  - `validate_plan_gate()` also missed the delivery-control / ownership-proof plan-phase validators.
- Validation action:
  - Static review of `delivery.md`, validator scripts, and `workflow-state.py`.
  - Added route blocker regression for delivery-stage validator failure.
- Fix:
  - `validate_plan_gate()` now calls:
    - `plan-validate.py`
    - `delivery-control-validate.py --phase plan`
    - `ownership-proof-validate.py --phase plan`
  - `validate_delivery_gate()` now calls:
    - `delivery-control-validate.py --phase delivery`
    - `ownership-proof-validate.py --phase delivery`
    - `source-watermark-guard.py --mode check` when ownership proof is enabled
  - `design` exit gating now also calls `ownership-proof-validate.py --phase design`.

### 4. Degraded mode was inconsistent across route / validate / step lookup

- Status: confirmed
- Evidence:
  - `/tmp/trellis-0.5.17-2/.trellis/scripts/task.py start` wrote degraded fallback.
  - `/tmp/trellis-0.5.17-2/.trellis/scripts/task.py current` still ignored degraded fallback.
  - `/tmp/trellis-0.5.17-2/.trellis/scripts/common/workflow_phase.py` depended on `task.py current`.
  - `workflow-state.py validate` only accepted session runtime before patch.
- Validation action:
  - Static review of installed `/tmp` files.
  - Added regression test `test_validate_uses_degraded_fallback_when_session_pointer_missing`.
  - Installer regression now checks for the new `degraded-current-read` patch marker.
- Fix:
  - `workflow-state.py validate` now accepts degraded fallback when no session current-task exists.
  - Installer / upgrade patch for target-project `task.py` now also patches `cmd_current` to read `.trellis/.runtime/degraded-active-task.json`.

### 5. Entry / finish-work runtime skills leaked patch instructions and stale routing semantics

- Status: confirmed
- Evidence:
  - `/tmp/trellis-0.5.17-2/.agents/skills/trellis-start/SKILL.md` still contained old Step-4 bootstrap text above the appended router patch.
  - `/tmp/trellis-0.5.17-2/.agents/skills/trellis-finish-work/SKILL.md` contained maintainer-only “替换说明” text in the installed runtime asset.
  - `upgrade-compat.py` still used append-only Codex skill patch logic.
- Validation action:
  - Static review of installed `/tmp` skills.
  - Installer tests now assert those maintainer instructions do not leak into deployed runtime skill files.
- Fix:
  - `build_codex_phase_router_skill_content()` now strips maintainer preface and replaces old Steps 1-4 when present.
  - `build_finish_work_content()` now injects only the runtime subsection, not maintainer patch notes.
  - `upgrade-compat.py` now reuses the same patched builder logic.
  - Router docs now explain the new `repair_ready` / `manual_confirmation_required` flow.

### 6. Plan stage could show false “awaiting confirmation” readiness

- Status: confirmed
- Evidence:
  - Source `collect_exit_gate_blockers()` had no `plan` branch before patch.
  - That allowed `route` to emit `awaiting_confirmation` while the later plan->execution gate still failed.
- Validation action:
  - Added regression test `test_route_plan_awaiting_reports_plan_gate_blockers`.
- Fix:
  - `collect_exit_gate_blockers()` now runs `validate_plan_gate()` for `plan`.
  - Route now reports `awaiting_confirmation_with_blockers` when plan artifacts or domain validators are still incomplete.

## Related Issue Found During Audit

### 7. Fresh first-entry routing could skip feasibility when only install profile existed

- Status: confirmed
- Evidence:
  - Source `cmd_route` could send `profile=personal` projects directly to `brainstorm` even with no reusable `assessment.md`.
  - Authoritative workflow docs require project-category judgment via `feasibility` before later stages unless an existing valid assessment is explicitly reused.
- Validation action:
  - Updated existing first-entry tests and added reuse-of-assessment coverage.
- Fix:
  - First entry now defaults to `feasibility` unless route is reusing an existing assessment that explicitly allows `brainstorm`.

## False Alarms / Already Fixed In Current Source

### A. `cmd_set` had no allowed-next / awaiting / execution-authorized / plan gate checks

- Status: false for current source
- Evidence:
  - Current source already enforced:
    - `allowed_next_stages`
    - `awaiting_user_confirmation`
    - `execution_authorized`
    - `validate_plan_gate()`
- Outcome:
  - No rollback needed.
  - Only the missing leaf-task gate and route-side exit blockers were patched.

## Modified Source Files

- `docs/workflows/新项目开发工作流/commands/shell/workflow-state.py`
- `docs/workflows/新项目开发工作流/commands/install-workflow.py`
- `docs/workflows/新项目开发工作流/commands/upgrade-compat.py`
- `docs/workflows/新项目开发工作流/commands/start-patch-phase-router.md`
- `docs/workflows/新项目开发工作流/commands/start-skill-patch-phase-router.md`
- `docs/workflows/新项目开发工作流/阶段状态机与强门禁协议.md`
- Tests:
  - `docs/workflows/新项目开发工作流/commands/shell/test_workflow_state.py`
  - `docs/workflows/新项目开发工作流/commands/test_workflow_installers.py`

## Verification

- `/ops/softwares/python/bin/python3 -m unittest docs.workflows.新项目开发工作流.commands.shell.test_workflow_state`
- `/ops/softwares/python/bin/python3 -m unittest test_workflow_installers`

Results:

- `test_workflow_state`: pass (`79` tests)
- `test_workflow_installers`: pass (`104` tests)
