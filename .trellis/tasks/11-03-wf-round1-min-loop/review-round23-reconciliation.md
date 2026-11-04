# 第二十三轮外部评审的复核与修正（1 项，2 个方向）

- 复核对象：外部评审第 23 轮 1 条（真实仓库两向验证）
- 处置编号 R60；实施与实跑见 `validation.md` §46

## 0. 结论

| # | 原判 | 复核 | 契约依据 | 处置 |
|---|---|---|---|---|
| 1 | 查证不核提交树终态，既误放又误挡；多文件回执排序抛错且待核被门禁忽略 | **成立（两个相反方向 + 一个静默忽略）** | 机制稿 §4.5「比较 HEAD 中的该操作回执和完整路径组终态…全部一致即可派生 persisted」 | R60 |

## 1. 复核

`maintenance_persisted_probe` 判的是「同一提交的 diff 里同时出现 writer.json 与全部路径」＋ 回执 `changes` 相等，**从不读该提交树里文件的实际内容**：

- 登记 A、实际提交 B → 仍判 persisted（误放，重叠阻断被解除）；
- 先提交正确文件、再单独提交回执 → 后一提交树已含完整结果，但因 diff 不含那些路径而判待提交（误挡）。

另外 `sorted(saved.get("changes") or [])` 对字典列表排序会抛 `'<' not supported…`，异常被 `receipt_state` 兜成 `pending_check`；而门禁只阻断 `applied_pending_commit`，于是**无法核实的维护组反而被放行**。

## 2. 处置（R60）

- 新增 `_committed_digest(root, sha, path)` 与 `_changes_by_path()`（按 path 稳定排序）。
- probe 改为**逐项核候选提交树的实际终态**：下界不变，候选提交只要求「树里有该回执」且回执 `operation`/`changes`（按 path 排序后）与登记一致，再用 `_committed_digest` 与登记 `after` 全等比较；不要求与其他路径同一次 diff。
- `pending_check` 的 facts 也带 `paths`（原先只有 applied 分支带，导致门禁无从匹配）。
- 门禁区分出口：`pending_check` 重叠 → `WF_HISTORY_UNRESOLVED`（待核）；`applied_pending_commit` 重叠 → `WF_WIP_UNRESOLVED`（待处置）。待核不再被静默忽略。

## 3. 边界

- 不改状态值与回执字段：`pending_check` 已有，只是让它进门禁。
- 不做「diff 含有即算」的宽松判定，也不要求「同一次提交」的过严判定——都改为看树终态。
- 读取仍不写 writer。

## 4. 对收口状态的影响

误放会解除本该保留的阻断，误挡会卡住已完成的维护，二者都直接破坏 §4.5 的派生语义；收口前必修。落地后需重跑开工/维护相关（CP1/CP2、V3、R1R2、R35–R39、R59）与三夹具全流程、F0。
