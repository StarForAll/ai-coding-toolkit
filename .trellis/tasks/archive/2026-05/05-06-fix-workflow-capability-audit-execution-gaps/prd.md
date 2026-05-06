# fix workflow-capability-audit execution gaps

## Goal

Repair the concrete execution gaps in `workflow-capability-audit` that were identified during maintainer review, focusing on atomic state updates, task rollback integrity, stricter CLI input validation, and source-of-truth alignment between runtime output and maintained skill references.

## Scope

- Fix premature compatibility-anchor write-back during fix lifecycle updates.
- Fix parent/child task metadata rollback when full-audit setup fails after child audit task creation.
- Require `--current-cli` to be one of `claude`, `opencode`, or `codex`.
- Reduce drift risk between structural-break runtime output and maintained reference templates/spec text.
- Add regression coverage for all repaired behaviors.

## Non-Goals

- No new workflow root support beyond `docs/workflows/新项目开发工作流/`.
- No redesign of the overall audit lifecycle or capability matrix model.
- No change to commit/archive workflow in this session.

## Requirements

- Production code must only be added after failing tests exist for the targeted gap.
- Runtime behavior, specs, and repo-local skill surfaces must stay aligned in the same change.
- Existing passing `workflow-capability-audit` tests must remain green.

## Verification

- Run targeted `workflow-capability-audit` unit tests.
- Run the full `workflow-capability-audit` test suite.
