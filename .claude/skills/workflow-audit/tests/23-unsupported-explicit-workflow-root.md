# 23 Unsupported Explicit Workflow Root

## Purpose

Verify that `workflow-audit` stops when the user supplies a single existing workflow path that is not the only supported workflow root.

## Input

User input:

> Audit `docs/workflows/旧项目重构工作流/` and confirm whether its workflow adaptation rules are correct.

## Expected Mode

Input-validation stop with unsupported-target blocking.

## Expected Key Behaviors

- resolve the requested workflow path before entering the evidence mainline
- detect that `docs/workflows/旧项目重构工作流/` exists on disk but is not the supported root `docs/workflows/新项目开发工作流/`
- stop as `Blocked / Invalid Input`
- report both the requested path and the supported path
- require the user to use `docs/workflows/新项目开发工作流/` before continuing

## Must Not

- must not proceed merely because the requested path exists
- must not silently remap the request to the default workflow root
- must not start A/B/C evidence gathering for the unsupported workflow root
- must not create task artifacts
