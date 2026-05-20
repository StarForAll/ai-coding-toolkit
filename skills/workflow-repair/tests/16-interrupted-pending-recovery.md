# 16 Interrupted Pending Recovery

## Purpose

Verify that a later run repairs stale `pending` continuation state by marking
it as `interrupted: session-did-not-complete` before recording the newer final
outcome.

## Input

User input:

> Resume `/workflow-repair --auto` for the same repair task after a previous run was interrupted between Step 11 and Step 12, leaving the older repair log at `Auto Follow-Through Outcome: pending`.

## Expected Mode

Resumed auto-follow-through run with stale-pending recovery.

## Expected Key Behaviors

- detect the older `pending` continuation state
- rewrite that stale state to `interrupted: session-did-not-complete`
- record the newer continuation outcome after the recovery step

## Must Not

- must not leave the older continuation state at `pending`
- must not overwrite the newer outcome with the stale value
- must not skip the recovery step when the same task is resumed
