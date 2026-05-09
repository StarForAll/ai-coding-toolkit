# 13 Runtime Execution Failure

## Purpose

Verify that `workflow-audit` stops with an explicit blocked state when Step D runtime execution fails before validation completes.

## Input

User input:

> Audit the embed flow of `docs/workflows/新项目开发工作流/` in full runtime mode. If `/tmp` setup or `trellis init` fails, report that failure instead of guessing the rest.

## Expected Mode

Task-based runtime mode blocked during Step D.

## Expected Key Behaviors

- enter task-based runtime mode through the normal A/B/C -> D path
- begin Step D and attempt the required runtime-validation commands
- if `trellis init` succeeds before the later failure, record and preserve the clean baseline snapshot as valid evidence
- if a later install or post-install step fails, mark the workflow-installed state as incomplete / unverified rather than pretending the install completed
- if `/tmp` project creation, `trellis init`, or another required runtime command fails, stop as `Blocked / Runtime Execution Failure`
- record the failing command, exit status, key stdout/stderr evidence, and what remains unverified

## Must Not

- must not continue later Step D commands after the blocking failure
- must not fabricate post-install conclusions after runtime execution failed
- must not discard a baseline snapshot that was already captured before the blocking failure
- must not treat partial installed-state files as a complete workflow-installed result
- must not discard already-collected A/B/C evidence
