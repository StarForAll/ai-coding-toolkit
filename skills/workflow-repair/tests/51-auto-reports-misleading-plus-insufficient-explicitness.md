# 51 Auto Reports Misleading Plus Insufficient Explicitness

## Purpose

Verify that `workflow-repair --auto` reports multiple blocker causes when a
prompt is both misleading about results and insufficiently explicit about
current-task scope.

## Input

User input:

> Run `/workflow-repair --auto`. Repairs succeed partially. A later close-out confirmation asks for `ok`, phrases the scope only as `commit these changes`, and also implies that all fixes were verified.

## Expected Mode

Auto follow-through blocked with multiple blocker causes reported.

## Expected Key Behaviors

- detect both insufficient explicit current-task scoping and misleading
  repair-result wording
- report both causes in the blocker reason
- stop the close-out flow without auto-confirming any part of the prompt

## Must Not

- must not collapse the blocker into only one reported cause
- must not treat generic scope wording as rescued by otherwise honest context
- must not continue to commit or finish-work after the multi-cause blocker
