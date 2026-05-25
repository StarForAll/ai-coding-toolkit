# Workflow Audit Report

## Audit Boundary

- Workflow target: `docs/workflows/新项目开发工作流/`
- Generated target project: `/tmp/trellis-0.5.17-2`
- Compatible Anchor Version: `0.5.17`
- Current Trellis Version: `0.5.17`
- Version Gate: passed
- Workflow installed state: `/tmp/trellis-0.5.17-2/.trellis/workflow-installed.json` reports `workflow_version = 0.1.28`, `workflow_schema_version = 3`, profile `outsourcing`, scripts including `workflow-state.py`, `state_utils.py`, `validators_gates.py`, and task patches.

## Confirmed Issues

### P1: `project-audit` non-delivery exits do not enforce project audit gate status

- Conclusion: confirmed.
- Evidence:
  - source repo: `commands/shell/validators_gates.py` `validate_project_audit_gate()` only requires `project_audit_gate_status` when `require_delivery_linkage=True`, and only sets that flag for `new_stage == "delivery"`.
  - generated target project workflow-installed state: `/tmp/trellis-0.5.17-2/.trellis/scripts/workflow/validators_gates.py` has the same behavior.
  - runtime command output: a repro `project-audit.md` with `project_audit_gate_status = fail` did not produce a project-audit status error from `workflow-state.py validate`; the observed blockers were unrelated feasibility/estimate prerequisites.
- Impact: a project-level audit with failed project-level status can still attempt to leave `project-audit` toward non-delivery stages if other gates are satisfied.
- Fix direction: make project-audit exit validation consume `project_audit_gate_status` for all exits, not only delivery. Keep `not_run` allowed only where the report records an accepted reason, but block `fail`.

### P1: `project-audit -> implementation` remains a canonical but under-documented return edge

- Conclusion: confirmed.
- Evidence:
  - source repo: `commands/shell/state_utils.py` includes `"project-audit": ["implementation", "check", "review-gate", "delivery"]`.
  - generated target project workflow-installed state: target `state_utils.py` has the same edge.
  - source repo: `commands/workflow-patch-projectization.md` quick reference lists `project-audit -> check/review-gate/delivery`, but not `project-audit -> implementation`; `commands/project-audit.md` says next steps are mainly stay in project-audit, go check, or go delivery.
- Impact: repair/recovered or manually edited states without a narrow `_allowed_next_override` can use a return edge that lacks clear evidence and re-gate closure.
- Fix direction: remove `implementation` from the canonical `project-audit` transition set unless we deliberately add a formal rework contract. Current docs already model project-audit fixes inside project-audit and then re-enter `check` when code changed, so removal is the lower-risk patch.

### P1: plan-created leaf task readiness conflicts with implementation entry gates

- Conclusion: confirmed.
- Evidence:
  - source repo: `commands/plan.md` says the recommended leaf task only needs a minimal `prd.md`; its template has Goal/In Scope/Out of Scope/Acceptance Anchors/Preferred CLI, no project-level estimate markers.
  - generated target project workflow-installed state: `workflow-state.py` blocks execution stages when current `prd.md` lacks `TASK_ESTIMATE_MARKERS`.
  - runtime command output: after applying `workflow-state.py repair --stage implementation --execution-authorized true --transition-from plan --apply` to a leaf with the documented minimal `prd.md`, `workflow-state.py route` returned `action = blocked` with reason `当前推荐执行任务说明卡缺少项目级粗估字段，不能进入执行态`.
- Impact: a leaf task produced exactly as documented can be blocked at implementation entry.
- Fix direction: preserve the project-level estimate gate, but allow implementation/check/project-audit/delivery leaf tasks to satisfy it from an ancestor task's `prd.md` when the leaf has a parent lineage. Standalone L0 tasks must still carry their own estimate.

### P1: new leaf task creation does not initialize `workflow-state.json`, while the documented path calls `workflow-state.py set`

- Conclusion: confirmed.
- Evidence:
  - generated target project workflow-installed state: `common/task_store.py` creates `task.json` and JSONL seed files, but no `workflow-state.json`.
  - runtime command output: a fresh task created in `/tmp/trellis-0.5.17-2` had no `workflow-state.json`; `workflow-state.py set ... --stage implementation ... --transition-from plan` failed with `workflow-state.json 不存在或无法读取；请先运行 init`.
  - source repo: `commands/workflow-patch-projectization.md` documents `plan -> implementation` as a direct `workflow-state.py set <leaf-dir> --stage implementation ... --transition-from plan` after switching to the leaf.
- Impact: the standard documented plan-to-leaf execution path falls into repair/init instead of normal progression.
- Fix direction: update the plan path to explicitly initialize the selected leaf task state before the final `set`, preferably `workflow-state.py init <leaf-dir> --stage plan` followed by setting `stage_status=awaiting_user_confirmation` and then the confirmed transition to `implementation`. Add tests/docs so this is not mistaken for Trellis native auto-dispatch.

