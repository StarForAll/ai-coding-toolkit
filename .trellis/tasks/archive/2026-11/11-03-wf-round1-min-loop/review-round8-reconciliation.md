# 第八轮外部评审的复核与修正（2 项）

- 复核对象：外部评审第 8 轮 2 条（含隔离探针）
- 处置编号 R38–R39（承接前七轮，不回退）；本轮只出复核与处置，实施随后单独进行

## 0. 结论摘要

| # | 原判 | 复核 | 契约依据 | 处置 |
|---|---|---|---|---|
| 1 | WIP 检查只接入了 `writer acquire`，`bind`/`task-new` 仍可绕过 | **成立 → 已修（§31）** | 机制稿 §4.2 授予写权的统一前置、§6.4 | R38 |
| 2 | WIP 实际提交后旧记录不解除，造成错误阻断 | **成立 → 已修（§31）** | 机制稿 §6.4「已授权提交或由人实际处置」 | R39 |

## 1. 逐条复核

### R38｜授予写权的入口不一致（原判 1）——成立

**代码事实**：`cmd_bind` 与 `cmd_task_new` 都在自己的 `lock.acquire` 区块内检查「writer 必须 idle」，随后直接 `writer_mod.acquire` 授予写权，**没有执行 `wip_blockers`**；只有 `_writer_acquire` 做了这项检查。探针：同一状态下 `writer acquire` 返回 `WF_WORKSPACE_UNRESOLVED`，而 `bind` 与 `task-new` 仍 `WF_OK` 并授予写权。新会话的常用入口（`wf-start` 走 `bind`/`task-new`）因此绕过限制。

**处置（R38）**：抽出统一的锁内判定 `assert_no_foreign_wip(ctx, exclude_id)`，由 `writer acquire`、`bind`、`task-new` 三处**在各自互斥内**调用，任一不过即 `WF_WORKSPACE_UNRESOLVED`（facts 列任务与路径）；以后新增授予写权的入口也必须调用它，作为该入口的固定前置。

### R39｜保留 WIP 不随实际处置解除（原判 2）——成立

**代码事实**：`stop_work` 无论 `choice` 是 keep / commit / reverse / transfer，都写同一份 `handoff.wip = {paths: items, pending: [], resolved: None}`；`wip_blockers` 只看「是否登记了路径」，不核这些路径现在是否仍未提交。探针：真实 `stop commit` 提交成功、工作树无残留，后续另一对象的获取条件仍把该任务列为阻塞者。

**处置（R39）**：
- `stop_work` 按实际处置写 `resolved`：commit/reverse/transfer 写 `{choice, evidence(commit/targets), at}`；只有 keep 留 `resolved: null`。
- 判据改为**状态事实**而非登记事实：`wip_blockers`/`ensure_releasable` 对每个保留路径再核当前工作树——已无未提交差异即不再阻断（无论 `resolved` 是否补写）；仍有差异才算保留 WIP。
- 解除结论经既有入口更新：`task-resume` 在恢复到继续执行时，若保留路径已干净则把 `handoff.wip.resolved` 补写为「已处置」并记录依据，不新增命令。

## 2. 处置队列

| 序 | 项 | 类型 | 出口判据 |
|---|---|---|---|
| 1 | R38 统一授予前置 | 代码 | `bind`、`task-new`、`writer acquire` 三处在同一 WIP 状态下都返回 `WF_WORKSPACE_UNRESOLVED` |
| 2 | R39 处置事实与解除结论 | 代码 | 真实 `stop commit` → 不再阻断其他对象；`stop keep` → 仍阻断；恢复时补写解除依据 |

## 3. 边界

- 不新增命令或字段：`resolved` 是既有字段，解除结论写在里面。
- 不在授予路径上自动提交或反向修正：只阻断，处置仍由人完成。
- 判据只读工作树与既有记录，不引入新的 WIP 账本。

## 4. 对收口状态的影响

两条都属「同一约束只覆盖部分入口」的一致性问题：R38 让新会话入口与 `writer acquire` 行为一致，R39 消除「已处置却仍被旧记录阻断」的误报。落地后需重跑授予相关（CP2、R1R2、R32、R37）、收工/恢复相关（CP1 A23、R24、R29）与三夹具全流程、F0。
