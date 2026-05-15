# 09 Older-version Contract Violation

## Purpose

Verify that `workflow-capability-audit` aborts with a non-zero error when the current Trellis version is older than `COMPATIBLE_TRELLIS_VERSION`, because that state violates the workflow maintenance contract.

## Input

User input:

> Run the compatibility audit even though the current Trellis version is older than the workflow's recorded compatibility anchor.

## Expected Mode

Immediate contract-violation abort before the normal audit path.

## Expected Key Behaviors

- compare current and compatible versions semantically
- detect that `current < compatible`
- abort with a non-zero error instead of entering the normal gate-result or full-audit flow
- explain that the state violates the workflow maintenance contract

## Must Not

- must not emit a normal full-audit payload
- must not create a task or A/B fixtures
- must not treat the older-version state as a normal supported audit direction
