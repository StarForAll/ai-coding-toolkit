# 32 Allowed Minor Version Mismatch

## Purpose

Verify that `workflow-audit` continues when the declared compatible version and the current `trellis -v` differ only by `patch`, both are stable releases, and the user explicitly allows that `minor version mismatch` for the current run.

## Input

User input:

> Audit `docs/workflows/新项目开发工作流/` for obvious static rule-propagation issues only. The workflow declares `0.5.0`, my current `trellis -v` is `0.5.5`, and I want to skip this minor version mismatch for this run.

Interpreted as:
```yaml
workflow_path: docs/workflows/新项目开发工作流/
candidate_issues: []
need_runtime_validation: auto
force_full_brainstorm: no
allow_minor_version_mismatch: yes
```

## Expected Mode

Lightweight mode.

## Expected Key Behaviors

- read `COMPATIBLE_TRELLIS_VERSION` from `docs/workflows/新项目开发工作流/commands/workflow_assets.py`
- run `trellis -v`
- recognize that the mismatch is limited to a stable `patch` difference under the same `major.minor`
- because the user explicitly allowed the `minor version mismatch`, continue past Step 0 instead of stopping as `Blocked / Version Drift`
- report both version values and the user-approved gate bypass explicitly in the output
- keep the bypass scoped to the current audit run only
- continue with the normal A/B/C static evidence mainline against `docs/workflows/新项目开发工作流/`
- remain in lightweight mode when no runtime-validation trigger is found

## Must Not

- must not rewrite `COMPATIBLE_TRELLIS_VERSION`
- must not reinterpret the bypass as compatibility approval or a signal to skip `workflow-capability-audit` for broader drift
- must not allow the same bypass semantics for `rc`, `beta`, prerelease-to-prerelease, or cross-`minor` / cross-`major` drift
- must not silently omit the fact that the version gate was bypassed by explicit user choice
