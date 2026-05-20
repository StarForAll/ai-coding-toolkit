# PRD

## Goal

Correct the `workflow-scan` skill so it analyzes the full set of workflow
content currently used inside a Trellis temp project, without depending on or
comparing against the current source repository.

## Problem

The current `workflow-scan` contract incorrectly requires source-repo files such
as `commands/shell/init-trellis-temp-project.sh` and
`docs/workflows/新项目开发工作流/commands/workflow_assets.py`.

That design makes the scan behave like a source-vs-installed comparison, while
the intended behavior is a temp-project-only runtime/worktree scan over the
installed workflow surfaces actually present in the temp project.

## Required Outcomes

1. `workflow-scan` no longer requires or references source-project-root input.
2. `workflow-scan` scans the temp project's current workflow surfaces only.
3. The shared `WORKFLOW_QUESTIONS.md` template no longer requires source-repo
   metadata or source-repo evidence-layer semantics.
4. Paired `workflow-repair` intake assumptions remain consistent with the new
   scan report contract.
5. Repo-local skill specs under `.trellis/spec/skills/` stay aligned with the
   updated contract.

## Non-Goals

1. Do not redesign `workflow-repair` scope beyond the minimum needed to keep the
   shared contract consistent.
2. Do not change workflow product source files under
   `docs/workflows/新项目开发工作流/`.

## Acceptance Criteria

1. `skills/workflow-scan/SKILL.md` defines a temp-project-only boundary.
2. `skills/workflow-scan/references/scan-output-template.md` removes required
   source-project fields and source-repo comparison assumptions.
3. Any paired contract wording in `skills/workflow-repair/` and
   `.trellis/spec/skills/` matches the new boundary.
4. `./scripts/validate-skills.sh` passes.
