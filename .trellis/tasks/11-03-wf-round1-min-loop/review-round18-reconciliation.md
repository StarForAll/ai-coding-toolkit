# 第十八轮外部评审的复核与修正（1 项）

- 复核对象：外部评审第 18 轮 1 条（两个隔离仓库的单变量对照）
- 处置编号 R55；实施与实跑见 `validation.md` §41

## 0. 结论

| # | 原判 | 复核 | 契约依据 | 处置 |
|---|---|---|---|---|
| 1 | 批准入口直接取 `decisions[0]` 写 `plan.approval`，从不核 `choice`；`reject` 也能批准并开工 | **成立** | 机制稿 §1.1（Decision 由入口记录人的决定）、§2.3（`approval` 记录 Decision）、§8.2 开工门禁 | R55 |

## 1. 复核

`cmd_task_approve` 在做完全部校验后执行 `approval = decisions[0]`，门禁侧只核 `approval` 存在、版本与等价链一致——**`choice` 从头到尾没被读过**。探针把唯一变量换成 `reject`：批准 `WF_OK`、开工 `WF_OK`、阶段照常进 `execute`，`plan.approval.choice` 原样存着 `reject`。这是「已提供的人判事实未被消费」，不是防伪问题。

## 2. 处置（R55）

- 新增 `APPROVE_CHOICES = ("approve", "批准")`（沿用 `finish`/`commit` 这类既有英中并列写法，不新造词）。
- 批准入口从决定集中**筛出**批准决定：没有 → `WF_SEMANTIC_DECISION`（facts 列实际 choice 与可接受值）。
- 覆盖核对：决定的 `object_digest` 若存在，必须等于当前 PRD 摘要；`subject` 若不空且不含任务 id，则必须靠摘要判定命中。两者都不符 → `WF_APPROVAL_MISSING`。
- 门禁 `task.plan-approved` 复核 `plan.approval.choice` 仍在 `APPROVE_CHOICES` 内，否则 `WF_APPROVAL_MISSING`（facts 给实际值与可接受值）——拒绝或无关决定不能因「记录存在」放行。

## 3. 边界

- 不新增原因码：类型不符走 `WF_SEMANTIC_DECISION`（要人改决定），对象/结论不符走 `WF_APPROVAL_MISSING`（要重批）。
- 不引入防伪：仍只核结构与取值，不判断答复真伪（设计稿 §1.5）。
- 不改机械修订路径：它有自己的 `choice` 常量与等价链校验。

## 4. 对收口状态的影响

属「人判事实未被消费」，且会连带放开三件套与强制审查，收口前必修。落地后需重跑批准/开工（CP1/CP2、R15/R17/R26/R44/R51/R53/R54）与三夹具全流程、F0。
