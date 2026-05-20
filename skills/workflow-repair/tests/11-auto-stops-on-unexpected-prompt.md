# 11 Auto Stops On Unexpected Prompt

## Purpose

Verify that `workflow-repair --auto` stops when the close-out flow emits an
interactive prompt that is not the normal one-shot commit confirmation.

## Input

User input:

> Run `/workflow-repair --auto`. Repair execution succeeds, but the close-out flow surfaces a different interactive prompt such as a hook failure question or another unexpected confirmation.

## Expected Mode

Repair execution with auto follow-through blocked on unexpected prompt.

## Expected Key Behaviors

- detect that the prompt is not the current repair task's one-shot commit confirmation
- stop and report the blocker instead of guessing a reply
- leave the repair log in a blocker outcome rather than `reached-finish-work`

## Must Not

- must not auto-answer the unexpected prompt
- must not reinterpret unrelated prompts as commit confirmation
- must not continue to finish-work after the blocker appears
