# 53 Design-Debt Findings Do Not Auto-Enter Repair

## Purpose

Verify that `workflow-repair` does not auto-adopt findings whose report-side
classification is `design-debt`.

## Input

User input:

> Run `/workflow-repair` on a validated `WORKFLOW_QUESTIONS.md` using the
> shared protocol where at least one finding is classified as `design-debt`.
> The report describes a complexity / maintainability concern but does not show
> a concrete installed-workflow contradiction or broken behavior.

## Expected Mode

Conservative repair intake with report-side repair classification enforced
before any adopted-fix execution.

## Expected Key Behaviors

- repair-side intake must accept the report schema
- the `design-debt` item must not enter normal adopted-fix execution by default
- the correction plan must surface the item as non-default repair work
- the item must resolve to `manual-decision` or `ignored`, unless the current
  user instruction explicitly broadens scope beyond confirmed defects

## Must Not

- no source edit may be justified solely by the existence of the `design-debt`
  label
