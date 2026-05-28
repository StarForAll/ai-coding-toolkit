# 17 Finish Work Checklist Template Is Not Missing Runtime File

## Purpose

Verify that `workflow-scan` does not emit a workflow finding merely because a
fresh temp project contains the installed shared
`.trellis/workflow-docs/finish-work-checklist-template.md` template but does
not yet contain a generated task-local `finish-work-checklist.md`.

## Input

User input:

> Run `/workflow-scan` against an embedded temp project where `.trellis/workflow.md`
> says `finish-work-checklist.md` records current close-out evidence,
> `.trellis/workflow-docs/finish-work-checklist-template.md` exists and is
> listed in `.trellis/workflow-installed.json` `workflow_shared_docs`, and no
> active or completed task has reached delivery / finish-work close-out.

## Expected Mode

Inline scan in the current CLI session using the shared v4 report contract.

## Expected Key Behaviors

- inspect `.trellis/workflow.md`, `.trellis/workflow-docs/`, and
  `.trellis/workflow-installed.json` together
- recognize that `finish-work-checklist-template.md` is an installed shared
  template rather than the task-local evidence file itself
- recognize that `finish-work-checklist.md` is generated later by a task that
  reaches delivery / finish-work readiness
- omit this observation from the `### WS-NNN` finding set when no task is at
  the gate requiring the generated checklist

## Must Not

- must not classify the missing task-local `finish-work-checklist.md` as
  `confirmed-defect` merely because the installed template has a different
  filename
- must not require the runtime checklist file to exist immediately after
  workflow install
- must not describe the template/runtime filename distinction as an install
  record contradiction when `workflow_shared_docs` correctly lists the template
