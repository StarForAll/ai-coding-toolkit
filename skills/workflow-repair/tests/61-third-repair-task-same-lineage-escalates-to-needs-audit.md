# 61 Third Repair Task On Same Lineage Escalates To Needs-Audit

## Purpose

Verify that `workflow-repair` does not keep opening ordinary repair batches when
the same temp-project/report lineage has already produced two earlier repair
tasks.

## Input

User input:

> Run `/workflow-repair`. Two earlier dedicated repair tasks already consumed
> the same `source-report` / `temp-project-root` lineage and both ended as
> ordinary repair runs. A third ordinary repair attempt starts from the same
> lineage.

## Expected Mode

Cross-task convergence escalation instead of ordinary repair execution.

## Expected Key Behaviors

- inspect earlier repair-task logs across active tasks and archive
- determine that two earlier repair tasks already match the same lineage
- stop ordinary repair execution before applying source edits
- report the result as broader cross-task non-convergence / `needs-audit`
- direct the operator to `workflow-audit`, `trellis-break-loop`, or an
  equivalent broader closure step

## Must Not

- must not treat the third repair task as a fresh ordinary run
- must not continue into another adopted-fix batch
- must not write closure rounds or bump the workflow version for that blocked
  ordinary repair attempt
