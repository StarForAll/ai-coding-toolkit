# 56 Schema Mismatch Is Invalid Embedded State

## Purpose

Verify that `workflow-repair` treats a matching workflow version with a
conflicting workflow schema version as invalid embedded state rather than as a
supported ordinary repair input.

## Input

User input:

> Run `/workflow-repair` on a report and temp project where all three workflow
> versions resolve to `0.1.2800`, but the report or temp-project record carries
> a different `workflow-schema-version` than the current source schema anchor.

## Expected Mode

Version-and-state preflight that stops before repair planning.

## Expected Key Behaviors

- detect that this state should not occur under a normal installer/upgrade path
- stop as `Blocked / Invalid Embedded State`
- treat the temp project or report as corrupted / half-upgraded / otherwise
  invalid for repair intake
- require the user to re-embed and re-run `workflow-scan`

## Must Not

- must not treat this as an acceptable same-version report
- must not silently prefer one schema version over the other
