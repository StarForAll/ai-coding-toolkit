# 63 Version Bump Does Not Reset Repair Lineage

## Purpose

Verify that an earlier successful workflow version bump does not hide an
ongoing cross-task incremental discovery loop on the same temp-project/report
lineage.

## Input

User input:

> Run `/workflow-repair`. Two earlier repair tasks already consumed the same
> temp-project/report lineage. One of those earlier tasks bumped
> `WORKFLOW_VERSION`, and the current report now targets the newer version, but
> the temp project and report lineage are still the same loop.

## Expected Mode

Cross-task convergence escalation that survives intermediate version bumps.

## Expected Key Behaviors

- recognize that workflow version bumps do not by themselves reset repair
  lineage
- match the current run to the earlier lineage using temp-project/report
  identity rather than treating the new version as a clean slate
- escalate the next ordinary repair attempt to audit / break-loop once the
  lineage threshold is reached

## Must Not

- must not use `base-workflow-version` equality (or `WORKFLOW_VERSION`
  equality) as the sole signal that a repair lineage is different
- must not allow repeated scan/repair loops to continue just because one
  earlier repair batch already bumped the workflow version
