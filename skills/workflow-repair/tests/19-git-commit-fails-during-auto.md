# 19 Git Commit Fails During Auto

## Purpose

Verify that `workflow-repair --auto` handles mechanical `git commit` failure as
a blocker without pretending the task was closed out.

## Input

User input:

> Run `/workflow-repair --auto`. Repairs succeed, but the close-out flow reaches `git commit` and that command fails mechanically because of a hook rejection, conflict, or another commit-time error.

## Expected Mode

Auto follow-through blocked on commit failure.

## Expected Key Behaviors

- stop the close-out flow when `git commit` fails
- record and report the commit failure as the blocker
- leave the repair changes in place rather than pretending the task was closed out

## Must Not

- must not report a successful commit
- must not continue to finish-work after commit failure
- must not auto-revert the repair changes unless a separate explicit rule requires it
