# 58 New-Family Closure Finding Stops Auto Progression

## Purpose

Verify that `workflow-repair` does not silently broaden the current repair
batch when closure discovers a finding from a new family.

## Input

User input:

> Run `/workflow-repair`. Source-side fixes for the current scan findings
> succeed, but closure discovers a new finding whose `issue-family-id` does not
> match any currently absorbed family.

## Expected Mode

Bounded closure verification with anti-drift scope control.

## Expected Key Behaviors

- write a closure-round artifact that records the new-family finding
- mark the finding as `in-scope: no` for automatic absorption
- stop automatic progression of the current batch
- return control to a planning/decision checkpoint instead of silently fixing it

## Must Not

- must not auto-absorb the new family
- must not continue as if the current repair scope were unchanged
