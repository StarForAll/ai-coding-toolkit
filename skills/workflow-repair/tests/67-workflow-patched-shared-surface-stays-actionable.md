# 67 Workflow-Patched Shared Surface Stays Actionable

## Purpose

Verify that `workflow-repair` keeps a workflow-patched shared surface in the
normal verification path when the temp project shows patch ownership evidence.

## Input

User input:

> Run `/workflow-repair` on a validated `WORKFLOW_QUESTIONS.md` where one
> finding points at a shared-carrier surface under `.agents/skills/` that
> carries workflow patch markers or other temp-project evidence showing that
> the embedded workflow patched that surface.

## Expected Mode

Conservative repair intake with temp-project ownership re-check before any
adopted-fix execution.

## Expected Key Behaviors

- repair-side intake must treat patch markers or equivalent temp-project patch
  evidence as ownership proof
- the item must remain actionable when the reported contradiction survives the
  re-check
- the correction plan must not explain the finding away purely on carrier
  location

## Must Not

- must not default the item to `ignored` merely because the surface still
  lives under a shared carrier directory
- must not require a non-shared carrier path before allowing normal repair
  verification
