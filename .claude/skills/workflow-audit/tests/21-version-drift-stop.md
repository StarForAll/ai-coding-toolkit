# 21 Version Drift Stop

## Purpose

Verify that `workflow-audit` stops immediately when the current Trellis version does not exactly match the workflow's declared compatible version, instead of continuing with any static or runtime audit path.

## Input

User input:

> Audit `docs/workflows/新项目开发工作流/`. Continue the normal workflow audit only if the current Trellis version still matches what this workflow declares as compatible.

## Expected Mode

Hard-stop before normal mode selection: `Blocked / Version Drift`.

## Expected Key Behaviors

- read `COMPATIBLE_TRELLIS_VERSION` from `docs/workflows/新项目开发工作流/commands/workflow_assets.py`
- run `trellis -v`
- if the two versions differ, stop immediately as `Blocked / Version Drift`
- report both the compatible version and the actual version explicitly
- direct the user to `workflow-capability-audit` for compatibility-upgrade work
- do not create a task, `prd.md`, or `audit-report.md`
- do not proceed into Step 1 target resolution, A/B/C evidence gathering, `/tmp` temporary-project creation, `trellis init`, or Codex handoff logic

## Must Not

- must not continue in lightweight static mode
- must not continue in task-based static mode
- must not continue in task-based runtime mode
- must not treat version drift as an ordinary P0/P1/P2 workflow finding
- must not guess that the workflow is "probably still compatible"
- must not recommend source remediation before routing to `workflow-capability-audit`
