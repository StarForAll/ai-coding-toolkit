# 65 Non-Workflow-Owned Shared Baseline Finding Defaults To Ignored

## Purpose

Verify that `workflow-repair` does not adopt an older scan finding whose only
surface is a shared or external baseline skill living under an in-scope carrier
directory when the temp project does not show current workflow ownership of
that surface.

## Input

User input:

> Run `/workflow-repair` on a validated `WORKFLOW_QUESTIONS.md` where one
> finding points at a shared baseline skill under `.agents/skills/`, but the
> temp project's install record, patch markers, and installed workflow
> docs/runtime rules do not show that the current workflow claimed, patched, or
> changed that surface.

## Expected Mode

Conservative repair intake with temp-project ownership re-check before any
adopted-fix execution.

## Expected Key Behaviors

- repair-side intake must accept the shared protocol and re-check the finding
  against temp-project ownership evidence
- the shared-baseline item must resolve to `ignored`
- the correction plan must explain that carrier location alone did not prove
  workflow ownership
- no source edit may be planned for that item

## Must Not

- must not adopt the finding solely because the scan report labeled it as a
  defect
- must not treat shared-carrier placement alone as enough evidence to justify
  workflow-source remediation
