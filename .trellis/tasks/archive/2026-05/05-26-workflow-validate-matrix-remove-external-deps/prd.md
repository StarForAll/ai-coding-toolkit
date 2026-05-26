# workflow-validate-matrix remove external deps

## Goal

Make `skills/workflow-validate-matrix` runnable as a globally installed skill without depending on source-repository-only workflow command files under `docs/workflows/新项目开发工作流/commands/`. Keep the skill self-contained where possible, while preserving its purpose as a workflow installation matrix validator.

## What I already know

- The current implementation depends on `WORKFLOW_SOURCE_REL = docs/workflows/新项目开发工作流`.
- `validate-matrix.py` searches upward from the current working directory to find the workflow source tree and reads version data from `commands/workflow_assets.py`.
- `validation_runner.py` directly executes source-repo command scripts:
  - `detect-embed-state.py`
  - `install-workflow.py`
  - `upgrade-compat.py`
- `scenario_setup.py` also directly runs source-repo `install-workflow.py` to prepare the preinstalled-upgrade scenario.
- The skill still requires `trellis` on PATH to create fresh baselines via `trellis init`; this is currently a runtime prerequisite, not a source-repo path dependency.
- The repository already documents Skills CLI global install flow such as `npx skills add . -g -y`.

## Assumptions (temporary)

- The primary dependency to remove is the source-repo workflow command dependency, not the `trellis` CLI itself.
- A reasonable replacement is to internalize the minimum behavior needed by the matrix skill, instead of shelling out to source-repo command scripts.
- The globally installed skill may still run inside the workflow source project, but it must no longer require source-tree-relative imports or script paths to function.
- When shared runtime source and the installable skill payload drift, the runtime should not try to mutate the repo or global install automatically; it should tell the user to sync the payload under `skills/workflow-validate-matrix/` and reinstall the global skill.

## Open Questions

- none

## Requirements (evolving)

- Remove hard dependency on `docs/workflows/新项目开发工作流/commands/` from `workflow-validate-matrix`.
- Remove hard dependency on `WORKFLOW_SOURCE_REL` path discovery for core validation flow.
- Provide internal equivalents for the currently shelled-out workflow command behaviors that the matrix needs.
- Keep `trellis` as an explicit runtime prerequisite.
- Preserve current report contract and current 5-scenario matrix intent unless requirement changes.
- Keep failure/report verification behavior correct after dependency removal.
- Avoid manual double-maintenance of the shared runtime logic.
- Shared runtime changes must have an explicit sync path into the globally installed skill payload.
- Drift between shared source and skill-runtime copy must be machine-detectable in validation.
- Runtime mismatch handling must provide concrete next-step commands, not only a generic error.
- If shared-runtime drift is detected, fail closed; do not continue with a potentially stale validator.

## Acceptance Criteria (evolving)

- [ ] `workflow-validate-matrix` can run without locating `docs/workflows/新项目开发工作流/commands/`.
- [ ] No validation step shells out to source-repo `install-workflow.py`, `detect-embed-state.py`, or `upgrade-compat.py`.
- [ ] The skill still produces valid `WORKFLOW_QUESTIONS.md` output.
- [ ] Existing focused tests are updated and pass.
- [ ] A real or representative matrix run still completes successfully.
- [ ] Shared-runtime drift is caught by an automated check, not by manual review alone.
- [ ] Runtime mismatch error tells the user how to sync `skills/workflow-validate-matrix/` and reinstall the global skill.
- [ ] Runtime mismatch path hard-fails and prints concrete sync + reinstall commands.

## Definition of Done (team quality bar)

- Tests added/updated (unit/integration where appropriate)
- Lint / typecheck / CI green
- Docs/notes updated if behavior changes
- Rollout/rollback considered if risky

## Out of Scope (explicit)

- Replacing the entire Trellis runtime or implementing a local clone of `trellis init` without confirmation
- Expanding the skill into a full workflow installer/reinstaller beyond matrix-validation needs
- Changing the `workflow-scan-repair-v3` report schema

## Technical Notes

- Relevant files:
  - `skills/workflow-validate-matrix/constants.py`
  - `skills/workflow-validate-matrix/scenario_setup.py`
  - `skills/workflow-validate-matrix/validation_runner.py`
  - `skills/workflow-validate-matrix/validate-matrix.py`
  - `skills/workflow-validate-matrix/report_generator.py`
- Current externalized workflow-command dependency surface:
  - `find_workflow_source()`
  - version read from `commands/workflow_assets.py`
  - direct subprocess calls to workflow command scripts
- Main risk to control:
  - duplicating installer / embed-state / upgrade logic in a second implementation and letting the skill drift away from the workflow command contract
- Recommended architecture:
  - source of truth: workflow-owned shared runtime code outside the skill payload
  - installable payload: synced runtime copy under `skills/workflow-validate-matrix/`
  - synchronization: dedicated sync script or update step that rewrites the skill copy from the shared source
  - runtime behavior: if mismatch is detected during source-repo usage, print explicit sync + reinstall instructions rather than silently proceeding
  - verification: drift check based on full-content comparison or generated markers/hash, so repo validation fails if the copy is stale
- Confirmed decision:
  - keep `trellis` as a runtime prerequisite
  - use one shared runtime source plus a synced copy inside `skills/workflow-validate-matrix/`
  - on mismatch, stop immediately and instruct the user to sync the repo copy and reinstall the global skill via the Skills CLI flow
