# 38 Auto Allows Provable Write-Scope Files Outside Task Dir

## Purpose

Verify that `workflow-repair --auto` may continue when a close-out
confirmation enumerates files outside the current repair task directory, as
long as those files are independently provable outputs of the current repair
run inside the skill's allowed write-scope locations.

## Input

User input:

> Run `/workflow-repair --auto`. Repairs succeed. The current run records repaired workflow source files under `docs/workflows/新项目开发工作流/`, writes the current task artifacts, and may also write the current run's optional `tmp/workflow-issues/NNNN.md` audit-shadow file. A later close-out confirmation enumerates some combination of those paths, explicitly frames them as part of the current repair task's commit scope, and asks for `ok`.

## Expected Mode

Auto follow-through allowed because every enumerated file is independently
provable as part of the current repair run's allowed write-scope outputs.

## Expected Key Behaviors

- treat workflow source files repaired by the current run as eligible even
  though they live outside the current task directory
- treat the current run's own optional `tmp/workflow-issues/NNNN.md`
  audit-shadow output as eligible when it is enumerated in the commit scope
- require repair-log-backed independent proof for every enumerated out-of-
  directory path before replying `ok`

## Must Not

- must not stop solely because an enumerated file is outside the current task
  directory
- must not accept files outside the current run's provable write-scope outputs
- must not broaden acceptance to unrelated files merely because some external
  paths are provably in scope
