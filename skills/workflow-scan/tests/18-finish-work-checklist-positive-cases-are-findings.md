# 18 Finish Work Checklist Positive Cases Are Findings

## Purpose

Verify that `workflow-scan` still emits actionable findings for real
template/runtime-file contradictions instead of blindly ignoring every
`finish-work-checklist.md` absence.

## Input

User input:

> Run `/workflow-scan` against embedded temp-project variants for the
> finish-work checklist contract:
>
> 1. `.trellis/workflow.md` and installed finish-work guidance require the
>    template path, but `.trellis/workflow-docs/finish-work-checklist-template.md`
>    is missing.
> 2. A current task has reached delivery / finish-work close-out readiness and
>    installed validators require task-local `finish-work-checklist.md`, but
>    that runtime file is absent from the task.
> 3. An installed workflow surface explicitly claims `finish-work-checklist.md`
>    must exist immediately after install, but the fresh temp project does not
>    contain that file.

## Expected Mode

Inline scan in the current CLI session using the shared v4 report contract.

## Expected Key Behaviors

- distinguish each positive case from the ordinary fresh-install template case
- emit a `### WS-NNN` finding when the installed template is missing
- emit a `### WS-NNN` finding when a task is already at the gate requiring the
  generated checklist and the task-local file is absent
- emit a `### WS-NNN` finding when an installed surface explicitly requires the
  runtime checklist immediately after install but the file is absent
- classify each finding according to the strongest available evidence:
  `confirmed-defect` only when the contradiction is concrete, otherwise
  `evidence-gap`

## Must Not

- must not apply the template/runtime false-positive guard when the template is
  missing
- must not ignore a missing task-local checklist after the workflow gate that
  requires it has been reached
- must not ignore an installed-surface contradiction that explicitly requires
  the runtime file immediately after install
