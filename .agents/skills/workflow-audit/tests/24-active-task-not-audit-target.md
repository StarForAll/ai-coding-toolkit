# 24 Active Task Not Audit Target

## Purpose

Verify that `workflow-audit` does not treat an already-active task directory as the workflow target when the user omits `workflow_path`.

## Input

User input:

> We already have an active task open in this repository. Audit this workflow for obvious source-level drift, but keep it static for now.

## Expected Mode

Lightweight mode.

## Expected Key Behaviors

- resolve the omitted target to `docs/workflows/新项目开发工作流/`
- keep any active task directory as runtime context only, not as the workflow root
- report `docs/workflows/新项目开发工作流/` as the audit target in the output
- continue with the normal A/B/C static evidence mainline against the supported workflow root

## Must Not

- must not reinterpret the active task directory as `workflow_path`
- must not ask the user to choose between the active task and the supported workflow root
- must not report the active task directory as the audited workflow root
