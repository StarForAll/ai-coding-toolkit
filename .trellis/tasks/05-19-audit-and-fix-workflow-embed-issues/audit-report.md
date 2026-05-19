# Audit Report

## Audit Boundary

- Workflow Root: `docs/workflows/新项目开发工作流/`
- Compatible Anchor Version: `0.5.17`
- Current Trellis Version: `0.5.17`
- Version Gate: `passed`
- Runtime Reference Project: `/tmp/trellis-0.5.17-2`

## Confirmed Issues

### 1. Personal-profile first-entry contract is internally inconsistent

- Source layer:
  - `docs/workflows/新项目开发工作流/commands/brainstorm.md`
  - `docs/workflows/新项目开发工作流/commands/shell/workflow-state.py`
  - `docs/workflows/新项目开发工作流/commands/workflow-patch-projectization.md`
- Generated target project layer:
  - `/tmp/trellis-0.5.17-2/.trellis/workflow.md`
- Validation action:
  - Read installed no-task entry contract in `/tmp`.
  - Compare against `brainstorm.md` preconditions and `workflow-state.py` validation logic.
- Result:
  - Installed workflow says personal profile may skip feasibility and supplement `assessment.md` core fields during brainstorm.
  - Source `brainstorm.md` and `workflow-state.py validate` still require an existing `assessment.md` before brainstorm can proceed.
  - This is a real source-asset defect.

### 2. Feasibility → brainstorm transition docs still contain stale one-step examples

- Source layer:
  - `docs/workflows/新项目开发工作流/commands/workflow-patch-projectization.md`
  - related stage-transition docs under the same workflow root
- Validation action:
  - Compare stage transition quick references with `workflow-state.py cmd_set` gate behavior.
- Result:
  - `cmd_set` requires `awaiting_user_confirmation` before entering any non-feasibility target stage.
  - Some source docs still document feasibility → brainstorm as a direct `set --stage brainstorm` action without the readiness step.
  - This is a real documentation/contract defect.

## False Alarms / Already Fixed In Current Version

### 1. `route` always suggests `init --stage feasibility` when state is missing

- Validation action:
  - Read `workflow-state.py cmd_route()` first-entry branch.
- Result:
  - Current logic already distinguishes between `feasibility` and `brainstorm` when a reusable assessment exists.
  - The real issue is incomplete alignment with personal-profile wording and brainstorm validation, not a fully missing route branch.

### 2. `task.py start` always flips `planning -> in_progress` and creates dual truth

- Validation action:
  - Inspect `/tmp/trellis-0.5.17-2/.trellis/scripts/task.py`.
- Result:
  - Current installed sample already includes `strong-gate-no-status-flip`.
  - When `workflow-state.json` exists, the status flip is skipped.

### 3. Codex hook route lookup is itself a confirmed defect

- Validation action:
  - Inspect `/tmp/trellis-0.5.17-2/.codex/hooks/inject-workflow-state.py`.
- Result:
  - Current hook intentionally surfaces route metadata so blocked/recovery states stay visible.
  - No fix planned in this scope.

## Repair Plan

1. Align personal-profile brainstorm entry across:
   - `commands/brainstorm.md`
   - `commands/shell/workflow-state.py`
   - `commands/workflow-patch-projectization.md`
2. Remove stale one-step feasibility → brainstorm transition examples from source docs.
3. Verify no sibling documents in the workflow root still restate the obsolete contract.
