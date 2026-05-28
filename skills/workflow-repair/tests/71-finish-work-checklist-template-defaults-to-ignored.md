# 71 Finish Work Checklist Template Defaults To Ignored

## Purpose

Verify that `workflow-repair` does not adopt a scan finding merely because an
installed workflow document references a later-generated task-local
`finish-work-checklist.md` while the fresh temp project only contains the
installed shared `.trellis/workflow-docs/finish-work-checklist-template.md`
template.

## Input

User input:

> Run `/workflow-repair` on a validated `WORKFLOW_QUESTIONS.md` where one
> finding says `.trellis/workflow.md` references `finish-work-checklist.md`,
> but the temp project only contains
> `.trellis/workflow-docs/finish-work-checklist-template.md`. The installed
> finish-work skill and workflow docs explain that the template is used to
> create a task-local checklist when a task reaches delivery / finish-work
> close-out, and no task is currently at that gate.

## Expected Mode

Conservative repair intake with content-level temp-project and source-file
verification before any adopted-fix execution.

## Expected Key Behaviors

- read the installed `.trellis/workflow.md` reference and surrounding close-out
  wording
- read the installed `.trellis/workflow-docs/finish-work-checklist-template.md`
  artifact
- read the relevant installed finish-work skill or workflow docs that explain
  the template-to-runtime-file generation path
- compare those temp-project surfaces with source workflow declarations such as
  `WORKFLOW_SHARED_DOCS`
- classify the finding as `ignored` when the template exists and no current
  task has reached the gate requiring the generated checklist
- record the ignored decision in the correction plan / repair log without
  planning a source edit

## Must Not

- must not adopt the finding solely because the scan report labeled it
  `confirmed-defect`
- must not treat the template filename and runtime evidence filename as a
  contradiction by themselves
- must not modify workflow source files when the installed surfaces already
  explain the generation path and no close-out gate is currently missing the
  generated file
