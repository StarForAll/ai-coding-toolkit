# 08 Auto Follow-Through Success

## Purpose

Verify that `workflow-repair --auto` may continue through the current repair
task's normal close-out flow after a successful repair run.

## Input

User input:

> Run `/workflow-repair --auto` on the validated report. Confirmed fixes succeed, the working tree is ready for commit, the close-out flow asks only for the normal one-shot commit confirmation or an equivalent explicit current-task commit-scope confirmation, and a Trellis finish-work command surface is available.

## Expected Mode

Main-session repair with auto follow-through into normal close-out.

## Expected Key Behaviors

- keep the normal repair verification flow unchanged before any auto close-out
- re-enter the current repair task through `continue` before and after commit
- reply `ok` only to the current repair task's one-shot commit confirmation or
  eligible explicit current-task commit-scope confirmation
- invoke the available Trellis finish-work surface only after `continue`
  recommends it
- update the repair log from `pending` to `reached-finish-work`

## Must Not

- must not bypass correction-plan presentation or post-repair verification
- must not auto-answer prompts unrelated to the current repair task's eligible
  commit confirmation
- must not broaden the close-out scope beyond the dedicated repair task
