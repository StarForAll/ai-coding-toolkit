# 01 Lightweight Static

## Purpose

Verify that `workflow-audit` remains in lightweight mode for a pure document/static-check scenario and does not escalate incorrectly into the task-based path.

## Input

User input:

> Check whether `docs/workflows/新项目开发工作流/` has obvious document-structure, command-doc, or rule-propagation issues. Do not do `/tmp` validation yet.

## Expected Mode

Lightweight mode.

## Expected Key Behaviors

- execute evidence mainline steps A (understand mechanics), B (static evidence), and C (gap analysis) first
- do not execute step D (runtime validation)
- produce step E output using the simplified template structure (sections for steps A, B, C)
- do not create a task
- do not create `prd.md`
- do not create `audit-report.md`
- do not enter `/tmp`
- do not run `trellis init`
- do not run embed / install / post-install verification
- if no issue is confirmed, explicitly allow the conclusion that no change-worthy issue is currently confirmed

## Must Not

- must not enter task-based mode when static-only checks are sufficient
- must not pre-decide mode before executing steps A/B/C
- must not silently escalate into the task-based path
- must not begin formal embed validation
- must not treat candidate issues as confirmed defects
- must not start modifying workflow source files
