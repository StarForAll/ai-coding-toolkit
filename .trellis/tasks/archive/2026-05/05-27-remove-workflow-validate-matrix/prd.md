# remove workflow-validate-matrix project data

## Goal

Remove the project-local `workflow-validate-matrix` skill surface and the remaining repository references, validation hooks, and generated artifacts that still assume the skill exists.

## What I already know

* The user has already manually deleted `skills/workflow-validate-matrix/`.
* The working tree shows that full directory as deleted.
* Remaining live references are in `.trellis/spec/skills/index.md`, `.trellis/spec/skills/workflow-validate-matrix.md`, `scripts/sync-workflow-validate-matrix-runtime.py`, and `scripts/validate-skills.sh`.
* A generated root-level `WORKFLOW_QUESTIONS.md` file from the matrix run is still present and untracked.

## Assumptions (temporary)

* Archived task history and backup snapshots should remain intact unless the user explicitly asks to rewrite history.
* Removing the project-local skill means removing its repo validation/spec surface too, not preserving dead references.

## Open Questions

* none

## Requirements (evolving)

* Remove remaining live repository references to `workflow-validate-matrix`.
* Remove validation and sync entrypoints that only exist for that deleted skill.
* Remove generated local artifact `WORKFLOW_QUESTIONS.md` if it only exists because of the deleted skill workflow.
* Do not modify archived task history or `.trellis/.backup-*` snapshots.

## Acceptance Criteria (evolving)

* [ ] `rg -n "workflow-validate-matrix" . -g '!**/.git/**' -g '!**/.trellis/.backup-*/**'` returns no live references outside archived task history if retained.
* [ ] Deleted skill directory remains removed with no live validation hooks pointing to it.
* [ ] Relevant validation command(s) pass after cleanup, or failures are reported accurately.

## Definition of Done (team quality bar)

* Changes are limited to the live repository surfaces that still reference the removed skill.
* Validation is run and reported with pass / fail / not run truthfully.
* No unrelated files are reverted.

## Out of Scope (explicit)

* Rewriting archived task records under `.trellis/tasks/archive/`
* Editing `.trellis/.backup-*` snapshots
* Replacing `workflow-validate-matrix` with a new skill

## Technical Notes

* Primary affected layers: skills spec, repo validation script, standalone sync helper, generated root artifact
* Manual delete already performed by user; this task completes the repository cleanup
