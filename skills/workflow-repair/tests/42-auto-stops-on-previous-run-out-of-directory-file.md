# 42 Auto Stops On Previous-Run Out-Of-Directory File

## Purpose

Verify that `workflow-repair --auto` stops when a close-out confirmation
enumerates an out-of-directory workflow file that was changed by a previous
repair run but is not recorded as an output of the current run.

## Input

User input:

> Run `/workflow-repair --auto`. Repairs succeed. A later close-out confirmation enumerates one workflow source file under `docs/workflows/新项目开发工作流/` that was changed by a previous repair run but was not changed in the current run. The prompt frames that file as part of the current task scope and asks for `ok`, but the current run's repair log does not list it as a changed, written, or output file.

## Expected Mode

Auto follow-through blocked because previous-run out-of-directory work lacks
current-run proof.

## Expected Key Behaviors

- require current-run repair-log evidence for out-of-directory files
- reject prompt framing alone when the file belongs to an earlier run
- report the blocker as failed independent scope proof rather than as success

## Must Not

- must not reply `ok` to an out-of-directory file that only a previous run can
  explain
- must not treat prior-run workflow edits as current-run outputs without
  current-run repair-log evidence
- must not continue to commit or finish-work after this blocker
