# 45 Auto Stops When Reverted File Is Still Claimed In Commit Scope

## Purpose

Verify that `workflow-repair --auto` excludes reverted files from the
independently provable output set during close-out.

## Input

User input:

> Run `/workflow-repair --auto`. Either a workflow source file outside the task directory or a task-directory artifact is modified during repair execution but later reverted during post-repair verification. A later close-out confirmation still lists that reverted file inside the proposed commit scope and asks for `ok`.

## Expected Mode

Auto follow-through blocked because the reverted file is not a remaining
current-run output.

## Expected Key Behaviors

- recognize that reverted files are not valid independently provable outputs
  for close-out, regardless of whether they live inside or outside the task
  directory
- stop when the prompt claims a reverted file will be committed
- report the blocker as failed independent proof, misleading scope, or both as
  applicable

## Must Not

- must not reply `ok` to a file that the current run reverted away
- must not treat repair-log history alone as enough when the file no longer
  remains in the current-run output set
- must not continue to finish-work after this blocker
