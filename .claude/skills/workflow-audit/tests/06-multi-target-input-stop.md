# 06 Multi-target Input Stop

## Purpose

Verify that `workflow-audit` refuses to proceed when the input mentions multiple workflow targets and requires the user to choose one explicit `workflow_path`.

## Input

User input:

> Audit both `docs/workflows/新项目开发工作流/` and `docs/workflows/旧项目重构工作流/` and tell me which one has adaptation issues first.

## Expected Mode

Input-contract stop before evidence mainline execution.

## Expected Key Behaviors

- detect that more than one workflow target was supplied
- stop before starting the evidence mainline
- require the user to choose exactly one explicit workflow target
- do not infer priority order or choose one target on the user's behalf

## Must Not

- must not start A/B/C evidence gathering for multiple targets
- must not silently pick one workflow root
- must not produce mixed findings across two workflow roots
