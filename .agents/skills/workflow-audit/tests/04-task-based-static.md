# 04 Task-based Static

## Purpose

Verify that `workflow-audit` enters task-based static mode when `force_full_brainstorm: yes` but A/B/C findings do not indicate runtime validation is needed. The audit should create a task, enter trellis-brainstorm, maintain `prd.md` and `audit-report.md`, skip Step D, and output via `audit-report.md`.

## Input

User input:

> I want a full structured audit of `docs/workflows/新项目开发工作流/` with task tracking and audit report — use the trellis-brainstorm mainline. But I know the embed/install flow is fine, so no `/tmp` or `trellis init` needed. Static-only analysis is enough.

Interpreted as:
```yaml
workflow_path: docs/workflows/新项目开发工作流/
candidate_issues: []
need_runtime_validation: no
force_full_brainstorm: yes
allow_minor_version_mismatch: no
```

## Expected Mode

Task-based static mode (task + trellis-brainstorm + `prd.md` + `audit-report.md`, without Step D).

## Expected Key Behaviors

- execute evidence mainline steps A (understand mechanics), B (static evidence), and C (gap analysis)
- after Step C: recognize `force_full_brainstorm: yes` triggers task-based path
- before creating task context, explain why task-based static mode was chosen
- judge that Step D is NOT needed (none of the D trigger conditions are met from A/B/C findings)
- explain why task context is warranted and why Step D is not needed
- enter task-based static mode (NOT lightweight, NOT task-based runtime)
- create audit task with default title `workflow-audit: 新项目开发工作流`
- enter the `trellis-brainstorm` mainline as the control container
- maintain `prd.md` through the `trellis-brainstorm` path
- initialize `audit-report.md`, seeding it with Step A/B/C evidence tagged with source layers
- if task-based static mode still evaluates CLI adaptation, the resulting `audit-report.md` must record official-doc evidence, repo-local evidence, and practical development-use evidence for each in-scope CLI
- if any CLI is out of scope in that report, `not-applicable` plus a brief reason is sufficient; the detailed evidence trio is not required for that CLI
- if any `generated target project` evidence is already present in that seeded report, distinguish its `Stage` as clean baseline vs workflow-installed state
- skip Step D entirely — do NOT create `/tmp` project, do NOT run `trellis init`, do NOT execute embed chain
- if A/B/C findings were to indicate Step D is necessary, follow the escalation rule: output Needs Confirmation block and wait for user, do NOT auto-execute D
- output findings in Step E via `audit-report.md`
- stop with a controlled next-step recommendation
- do not manufacture optimization work for evidence-backed non-defects in the static report

## Must Not

- must not pre-decide mode before Step A/B/C
- must not enter lightweight static mode (task context is explicitly requested)
- must not switch into task-based static mode silently
- must not execute runtime validation (Step D) when findings do not justify it
- must not create `/tmp` project
- must not run `trellis init`
- must not emit the human-terminal-required block (D not reached)
- must not silently drop the task or trellis-brainstorm context
- must not output using the lightweight template
- must not auto-execute Step D even if A/B/C findings indicate it is needed
- must not treat a non-defective carrier difference as a default cleanup target in task-based static mode
