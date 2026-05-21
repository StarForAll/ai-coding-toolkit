# 30 Auto Stops On Unreliable Commit Confirmation

## Purpose

Verify that `workflow-repair --auto` stops when the close-out flow surfaces a
prompt that might be the repair task's commit confirmation, but the skill
cannot identify it reliably enough to risk replying `ok`.

## Input

User input:

> Run `/workflow-repair --auto`. Repairs succeed and `continue` re-enters the current repair task, but the close-out flow now emits a prompt that looks somewhat like commit confirmation while never clearly tying the decision to the current repair task or clearly asking for a direct `ok`/yes reply, so one-shot commit-confirmation identification is unreliable.

## Expected Mode

Auto follow-through blocked on unreliable commit-confirmation identification.

## Expected Key Behaviors

- detect that the prompt cannot be identified reliably as the current repair
  task's one-shot commit confirmation or eligible explicit current-task
  commit-scope confirmation
- stop and report the blocker instead of risking over-confirmation
- avoid continuing to commit or finish-work after the unreliable prompt
- keep this blocker distinct from explicit current-task commit-scope
  confirmations that do ask for `ok`

## Must Not

- must not reply `ok` to the ambiguous prompt
- must not reinterpret the ambiguity as an unrelated prompt and keep going
- must not pretend the task advanced safely after stopping
