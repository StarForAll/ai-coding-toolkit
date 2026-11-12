# 第十四轮外部评审的复核与修正（1 项）

- 复核对象：外部评审第 14 轮 1 条（含隔离探针）
- 处置编号 R50；实施与实跑见 `validation.md` §37

## 0. 结论

| # | 原判 | 复核 | 契约依据 | 处置 |
|---|---|---|---|---|
| 1 | `baseline-apply` 仍可写入嵌套仓库目标 | **成立（同一约束的第三个入口漏接）** | 设计稿 §6.1、机制稿 §3.1 的仓库边界 | R50 |

## 1. 复核

上一轮把「项目包含性 + 字面祖先 + 真实祖先」写进了 `spec.path_violation` 与 `spec.validate_changes`，但 `cmd_baseline_apply` 单独实现了一份「`realpath` 仍在项目根内」的检查，**没有消费嵌套仓库判定**。探针：批准与触碰面都覆盖 `.wf/spec/**` 的任务，把 `.wf/spec/alias` 链到 `vendor/subrepo/data/`（`vendor/subrepo/.git` 为 gitfile），`baseline-apply` 写 `.wf/spec/alias/baseline-created.md` 返回 `WF_OK`，文件落在嵌套仓库里。

根因是判据重复实现：同一约束在第二个入口各自写了一份，第三个入口漏掉。

## 2. 处置（R50）

- 在 `paths.py` 增加唯一判据 `boundary_violation(root, rel)`：项目包含性 + 字面祖先 + 真实祖先，返回 `None` 或原因字符串。
- `spec.path_violation` 改为直接委托它；`spec.validate_changes` 改用它（替换原先内联的两段判断）。
- `cmd_baseline_apply` 的整批预校验改为调用同一函数，替换原先的 `realpath` 内联判断。
- 一致性用例：**同一个目标**分别经 `baseline-apply` 与 `spec-update` 提交，两者都返回 `WF_PATH_INVALID` 且 reason 同为 `nested repository root: …`；普通 spec 骨架仍可写入。

## 3. 边界

- 不新增原因码：仍 `WF_PATH_INVALID`。
- 不改三个入口各自的前置（阶段/批准/触碰面/类别）：只统一「边界判定」这一层。
- 不把该判据扩到读之外的其他路径（如 review 报告暂存目录）：它们不在项目树内。

## 4. 对收口状态的影响

属「同一约束在多个入口重复实现导致漏接」，收口前必修；R50 让三个入口（读、spec 写、基线写）共用一份判据，后续新增写入入口只需调用 `paths.boundary_violation`。落地后需重跑 spec 与基线相关套件、三夹具全流程与 F0。
