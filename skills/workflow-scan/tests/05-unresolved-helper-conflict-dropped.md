# 05 Unresolved Helper Conflict Dropped

## Purpose

Verify that when two helper agents both return structurally valid but mutually
conflicting claims, and the coordinator's local re-check still cannot resolve
the dispute, the disputed claim is dropped conservatively rather than guessed
through.

## Input

User input:

> Run `/workflow-scan --agent`. Two helper agents each return a valid handoff for the same workflow slice, but their claims conflict. The coordinator re-checks the temp-project evidence locally and still cannot determine which claim is correct.

## Expected Mode

Agent-assisted scan with coordinator-side conservative conflict drop.

## Expected Key Behaviors

- treat both helper handoffs as candidate evidence only, not as final findings
- perform a local temp-project re-check in the coordinator session
- if the local re-check still leaves the dispute unresolved, drop the disputed
  claim from final findings instead of guessing
- continue the scan if the remaining evidence still supports a valid
  `WORKFLOW_QUESTIONS.md`

## Must Not

- must not arbitrarily choose one helper's claim without local confirmation
- must not merge conflicting helper claims into one synthesized finding
- must not upgrade unresolved helper disagreement into a workflow defect by
  itself
