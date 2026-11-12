# 第二十九轮外部评审的复核与修正（5 项 + N1/N2）

- 处置编号 R66；实跑见 `validation.md` §55

## 0. 结论

| # | 原判 | 复核 | 处置 |
|---|---|---|---|
| 1 | 日常入口不复核 `instance_id` | **成立** | 绑定核验里补实例标识比对（缺失→`WF_IDENTITY_UNRESOLVED`，不同→`WF_BINDING_MISMATCH`） |
| 2 | 写权检查接受未知 schema、代次矛盾 | **成立** | `writer.require_supported()` 统一校验 schema/状态组合/代次一致 |
| 3 | 已归档对象仍可暂停 | **成立** | `task-pause`/`task-resume` 补终态检查 |
| 4 | 义务集合由代码常量决定 | **成立** | `declared_step_specs()` 从已校验清单读，缺失/未知/矛盾一律 `WF_ASSET_DECISION` |
| 5 | 重复任务记录静默取一 | **成立** | `locate_task_dirs()` 收全部匹配，重复即拒并给诊断 |
| N1 | 「32 套全通过」缺复现路径 | **成立** | 新增 `run_all.sh`：每套件重建夹具，顺序无关 |
| N2 | R4 只有单元级覆盖 | **成立**（备忘） | 登记，不扩测试 |

## 1. 逐条处置

**① 实例标识**：`_require_binding()` 现在同时核对象与实例标识——绑定里缺 `instance_id` 记 `WF_RECORD_INVALID`；请求未携带记 `WF_IDENTITY_UNRESOLVED`（机制稿 §1.4「待核对携带标识」）；两侧不同记 `WF_BINDING_MISMATCH`（同条「转 §5.4 出口」）。
配套修了测试驱动器：`wfdrive` 现在扮演适配层，从持久绑定里取 `instance_id` 随请求携带——否则「首次绑定生成、此后每次必须携带」在测试里根本走不通。真实适配层可以从 `status` 的 `binding.instance_id` 取值。

**② 写者结构**：`writer.require_supported()` 成为所有读者的统一前置：`schema_version` 必须是 1；`state` 只能取 idle/held/recovering；idle 不得留 holder、held 必须有 holder；holder 代次必须是整数且**等于顶层代次**。最后一条放在读取层而非 `require_held`，因为「所有权事实矛盾」不该只在写权检查里被拦。

**③ 终态**：`task-pause`/`task-resume` 遇 `status=archived` 或 `terminal` 一律 `WF_BINDING_MISMATCH`，与 `task-knowledge`/`task-curate`/`task-retrospect` 一致；未完成的归档动作仍走专用恢复分支。

**④ 义务集合**：新增 `gates.declared_step_specs(ctx)`，从 `assets.load_installed_manifest()` 取 `required_steps`；清单缺声明、声明未知步骤、或声明与处理器表的 `condition`/`mode`/`due` 矛盾，都抛 `WF_ASSET_DECISION`（不退回常量、不跳过）。
`HANDLERS`/`TASK_STEP_SPECS` 保留为「谁来算、按什么顺序算」的处理器表——这正是评审建议的「保留固定处理器表，把义务来源换成清单」。

**⑤ 重复记录**：`locate_task_dirs()` 收集活动区 + 归档区全部匹配（含目录名同 id 但记录内 id 不符的情形），`task_dir()` 多于一个即抛 `RecordInvalid` 并列出双方；`load_task()` 再核记录内 id 与请求一致。

## 2. N1 复现性

新增 `scripts/tests/wf_runtime/full/run_all.sh`：**每个套件前重建夹具**，因此不再依赖跑序，也不需要中间手工 pause/release。实测 32 套 + 3 个专项流程全绿、失败计数 0。此前"某些套件必须排在后面"的现象是套件间的写者/绑定残留，不是框架缺陷。

## 3. N2 登记

R4 的 outcome 单调性目前只有 `r65` 的单元断言。代码路径在 `review.decide` 的锁内主路径上，人工核对正确；端到端用例（review-launch → decide 两轮）留待需要时补，不阻塞收口。
