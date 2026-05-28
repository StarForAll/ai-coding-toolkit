# 13 Workflow-Patched Shared Surface Enters Actionable Finding Set

## Purpose

Verify that `workflow-scan` treats a shared-carrier surface patched by the
embedded workflow as part of the actionable finding set when that patched
surface itself is contradictory or incomplete.

## Input

User input:

> Run `/workflow-scan` against an embedded temp project where a shared-carrier
> surface under `.agents/skills/` carries a workflow patch marker or other
> temp-project proof that the embedded workflow modified it, and the patched
> content still contains a contradiction or missing strong-gate rule.

## Expected Mode

Inline scan in the current CLI session using the shared v4 report contract.

## Expected Key Behaviors

- treat the workflow patch marker or equivalent temp-project evidence as
  sufficient proof that the surface is workflow-managed
- include the observation in the actionable `### WS-NNN` finding set
- classify the finding as `workflow-source`
- provide investigation guidance aimed at the workflow source that produced the
  patched surface

## Must Not

- must not omit the finding merely because the patched file is still stored
  under a shared carrier directory
- must not treat an explicitly workflow-patched shared surface as an external
  baseline carrier
