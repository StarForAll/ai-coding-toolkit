# 31 Auto Continue Closes Task Before Commit

## Purpose

Verify that `workflow-repair --auto` recognizes the case where the very first
`continue` re-entry already reports the repair task as closed, before any
commit-confirmation prompt appears.

## Input

User input:

> Run `/workflow-repair --auto`. Repairs succeed. On the first `continue` re-entry, the current repair task is reported as already completed/closed with no remaining close-out work, and no commit-confirmation prompt appears first.

## Expected Mode

Auto follow-through completed immediately via normal task closure reached
through the first `continue` re-entry.

## Expected Key Behaviors

- re-enter the current repair task through `continue`
- detect that the first `continue` result already closes the task
- record a successful final outcome for normal task closure without waiting for
  commit confirmation

## Must Not

- must not wait for a commit-confirmation prompt that never appears
- must not invoke another `continue` after the task is clearly closed
- must not claim `reached-finish-work` when finish-work was never run
