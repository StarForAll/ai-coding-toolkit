# wf 步骤契约与单次验证运行

## Goal

把工作流定义里**已经声明**的三类步骤契约接进实例生成的任务记录，并由 Check 消费；同时提供
**单次验证运行**的记录入口，使 TDD 的红证据不再必须来自整轮 Check。

目的对齐：定义里的声明是**可算事实**（谁声明了什么、必须消费什么），机制负责"声明被兑现"；
动作怎么做、产物是否满足业务用途、失败是否命中目标仍由 AI 判断。

## Requirements

1. **步骤契约进任务记录**：实例为某步骤创建任务时，把该步骤的
   `actions`（必做动作）、`human_points`（步骤内人判点）、`verifications`（验证声明）与
   `workflow_id`/`step_id`/`definition_digest` 写入任务记录的 `execution`：
   - `execution.step` = `{workflow_id, step_id, definition_digest}`
   - `execution.actions` = `[{id, text, required, skip, human_points, result: "pending"}]`（供既有
     `work_satisfied_fact` 消费）
   - `execution.human_points` / `execution.verifications` = 定义里的原样声明摘要
   非实例生成的任务不写这些字段（行为不变）。
2. **Check 消费**：`task-check` 的锁内准备段对带 `execution.step` 的任务：
   - 必做动作仍有 `result=pending` → 阻断，并给"如何记录动作结果"的出口；
   - 声明了步骤内人判点但没有对应决定 → 阻断；
   - 定义声明的验证 id 未出现在**已批准 plan** 的 `verifications` 里 → 阻断（回 Plan 补齐）。
3. **动作结果可记录**：`task-check --decision` 接受 `subject` 含动作 id、`choice` ∈
   `done/完成/waived/不适用` 的条目，把 `execution.actions[].result` 与证据写回任务记录
   （不作自证门禁：动作是否真做完由 AI 判，机制只记"谁在何时给出该结论"）。
4. **单次验证运行**：新增 `task-check --run-verification <verification_id>`——只跑这一条已批准的
   验证并记一次运行（`execution.verification_runs[]`：verification_id、verification_digest、
   invocation、cwd、exit_code、status、at、log），**不产生 Check 结论**、不改 `check`/锚点。
5. **TDD 消费**：`tdd_evidence_problem` 的红证据来源增加 `execution.verification_runs` 的失败运行；
   绿证据仍只取本次 Check 的通过运行。
6. **帮助与用法**：`wf help task-check` 登记新旗标与决定取值域；`--run-verification` 与
   `--decision/--review-notes` 互斥（一处登记）。

## Constraints

- 不新增 skill、不新增层级；沿用 `task-check` 与 `--decision` 两个已有入口。
- 不改任何已有判定语义；无 `execution.step` 的任务（普通任务、升级前记录）行为完全不变。
- 记录 schema 只增字段，不重命名既有字段；`work_satisfied_fact` 的 pending-actions 判据保持不变。

## Acceptance Criteria

- [ ] 实例建任务后 `execution.step`/`actions`/`human_points`/`verifications` 落盘，且 `status` 可见。
- [ ] 必做动作未记录结果时 `task-check` 阻断，`--decision` 记录后可通过。
- [ ] 定义声明的人判点未给决定时 `task-check` 阻断。
- [ ] 定义声明的验证 id 不在批准 plan 时 `task-check` 阻断（出口回 Plan）。
- [ ] `--run-verification` 只跑一条、只写运行记录，`check`/锚点不变；失败运行可作为 TDD 红证据。
- [ ] 普通任务（无 `execution.step`）的全部既有用例不受影响。
