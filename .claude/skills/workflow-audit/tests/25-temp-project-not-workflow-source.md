# 25 Temp Project Not Workflow Source

## Purpose

Verify that `workflow-audit` keeps the temporary `/tmp` target-project root separate from the fixed workflow source root during runtime validation.

## Input

User input:

> Audit this workflow's embed flow, create a temporary project under `/tmp`, and verify that the audit keeps the temp project separate from the workflow source root when it reaches the manual embed-command boundary.

## Expected Mode

Task-based runtime mode.

## Expected Key Behaviors

- bind the workflow target to `docs/workflows/新项目开发工作流/` before task creation or `/tmp` project work begins
- treat the `/tmp` project root only as generated target-project context for step D evidence
- distinguish clean `trellis init` baseline evidence from workflow-installed-state evidence inside that generated target-project layer
- stop before executing the embed-chain commands itself and instead emit the manual shell command block for the user
- keep source-repo evidence and generated target-project evidence labeled separately
- report the workflow root and temporary target-project root as different boundaries in the audit report

## Must Not

- must not reinterpret the `/tmp` project root as the workflow source root
- must not run the embed-chain commands itself after the manual shell boundary is reached
- must not attribute clean baseline files to the workflow without comparing pre-install and post-install states
- must not use generated target-project files as a substitute for step A/B source-repo reading
- must not report the temporary target-project root as `workflow_path`
