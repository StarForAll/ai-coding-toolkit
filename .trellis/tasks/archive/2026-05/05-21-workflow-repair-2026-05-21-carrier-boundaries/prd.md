# PRD

## Background

`/tmp/trellis-0.5.17-2/WORKFLOW_QUESTIONS.md` still reports recurring carrier-boundary findings around:

- `.backup-original/` being treated as residual defects instead of intentional restore surfaces
- Claude/OpenCode "missing skills" being judged from skill directories alone instead of the command + skill surface together
- Codex `WS-008` over-weighting `.codex/skills/` and under-weighting `.agents/skills/` as the shared primary carrier

Recent repair history shows the same class of misunderstanding has already been addressed partially, but the maintainer-facing docs do not state the judgment rules explicitly enough to prevent re-reporting.

## Goal

Update workflow-source documentation under `docs/workflows/新项目开发工作流/` so future scans and maintainers can judge these surfaces correctly.

## Scope

- Clarify `.backup-original/` as an intentional backup/restore surface whose presence alone is not a defect
- Clarify Claude/OpenCode availability judgment must consider both their formal command carrier and the relevant skill carrier
- Clarify Codex availability judgment must treat `.agents/skills/` as the shared primary workflow skill carrier and `.codex/skills/` as a secondary carrier
- Keep changes documentation-only unless a directly coupled workflow-local verification surface also needs an update

## Non-Goals

- No installer behavior change
- No workflow-runtime behavior change
- No cross-repo skill rename or carrier migration

## Acceptance

1. Maintainer-facing boundary docs explicitly describe the above three judgment rules.
2. Platform README files for Claude/OpenCode/Codex align with the same wording.
3. The repair run records a correction plan, repair log, and issue-history summary.
