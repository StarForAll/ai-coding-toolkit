<!-- start-skill-phase-router-step-replacement -->

**⚠️ 强门禁模式下 Steps 1-4 替换说明**：本补丁内容替换 SKILL.md 正文中的旧 Step 1（Load Current Context）、Step 2（Load the Phase Index）、Step 3（Decide Where You Are）和 Step 4（Load the Specific Step）。在嵌入安装时，安装器必须将 SKILL.md 中从 "## Step 1: Load Current Context" 到 "## Step 4: Load the Specific Step" 结束的整个段落替换为下方 "### Routing" 和 "### Implementation Entry" 中的新路由逻辑。

旧 Step 3 中按 `status=planning` / `status=in_progress` 路由的方式已废弃。在强门禁模型下，路由基于 `workflow-state.json` 的 `stage` 字段，由 `workflow-state.py route` 命令计算。

---

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
`workflow-state.py repair` 只能基于现有 `workflow-state.json` 可恢复字段或用户显式给出的 `--stage` 重建状态；它不会根据这些任务产物反推阶段。

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
| `first_entry` | New project and no resumable task exists | Use the skill matching the `target` field. Fresh projects without a reusable assessment should enter `feasibility`; `brainstorm` is only valid when route explicitly reuses an existing assessment that already allows it. |
| `reenter` | Re-enter current stage | Use the skill matching the `target` field |
| `awaiting_confirmation` | Stage done, waiting for user | Report completed/missing items; wait for confirmation |
| `awaiting_confirmation_with_blockers` | Stage reached confirmation point but blockers remain | Show `blockers`; do not ask for confirmation until they are fixed |
| `blocked` | Execution blocked | Show `blockers` list; do not proceed |
| `context_needed` | Current task cannot continue directly | The current stage requires a leaf task but the task has children; switch to a child task instead of proceeding on the parent task. |
| `recovery_needed` | Cannot determine the current active task | Ask user to clarify the current task |
| `repair_needed` | State file missing or corrupt | Run `workflow-state.py repair`. If it reports `repair_ready`, confirm and re-apply; if it reports `manual_confirmation_required`, ask the user to confirm the current stage and rerun with `--stage <stage>` instead of inferring from artifacts. |
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
