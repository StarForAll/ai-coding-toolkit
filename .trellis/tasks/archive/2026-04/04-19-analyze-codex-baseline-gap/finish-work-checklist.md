# Finish Work Checklist

## Task

- Task directory: `.trellis/tasks/04-19-analyze-codex-baseline-gap`
- Scope: Codex workflow skills active-directory boundary fix and follow-up doc/spec sync
- Active task pointer: not set (`.trellis/.current-task` absent at verification time)

## Verification Matrix

| Check | Command or Method | Result |
|------|--------------------|--------|
| Python syntax / compile sanity | `/ops/softwares/python/bin/python3 -m py_compile docs/workflows/新项目开发工作流/commands/install-workflow.py docs/workflows/新项目开发工作流/commands/upgrade-compat.py docs/workflows/新项目开发工作流/commands/uninstall-workflow.py docs/workflows/新项目开发工作流/commands/test_workflow_installers.py` | PASS |
| Workflow installer regression module | `cd docs/workflows/新项目开发工作流/commands && /ops/softwares/python/bin/python3 -m unittest test_workflow_installers` | PASS |
| Diff whitespace / patch formatting | `git diff --check` | PASS |
| trellis-library validation | Not applicable: no files under `trellis-library/` changed | NOT RUN |
| trellis-library CLI unit tests | Not applicable: no files under `trellis-library/` changed | NOT RUN |

## Code-Spec Sync

- Updated `.trellis/spec/scripts/workflow-installer-upgrade-contracts.md` to record the new Codex active-directory contract:
  - distributed workflow skills sync to every existing Codex skills directory
  - `start` / `finish-work` patches only apply to the active skills directory
  - uninstall / force-restore / drift-check keep the same boundary

## Docs Sync

- Updated workflow docs to match the implemented boundary:
  - `docs/workflows/新项目开发工作流/commands/codex/README.md`
  - `docs/workflows/新项目开发工作流/CLI原生适配边界矩阵.md`
  - `docs/workflows/新项目开发工作流/目标项目兼容升级方案指导.md`

## Cross-Layer Notes

- Changed layers:
  - workflow source scripts under `docs/workflows/新项目开发工作流/commands/`
  - workflow docs under `docs/workflows/新项目开发工作流/`
  - repo-local code-spec under `.trellis/spec/scripts/`
- Hidden deployment directories in this repository root were not edited in this round; this change stays at source-of-truth and source-spec layers.

## Evidence Gaps

- No additional manual runtime install to a fresh `/tmp` fixture was rerun after the final doc/spec-only follow-up edits.
- No commit was created.
