# 33 Prerelease Drift Ignores Bypass

## Purpose

Verify that `workflow-audit` still stops when prerelease labels are involved, even if the user explicitly sets `allow_minor_version_mismatch: yes`.

## Input

User input:

> Audit `docs/workflows/新项目开发工作流/`. The workflow declares `0.5.0-rc.1`, my current `trellis -v` is `0.5.0`, and I want to allow this mismatch for the run.

Interpreted as:
```yaml
workflow_path: docs/workflows/新项目开发工作流/
allow_minor_version_mismatch: yes
```

## Expected Mode

Hard-stop before normal mode selection: `Blocked / Version Drift`.

## Expected Key Behaviors

- read `COMPATIBLE_TRELLIS_VERSION` from `docs/workflows/新项目开发工作流/commands/workflow_assets.py`
- run `trellis -v`
- recognize that a prerelease-to-stable mismatch is **not** the contract-defined `minor version mismatch`
- ignore the bypass request for this mismatch class and stop as `Blocked / Version Drift`
- report both version values explicitly
- direct the user to `workflow-capability-audit`
- do not create a task, `prd.md`, or `audit-report.md`

## Must Not

- must not reinterpret `allow_minor_version_mismatch: yes` as permission to ignore prerelease labels
- must not continue into Step 1, A/B/C evidence gathering, or Step D runtime validation
- must not suggest that the user can resolve this case merely by restating the same bypass request
