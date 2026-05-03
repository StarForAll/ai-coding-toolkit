# 11 Invalid Workflow Path

## Purpose

Verify that `workflow-audit` stops immediately when the resolved `workflow_path` does not exist on disk.

## Input

User input:

> Audit `docs/workflows/does-not-exist/` and confirm whether its workflow adaptation rules are correct.

## Expected Mode

Input-validation stop with invalid-path blocking.

## Expected Key Behaviors

- resolve the requested workflow path before entering the evidence mainline
- detect that the path does not exist on disk
- stop as `Blocked / Invalid Input`
- require the user to provide one valid workflow root before continuing

## Must Not

- must not silently fall back to the default workflow root
- must not start A/B/C evidence gathering for a nonexistent workflow
- must not create task artifacts
