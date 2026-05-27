# 59 Backup-Original Restore Surface Defaults To Ignored

## Purpose

Verify that `workflow-repair` does not auto-adopt a finding whose only claim
is that a managed `.backup-original/` carrier tree exists, when temp-project
evidence shows the copies are intentional restore surfaces.

## Input

User input:

> Run `/workflow-repair` on a validated `WORKFLOW_QUESTIONS.md` where one finding complains only about `.backup-original/` copies under a managed command/skill carrier, and the temp project's `.trellis/workflow-installed.json` plus active carrier names show those copies are paired restore surfaces for patched/overlay assets.

## Expected Mode

Conservative repair intake with temp-project-first verification.

## Expected Key Behaviors

- repair-side verification must re-check the active carrier names and install
  record pairing evidence
- the backup-copy finding must resolve to `ignored`
- no source-side fix may be proposed solely to remove a valid restore-surface
  `.backup-original/` tree

## Must Not

- must not auto-adopt the finding as a workflow defect
- must not propose deleting intentional restore-surface backups merely because
  they are hidden or unreferenced by runtime routing
