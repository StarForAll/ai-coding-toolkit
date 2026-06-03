# 03 Full Audit Newer Path

## Purpose

Verify that `workflow-capability-audit` enters the full task-based audit path when the current Trellis version is newer than `COMPATIBLE_TRELLIS_VERSION`, but stops for manual shell continuation once `B` would require workflow embed commands.

## Input

User input:

> Audit whether the newer Trellis version changed capabilities or mechanics that require compatibility updates in `docs/workflows/新项目开发工作流/`.

## Expected Mode

Task-based full compatibility audit.

## Expected Key Behaviors

- pass version gating whenever `current > compatible`
- require `current_cli` before task creation or fixture setup because this path enters full audit
- create a task after the gate passes
- create fresh A/B fixtures
- maintain `prd.md`
- maintain `capability-report.md`
- if the run reaches the embed boundary for `B`, stop and emit the manual human-shell command chain instead of executing embed commands inside the audit
- when embed continuation is still pending, record that pending state in `capability-report.md`
- only build the full unified capability matrix after the required manual shell continuation evidence exists
- stop after audit conclusion and wait for user confirmation

## Must Not

- must not reuse existing A/B roots
- must not recycle earlier unrelated fixtures
- must not auto-run the embed chain for `B` through AI execution once the manual shell boundary is reached
- must not enter the audit path when versions are equal unless explicit continuation was requested
- must not enter the audit path when `current < compatible`
- must not auto-execute workflow source remediation
