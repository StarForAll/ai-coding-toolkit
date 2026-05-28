# 08 Classifies Repair Eligibility Before Emitting Findings

## Purpose

Verify that `workflow-scan` does not emit every suspicious observation as an
implicitly repairable defect. The final `WORKFLOW_QUESTIONS.md` contract must
distinguish between:

- `confirmed-defect`
- `design-debt`
- `evidence-gap`

## Input

User input:

> Run `/workflow-scan` against an embedded temp project where one installed runtime surface clearly contradicts another installed runtime surface, one observation is only a complexity / maintainability concern without a concrete installed-workflow contradiction, and one observation looks suspicious but cannot yet be confirmed from the temp project evidence alone.
>
> Also include one carrier that is still present on disk, but whose installed
> workflow docs explicitly say it is intentionally gated off for now and kept
> only as a compatibility or future-reenable surface.

## Expected Mode

Inline scan in the current CLI session using the shared v4 report contract.

## Expected Key Behaviors

- the coordinator must still write one `WORKFLOW_QUESTIONS.md`
- each finding must include the shared finding-level classification field
- the contradiction item must be classified as `confirmed-defect`
- the complexity-only item must be classified as `design-debt`
- the insufficient-evidence item must be classified as `evidence-gap`
- the intentionally gated-but-present carrier item must be omitted from the
  `### WS-NNN` finding set unless the temp project shows a separate
  contradiction
- the analysis summary must make the three classes visible so repair-side
  intake can stay conservative by default

## Must Not

- `workflow-scan` must not silently upgrade `design-debt` or `evidence-gap`
  into a repair-ready defect
- must not omit the finding-level repair classification just because severity,
  category, or origin is already present
- must not emit a standalone finding whose only basis is that the retained
  carrier remains on disk while the installed workflow explicitly marks it as
  currently disabled
