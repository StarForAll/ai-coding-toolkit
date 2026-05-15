# workflow-capability-audit: equal-version user-override

## Goal

Update the repo-local `workflow-capability-audit` contract so version mismatch still requires the full audit path, while equal-version no longer forces termination when the user explicitly asks to continue into the audit flow.

## What I already know

* The current contract hard-stops on `current == COMPATIBLE_TRELLIS_VERSION`.
* The user wants equal-version to remain a gated state, but to permit continuing when the user explicitly requests it.
* The canonical runtime engine is `docs/workflows/新项目开发工作流/commands/workflow-capability-audit.py`.
* Behavior-affecting changes must stay synchronized across spec, repo-local skill entry files, references, and tests.

## Assumptions (temporary)

* The safest implementation is an explicit input/flag contract for equal-version override rather than implicit natural-language inference in the script.
* Under the workflow's own maintenance contract, `COMPATIBLE_TRELLIS_VERSION` is never greater than the actual `trellis -v` used for audit execution.
* Existing version-gate stop output should remain available for equal-version runs when the override is not supplied.

## Open Questions

* None. The user clarified the desired equal-version behavior directly.

## Requirements

* Preserve version gate ordering as the first decision point.
* Keep `current > compatible` as a mandatory full-audit continuation path.
* Allow `current == compatible` to continue into the full audit path only when the user explicitly requests it.
* Remove `current < compatible` handling from the normal workflow contract and persisted test scenarios.
* Make the equal-version continuation contract explicit in spec, skill docs, script input, and runbook wording.
* Update tests and persisted scenario docs to cover both equal-version stop and equal-version explicit continuation.

## Acceptance Criteria

* [ ] `workflow-capability-audit.py` can still emit `equal-version-stop` by default.
* [ ] `workflow-capability-audit.py` can continue into full audit when `current == compatible` and the explicit equal-version continuation input is provided.
* [ ] Skill/spec/reference docs describe the new equal-version override behavior consistently.
* [ ] Tests cover the default equal-version stop and the explicit equal-version continue path.

## Definition of Done (team quality bar)

* Tests added/updated (unit/integration where appropriate)
* Lint / typecheck / CI green
* Docs/notes updated if behavior changes
* Rollout/rollback considered if risky

## Out of Scope (explicit)

* Changing the behavior of `workflow-audit`
* Redesigning the broader task model or Codex inline rules
* Auto-inferring user intent from arbitrary natural-language phrasing inside the Python execution engine

## Technical Notes

* Primary behavior source: `.trellis/spec/skills/workflow-capability-audit.md`
* Repo-local entry artifacts: `.agents/skills/workflow-capability-audit/`, `.claude/skills/workflow-capability-audit/`
* Runtime engine: `docs/workflows/新项目开发工作流/commands/workflow-capability-audit.py`
* Test coverage: `docs/workflows/新项目开发工作流/commands/test_workflow_capability_audit.py`
