# 01 Version Equal Stop

## Purpose

Verify that `workflow-capability-audit` terminates before task creation when the current Trellis version equals `COMPATIBLE_TRELLIS_VERSION` and no explicit same-version continuation was requested.

## Input

User input:

> Check whether `docs/workflows/新项目开发工作流/` needs a Trellis compatibility audit for the current environment.

## Expected Mode

Version-gate termination. No task-based audit starts.

## Expected Key Behaviors

- run version gating before task creation
- compare current Trellis version against `COMPATIBLE_TRELLIS_VERSION`
- emit the version-gate stop template with `Gate Result = equal-version-stop`
- explain that no same-version full audit will run unless explicit continuation is requested
- do not create a task
- do not create `prd.md`
- do not create `capability-report.md`
- do not create A/B fixtures

## Must Not

- must not create a task before version gating
- must not continue into fresh A/B setup
- must not emit a normal compatibility matrix
