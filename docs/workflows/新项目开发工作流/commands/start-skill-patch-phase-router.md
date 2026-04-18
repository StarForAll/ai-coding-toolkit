## Workflow Phase Router Patch `[AI]`

When this `start` skill is used in a target project that has installed `docs/workflows/新项目开发工作流`, treat it as the workflow Phase Router, not as the original generic Trellis task workflow.

### Hard Boundary

- Do not auto-advance across workflow stages.
- Do not enter implementation from `plan` unless the current leaf task has explicit user confirmation and `checkpoints.execution_authorized = true`.
- Use this state chain as the only source of truth:

```text
.trellis/.current-task
  -> current leaf task
  -> $TASK_DIR/workflow-state.json
```

If any part is missing or stale, stop in the recovery branch. Do not infer the active stage from the presence of `prd.md`, `task_plan.md`, `design/`, `check.md`, or chat history alone.

### First Entry Routing

For a newly embedded target project:

1. Run:

```bash
python3 ./.trellis/scripts/get_context.py
```

2. If this is a new project, new client, first project intake, feasibility/risk/pricing question, or there is no current task yet, route to the feasibility workflow:

```text
Use the `feasibility` skill.
```

3. If `.trellis/workflow-installed.json` exists but `.trellis/library-lock.yaml` is missing or does not contain `pack.requirements-discovery-foundation`, stop and repair the installation baseline before routing further.

### Existing Task Routing

When there is a current task, validate its state before resuming:

```bash
python3 .trellis/scripts/workflow/workflow-state.py validate <task-dir>
```

Then route only to the currently confirmed stage:

| `workflow-state.stage` | Allowed re-entry |
|------------------------|------------------|
| `feasibility` | Use the `feasibility` skill |
| `brainstorm` | Use the `brainstorm` skill |
| `design` | Use the `design` skill |
| `plan` | Use the `plan` skill; do not implement |
| `test-first` | Use the `test-first` skill only when `execution_authorized = true` |
| `implementation` | Implement only when `execution_authorized = true`; run before-dev first |
| `project-audit` | Use the `project-audit` skill |
| `check` | Use the `check` skill |
| `review-gate` | Use the `review-gate` skill |
| `finish-work` | Use the `finish-work` skill |
| `delivery` | Use the `delivery` skill |
| `record-session` | Use the `record-session` skill |

If `stage_status = awaiting_user_confirmation`, report completed / missing / candidate next stage and wait for explicit user confirmation. Do not switch stages yourself.

### Implementation Entry

Before writing implementation code:

1. Confirm the current task is a leaf task.
2. Confirm `workflow-state.py validate <task-dir>` passes.
3. Run before-dev and write or refresh `$TASK_DIR/before-dev.md`.
4. Keep work scoped to the selected leaf task only.

For external outsourcing projects, do not enter implementation or test-first until `assessment.md` records `kickoff_payment_received = yes`.