### P1: delivery validation can lose the task-level `check.md` context for independent PROJECT-AUDIT carriers

- Conclusion: confirmed.
- Evidence:
  - source repo and generated target project: transition validation from `project-audit -> delivery` resolves parent/current `check.md` through `_resolve_project_audit_check_task_dir()`.
  - source repo and generated target project: `validate_delivery_gate()` later calls `validate_check_gate(task_dir, ...)` and passes `check_task_dir=task_dir` to formal PROJECT-AUDIT validation.
  - source repo docs: `commands/project-audit.md` and `commands/delivery.md` explicitly say formal PROJECT-AUDIT and current task check are parallel evidence dimensions, and delivery must not require the PROJECT-AUDIT carrier to own a separate `check.md`.
- Impact: a direct carrier-to-delivery path can pass transition-time context resolution but fail or drift at delivery validation time.
- Fix direction: reuse the same resolved task-level check context inside `validate_delivery_gate()`, so delivery and transition gates agree. Keep formal PROJECT-AUDIT validation separate from task-level check validation.

### P2: `--awaiting-user-confirmation` is accepted and documented but not consumed

- Conclusion: confirmed.
- Evidence:
  - generated target project workflow-installed state: `workflow-state.py` parser accepts `--awaiting-user-confirmation` for `set` and `repair`.
  - generated target project workflow-installed state: `state_utils.py build_pending_state_for_set()` never reads `args.awaiting_user_confirmation`.
  - generated target project runtime output: running `workflow-state.py set <task> --awaiting-user-confirmation true` changed only `updated_at`; status stayed `in_progress`.
  - generated target project workflow-installed state: `common/tasks.py` still reads `state.get("awaiting_user_confirmation")` for display details.
- Impact: the CLI surface suggests a state contract that no longer exists, and documented commands can give a false sense that waiting-for-confirmation was recorded.
- Fix direction: consume the flag as a compatibility alias for `status=awaiting_user_confirmation` / `status=in_progress` with conflict checks against `--stage-status`, or remove the flag from docs and parser. Compatibility alias is lower-risk because many command docs still include the flag.

## Related Similar Issues To Fix Together

- Documentation occurrences of `--awaiting-user-confirmation` appear in transition tables and tests; whichever fix is chosen must update source docs and installer tests together.
- `PROJECT_ESTIMATE_REQUIRED_STAGES` currently applies to execution and downstream stages without considering parent lineage; this is the same root cause as the plan leaf mismatch.
- `validate_delivery_gate()` and `validate_stage_transition_gates()` have duplicate project-audit delivery context logic; the fix should extract/reuse one helper instead of creating another special case.

## Recommended Patch Plan

1. Tighten project-audit exits:
   - Remove `implementation` from `STAGE_TRANSITIONS["project-audit"]`.
   - Enforce `project_audit_gate_status` for project-audit exits, with explicit treatment for `pass`, `fail`, and `not_run`.
   - Update `commands/project-audit.md`, `workflow-patch-projectization.md`, and any generated skill/deployed source expectations that reference the transition.

2. Align leaf readiness:
   - Add a helper that checks project estimate markers in the current task or its ancestor lineage.
   - Use it from route entry blockers and project doc boundary validation.
   - Update `commands/plan.md` leaf template/requirements to say minimal leaf PRD is valid when the parent/main task carries the project-level estimate.

3. Normalize new leaf state initialization:
   - Update plan and transition docs so selected leaf tasks are initialized with a plan-stage workflow state before `plan -> implementation`.
   - Add tests proving the documented path no longer falls into missing-state repair.

4. Preserve delivery context:
   - Resolve task-level check dir once for delivery, using the same parent/current fallback used during `project-audit -> delivery`.
   - Pass that resolved check dir into both `validate_check_gate()` and formal PROJECT-AUDIT validation.

5. Fix the awaiting confirmation flag:
   - Treat `--awaiting-user-confirmation true` as `status=awaiting_user_confirmation` when `--stage-status` is absent.
   - Treat `--awaiting-user-confirmation false` as `status=in_progress` when `--stage-status` is absent.
   - If both are supplied and conflict, reject the command.
   - Keep legacy display compatibility in `common/tasks.py` unless tests show it creates noise.

## Validation To Run After Patch

- `PYTHONPATH=docs/workflows/新项目开发工作流/commands/shell /ops/softwares/python/bin/python3 -m unittest docs.workflows.新项目开发工作流.commands.shell.test_workflow_state`
- `PYTHONPATH=docs/workflows/新项目开发工作流/commands /ops/softwares/python/bin/python3 -m unittest docs.workflows.新项目开发工作流.commands.test_workflow_installers`
- `/ops/softwares/python/bin/python3 trellis-library/cli.py validate --strict-warnings`

## Current Stop Point

Per user instruction, no source workflow files have been modified yet. Waiting for approval before patching `docs/workflows/新项目开发工作流/`.
