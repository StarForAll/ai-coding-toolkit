# 22 Implicit Default Workflow Root

## Purpose

Verify that `workflow-audit` resolves an omitted `workflow_path` to the fixed supported workflow root instead of inferring repo root, current project, active task, or another workflow directory.

## Input

User input:

> Audit this workflow for obvious document-structure or rule-propagation issues. Keep it static for now.

## Expected Mode

Lightweight mode.

## Expected Key Behaviors

- resolve the omitted target to `docs/workflows/新项目开发工作流/` before step A begins
- report the workflow root as `docs/workflows/新项目开发工作流/` in the lightweight output
- proceed with the normal A/B/C static evidence mainline against that fixed root
- remain in lightweight mode when no runtime-validation trigger is found

## Must Not

- must not treat repo root, current working directory, active task, or any sibling workflow directory as the audit target
- must not ask the user to choose among workflow roots when the omitted target can be resolved to the supported default
- must not skip explicit target resolution in the final output
