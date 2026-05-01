# 01 Lightweight Static

## Purpose

Verify that `workflow-audit` remains in lightweight mode for a pure document/static-check scenario and does not escalate incorrectly into the non-trivial path.

## Input

User input:

> Check whether `docs/workflows/新项目开发工作流/` has obvious document-structure, command-doc, or rule-propagation issues. Do not do `/tmp` validation yet.

## Expected Mode

Lightweight mode.

## Expected Key Behaviors

- do not create a task
- do not create `prd.md`
- do not enter `/tmp`
- do not run `trellis init`
- do not run embed / install / post-install verification
- produce the simplified structured output
- if no issue is confirmed, explicitly allow the conclusion that no change-worthy issue is currently confirmed

## Must Not

- must not silently escalate into the non-trivial path
- must not begin formal embed validation
- must not treat candidate issues as confirmed defects
- must not start modifying workflow source files
