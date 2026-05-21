# 49 Auto Reports All Triggered Blocker Causes

## Purpose

Verify that `workflow-repair --auto` reports every triggered blocker cause when
one close-out confirmation violates multiple blocker rules at the same time.

## Input

User input:

> Run `/workflow-repair --auto`. Repairs succeed. A later close-out confirmation asks for `ok`, but it both mixes non-task working-tree files into the scope and describes the result as if all fixes were verified.

## Expected Mode

Auto follow-through blocked with multi-cause blocker reporting.

## Expected Key Behaviors

- detect each applicable blocker cause instead of picking only one
- report both mixed-scope and misleading-result wording in the blocker reason
- stop the close-out flow without auto-confirming any part of the prompt

## Must Not

- must not collapse multiple triggered blocker causes into a single generic
  label
- must not report only one cause when the prompt clearly triggers more than one
- must not continue to commit or finish-work after the multi-cause blocker
