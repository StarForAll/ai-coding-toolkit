# 60 Successful Repair Bumps Workflow Version

## Purpose

Verify that a successful `workflow-repair` run does not stop at source edits and
closure artifacts, but also advances the workflow's active repair version so the
next scan report can be invalidated as stale if it still targets the previous
workflow state.

## Input

User input:

> Run `/workflow-repair` on a validated same-version report. At least one
> finding is repaired successfully, closure converges cleanly, and no unresolved
> in-scope closure findings remain.

## Expected Mode

Successful repair with same-run version advancement.

## Expected Key Behaviors

- keep `report workflow version == temp-project install-record workflow version == current source WORKFLOW_VERSION`
  during intake and verification
- after closure converges, bump only the final numeric segment of
  `WORKFLOW_VERSION`
- synchronize the active current-version references in the same change
- write the repair log / closure artifact against the original base version,
  but report the new bumped version in the final summary
- ensure a later report still carrying the old version would now hit the stale
  report gate

## Must Not

- must not bump before closure converges
- must not leave current-version references half-updated
- must not consume a new version number when every attempted fix failed,
  reverted, or produced no remaining repair-side change
