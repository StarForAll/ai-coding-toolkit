# 11 Invalid Workflow Path

## Purpose

Verify that `workflow-audit` stops immediately when its single supported workflow root is missing from the repository checkout.

## Input

User input:

> Audit this workflow, but assume the repository checkout no longer contains `docs/workflows/新项目开发工作流/`.

## Expected Mode

Input-validation stop with invalid-path blocking.

## Expected Key Behaviors

- bind the target to `docs/workflows/新项目开发工作流/`
- detect that the supported root is missing on disk
- stop as `Blocked / Invalid Input`
- explain that the repository checkout is missing the supported workflow root and must be repaired before the audit can continue

## Must Not

- must not silently fall back to the default workflow root
- must not start A/B/C evidence gathering for a nonexistent workflow
- must not create task artifacts
