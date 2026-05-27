# 57 Unresolved In-Scope Closure Finding Blocks Close-Out

## Purpose

Verify that `workflow-repair` refuses close-out when closure still contains a
new in-scope finding that has not been absorbed or otherwise resolved.

## Input

User input:

> Run `/workflow-repair --auto`. The initial confirmed repair succeeds, but
> closure round 1 discovers one new in-scope same-family finding that remains
> unresolved at the end of the round.

## Expected Mode

Bounded closure repair flow with close-out gating.

## Expected Key Behaviors

- write the repair log and the current closure-round artifact
- mark the unresolved closure finding as in scope
- stop automatic close-out and do not invoke commit confirmation or
  `finish-work`
- do not bump the workflow version

## Must Not

- must not treat an unresolved in-scope closure finding as a mere note
- must not continue to close-out just because the original scan findings were fixed
