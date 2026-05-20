# 24 Auto Mixed Success And Reverted

## Purpose

Verify that `workflow-repair --auto` may still continue when some executed
fixes succeed while others fail verification and are reverted.

## Input

User input:

> Run `/workflow-repair --auto`. Multiple fixes enter execution. At least one fix verifies successfully, while at least one other fix later fails verification and is reverted.

## Expected Mode

Auto follow-through allowed after mixed succeeded/reverted execution results.

## Expected Key Behaviors

- count the executed fixes in `total-attempted`
- keep the successful fixes as succeeded and the failed ones as reverted
- allow auto follow-through to continue only because `total-succeeded > 0`
- keep the reverted work visible enough that the resulting commit does not
  imply every attempted repair succeeded

## Must Not

- must not collapse reverted fixes into implicit success
- must not stop only because some executed fixes were reverted, when valid
  succeeded fixes still remain
- must not let the final commit message or close-out summary imply that all
  attempted fixes passed verification
