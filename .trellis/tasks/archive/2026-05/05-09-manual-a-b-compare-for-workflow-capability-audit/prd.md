# manual-a-b-compare-for-workflow-capability-audit

## Goal

Use the user-provided real Trellis init baseline projects at `/tmp/trellis-0.5.9-1` and `/tmp/trellis-0.5.9-2` to perform a real A/B compatibility-style comparison for `docs/workflows/新项目开发工作流/`. Keep `A` as the untouched Trellis init baseline, install the current workflow into `B`, then judge whether the workflow still looks normally adaptable or shows structural-break-like signals when compared against the real baseline.

## What I already know

- The user explicitly asked to ignore the formal version gate and proceed with deep analysis.
- The user manually initialized two temporary project roots: `/tmp/trellis-0.5.9-1` and `/tmp/trellis-0.5.9-2`.
- Both roots currently contain Trellis init outputs only and both `.trellis/.version` files are `0.5.9`.
- `install-workflow.py` requires the target project to be a Git repo, to have run `trellis init`, and to satisfy the `origin` remote push-url preconditions before real install can proceed.
- The current repository rule model distinguishes workflow-managed surfaces from workflow-dependent Trellis-native carriers, and its structural-break heuristic currently escalates `present-but-gated` as a possible structural-break signal.

## Assumptions (temporary)

- The user wants a real install-based comparison even though it bypasses the formal `workflow-capability-audit` version gate.
- It is acceptable to minimally prepare the `/tmp` fixture repos so they satisfy install-time Git preconditions, without altering the source repository.
- `A` should remain baseline-only; only `B` should receive workflow installation.

## Open Questions

- none currently blocking from repo context

## Requirements (evolving)

- Verify both `/tmp` roots are equivalent Trellis init baselines before changing `B`.
- Preserve `A` as the untouched comparison baseline.
- Use the real workflow installer path on `B` rather than mocked audit fixtures.
- Capture any install blockers separately from compatibility conclusions.
- Base the final judgment on real filesystem evidence plus the current audit matrix/classification rules.

## Acceptance Criteria (evolving)

- [ ] The task records the real A/B audit setup and execution boundary.
- [ ] `A` and `B` baseline status is verified from actual `/tmp` project contents.
- [ ] `B` runs through the real embed validation/install/check chain or stops with explicit blocker evidence.
- [ ] The final conclusion distinguishes install/runtime blockers from structural-break-like compatibility findings.
- [ ] The final report cites concrete file/command evidence from the real `/tmp` fixtures.

## Definition of Done (team quality bar)

- Tests added/updated (unit/integration where appropriate)
- Lint / typecheck / CI green
- Docs/notes updated if behavior changes
- Rollout/rollback considered if risky

## Out of Scope (explicit)

- Modifying the source workflow implementation itself
- Promoting `COMPATIBLE_TRELLIS_VERSION`
- Creating or destroying fresh canonical workflow-capability-audit fixtures

## Technical Notes

- Relevant source files:
  - `docs/workflows/新项目开发工作流/commands/install-workflow.py`
  - `docs/workflows/新项目开发工作流/commands/detect-embed-state.py`
  - `docs/workflows/新项目开发工作流/commands/upgrade-compat.py`
  - `docs/workflows/新项目开发工作流/commands/workflow-capability-audit.py`
  - `docs/workflows/新项目开发工作流/commands/workflow_assets.py`
- Real baseline fixtures:
  - `/tmp/trellis-0.5.9-1`
  - `/tmp/trellis-0.5.9-2`
- Current blocker already observed:
  - the `/tmp` roots are not yet Git repos, so installer preconditions are not satisfied as-is
