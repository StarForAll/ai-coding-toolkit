# audit and repair embedded workflow source for temp project

## Goal

Use the embedded workflow runtime under `/tmp/trellis-0.5.17-2` as the primary
behavior evidence to audit whether `docs/workflows/新项目开发工作流/` still has
real maintenance defects, then repair only the confirmed defects within the
workflow source tree so future embeds behave correctly.

## What I already know

- The fix scope is restricted to `docs/workflows/新项目开发工作流/`.
- Task artifacts may be created and kept; they do not need deletion after the
  repair.
- The temp project `/tmp/trellis-0.5.17-2` is already a `trellis init` baseline
  with this workflow embedded, so it can be used as runtime evidence without
  performing a new embed.
- `docs/workflows/新项目开发工作流/commands/workflow_assets.py` declares
  `COMPATIBLE_TRELLIS_VERSION = "0.5.17"`, and `trellis -v` returned `0.5.17`,
  so the workflow-audit version gate passes.
- The installed temp-project `.trellis/workflow.md` is currently 558 lines and
  `.trellis/scripts/workflow/workflow-state.py` is currently 2812 lines.
- Prior repair history exists under `tmp/workflow-issues/0001.md` through
  `0012.md`, so repeated findings must be checked against earlier closure.

## Assumptions (temporary)

- The user wants direct execution after evidence-based confirmation and does not
  want a plan-only audit.
- If a problem is Trellis-native rather than workflow-source, the repair must
  still stay inside `docs/workflows/新项目开发工作流/` by adding or adjusting an
  installer patch/overlay rather than editing upstream Trellis files.
- Temp-project inspection may be read-only for this run unless a pre-existing
  report already exists there.

## Open Questions

- none at the moment; derive from repo and temp-project evidence first

## Requirements (evolving)

- Re-check the user-supplied candidate issues as hypotheses, not confirmed
  defects.
- Use `/tmp/trellis-0.5.17-2` as the main truth source for whether an issue
  really exists.
- Review same-pattern variants when a defect is confirmed and repair safe
  siblings in the workflow source together.
- Do not modify files outside `docs/workflows/新项目开发工作流/` plus this task's
  own artifacts.
- Do not introduce new behavior drift while reducing complexity or tightening
  contracts.
- Prefer source-side fixes that preserve installer/runtime closure and update
  aligned docs/tests in the same workflow directory when needed.

## Acceptance Criteria (evolving)

- [ ] Candidate complexity/structure issues are reclassified as confirmed defect,
      false alarm, or out-of-scope optimization based on evidence.
- [ ] Any confirmed defect has source-level root cause and impact scope recorded.
- [ ] All adopted fixes stay inside `docs/workflows/新项目开发工作流/`.
- [ ] Same-pattern variants within the workflow source are checked and fixed when
      safe.
- [ ] Relevant tests/validation commands are run and their pass/fail/not-run
      status is reported truthfully.

## Definition of Done (team quality bar)

- Relevant workflow tests updated or confirmed
- Validation commands executed where available
- Cross-file contract propagation completed inside the workflow directory
- Risks and remaining non-defects documented clearly

## Out of Scope (explicit)

- Editing repository files outside `docs/workflows/新项目开发工作流/`
- Editing upstream/native Trellis source outside the workflow source tree
- Re-embedding the workflow into a fresh temp project unless later proven
  strictly necessary
- Deleting existing task files or previous issue-history artifacts

## Technical Notes

- Primary source workflow root: `docs/workflows/新项目开发工作流/`
- Primary runtime evidence root: `/tmp/trellis-0.5.17-2`
- Prior issue history: `tmp/workflow-issues/*.md`
- Candidate issue themes from the user:
  - workflow.md / 总纲 complexity inflation
  - state-machine learning cost
  - patch-script count and `workflow-state.py` size
