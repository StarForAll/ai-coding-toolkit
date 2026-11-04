# 第五十一轮：第八轮独立复审（pi/kimi，18 条 + 崩溃）的复核与修正

- 处置编号 R86；实跑见 `validation.md` §78
- 结论：**12 条已修、1 条崩溃已修、5 条登记/三选一裁定**。
- 这轮最重要的不是哪条缺陷，而是**复审的判断方式变了**：它问"协议是否成立"，并给出了 `不成立` 的裁定。

## 0. 先修崩溃（最紧急）

上一轮为"删除型交付"加的 `_removal_attributed` 把 `scope.attributed_paths()` 的**列表**当字典用（`.get("changes")`）。归属为空时被 `or {}` 兜住不崩，归属非空时——正是这个函数要服务的场景——直接 `AttributeError` → exit 70。

修法：按列表语义判成员关系。补了行为用例（真删文件 + 归属提交）。这是同型错误（对可能为空的返回值用 `or` 兜底）的**第三次**复发，已记入纪律。

## 1. P1 协议裁定：不成立（部分修，主体登记人裁）

复审裁定 `task-new` 的意图位置不符合机制稿 §5.1/§5.2：机制稿要求「首次创建 = writer 上的单一父动作，targets 固定 writer/binding/runtime/目录/模板产物/instance_id/scope」，而实现把意图写在 `task.action`、写权与绑定各自成段。

这一条我**不作为本轮修复**，理由与处置都写清楚：
- 它需要 `action` 记录保存 `owner_ref` 与 `normalized_inputs` 原值——机制稿的 action schema 没有这两个字段，属机制级登记；
- 已把完整方案（targets 清单、步骤推进、恢复定位、后置清单）写进 `pending-decisions.md` §3 第 1 项，等人裁。

同时把**能立即修的部分**修掉：`already_completed` 现在要求 action.kind 与绑定对象一致（D-09 的一半）；恢复的实例核验与后置核验已在前几轮就位。

## 2. 已修的 12 条

| 编号 | 缺陷 | 修法 |
|---|---|---|
| **D-01**（高） | 外部变更静默 pass，且留着两个未接线 helper | 删掉死 helper（登记口径与代码一致）；`external_pending` 计数留在 facts。阻断与否等 `pending-decisions` §3 第 2 项裁决 |
| **D-02**（中） | `spec-update` 与 `baseline-apply` 阶段口径不一致、finish 期变更无迁移 | 两处统一允许 `execute/check/finish`；`spec-update` 在 finish 期返回 `requires_recheck`；迁移本体登记人裁 |
| **D-04**（高） | d 桶静默 pass + 跨任务双认领 | d 桶纳入 `scope_facts` 并在 Check 阻断；新增 `cross_task_conflicts()`（**只认活冲突**：未提交 + 另一活动任务归属 + 落在本任务触碰面） |
| **D-11/D-12**（中） | `check:<id>` 被当文件、目录被当证据、check 条目内证据文件不核 | 按引用类别分流：符号引用白名单、`check:<id>` 解析、目录报"不是文件"、check 条目内 `evidence_ref` 必须存在 |
| **D-13**（中） | 异常归档被误报"未持久化" | `terminal=abnormal` 改用 `_record_committed` 判据 |
| **D-14**（中） | 引用检查只扫归档任务、实例字段当通过 | 活动+归档全扫；第二轮字段记 `unknown` 并给 `status` 三档 |
| **D-15/D-16**（中） | 预览与落盘证据不一致；开发态预览无身份 | `_profile_evidence()` 单一构造供预览与落盘；dev-deploy 预览补 `session_profile` 文本与 facts |
| **D-17**（中） | `--verify` 可被等长同 mtime 差异绕过 | `diff_tree()` 改逐文件 sha256 比对 |
| **D-18**（中） | 版本同步无机械校验 | `_assert_version_consistency()`：dev-manifest 若写了非占位版本必须与发行版一致 |
| **D-10**（中） | inspect 不报孤儿目录/治理面问题 | 治理面问题与非可解析目录进 `warnings` |
| 收尾 | stdin 无管道时静默挂起 | `isatty()` 时直接 `WF_PATH_INVALID` 要求管道 |

## 3. 登记（3 条 + 2 项已知）

`pending-decisions.md` §3 新增三条待人裁决：①主记录/意图归属合并为 writer 单一父动作（含字段登记）；②外部变更是否启用阻断（需先有提交归属判定面）；③Finish→Check 受控迁移是否新增。

另登记：`.wf/out-of-scope/`（P2-1/D-03）与 `assets.branch_source_check`（P2-5a）第三轮才消费，本轮在实现稿标注。

## 4. 复审判通过的部分

F2（索引与后像，含合法 disable 日常路径）、F5 的前六态（provider/host_id/transport/status 一致）、发行树一致性（27 个 Python 文件哈希一致）——三条复跑通过，未再改动。

## 5. 期间新发现（都是我自己改出来的）

- **N-R93**：`classify_candidates` 加 d 桶阻断后 check 立刻 `WF_CHECK_STALE`——"结束前重算"的快照键集合没跟上（before 有 `d`、after 没有）。补 after 快照键。
- **N-R94**：`cross_task_conflicts` 起初把**已归档任务的历史归属**也算冲突，导致 r46/r56 等正常流程被 `WF_SCOPE_UNRESOLVED` 挡住。改为只认活冲突。
- **N-R95**：`spec-update` 阶段放宽后，finish 期返回的 `next_` 必须明说"要重新 Check"，否则方向不明。
- **N-R96**：删死 helper 时用 `find("\ndef ")` 切片，需确认没连带删掉相邻函数——本轮已用编译 + 54 项回归复核。

## 6. 口径

八轮独立复审 + 其他 agent 累计：**67 条已处置、7 条登记**（其中 3 条待人裁决）。跨记录写入与提交归属两处已连续四轮出问题，本轮把这两处的"结构性问题"正式推到人裁，而不是继续在实现层打补丁。
