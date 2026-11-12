# 第二十二轮外部评审的复核与修正（1 项）

- 复核对象：外部评审第 22 轮 1 条（真实仓库构造 + 实际提交）
- 处置编号 R59；实施与实跑见 `validation.md` §45

## 0. 结论

| # | 原判 | 复核 | 契约依据 | 处置 |
|---|---|---|---|---|
| 1 | 维护组已完整提交仍被判「待提交」 | **成立** | 机制稿 §4.5「每次读取先比较 HEAD 中的该操作回执和完整路径组终态…全部一致即可派生 persisted，读取本身不为了更新结果再次写 writer」 | R59 |

## 1. 复核

`writer.receipt_state` 早就支持 `probe`，但**没有任何调用方传**：`task_receipts()` 裸调 `receipt_state(record)`，开工处的重叠检查与巡检又各自 `receipt_state(..., probe=None)`。于是 `persisted` 分支是死代码：登记终态原样提交后工作区已干净、HEAD 已含回执与全部路径，读取仍派生 `applied_pending_commit`，重叠任务开工被判 `WF_WIP_UNRESOLVED`，只能靠人再跑 `repair --dispose` 绕过。

## 2. 处置（R59）

- 新增 `tasks.maintenance_persisted_probe(root)`：以回执 `head_before` 为下界做可达查证——候选提交必须同时包含 `.wf/writer.json` 与**全部**登记路径，且该提交中同 `operation` 的回执 `changes` 与当前登记一致。
- `task_receipts(root)` 统一带上该 probe（唯一读取入口）。
- 开工的重叠检查与 `inspect` 巡检改调 `task_receipts`，不再各自 `probe=None`。
- 读取仍不写 writer（回执 `result` 保持 `applied_pending_commit`），符合「读取本身不为了更新结果再次写 writer」。

## 3. 边界

- 不改回执字段与状态值：`persisted` 已有，仍只在派生层出现。
- 不做「提交内容模糊也放行」：路径组必须全含、回执必须同 `operation` 且 `changes` 一致，否则维持待提交。
- 不自动回写 `result`：历史由 Git 保存，读取只派生。

## 4. 对收口状态的影响

属「已实现的分支没有被消费」，直接卡住正常开工；收口前必修。落地后需重跑开工/维护相关（CP1/CP2、V2/V3、R1R2、R35/R36/R37/R38/R39）与三夹具全流程、F0。
