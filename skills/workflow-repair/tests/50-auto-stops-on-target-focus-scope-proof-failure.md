# 50 Auto Stops On Target-Focus Scope-Proof Failure

## Purpose

Verify that `workflow-repair --auto --target_focus ...` still stops when an
enumerated out-of-directory file cannot be independently proved as part of the
current focused run.

## Input

User input:

> Run `/workflow-repair --auto --target_focus WS-002`. The focused repair succeeds, but a later close-out confirmation also lists one out-of-directory working-tree file that is not recorded as an output of the current focused run. The prompt asks for `ok`.

## Expected Mode

Auto follow-through blocked on failed independent scope proof under
`target_focus`.

## Expected Key Behaviors

- apply the same out-of-directory proof rule under `target_focus`
- stop even though the focused repair itself succeeded
- report the blocker as failed independent proof rather than as a generic
  `target_focus` problem

## Must Not

- must not relax scope-proof requirements just because the focused repair
  succeeded
- must not reply `ok` to the unprovable out-of-directory file
- must not continue to finish-work after this blocker
