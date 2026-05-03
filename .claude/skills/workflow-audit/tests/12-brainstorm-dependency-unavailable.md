# 12 Brainstorm Dependency Unavailable

## Purpose

Verify that `workflow-audit` stops cleanly when a task-based mode is required but the `trellis:brainstorm` entrypoint is unavailable.

## Input

User input:

> Run a full structured workflow audit for `docs/workflows/新项目开发工作流/` with task tracking, but the current environment does not have the `trellis:brainstorm` command available.

## Expected Mode

Task-based transition blocked by missing dependency.

## Expected Key Behaviors

- execute A/B/C first and determine that a task-based mode is required
- detect that the required `trellis:brainstorm` entrypoint is unavailable before entering task context
- stop as `Blocked / Dependency Unavailable`
- preserve the already-collected A/B/C evidence

## Must Not

- must not silently fall back to lightweight mode
- must not continue into task creation without the required control container
- must not discard the evidence already collected before the dependency check failed
