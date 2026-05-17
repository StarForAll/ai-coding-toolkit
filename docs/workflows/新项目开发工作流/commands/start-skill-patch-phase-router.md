## Workflow Phase Router Patch `[AI]`

When this Codex entry skill is used in a target project that has installed `docs/workflows/新项目开发工作流`, treat it as the workflow Phase Router, not as the original generic Trellis task workflow.

**⚠️ Old status routing is deprecated**: Do not use `status=planning` / `status=in_progress` for Step 3 routing. Under the strong-gate model, routing is based on the `stage` field from `workflow-state.json`, computed by the `workflow-state.py route` command.

### Hard Boundary

- Do not auto-advance across workflow stages.
- Do not enter implementation from `plan` unless the current leaf task has explicit user confirmation and `checkpoints.execution_authorized = true`.
- Use this state chain as the only source of truth:

```text
.trellis/.runtime/sessions/<context>.json
  -> current active leaf task
  -> $TASK_DIR/workflow-state.json
```

If any part is missing or stale, stop in the recovery branch. Do not infer the active stage from the presence of `prd.md`, `task_plan.md`, `design/`, `check.md`, or chat history alone.

### Routing

1. Run context gathering:

```bash
python3 ./.trellis/scripts/get_context.py
```

2. Compute the routing target:

```bash
python3 <WORKFLOW_DIR>/commands/shell/workflow-state.py route <task-dir> --project-root <project-root>
```

If the current session runtime already points at the active task, or if you are entering first-entry / recovery mode, omit `<task-dir>`:

```bash
python3 <WORKFLOW_DIR>/commands/shell/workflow-state.py route --project-root <project-root>
```

3. Act on the JSON output's `action` field:

| action | Meaning | Action |
|--------|---------|--------|
| `first_entry` | New project and no resumable task exists | Use the `feasibility` skill |
| `reenter` | Re-enter current stage | Use the skill matching the `target` field |
| `awaiting_confirmation` | Stage done, waiting for user | Report completed/missing items; wait for confirmation |
| `blocked` | Execution blocked | Show `blockers` list; do not proceed |
| `recovery_needed` | Cannot determine the current active task | Ask user to clarify the current task |
| `repair_needed` | State file missing or corrupt | Run `workflow-state.py repair`; show inference and ask for confirmation |
| `embed_invalid` | Installation incomplete | Stop; tell user to check installation integrity |

4. If the output contains `blockers`, display each one and do not proceed.

### Implementation Entry

Before writing implementation code:

1. Confirm the current task is a leaf task.
2. Run before-dev and write or refresh `$TASK_DIR/before-dev.md`.
3. Keep work scoped to the selected leaf task only.
4. Do not auto-continue to the next task after completion — require a new explicit re-entry through the current entry skill.

Within `implementation`, use this internal role chain:

```text
trellis-research -> trellis-implement -> trellis-check
```

Rules:

- The internal `trellis-check` agent is not the same as the formal `check` stage.
- If the target project keeps `codex.dispatch_mode = inline`, Codex main sessions do not manually dispatch this chain and instead perform the corresponding research / implement / check work inline.
- After the chain completes, only recommend the `check` skill as a candidate next stage and wait for user confirmation.
- If the formal `check` stage fails, return to `implementation` and re-run the internal chain.
- For `UI -> 首版代码界面` tasks: Codex cannot be the main executor; completion must produce `design/frontend-ui-spec.md`.
- For external outsourcing projects, do not enter implementation or test-first until `assessment.md` records `kickoff_payment_received = yes`.
