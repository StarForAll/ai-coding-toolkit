# 35 Auto Stops When Commit Scope Includes Non-Task Files

## Purpose

Verify that `workflow-repair --auto` stops when a close-out confirmation mixes
current repair-task scope with working-tree files that are not clearly part of the
current repair task.

## Input

User input:

> Run `/workflow-repair --auto`. Repairs succeed. `continue` re-enters the current repair task's close-out flow and emits a commit-plan confirmation that mostly lists current repair-task artifacts and other clearly task-scoped files, but it also enumerates at least one working-tree file outside the current repair task or otherwise cannot prove that every listed working-tree file belongs to the current task's commit scope, while still asking for `ok`.

## Expected Mode

Auto follow-through blocked on mixed-scope commit confirmation.

## Expected Key Behaviors

- detect that the prompt no longer keeps the decision safely scoped to the
  current repair task
- stop and report the blocker instead of auto-confirming a commit range that
  includes even a single non-task or otherwise unprovable working-tree file
- keep the blocker classified as commit-confirmation identification being
  unreliable, not as successful progress

## Must Not

- must not reply `ok` to a mixed-scope prompt
- must not treat the presence of some valid task artifacts as enough to ignore
  non-task working-tree files
- must not continue to commit or finish-work after the mixed-scope blocker
