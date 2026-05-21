# 54 Evidence-Gap Findings Stop Before Source Repair

## Purpose

Verify that `workflow-repair` refuses to treat insufficiently evidenced scan
findings as safe source-side repair candidates.

## Input

User input:

> Run `/workflow-repair` on a validated `WORKFLOW_QUESTIONS.md` using the
> shared protocol where at least one finding is classified as `evidence-gap`.
> The report says the temp project observation looks suspicious but cannot yet
> confirm a real defect or a source-owned root cause.

## Expected Mode

Conservative repair intake that stops evidence-gap items before source-edit
execution.

## Expected Key Behaviors

- repair-side intake must accept the report schema
- the `evidence-gap` item must not be auto-adopted
- the correction plan must stop the item at `blocked` or `manual-decision`
- repair-side verification must require further temp-project proof, broader
  audit evidence, or an explicit user decision before any source edit is
  allowed for that item

## Must Not

- the run must not claim that `evidence-gap` findings are part of the normal
  repair-ready set
