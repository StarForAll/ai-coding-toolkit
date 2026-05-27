# 62 Legacy Repair Log Fallback Still Catches Lineage Loop

## Purpose

Verify that cross-task loop detection still works when earlier repair logs
predate explicit lineage fields such as `repair-lineage-key`.

## Input

User input:

> Run `/workflow-repair`. Two earlier repair-task logs exist for the same temp
> project lineage, but they only record legacy fields such as `source-report`
> and `trellis-version` and do not contain explicit lineage metadata.

## Expected Mode

Cross-task convergence escalation with legacy fallback matching.

## Expected Key Behaviors

- fall back to legacy matching on `source-report` + `temp-project-root` +
  `trellis-version`
- avoid claiming `no-prior-task-evidence` merely because older logs lack new
  lineage fields
- stop the third ordinary repair attempt and escalate to audit / break-loop

## Must Not

- must not require every earlier repair log to already contain
  `repair-lineage-key`
- must not silently continue the loop because the lineage metadata format was
  introduced later
