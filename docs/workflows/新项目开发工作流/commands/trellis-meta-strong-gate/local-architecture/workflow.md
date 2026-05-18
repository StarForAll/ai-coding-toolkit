<!-- workflow-embed-patch:trellis-meta-strong-gate -->

# Local Workflow System

`.trellis/workflow.md` is the Trellis workflow source of truth inside the user project, but for this installed workflow the live stage contract is the strong-gate model rather than the old three-phase status table.

## File Responsibilities

`.trellis/workflow.md` has three responsibilities:

1. Explain the installed workflow stages and their guardrails.
2. Define entry routing and next-action hints for each platform.
3. Provide `[workflow-state:...]` prompt blocks that hooks can inject for the current strong-gate stage.

## Current Stage Model

```text
feasibility -> brainstorm -> design -> plan -> implementation
-> test-first -> project-audit -> check -> review-gate
-> finish-work -> delivery -> record-session
```

The installed workflow does not use the old `planning / in_progress / completed` route table as its routing source of truth.

## Source Of Truth Chain

Use this chain to determine the current stage:

```text
.trellis/.runtime/sessions/<context>.json
  -> current active task
  -> $TASK_DIR/workflow-state.json.stage
```

Key implications:

- `task.json.status` is a legacy task-lifecycle field, not the stage-routing authority.
- `task.py start` refreshes the active-task pointer, but stage changes must still go through `workflow-state.py set`.
- `workflow-state.py route` is the authoritative router for `first_entry`, `reenter`, `blocked`, `awaiting_confirmation`, and `repair_needed`.

## Workflow-State Prompt Blocks

The injected block should match the current strong-gate stage, for example:

```text
[workflow-state:design]
...
[/workflow-state:design]
```

Typical live blocks are stage-based (`design`, `plan`, `finish-work`, `delivery`) plus `no_task`. Do not assume `planning` / `in_progress` / `completed` blocks remain meaningful after this workflow is installed.

## Local Modification Patterns

Common changes:

| Goal | Edit point |
| --- | --- |
| Add or rename a stage | `.trellis/workflow.md` plus `.trellis/scripts/workflow/workflow-state.py` |
| Change task creation policy | `[workflow-state:no_task]` block plus the entry skill/command patches |
| Change stage routing rules | `workflow-state.py route` and the corresponding continue/start carrier files |
| Change close-out flow | `finish-work`, `delivery`, `record-session`, and workflow-state gate logic together |
| Change platform differences | Update the relevant command/skill/hook carrier after the semantic change is defined |

## Close-Out Boundary

The current close-out chain is:

```text
finish-work -> delivery -> record-session
```

- `finish-work` freezes `finish-work-checklist.md` and close-out evidence.
- `delivery` handles acceptance and deliverables.
- `record-session` performs `task.py archive` plus `add_session.py`.

Do not describe `/trellis:finish-work` as the stage that archives the task or records the session.
