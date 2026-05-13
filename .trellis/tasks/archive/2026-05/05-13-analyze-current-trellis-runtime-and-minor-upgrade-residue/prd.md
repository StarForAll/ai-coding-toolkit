# PRD: Analyze Current Trellis Runtime And Minor Upgrade Residue

## Goal

Produce a deep, evidence-based analysis of the Trellis runtime that is actually in use in this repository, then review the current minor-version upgrade residue from the live working tree and determine whether the retained edits are correct, incomplete, or regressive.

## Scope

This analysis must target the repository's live Trellis runtime surfaces:

- `.trellis/`
- `.agents/skills/trellis-*`
- `.codex/`
- `.claude/`
- `.opencode/`
- `.qoder/`
- `.kiro/`

It must **not** treat `docs/workflows/新项目开发工作流/` as the runtime source of truth for this task, except where a file in the live runtime explicitly references it.

## Required Analysis

1. Explain the current Trellis work and usage mechanism in this repository:
   - developer/session bootstrap
   - workflow phase guidance
   - active-task resolution
   - task lifecycle
   - context loading and injection
   - platform-specific agent/hook differences
   - workspace/journal recording
   - finish-work / continue / before-dev / check / research relationships
2. Analyze the current Trellis minor upgrade changes from `git status` / `git diff`.
3. For every `.new`-style upgrade decision implicated by the current changes, classify the correct treatment:
   - discard
   - merge
   - replace/overwrite
   - already settled / no further action
4. Judge whether the current non-`.new` modifications are correct.
5. Identify omissions, regressions, inconsistent phase numbering, broken repair attempts, or partially applied upgrade logic.

## Constraints

- Phase numbering in the final analysis must use the repository's original live numbering from `.trellis/workflow.md`.
- `trellis-research` must be used for research evidence gathering, and it should use `ace` and other relevant tools where useful.
- Conclusions must be tied to live files, command output, or current diffs.

## Deliverable

A structured review that includes:

- runtime mechanism map
- file-by-file upgrade review
- `.new` handling recommendations
- missing/faulty repair findings
- verification boundaries and residual risks
