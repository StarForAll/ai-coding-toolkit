# 29 Auto Mixed Surface Availability

## Purpose

Verify that `workflow-repair --auto` handles asymmetric surface availability
correctly when one close-out action uses a callable command surface while the
other action uses only a same-session skill surface.

## Input

User input:

> Run `/workflow-repair --auto`. Repairs succeed. The current platform/session exposes a callable `continue` command surface but no `finish-work` command surface. After the normal `continue` loop advances the repair task and commit succeeds, `finish-work` is available only as a same-session `trellis-finish-work` skill surface.

## Expected Mode

Auto follow-through with mixed command/skill surface availability.

## Expected Key Behaviors

- use the callable `continue` command surface without forcing a skill fallback
- fall back to the same-session `trellis-finish-work` skill surface only when
  `finish-work` later becomes necessary
- complete the close-out flow without misclassifying the mixed availability as
  a blocker

## Must Not

- must not require both surfaces to come from the same transport type
- must not fail just because only one of the two surfaces uses skill fallback
- must not skip normal `continue` progression before invoking finish-work
