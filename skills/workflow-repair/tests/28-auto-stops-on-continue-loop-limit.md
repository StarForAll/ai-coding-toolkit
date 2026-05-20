# 28 Auto Stops On Continue Loop Limit

## Purpose

Verify that `workflow-repair --auto` does not loop forever when `continue`
keeps re-entering the same repair task without reaching `finish-work`,
`reached-task-close`, or another clearly new close-out checkpoint.

## Input

User input:

> Run `/workflow-repair --auto`. Repairs succeed, `continue` is available, but the same repair task keeps re-entering through `continue` with no clear terminal outcome or clearly new close-out checkpoint for 5 consecutive re-entries.

## Expected Mode

Auto follow-through blocked on the bounded `continue` loop ceiling.

## Expected Key Behaviors

- count consecutive `continue` re-entries for the same repair task within the
  current auto-follow-through run
- stop and report a blocker once the configured ceiling is reached without a
  safe terminal outcome
- treat that ceiling as evidence that safe advancement can no longer be proved

## Must Not

- must not loop indefinitely
- must not mistake repeated non-terminal `continue` output for successful
  advancement
- must not skip directly to `finish-work` just to escape the loop
