# 第五十四轮：人裁 A 的落地（writer 单一父动作 + Finish→Check 受控迁移）

- 处置编号 R89；实跑见 `validation.md` §81
- 依据：第十轮复审的裁决建议 A（两条阻塞项）；`pending-decisions.md` §3 第 1、3 项

## 1. `task-new` 合并为 writer 上的单一 `task.create` 父动作

**改前**：意图写在 `task.action`；写权授予与绑定各自成段；恢复按当前会话键 + 当前 title/kind 重算 `action.id`。
**改后**：

| 环节 | 实现 |
|---|---|
| 主记录 | writer 的 `action`（`kind=task.create`），`task.json` **不再承载创建动作**（用例 A4 断言 `task.action` 为空） |
| 目标固定 | `targets` 一次写定：`writer` / `task:<id>` / `binding:<key>` / `runtime:<key>`（用例 A3） |
| 步骤 | `create_dir` → `write_record` → `acquire_writer` → `bind`，每步完成即回写 writer（`_advance_writer_steps`），全部 done 才允许结案（`_finish_writer_action` 会拒未完成步骤） |
| 身份 | `instance_id` 在写意图时一次固定；不再出现"恢复时重新生成 instance_id" |
| 目录发布 | 模板产物与记录先在 `.staging-<id>` 备好再 `rename`，失败即清理（不留空目录/无意图记录） |
| 恢复 | `_writer_create_intent()` 从 writer 读意图；`_resume_task_create()` 的任务 id 取自 `action.targets`，**不按当前参数重建**；实例核验走 `_require_instance_match`，绑定对象不符即拒绝 |

用例 A1–A7 覆盖：主记录位置、四步结案、目标固定、记录不带动作、绑定与运行态齐备、退回未结案后重入续做同一对象、续做后结案。

## 2. Finish→Check 受控迁移

**改前**：finish 期 `spec-update`/`baseline-apply` 只给"必须重新 Check"的提示。
**改后**：`_reenter_check_from_finish()` 作为**父动作内部的一步**：

- 旧检查结果**保留**在 `task.check`，并追加 `invalidated={at, by, action_id, reason}`；
- `phase` 置回 `check`；
- 不伪造新的 Check 成功回执（不写 `task.check-passed` 回执）；
- 门禁侧：`task.check-passed` 见到 `check.invalidated` 即 `WF_CHECK_STALE`。

用例 B1–B3 覆盖：回到 check、失效事实齐全、旧 pass 不再通过门禁。

## 3. 期间新发现（都是我改出来的）

- **N-R101**：重写 `cmd_task_new` 时按文本切片删掉了两个模块级常量（`APPROVE_CHOICES`、`COMPLEXITY_CONDITIONS`），运行期才暴露 `NameError`。已补回，并把 `COMPLEXITY_CONDITIONS` 的键名与批准入口的 `complexity_conditions`（`governance/contract/acceptance/scope`）对齐——此前该常量在两份产物里**都没有定义**，属潜伏死路径。
- **N-R102**：恢复路径最初排在"已绑定"分支之后，导致"绑定已写、动作未结案"时直接返回成功；已把恢复判定提到绑定分支之前。
- **N-R103**：三个测试的注入点仍按旧结构（改 `task.action`、把 writer 置 idle），与新协议不符；改为"把 writer 父动作退回 prepared、保留写权"，这才是真实中断态。

## 4. 口径

按裁决 A 落地后，第十轮给出的三条阻塞项**全部处置**：外部变更阻断（上轮）、意图归属合并（本轮）、Finish→Check 迁移（本轮）。

当前 56 项回归全绿、两组 unittest OK、字节复现与令牌一致通过、引用检查 0 problem、设计机检全绿。剩下登记项均为**不阻塞**：`.wf/out-of-scope/`、巡检知识治理两类、`branch_source_check` 消费点、`enable` 残留通道、P3 若干。
