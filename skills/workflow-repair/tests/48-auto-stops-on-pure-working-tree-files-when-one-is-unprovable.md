# 48 Auto Stops On Pure Working-Tree Files When One Is Unprovable

## Purpose

Verify that `workflow-repair --auto` stops when a pure working-tree-file
confirmation contains even one file that fails the normal scope or proof rules.

## Input

User input:

> Run `/workflow-repair --auto`. Repairs succeed. A later close-out confirmation enumerates only unrecognized working-tree files, without listing task artifacts or proposed commit batches. At least one listed file cannot be independently proved as part of the current repair task scope.

## Expected Mode

Auto follow-through blocked because one listed working-tree file is unprovable.

## Expected Key Behaviors

- apply the same mixed-scope / proof rules even when no task artifacts appear
- stop as soon as one listed file fails eligibility
- report the blocker without auto-confirming the rest of the list

## Must Not

- must not reply `ok` when any one listed file is out-of-scope or unprovable
- must not treat the absence of task artifacts as a reason to weaken proof
  requirements
- must not continue to commit or finish-work after this blocker
