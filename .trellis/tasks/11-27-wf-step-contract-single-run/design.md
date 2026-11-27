# 设计：步骤契约接任务记录 + 单次验证运行

## 1. 记录形态（只增字段）

实例建任务时写入（`runs.advance` 的建任务分支，唯一写入点）：

```json
"execution": {
  "step": {"workflow_id": "…", "step_id": "…", "definition_digest": "sha256:…"},
  "actions": [{"id": "…", "text": "…", "required": true, "skip": null,
               "human_points": [], "result": "pending"}],
  "human_points": [{"id": "…", "question": "…"}],
  "verifications": [{"id": "…", "source": "current_plan", "consume_at": "check"}],
  "verification_runs": []
}
```

- `execution.actions` 的 `result` 取值：`pending|done|waived`。既有消费者
  `tasks.work_satisfied_fact` 已按 `result in ("pending", None)` + `required` 判待办，形状对齐。
- 非实例任务不写 `execution.step`；升级前记录同样没有——所有新判定都以 `execution.step` 存在为前提。

## 2. 生产点

`runs.advance` 建任务分支（`task = tasks_mod.new_task_record(...)` 之后、发布目录之前）：
按步骤声明生成上述契约；`definition_digest` 取实例固定快照的摘要（与 `run` 记录同源）。
`verifications` 只记声明摘要（`id/source/consume_at`），不复制其解析后的命令。

## 3. 消费点

### 3.1 Check 锁内准备段（`check.run_check_scope`）

在范围核对之后、锚点固定之前，新增 `_step_contract_problems(ctx, task, decisions, plan)`：

| 事实 | 判据 | 结果 |
|---|---|---|
| 必做动作未记录结果 | `execution.actions[].required` 且 `result == "pending"` | `WF_SEMANTIC_DECISION` + `pending_actions` |
| 步骤内人判点无决定 | `execution.human_points[].id` 未在任一决定 `subject` 里整词出现 | `WF_SEMANTIC_DECISION` + `missing_human_points` |
| 声明的验证未进批准 plan | `execution.verifications[].id` ∉ `plan.verifications[].id` | `WF_SEMANTIC_DECISION` + `missing_verifications`（出口回 Plan） |

三类问题一次列全（同一 facts），出口按类型分组——不做"报一个改一个"。

### 3.2 动作结果的记录（复用 `task-check --decision`）

新增取值域 `action_result`：`done/完成/waived/不适用`。准备段先按 `execution.actions[].id` 匹配决定
（`subject` 整词含该 id），把 `result`、`decision{choice,by,at,source,reason}` 写回**内存态**，
由既有 `_start_task_action/_finish_task_action` 在定稿段落盘（沿用 Check 的动作记录，不新开写入面）。
未给出决定的动作保持 `pending`，于是 3.1 的判据照旧阻断。

### 3.3 单次验证运行（`task-check --run-verification <id>`）

- 入口仍走 `cmd_task_check`：`--run-verification` 存在时走独立分支（锁内取记录→锁外跑一条→锁内写回），
  不进入五步 Check；与 `--decision/--review-notes/--review-notes-draft` 互斥（用法校验一处登记）。
- 运行的记录形状与 Check 的 command 记录同源（`verification_id`、`verification_digest`、
  `invocation`、`cwd`、`exit_code`、`status`、`at`、`log`），复用 `check._run_argv` 的执行与日志落点。
- 写入 `execution.verification_runs`（追加，不覆盖历史）。

### 3.4 TDD 红证据来源

`check.tdd_evidence_problem(evidence, commands, history_commands)`：调用方把
`execution.verification_runs` 归一成 command 形状后**并入 `history_commands`**——红证据因此可以来自
一次针对性运行；绿证据仍是本次 Check 的通过运行（绿=最终验证，不能只跑一条就收工）。

## 4. 边界（本轮不做）

- 步骤 `verifications` 的 `source=project`（既有项目命令）不在本任务解析成命令：它的落地方式是
  **批准 plan 必须声明同一 id**（3.1 第三行），命令本体仍由 plan 给出。理由：定义不复制命令，
  避免两处命令漂移。
- 动作的"业务完成度"不由机制判：机制只记"谁给出 done/waived"；waived 的正当性由人/审查看。

## 5. 影响面与兼容

- 新字段只增；无 `execution.step` 的任务行为不变（全量既有用例是回归面）。
- `work_satisfied_fact` 的 pending-actions 判据与 3.1 第一条**同源不同时点**：前者在开工/门禁面，
  后者在 Check 准备段；两处读同一字段，不另立判据。
