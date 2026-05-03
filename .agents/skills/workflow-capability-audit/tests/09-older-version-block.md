# 09 Older-version Block

## Purpose

Verify that `workflow-capability-audit` terminates when the current Trellis version is older than `COMPATIBLE_TRELLIS_VERSION`.

## Input

User input:

> Check whether the workflow is compatible, but the current Trellis version is older than the workflow's recorded compatibility anchor.

## Expected Mode

Version-gate termination with unsupported-direction classification.

## Expected Key Behaviors

- compare current and compatible versions semantically
- detect that `current < compatible`
- classify the stop as `Blocked / Unsupported Direction`
- terminate before task creation and before A/B fixture setup

## Must Not

- must not treat the older-version direction as a normal full-audit case
- must not create task artifacts after the unsupported-direction result
- must not rewrite the compatibility anchor automatically
