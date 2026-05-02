# 03 Full Audit Upgrade Path

## Purpose

Verify that `workflow-capability-audit` enters the full task-based audit path only when the current Trellis version is newer than `COMPATIBLE_TRELLIS_VERSION`.

## Input

User input:

> Audit whether the new Trellis version changed capabilities or mechanics that require compatibility updates in `docs/workflows/新项目开发工作流/`.

## Expected Mode

Task-based full compatibility audit.

## Expected Key Behaviors

- pass version gating only when `current > compatible`
- create a task after the gate passes
- create fresh A/B fixtures
- maintain `prd.md`
- maintain `capability-report.md`
- build one unified capability matrix with:
  - workflow-managed surface
  - workflow-dependent Trellis-native surface
- stop after audit conclusion and wait for user confirmation

## Must Not

- must not reuse existing A/B roots
- must not enter the audit path when versions are equal
- must not auto-execute workflow source remediation
