# 32 Auto Mixed Surface Availability Reversed

## Purpose

Verify that `workflow-repair --auto` also handles the reverse asymmetric
surface case where `continue` is available only through a same-session skill
surface while `finish-work` is available as a callable command surface.

## Input

User input:

> Run `/workflow-repair --auto`. Repairs succeed. The current platform/session has no callable `continue` command surface, but a same-session `trellis-continue` skill surface is available. Later in the close-out flow, `finish-work` is available as a callable command surface.

## Expected Mode

Auto follow-through with reversed mixed command/skill surface availability.

## Expected Key Behaviors

- fall back to the same-session `trellis-continue` skill surface for close-out
  re-entry
- use the callable `finish-work` command surface once `continue` later
  recommends finish-work
- complete the close-out flow without misclassifying the reversed mixed
  availability as a blocker

## Must Not

- must not require `continue` and `finish-work` to use matching transport
  types
- must not fail just because only `continue` needs skill fallback
- must not bypass normal `continue` progression before invoking finish-work
