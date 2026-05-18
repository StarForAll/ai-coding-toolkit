# PRD: Fix workflow install post-check drift

## Goal

Fix the installer bug that leaves a fresh target project's `.trellis/workflow.md` with the old `Current-task mechanism` contract, causing the installer's own post-install `upgrade-compat.py --check` to fail with `.trellis/workflow.md: 项目化补丁内容漂移` even though the target project started from a clean Trellis baseline.

## What I already know

- The failure reproduces on a fresh `/tmp` Git repo after `trellis init` followed by the standard embed chain.
- The target project is correctly marked failed because the installer's final self-check returns non-zero and leaves `.trellis/workflow-embed-attempt.json`.
- The concrete mismatch is the residual old sentence `flips \`task.json.status\` from \`planning\` to \`in_progress\`` in the embedded `.trellis/workflow.md`.
- `upgrade-compat.py --check` intentionally rejects that old sentence as drift.
- The current failure is in source-repo installer logic, not in the temporary target project setup.

## Requirements

- Fix the source installer so a fresh embed no longer leaves the old `Current-task mechanism` wording in target-project `.trellis/workflow.md`.
- Add or update automated regression coverage for this exact failure mode.
- Keep the fix scoped to the installer / workflow-doc patching path; do not weaken the post-install self-check and do not change the first-embed blocking protocol.
- After code changes and local verification, stop and let the user run manual end-to-end testing on a fresh temporary project.
- Do not proceed with any follow-up execution beyond local verification until the user explicitly reports the manual test has no issue.

## Non-Goals

- Do not repair the already-failed `/tmp/trellis-0.5.17-2` fixture in place.
- Do not change the documented rule that a failed embed leaves the target project in `BLOCKED_NON_INITIAL_STATE`.
- Do not introduce `--merge`, `--force`, or uninstall as part of the fresh embed mainline.

## Acceptance Criteria

- A targeted regression test fails before the fix and passes after the fix.
- The installer source no longer emits the stale `Current-task mechanism` text in fresh embedded `workflow.md`.
- Relevant automated verification for the changed files passes locally.
- The user receives explicit manual test steps for a fresh temporary target project.
- Work pauses after handing off manual test steps; no extra execution is performed until the user confirms the manual test result.

## Technical Notes

- Primary files: `docs/workflows/新项目开发工作流/commands/install-workflow.py`, `docs/workflows/新项目开发工作流/commands/test_workflow_installers.py`.
- Related contract/spec files:
  - `.trellis/spec/scripts/workflow-installer-upgrade-contracts.md`
  - `.trellis/spec/scripts/python-conventions.md`
  - `.trellis/spec/guides/cross-layer-thinking-guide.md`
- Likely root cause: the replacement of `_BASELINE_WORKFLOW_TASK_MECHANISM` with `_STRONG_GATE_WORKFLOW_TASK_MECHANISM` is applied only in a specific code path and misses the actual fresh install output shape.
