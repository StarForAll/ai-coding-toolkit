# 41 Auto Allows Task-Dir Files Without Current-Run Proof

## Purpose

Verify that `workflow-repair --auto` does not require separate current-run
output proof for files already inside the current repair task directory when
the close-out prompt clearly scopes them to the current task.

## Input

User input:

> Run `/workflow-repair --auto`. Repairs succeed. The current repair task directory already contains older task-local files from a previous run, such as an older repair log, and the later close-out confirmation enumerates those files together with this run's task artifacts as part of the current task's commit scope while asking for `ok`.

## Expected Mode

Auto follow-through allowed for task-directory artifacts without extra
current-run proof.

## Expected Key Behaviors

- treat task-directory membership plus explicit current-task scoping as
  sufficient for task-local files
- avoid demanding repair-log proof for files that are already inside the
  current repair task directory
- continue to apply stricter independent-proof checks only to files outside the
  task directory

## Must Not

- must not stop solely because a task-directory file was created by an earlier
  run rather than the current run
- must not require out-of-directory proof rules for task-directory artifacts
- must not broaden acceptance to outside-task files that still lack proof
