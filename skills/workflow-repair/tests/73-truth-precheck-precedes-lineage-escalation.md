# 73 Truth Precheck Precedes Lineage Escalation

## Purpose

Verify that `workflow-repair` checks whether a reported problem is real before
escalating a repeated same-lineage report to audit when the report points at
existing temp-project evidence files.

## Input

User input:

> Run `/workflow-repair`. The current report uses the same
> `source-report` / `temp-project-root` / `trellis-version` lineage as two
> earlier repair tasks. The report findings point at existing temp-project
> files. Reading those files and the matching source workflow surfaces shows
> that every finding is a false alarm or expected gated/template-runtime state.

Example false-alarm families:

- retained `.codex/agents/*.toml` files while installed docs and config
  explicitly disable agent/subagent dispatch
- empty `.codex/skills/` while `.agents/skills/` is documented as the shared
  workflow skills primary carrier
- absent task-local `finish-work-checklist.md` in a fresh temp project where
  `.trellis/workflow-docs/finish-work-checklist-template.md` exists and no task
  has reached delivery / finish-work readiness

## Expected Mode

Read-only truth precheck before cross-task convergence escalation.

## Expected Key Behaviors

- validate the report and same-version temp project as usual
- read every existing `Temp Project Location` artifact needed to judge whether
  the finding survives the report claim
- read the relevant source workflow surface needed for focused content-level
  comparison
- classify false alarms as `ignored` before applying the cross-task lineage
  escalation gate
- write or summarize a task-local truth judgment / repair log that records the
  ignored decisions and source evidence
- skip source edits, closure rounds, and workflow version bump when all
  findings are ignored
- route to `workflow-audit` / `trellis-break-loop` only if one or more
  truth-surviving findings remain after this precheck and the same-lineage
  threshold is still met

## Must Not

- must not stop on the cross-task lineage gate before reading existing evidence
  files that can prove the reported problems are false
- must not mark a report as broader non-convergence when all findings fail the
  temp-project/source truth check
- must not adopt or repair a finding solely because it appears in a repeated
  same-lineage report
