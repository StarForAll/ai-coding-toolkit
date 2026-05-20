# 09 Auto Stops On Zero Success

## Purpose

Verify that `workflow-repair --auto` stops when execution ran but no effective
repair succeeded.

## Input

User input:

> Run `/workflow-repair --auto`. The user confirms execution, but every attempted fix later fails or is reverted, so `total-succeeded = 0` and `total-attempted > 0`.

## Expected Mode

Repair execution with auto follow-through blocked before close-out.

## Expected Key Behaviors

- perform the requested repair execution and record the failed/reverted results
- stop auto follow-through after the repair summary
- record that no effective repair was made
- leave finish-work uninvoked

## Must Not

- must not treat failed or reverted fixes as a successful close-out candidate
- must not continue to commit confirmation or finish-work
- must not report `--auto` as a no-op when execution actually ran
