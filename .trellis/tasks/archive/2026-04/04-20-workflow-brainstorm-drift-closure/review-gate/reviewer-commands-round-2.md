# Reviewer Commands - Round 2

## Task

- Task ID: `04-20-workflow-brainstorm-drift-closure`
- Review root: `tmp/multi-cli-review/04-20-workflow-brainstorm-drift-closure`
- Review round: `2`
- Target path: `docs/workflows/新项目开发工作流`

## Round 2 Context

Round 1 reviewer feedback has already been aggregated and applied. The current fix set includes:

- Added post-install verification commands and a Codex dual-skills verification matrix
- Corrected helper-script inventory drift in `命令映射.md`
- Clarified `workflow-installed.json` / `bootstrap_cleanup_status` wording
- Tightened installer messaging around `.trellis/library-lock.yaml`
- Added `AGENTS.md workflow-nl-routing` drift detection and merge-time recovery to `upgrade-compat.py`
- Added regression tests covering the new `AGENTS.md` routing detection/recovery path

## Review Goal

Review the post-round-1 state and identify only **remaining** defects or regressions, especially:

- any remaining documentation drift across canonical docs, walkthrough docs, and the HTML mindmap
- any mismatch between docs and the current behavior of `install-workflow.py`, `upgrade-compat.py`, and related tests
- whether the new `AGENTS.md workflow-nl-routing` detection/recovery logic is documented and tested consistently
- whether the new post-install verification steps are now complete and non-contradictory
- whether the newly accepted fixes introduced fresh ambiguity around `.agents/skills/`, `.codex/skills/`, `library-lock.yaml`, or manual CLI-owned assets

Reviewer output must be a structured defect report only. Reviewers must not modify files and must not create directories.

## Reviewer Commands

Run these in other CLIs from the project root. The two commands are intentionally identical except for `--reviewer-id`.

```text
/multi-cli-review "Review the post-round-1 state for docs/workflows/新项目开发工作流. Identify any remaining documentation drift, new contradictions introduced by the latest fixes, mismatches with install-workflow.py / upgrade-compat.py / test_workflow_installers.py, and any incomplete closure around AGENTS.md workflow-nl-routing detection, post-install verification, Codex skills boundary, library-lock.yaml semantics, or manual CLI-owned assets. Output a structured defect report only; do not modify files." "docs/workflows/新项目开发工作流" --task-dir "tmp/multi-cli-review/04-20-workflow-brainstorm-drift-closure" --reviewer-id "claude-reviewer-r2" --round 2 --review-focus "post-round-1 regression check, remaining drift, AGENTS routing detection, installer/upgrade/test consistency"
```

```text
/multi-cli-review "Review the post-round-1 state for docs/workflows/新项目开发工作流. Identify any remaining documentation drift, new contradictions introduced by the latest fixes, mismatches with install-workflow.py / upgrade-compat.py / test_workflow_installers.py, and any incomplete closure around AGENTS.md workflow-nl-routing detection, post-install verification, Codex skills boundary, library-lock.yaml semantics, or manual CLI-owned assets. Output a structured defect report only; do not modify files." "docs/workflows/新项目开发工作流" --task-dir "tmp/multi-cli-review/04-20-workflow-brainstorm-drift-closure" --reviewer-id "opencode-reviewer-r2" --round 2 --review-focus "post-round-1 regression check, remaining drift, AGENTS routing detection, installer/upgrade/test consistency"
```

## Aggregation Command

After both reviewer reports are present under:

```text
tmp/multi-cli-review/04-20-workflow-brainstorm-drift-closure/review-round-2/
```

run this in the current CLI:

```text
/multi-cli-review-action --task-dir "tmp/multi-cli-review/04-20-workflow-brainstorm-drift-closure" --round 2
```
