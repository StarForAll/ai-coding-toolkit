# PRD

## Title

Audit and patch embedded workflow state guards

## Goal

Audit whether the workflow source under `docs/workflows/新项目开发工作流/` really contains the reported strong-gate/state-machine defects when embedded into a target project, using `/tmp/trellis-0.5.17-2` as the runtime evidence project. If a defect is confirmed, patch the workflow source so future embeds install the corrected behavior.

## Scope

- Analyze the installed workflow behavior in `/tmp/trellis-0.5.17-2`
- Compare installed behavior with source assets under `docs/workflows/新项目开发工作流/`
- Confirm or reject the six user-supplied candidate issues
- Search for adjacent defects of the same class and patch them together when evidence supports it
- Apply fixes only inside `docs/workflows/新项目开发工作流/`
- Allow task-artifact updates inside `.trellis/tasks/05-18-audit-and-patch-embedded-workflow-state-guards/`

## Out of Scope

- Modifying repository directories outside `docs/workflows/新项目开发工作流/` and the current task directory
- Treating this as a fix to the authoring repository's own runtime instead of the embedded workflow product
- General Trellis version-drift compatibility work outside same-version workflow maintenance

## Candidate Issues To Validate

1. Parent coordinator task can be switched directly into execution stages before a leaf-task check blocks it later.
2. `repair` infers stage from artifacts that the entry skill explicitly says must not be used for stage inference, and `--apply` may reset semantic fields unsafely.
3. Delivery / ownership / watermark validators exist but the main workflow-state gate only checks file presence and misses stronger validator rules.
4. Degraded-mode active-task fallback is inconsistent across route, validate, and phase-step resolution.
5. Entry skills retain conflicting legacy semantics, especially around `trellis-start` and `trellis-finish-work`.
6. Plan stage may signal "ready for confirmation" too early and only fail when switching into execution stages.

## Constraints

- Evidence first: no issue is treated as real without source or runtime proof.
- The temporary project `/tmp/trellis-0.5.17-2` is the analysis target, not the edit target.
- Any fix to a Trellis-native gap must be delivered as a workflow-side patch/install behavior change inside `docs/workflows/新项目开发工作流/`.
- Avoid introducing new state-machine inconsistencies or widening false-positive gates.

## Validation

- Static review of workflow source assets and installed target-project files
- Reproduce or verify behavior with the installed scripts in `/tmp/trellis-0.5.17-2` when needed
- Run focused tests or validator scripts that prove the patched behavior
