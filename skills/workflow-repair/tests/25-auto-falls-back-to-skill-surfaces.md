# 25 Auto Falls Back To Skill Surfaces

## Purpose

Verify that `workflow-repair --auto` does not stop just because the current
platform/session lacks callable Trellis command surfaces, as long as matching
same-session skill surfaces exist for the current project/runtime.

## Input

User input:

> Run `/workflow-repair --auto`. The repair run succeeds, but this current platform/session does not expose callable `/trellis:continue` or `/trellis:finish-work` command surfaces. The current project/runtime does expose same-session `trellis-continue` and `trellis-finish-work` skill surfaces.

## Expected Mode

Auto follow-through using skill-surface fallback for both `continue` and
`finish-work`.

## Expected Key Behaviors

- detect that the callable command surfaces are unavailable
- fall back to the same-session `trellis-continue` skill surface for close-out
  re-entry
- fall back to the same-session `trellis-finish-work` skill surface when
  `continue` later recommends finish-work
- avoid reporting a false "missing command surface" blocker

## Must Not

- must not require a command surface when the matching skill surface exists
- must not skip the `continue` loop just because fallback is using skills
- must not simulate a different ad-hoc close-out path

## Coverage Note

This scenario intentionally covers the symmetric case where both `continue`
and `finish-work` fall back to same-session skill surfaces. Mixed-surface
availability cases are covered separately and must not be inferred solely from
this test.
