# 26 Auto Stops When Continue Surface Missing

## Purpose

Verify that `workflow-repair --auto` stops before blind close-out when neither
the command surface nor the same-session skill surface for `continue` is
available.

## Input

User input:

> Run `/workflow-repair --auto`. Repairs succeed, but this current platform/session exposes neither a callable `continue` command surface nor a same-session `trellis-continue` skill surface.

## Expected Mode

Auto follow-through blocked on missing `continue` surface.

## Expected Key Behaviors

- check for a callable `continue` command surface first
- fall back to a same-session `trellis-continue` skill surface if present
- stop and report a blocker only after both surfaces are unavailable

## Must Not

- must not jump directly from repair summary to `finish-work`
- must not pretend `continue` exists when neither surface is available
- must not keep looping or guessing a substitute re-entry path
