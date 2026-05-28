# 70 Disabled Command Active Absence Defaults To Ignored

## Purpose

Verify that `workflow-repair` defaults scan findings about missing active
disabled-command surfaces such as `parallel` to `ignored` when the temp
project's installed workflow contract explicitly removes that surface from the
active embedded state.

## Input

User input:

> Run `/workflow-repair` on a validated `WORKFLOW_QUESTIONS.md` where one
> finding says disabled command `parallel` has no active command/skill file,
> marker, or stub, but the temp project's installed workflow contract says
> `parallel` is intentionally disabled and removed from the active embedded
> surface.

## Expected Mode

Conservative repair intake with temp-project disabled-surface re-check before
any adopted-fix execution.

## Expected Key Behaviors

- repair-side intake must compare the finding against the install record and
  installed docs/runtime rules for disabled surfaces
- the item must resolve to `ignored` when active absence is the documented
  disabled state
- no source edit may be planned for that item unless another installed surface
  explicitly requires a retained marker or stub

## Must Not

- must not adopt the finding solely because no active `parallel` file exists
- must not require a `.disabled` marker, placeholder command file, or active
  skill stub when the temp-project contract does not require one
