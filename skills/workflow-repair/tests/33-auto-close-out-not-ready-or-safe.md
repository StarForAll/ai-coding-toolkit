# 33 Auto Close-Out Not Ready Or Safe

## Purpose

Verify that `workflow-repair --auto` stops when the current repair task is not
yet ready for commit or finish-work, or when close-out would otherwise be
unsafe.

## Input

User input:

> Run `/workflow-repair --auto`. Repairs succeed partially, but after Step 12 readiness evaluation the current repair task is not yet ready for commit or finish-work, or close-out would be misleading or unsafe.

## Expected Mode

Auto follow-through blocked because close-out is not ready or not safe.

## Expected Key Behaviors

- stop after the repair summary instead of forcing commit confirmation or
  finish-work
- explain the blocker in terms of close-out readiness or safety
- preserve the repair/task state without pretending close-out completed

## Must Not

- must not auto-confirm commits when close-out is not ready
- must not invoke finish-work when close-out is not safe
- must not report successful auto follow-through
