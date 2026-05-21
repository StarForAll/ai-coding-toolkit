# 27 Auto Continue Closes Task

## Purpose

Verify that `workflow-repair --auto` recognizes the case where re-entering the
current task through `continue` causes the repair task itself to close, so the
loop stops without forcing another `continue` or a fake finish-work step.

## Input

User input:

> Run `/workflow-repair --auto`. Repairs succeed. Auto follow-through re-enters the current repair task through `continue`, handles the normal one-shot commit confirmation or an equivalent explicit current-task commit-scope confirmation, and on the next `continue` call the task is reported as already completed/closed with no remaining close-out work.

## Expected Mode

Auto follow-through completed via normal task closure reached through
`continue`.

## Expected Key Behaviors

- re-enter the current repair task through `continue`
- reply `ok` only to the repair task's one-shot commit confirmation or
  eligible explicit current-task commit-scope confirmation
- detect that a later `continue` reports the repair task as already closed
- record a successful final outcome for normal task closure rather than a
  blocker

## Must Not

- must not keep invoking `continue` after the task is clearly closed
- must not claim `reached-finish-work` when finish-work was never run
- must not treat normal task closure as an error
