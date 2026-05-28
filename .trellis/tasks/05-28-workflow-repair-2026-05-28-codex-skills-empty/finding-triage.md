# Finding Triage

## Scope

- Report: `/tmp/trellis-0.5.17-2/WORKFLOW_QUESTIONS.md`
- Temp project: `/tmp/trellis-0.5.17-2`
- Trellis version: `0.5.17`
- Workflow version: `0.1.2803`
- Purpose: judge whether each reported finding is a real workflow-source defect or a scan-side false problem.

## Summary

| Finding | Report Claim | Triage Result | Reason |
| --- | --- | --- | --- |
| WS-001 | `.codex/skills/` is empty while install record lists patched Codex skills | False problem | `.codex/skills/` is a secondary Codex-local carrier; shared workflow and baseline patched skills live in `.agents/skills/` for this install. |
| WS-002 | `workflow.md` references `finish-work-checklist.md` but only `finish-work-checklist-template.md` is installed | False problem | The installed template and task-local evidence file are intentionally different artifacts. A fresh installed project has the template before any task creates its own checklist. |

## WS-001: `.codex/skills/` Empty

### Verdict

False problem. No workflow-source repair is needed for the empty `.codex/skills/` directory.

### Evidence

- The temp project has an empty `.codex/skills/` directory.
- The same temp project has shared skills in `.agents/skills/`, including:
  - `.agents/skills/trellis-start/SKILL.md`
  - `.agents/skills/trellis-continue/SKILL.md`
  - `.agents/skills/trellis-finish-work/SKILL.md`
- The installed `.agents/skills/trellis-continue/SKILL.md` contains the workflow Phase Router patch.
- The installed `.agents/skills/trellis-finish-work/SKILL.md` contains the finish-work projectization patch.
- Source documentation in `docs/workflows/新项目开发工作流/commands/codex/README.md` states:
  - shared workflow skills are written only to `.agents/skills/`
  - `.codex/skills/` is for Codex-specific or project-local skills
  - `.codex/skills/` being empty does not by itself constitute shared workflow missing-install
  - `trellis-start` / `trellis-continue` / `trellis-finish-work` should be checked in `.agents/skills/` first
- Source installer/upgrade contract also defines `.codex/skills/` as Codex-local / duplicate-cleanup scope, not a required shared workflow skill deployment target.

### Why The Report Is Wrong

The report assumes that `patched_codex_skills` must imply files under `.codex/skills/`. That assumption is too narrow for the current Codex carrier model. For this workflow, the active skills directory is the shared `.agents/skills/` carrier, and the relevant patched skills are present there. There is no current requirement for an extra Codex-specific skill in `.codex/skills/`, so an empty `.codex/skills/` directory is valid.

### Follow-Up

This should be fixed in the scan-side classification rules, not in the workflow installer. A future scan should downgrade this pattern to ignored when:

- `.agents/skills/` contains the shared/patched workflow skills
- `.codex/skills/` has no Codex-specific expected skill declared by another contract
- the installed docs identify `.codex/skills/` as a secondary local/duplicate-cleanup carrier

## WS-002: `finish-work-checklist.md` vs `finish-work-checklist-template.md`

### Verdict

False problem. No workflow-source repair is needed for the template/runtime filename distinction.

### Evidence

- The temp project has `.trellis/workflow-docs/finish-work-checklist-template.md`.
- The temp project does not yet have a generated `finish-work-checklist.md`.
- Source documentation in `docs/workflows/新项目开发工作流/装后隐藏目录与托管边界核对清单.md` says `.trellis/workflow-docs/finish-work-checklist-template.md` must exist and is used as the fixed skeleton for generating a task-local `finish-work-checklist.md`.
- Source workflow guidance in `docs/workflows/新项目开发工作流/工作流总纲.md` says the current task should form `finish-work-checklist.md`, and if it has not yet generated the file, it may use `.trellis/workflow-docs/finish-work-checklist-template.md` as the skeleton.
- The installed `.agents/skills/trellis-finish-work/SKILL.md` tells the operator to create/update `finish-work-checklist.md`, and if absent, first use `.trellis/workflow-docs/finish-work-checklist-template.md` as the skeleton.
- Source constants list `finish-work-checklist-template.md` under `WORKFLOW_SHARED_DOCS`, meaning the template is the installer-managed shared document.
- Runtime validators check `finish-work-checklist.md` under the current task directory when delivery/finish-work gates are reached, not as a required root-level installed file immediately after embed.

### Why The Report Is Wrong

The report conflates two artifacts:

- `.trellis/workflow-docs/finish-work-checklist-template.md`: an installer-managed template distributed with the workflow
- `finish-work-checklist.md`: a task-local close-out evidence file created when a task reaches delivery/finish-work readiness

A freshly embedded temp project has no completed workflow task, so the absence of task-local `finish-work-checklist.md` is expected. The installed `workflow.md` line says the close-out evidence file records current task evidence; it does not require that file to preexist before a task has reached close-out.

### Follow-Up

This should be fixed in the scan-side rule so it does not treat the missing task-local checklist as an install defect when the template exists and no active/completed task is at delivery/finish-work close-out.

## Overall Judgment

Both findings are scan-side false positives under the current workflow contract. The correct action is to update scan/audit classification logic or prompt rules so it recognizes:

- Codex shared workflow skills are carried by `.agents/skills/`, while `.codex/skills/` is secondary and may be empty.
- `finish-work-checklist-template.md` is an installed template, while `finish-work-checklist.md` is task-local runtime evidence created later.
