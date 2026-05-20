# 20 Auto With Preexisting Active Task

## Purpose

Verify that `workflow-repair --auto` creates or switches to a dedicated repair
task before execution, and that any later auto close-out applies to that repair
task rather than to an unrelated pre-existing active task.

## Input

User input:

> Run `/workflow-repair --auto` while another unrelated task is already active in the current session.

## Expected Mode

Main-session repair in a newly created or newly switched dedicated repair task,
with auto close-out scoped to that repair task only.

## Expected Key Behaviors

- detect the pre-existing active task
- create or switch into a dedicated repair task before repair execution
- keep all later commit confirmation / finish-work decisions scoped to that
  dedicated repair task

## Must Not

- must not reuse the unrelated pre-existing task for repair execution
- must not let auto close-out target the unrelated pre-existing task
- must not blur the dedicated repair-task boundary in summaries or logs
