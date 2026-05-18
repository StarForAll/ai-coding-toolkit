# fix trellis 0.5.17 runtime contract drift

## Goal

Repair the live Trellis runtime contract used in this repository so the
workflow docs, per-turn breadcrumb behavior, and maintainer references match
the actual runtime again after the 0.5.17 alignment work.

## What I already know

- The live runtime surface is `.trellis/` plus the platform hook/plugin files
  under `.claude/`, `.codex/`, `.opencode/`, and `.qoder/`.
- `task.py start` still enters degraded mode and advances `task.json.status`
  to `in_progress` when no session identity is available.
- `workflow.md` currently documents a different behavior: fail with a session
  identity hint and retry.
- The hooks still emit `stale_<source_type>` statuses, but the dedicated
  `[workflow-state:stale]` guidance block was removed, so stale sessions now
  fall back to the generic "Refer to workflow.md" message.
- `workflow.md` and several `trellis-meta` reference files point at missing
  paths: `.trellis/spec/cli/backend/workflow-state-contract.md` and
  `.trellis/scripts/inject-workflow-state.py`.

## Assumptions (temporary)

- The correct fix is to align docs and breadcrumb behavior with the live
  runtime instead of changing `task.py start` semantics in this task.
- `stale` remains a useful runtime state and should keep dedicated repair
  guidance.
- The right reference targets are existing live files in this repository, not
  a new speculative spec subtree.

## Open Questions

- None currently blocking; repo inspection already resolved the key choices.

## Requirements

- Restore a dedicated stale workflow-state contract for live runtime users.
- Make breadcrumb builders map stale runtime statuses back to the stale
  workflow-state block.
- Update `.trellis/workflow.md` so the current-task mechanism and Phase 1.4
  instructions describe the actual degraded-mode runtime behavior.
- Remove or replace all broken references to missing workflow-state contract
  files/scripts in live maintainer docs touched by this runtime surface.
- Add regression tests that fail on these drift classes.

## Acceptance Criteria

- [ ] `workflow.md` no longer claims `task.py start` fails when no session
      identity exists if the runtime still degrades and advances status.
- [ ] stale task pointers produce dedicated stale guidance instead of the
      generic fallback text.
- [ ] touched live docs reference existing files only.
- [ ] regression tests cover stale mapping and reference validity.
- [ ] targeted test suite passes.

## Definition of Done (team quality bar)

- Tests added or updated first for the changed behavior.
- Relevant runtime tests pass.
- No agent dispatch is introduced; Codex stays inline.
- Documentation and runtime behavior say the same thing for the touched paths.

## Out of Scope (explicit)

- Renaming `trellis-spec-bootstarp`.
- Reworking the whole active-task model.
- Product workflow docs under `docs/workflows/新项目开发工作流/`.
- Git commit / archive / finish-work handling in this turn.

## Technical Notes

- Primary files expected: `.trellis/workflow.md`,
  `.trellis/scripts/common/tests/test_workflow_phase_contracts.py`,
  `.claude/hooks/inject-workflow-state.py`,
  `.codex/hooks/inject-workflow-state.py`,
  `.qoder/hooks/inject-workflow-state.py`,
  `.opencode/plugins/inject-workflow-state.js`,
  `.agents/skills/trellis-meta/references/customize-local/change-task-lifecycle.md`,
  `.claude/skills/trellis-meta/references/customize-local/change-task-lifecycle.md`,
  `.opencode/skills/trellis-meta/references/customize-local/change-task-lifecycle.md`,
  `.qoder/skills/trellis-meta/references/customize-local/change-task-lifecycle.md`.
