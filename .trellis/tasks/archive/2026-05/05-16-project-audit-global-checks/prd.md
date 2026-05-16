# project-audit: add project-level vulnerability and quality checks

## Goal

Narrowly update the workflow so that `project-audit` explicitly owns project-level vulnerability detection and project-level code quality total-check responsibilities after all code-related tasks are complete. This change must stay within `project-audit` scope only and must not modify task-level `check` behavior or helper scripts such as `check-quality.py`.

## What I already know

* The previous attempt mixed two different concerns: project-level audit responsibility and task-level `check` gate behavior.
* The user explicitly rejected changing task-level `check` behavior in this task.
* The current `project-audit` command already owns project-wide review and remediation after all code-related tasks are complete.
* The current `project-audit` source doc does not yet explicitly require a project-level vulnerability detection matrix or a project-level quality total-check matrix.

## Assumptions (temporary)

* The intended behavior is documentation/workflow-contract level only for this round, not a new helper script or a change to `check-quality.py`.
* Existing project-specific command-matrix conventions should be reused: real commands come from the target project's confirmed automation matrix, not guessed defaults.

## Open Questions

* None currently blocking. The user already confirmed the main boundary: pure `project-audit` scope.

## Requirements (evolving)

* Update `project-audit` so it explicitly covers:
  * project-level vulnerability detection
  * project-level code quality total-check
* Define where in `project-audit` these checks are planned, confirmed, executed, and recorded.
* Keep task-level `check` semantics unchanged.
* Propagate rule wording to the minimum required referencing docs/tests.

## Acceptance Criteria (evolving)

* [ ] `project-audit.md` explicitly states the new project-level responsibilities.
* [ ] At least the main referencing docs reflect the same boundary.
* [ ] No changes are made to `check-quality.py` or task-level `check` execution semantics.
* [ ] Relevant regression coverage or installer assertions are updated if deployed command content expectations changed.

## Definition of Done (team quality bar)

* Scope stays limited to `project-audit` and directly dependent propagation surfaces.
* Documentation remains consistent across the main workflow authority, routing, and walkthrough layers.
* Verification commands pass for changed tests/docs contracts.

## Out of Scope (explicit)

* Changing `check-quality.py`
* Changing task-level `check` gate behavior
* Changing `review-gate` trigger logic
* Adding a new scanner helper script in this round

## Technical Notes

* Primary source file: `docs/workflows/新项目开发工作流/commands/project-audit.md`
* Confirmed propagation files:
  * `工作流总纲.md`
  * `命令映射.md`
  * `工作流全局流转说明（通俗版）.md`
  * `多CLI通用新项目完整流程演练.md`
  * `commands/test_workflow_installers.py`
* Evaluated and intentionally skipped for this round:
  * `check.md` — out of scope because task-level `check` behavior must remain unchanged
  * `review-gate.md` — out of scope because task-level supplemental review logic is unchanged
