# 第七轮外部评审的复核与修正（3 项）

- 复核对象：外部评审第 7 轮 3 条（含隔离探针）
- 处置编号 R35–R37；实施与实跑见 `validation.md` §29

## 0. 结论摘要

| # | 原判 | 复核 | 契约依据 | 处置 |
|---|---|---|---|---|
| 1 | 异常归档续做可能误报完成并绕过互斥 | **成立** | 机制稿 §6.4 退出条件、§4.2 互斥 | R35 |
| 2 | 同一会话新代次仍可被旧调用释放 | **成立** | 机制稿 §4.2「锁内核验旧值」 | R36 |
| 3 | WIP 判据没消费真实 `stop --choice keep` 的产物 | **成立** | 机制稿 §6.4 | R37 |

## 1. 逐条复核

### R35｜异常归档的续做（原判 1）——成立
`_abandon_resume` 只核记录提交，不核目录位置；且它在 `cmd_task_abandon` 取锁**之前**被调用，续做提交发生在互斥之外。探针：模拟「终态已写、目录未移动」后重入 → 返回 `WF_OK`、`record_persisted=true`，但任务仍在活动目录。正常归档的同类场景已在 R31 修好，异常归档没跟上。

**处置**：放弃续做与归档续做共用同一套三步判定（位置 → 提交 → 事实一致），并把续做整体移进 `lock.acquire` 区块、先 `require_held` 再恢复。

### R36｜写权代次（原判 2）——成立
R32 的锁内复核对 `holder.id` 的检查只能挡住「A 变成 B」；同一会话释放后重新取得第 3 代时，携带第 1 代的旧调用仍能释放。锁内必须重跑**完整**核验（含调用携带的 generation 与 scope）。

**处置**：锁内直接调用 `ctx.require_held()`（它读最新记录并比对 generation/scope），不再手写只比 id 的判断。

### R37｜保留 WIP 的真实来源（原判 3）——成立
`stop --choice keep` 把保留 WIP 写入 `handoff.wip`，其 `paths` 是**指纹条目**（`{path,digest,kind,exists,executable}`）、`resolved` 为 null、`pending` 为空；`wip_blockers` 只读 `disposition.pending`，因此真实收工保留的 WIP 完全识别不到，释放守卫也照样放行，`task-resume` 直接清暂停。

**处置**：
- 统一 `tasks.wip_paths(task)`：从 `handoff.wip.paths` 取 `path`（字符串或指纹条目都支持），`resolved` 非空即视为已处置。
- `wip_blockers` 判据改为 `wip_paths ∪ disposition.pending`。
- `ensure_releasable(task, root)`：保留 WIP 仍留在工作树差异中 → `WF_WORKSPACE_UNRESOLVED`。
- `task-resume`：恢复前核保留路径仍在工作树或仍属本任务未提交改动；被改动过 → 拒绝恢复。

## 2. 边界

- 不新增字段或状态值：判据只消费既有 `handoff.wip` 与 `disposition.pending`。
- 不给续做单独开锁：续做与正常路径同一互斥、同一写权要求。
- 不自动把保留 WIP 归给其他任务：只阻断、不认领。

## 3. 对收口状态的影响

三条都是「恢复/边界」类正确性缺陷，收口前必修；R35 使异常归档与正常归档的恢复语义对齐，R37 让 `stop keep` 的产品真正进入后续判据。落地后需重跑：归档/放弃相关（CP1 A23、CP5 B3、R23/R24、R29、R31）、写权相关（CP2、R1R2、R32）、以及三夹具全流程与 F0。
