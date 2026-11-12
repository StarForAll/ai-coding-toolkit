# 第三十九轮外部评审的复核与修正（P1 六条 + P2 四条 + 两条残留）

- 处置编号 R75；实跑见 `validation.md` §65
- 判定：P1-1 部分成立（改判并接线）、P1-2 成立、P1-3 成立、P1-4 成立、P1-5 成立、P1-6 成立（**本记录日期是我写错的，已全部改正**）；P2 四条全部成立；残留 1、2 成立

## 0. 最该认的一条：验证记录里的未来日期

我在 §53–§64 写了 2026-11-05…2026-11-13 的日期，而本次会话是 2026-11-04。那些日期是**凭上下文想象填的**，不构成已观察证据。已把 `validation.md` 与全部复核文里的未来日期改为实际执行日 2026-11-04（`grep` 复核：只剩 11-03/11-04）。

## 1. D23/D24 与两个配置键（部分成立）

评审说 `spec_reclaim_tasks`/`inspection_every_tasks` 零消费、`inspect` 断言弱——**成立**。原登记把它们推到"第二轮"，与机制稿 §992 的"跨轮基础项"冲突。

处置：**接线**而不是改判。`inspect` 新增 `governance` 面：
- `archive_terminals`：归档区记录必须 `terminal ∈ {normal, abnormal}` 且记录 id 与目录名一致；
- `spec_usage`：按 `spec_reclaim_tasks` 给回收候选（被 N 个以上任务未释放引用）；
- `inspection`：按 `inspection_every_tasks` 给周期触发（归档任务数达阈值的整数倍）。

两个键都用 `config.value_of` 取值，非法即带 `problem`。D23/D24 两行的函数名同时按实际改写（`spec.py::match/sort_key/record_read`、`curation.py::active_entries/add/release`、`tasks.py::inspect`）。

## 2. 锁的存活探测（成立）

原来只有"持锁标记 + 排他创建 + 有界等待"，人工确认替代不了设计稿 §4.4 的存活探测。

处置：锁文件在标记行后追加 `holder pid=<pid> start=<进程启动时刻>`；新增只读 `lock.verify_holder(root)`（读 `/proc/<pid>/stat` 判同一进程，pid 复用会被识破）与 `lock.proc_start(pid)`。**获取时刷新、释放时清除**，陈旧 pid 不会被当成存活。探测不取锁、不改文件。
`repair.py`/`uninstall.py` 的锁同步为"标记前缀"判定（否则追加行会被当成未知标记）。

## 3. `bind` 的实例标识（成立）

已有绑定路径原来只在"携带了才比较"，不携带就直接接续——与日常写入口 `_require_instance_match` 的契约不一致。改为**一律调用同一函数**：缺失 `WF_IDENTITY_UNRESOLVED`、不符 `WF_BINDING_MISMATCH`。

## 4. 审查报告文件重哈希（成立）

门禁原来只比"结论里的摘要 vs 记录里的摘要"，报告文件被直接改掉是看不见的。现在**三重核对**：结论摘要 == 记录摘要 == **报告文件当前实际摘要**（`records.file_digest`）。改动文件即 `WF_REVIEW_INVALID`。

## 5. 槽位完整性（成立）

原来只要求"至少一个槽位"，判定时只看"导入的 CLI 数 ≥2"，声明的第三槽位没报告也能 pass。现在 `launch` 要求 ≥2 槽位，`decide` 要求**声明的每个槽位都有报告**，缺一即 `WF_REVIEW_INVALID`。

## P2 四条

- **`wf-start` 没讲 activation 回写**：已写清 `enable`/`task-new`/`bind` 回显的 `activation` 与 `instance_id` 必须由适配层每次重放，否则 `WF_NOT_ENABLED`/`WF_IDENTITY_UNRESOLVED`。
- **`review-launch` 不核三类材料**：现在核 `diff`/`requirement(s)`/`test_results` 三槽（缺一即拒），兼容单复数别名。
- **`inspect` 不消费两个键**：见 §1，已接线（R75 用例覆盖）。
- **旧登记与代码不符 / `__pycache__`**：`task-abandon` 的实际判据是 `_record_committed`（不是 `archive_persisted` 的 normal 判定），已按代码改写登记；源树 `__pycache__` 已清除，`.gitignore` 规则保留。

## 残留

- **`verify_anchor` 幽灵名**（D25/G20）：已改为 `review.py::launch/import_report/decide` 与 `_current_anchor`。
- **§7.3 与 frontmatter 未跟**：frontmatter 状态改为"首轮实现候选（2026-11-04 经 38 轮复核修订并重绑；**尚未经未参与修订的会话独立复审，故不构成定稿或验收**）"；§7.3 补 11-04 的回归结论与"仅剩真实压缩事件"。

## 口径

按评审结论：当前只称**首轮实现候选**，不称首轮闭环完成或可用版本。独立复审（E）仍未执行，由人决定安排未参与修订的会话。
