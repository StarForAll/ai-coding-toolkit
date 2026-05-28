# 72 Finish Work Checklist Positive Cases Stay Actionable

## Purpose

Verify that `workflow-repair` does not over-apply the
template/runtime-file false-positive guard. Real contradictions around
`finish-work-checklist-template.md` and task-local `finish-work-checklist.md`
must remain actionable after repair-side re-verification.

## Input

User input:

> Run `/workflow-repair` on validated `WORKFLOW_QUESTIONS.md` variants for the
> finish-work checklist contract:
>
> 1. The report says the installed
>    `.trellis/workflow-docs/finish-work-checklist-template.md` template is
>    missing even though installed workflow surfaces require it.
> 2. The report says a current task has reached delivery / finish-work
>    close-out readiness, installed validators require task-local
>    `finish-work-checklist.md`, and that runtime file is absent.
> 3. The report says an installed workflow surface explicitly requires
>    `finish-work-checklist.md` to exist immediately after install, but the
>    fresh temp project lacks that file.

## Expected Mode

Conservative repair intake with focused content-level verification before any
correction plan is drafted.

## Expected Key Behaviors

- read the relevant installed workflow document / skill / validator wording for
  each case
- keep the missing-template case in the normal verification path instead of
  downgrading it under the runtime-file guard
- keep the reached-gate missing-runtime-file case in the normal verification
  path because the runtime file is now required
- keep the immediate-after-install contradiction in the normal verification
  path because another installed surface explicitly requires that state
- adopt, mark `trellis-native`, block, or ask for manual decision according to
  the normal repair verification result for each positive case

## Must Not

- must not classify all `finish-work-checklist.md` absence reports as
  `ignored`
- must not skip source-side repair planning when the template itself is missing
  from the installed shared docs
- must not ignore a missing runtime checklist once a task has reached the gate
  where installed validators require it
