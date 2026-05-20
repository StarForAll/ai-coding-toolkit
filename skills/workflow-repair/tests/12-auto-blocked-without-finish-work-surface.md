# 12 Auto Blocked Without Finish-Work Surface

## Purpose

Verify that `workflow-repair --auto` stops when the current platform/session
does not provide any usable Trellis finish-work surface after the `continue`
loop has already advanced the repair task to the point where `finish-work`
should be resolved.

## Input

User input:

> Run `/workflow-repair --auto`. The repair run succeeds, the current repair task re-enters through `continue`, the normal commit confirmation is handled, a later `continue` call recommends `finish-work`, but this current platform/session exposes neither a callable finish-work command surface nor a same-session `trellis-finish-work` skill surface.

## Expected Mode

Repair execution with auto follow-through blocked at finish-work surface
resolution.

## Expected Key Behaviors

- allow the `continue` loop itself to proceed normally before the blocker
- detect that neither the finish-work command surface nor the same-session
  skill surface is available
- stop and report that missing finish-work surface as the blocker
- avoid inventing substitute wrap-up commands

## Must Not

- must not simulate finish-work with ad-hoc commands
- must not stop early at the `continue` step when `continue` itself is usable
- must not report successful auto follow-through
- must not hide the missing command surface behind a generic success summary
