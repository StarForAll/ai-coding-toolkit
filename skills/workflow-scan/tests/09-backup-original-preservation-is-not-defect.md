# 09 Backup-Original Preservation Is Not A Defect

## Purpose

Verify that `workflow-scan` does not emit a workflow defect merely because the
temp project contains `.backup-original/` trees under managed command/skill
carriers.

## Input

User input:

> Run `/workflow-scan` against an embedded temp project where `.agents/skills/.backup-original/` or another managed `.backup-original/` tree contains backup copies whose names pair cleanly with active patched/overlay assets recorded in `.trellis/workflow-installed.json`.

## Expected Mode

Inline scan in the current CLI session using the shared v4 report contract.

## Expected Key Behaviors

- the scan must inspect the backup tree together with the temp project's active
  carrier names and `.trellis/workflow-installed.json`
- when the backup copies pair cleanly with active patched/overlay assets, the
  scan must treat them as intentional restore surfaces rather than as residual
  defects
- the final report must not emit a `confirmed-defect` finding whose only basis
  is the presence of that valid `.backup-original/` tree

## Must Not

- must not classify a valid restore-surface backup tree as `residual`
- must not upgrade the mere presence of `.backup-original/` into a workflow
  defect when active-carrier pairing is intact
