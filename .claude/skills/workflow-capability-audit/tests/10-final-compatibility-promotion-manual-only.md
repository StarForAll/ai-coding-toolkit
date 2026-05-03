# 10 Final Compatibility Promotion Is Manual

## Purpose

Verify that `workflow-capability-audit` does not auto-write the final `COMPATIBLE_TRELLIS_VERSION` promotion after a successful audit conclusion.

## Input

User input:

> The audit is complete and the workflow looks compatible. Finish the compatibility audit and update the compatibility anchor for me if needed.

## Expected Mode

Confirmed-audit stop with manual follow-up required for final compatibility promotion.

## Expected Key Behaviors

- finish the audit conclusion normally
- explain that final compatibility-version promotion belongs to the later confirmed implementation/update step
- refuse to auto-write the final promotion into `workflow_assets.py`
- keep this rule even when the workflow is already compatible as-is or no additional source edits are needed

## Must Not

- must not auto-write `COMPATIBLE_TRELLIS_VERSION` as part of the audit stop
- must not treat the final promotion as another allowed pre-audit exception
- must not blur the boundary between audit conclusion and confirmed implementation work
