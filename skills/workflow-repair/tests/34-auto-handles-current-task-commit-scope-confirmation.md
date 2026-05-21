# 34 Auto Handles Current Task Commit-Scope Confirmation

## Purpose

Verify that `workflow-repair --auto` treats an explicit current-task
commit-plan/scope confirmation as eligible for the one-shot `ok` reply, even
when the prompt enumerates proposed commits, only those unrecognized dirty
working-tree files that are explicitly framed as part of the current repair task's commit
scope, or current repair-task artifacts.

## Input

User input:

> Run `/workflow-repair --auto`. Repairs succeed. `continue` re-enters the current repair task's close-out flow and emits a commit-plan confirmation that lists proposed commits, names current repair-task artifacts such as `check.jsonl`, `implement.jsonl`, and `task.json` as part of the current task scope, frames any listed unrecognized working-tree files as belonging to that same current repair task scope, and explicitly asks to reply `ok` if that commit range is acceptable.

## Expected Mode

Main-session repair with auto follow-through through current-task commit-scope
confirmation.

## Expected Key Behaviors

- detect that the prompt is still the current repair task's close-out
  confirmation even though it enumerates commit batches and task-local
  artifacts
- reply `ok` exactly once because the prompt keeps the decision scoped to the
  current repair task and explicitly asks for yes/confirm style approval
- continue through the later close-out steps after commit instead of stopping
  on a false ambiguity blocker

## Must Not

- must not treat unrelated working-tree-file prompts as eligible when current-task
  scope is not explicit
- must not treat mixed-scope prompts that also enumerate non-task working-tree files
  as eligible
- must not broaden commit scope beyond the current repair task
- must not stop merely because task-local artifacts appear inside the
  confirmation prompt
- must not accept prompts whose wording would overstate the actual repair
  result
