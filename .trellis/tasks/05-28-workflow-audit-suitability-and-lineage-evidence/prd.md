# workflow-audit suitability and lineage evidence

## Goal

Confirm whether `workflow-audit` is appropriate for the current repeated
`workflow-scan` / `workflow-repair` loop, identify any repo-local compatibility
or contract issues that must be fixed before using it, and then prepare a
dedicated `workflow-audit` direction with the prior repair-lineage evidence
organized for follow-up work.

## What I already know

- The current problem is no longer a normal single repair attempt; the user
  reports this is already the sixth scan/repair loop on the same lineage.
- `workflow-repair` v3.3 requires cross-task escalation when the same lineage
  already has two earlier repair tasks.
- `workflow-audit` is the repo-local maintainer audit skill for
  `docs/workflows/新项目开发工作流/`.
- `workflow-audit` version preflight currently passes in this repo:
  `COMPATIBLE_TRELLIS_VERSION = 0.5.17` and `trellis -v = 0.5.17`.
- Under Codex, `workflow-audit` may execute in the main session, but if the
  audit reaches the formal embed step it must stop and hand off to a main
  interactive Claude Code or OpenCode session.
- No active task existed before this task was created.

## Assumptions (temporary)

- The target lineage is still the same temp-project/report lineage rather than
  a genuinely new audit surface.
- The user wants evidence-first judgment before any source edits.
- If a compatibility issue exists, the expected fix scope stays within the
  workflow-authoring surfaces for `workflow-audit` and related workflow assets.

## Open Questions

- None currently blocking. If lineage matching becomes ambiguous after reading
  old repair logs, capture that ambiguity explicitly before any repair.

## Requirements (evolving)

- Determine whether `workflow-audit` is the correct next tool for the current
  cross-task non-convergence situation.
- Verify the current `workflow-audit` contract against repo-local source of
  truth, live skill surfaces, and current runtime version.
- Identify whether any compatibility or contract drift would prevent safe use
  of `workflow-audit` right now.
- If such drift exists and is within safe scope, repair it before opening the
  audit-direction follow-up.
- Organize prior repair-lineage evidence from existing tasks/logs into task
  artifacts so the eventual audit starts from persisted evidence rather than
  chat memory.

## Acceptance Criteria (evolving)

- [ ] `workflow-audit` suitability is classified as usable / blocked / needs fix
- [ ] Any blocking compatibility issue is either fixed or explicitly reported
- [ ] A task-local evidence summary exists for the prior repair lineage
- [ ] The next-step recommendation clearly states whether to proceed with a
      dedicated `workflow-audit` task

## Definition of Done (team quality bar)

- Evidence references are persisted in task files
- Any code or doc edits are verified with relevant checks
- No unsupported conclusion relies on memory alone
- Risks and blockers are recorded explicitly

## Out of Scope (explicit)

- Running the full end-to-end `workflow-audit` itself in this task unless the
  suitability check shows it is immediately appropriate and no separate
  follow-up task is needed
- Repairing unrelated workflow features outside the `workflow-audit`
  compatibility path
- Treating adversarial or security-only bypass behavior as the default defect
  model

## Technical Notes

- Relevant source-of-truth files:
  - `.trellis/spec/skills/workflow-audit.md`
  - `.agents/skills/workflow-audit/SKILL.md`
  - `docs/workflows/新项目开发工作流/commands/workflow_assets.py`
- Relevant prior evidence likely lives under `.trellis/tasks/archive/2026-05/`
  in `workflow-repair-log.md`, `closure-round-*.md`, and older audit reports.
