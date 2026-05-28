# 66 Workflow-Owned Shared Surface Stays Actionable

## Purpose

Verify that `workflow-repair` does not downgrade a finding merely because the
affected surface lives under a shared carrier when the temp project does show
current workflow ownership of that surface.

## Input

User input:

> Run `/workflow-repair` on a validated `WORKFLOW_QUESTIONS.md` where one
> finding points at a shared skill surface under `.agents/skills/`, and the
> temp project's install record, patch markers, or installed workflow docs
> explicitly show that the current workflow owns or manages that surface.

## Expected Mode

Conservative repair intake with temp-project ownership re-check before any
adopted-fix execution.

## Expected Key Behaviors

- repair-side intake must re-check the shared surface against temp-project
  ownership evidence
- the item must stay in the normal verification path rather than being ignored
  solely because it lives under a shared carrier
- if the contradiction remains concrete after re-check, the correction plan may
  still present an adopted or trellis-native fix

## Must Not

- must not downgrade the finding to `ignored` solely because the file lives
  under `.agents/skills/`
- must not treat shared-carrier location as a negative ownership proof when
  the temp project explicitly shows current workflow ownership
