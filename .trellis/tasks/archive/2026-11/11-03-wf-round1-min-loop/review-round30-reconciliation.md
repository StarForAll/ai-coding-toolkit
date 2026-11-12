# 第三十轮外部评审的复核与修正（4 项）

- 处置编号 R67；实跑见 `validation.md` §56

## 0. 结论

| # | 原判 | 复核 | 处置 |
|---|---|---|---|
| 1 | 实例标识核验没覆盖写权入口；日常入口不消费能力状态 | **成立** | `writer acquire/release` 复用同一核验；核验函数内加能力状态检查 |
| 2 | `baseline-apply` 不查 paused/suspended/archived，提案无批准引用与前像核对 | **成立** | 三项状态检查、提案须带批准引用、可选 `before` 指纹核对 |
| 3 | 清单声明 `scope != task` 被静默跳过，缺 mode/重复 id 被接受 | **成立** | 声明先完整校验；scope 与处理器不一致即判矛盾 |
| 4 | `run_all.sh` 不传播退出码，失败可汇总为通过 | **成立** | 重写：检查退出码、`[FAIL]` 计数、`saved N/M` 与 PASS 计数，任一不符即累计失败并 `exit 1` |

## 1. 逐条处置

**① 写权入口**：`_require_instance_match` 上移到 `cli`，`writer acquire` 在锁前调用、`writer release` 在核验后调用；函数内追加能力状态检查——`session_profile.capability.status != verified` 时任何依赖身份的写入都返回 `WF_IDENTITY_UNRESOLVED`。`tasks._require_instance_match` 改为转调，保证两条路径同源。
这条同时纠正了上一轮文档的表述：不是"所有日常入口已统一核验"，而是"绑定相关入口 + 写权入口走同一实现"，本轮补齐后才成立。

**② baseline-apply**：补 `archived/terminal` → `WF_BINDING_MISMATCH`；`paused/suspended` → `WF_SEMANTIC_DECISION`（持写权不等于任务在可写状态）；提案须带 `approval`（兼容既有的 `decision` 字段）含 `choice` 与 `subject`；条目可带 `before` 指纹（摘要串或完整指纹对象），与当前文件不符即 `WF_WORKSPACE_UNRESOLVED`。
顺序上**先核提案结构与范围、再核批准引用**——与既有"范围先于批准"一致，也让"非法路径整批拒绝"这类用例继续命中 `WF_PATH_INVALID`。

**③ 清单声明**：`declared_step_specs` 先完整校验声明——非对象、缺 id、未注册处理器、重复 id、缺 `mode`/`due` 一律 `WF_ASSET_DECISION`；随后任务步骤若声明 `scope != "task"`，判为与处理器矛盾（改 scope 就能把门禁移出义务集合，正是必须堵的路）。

**④ 聚合脚本**：`run_all.sh` 现在对每个套件检查 ①夹具是否建成（`wf.py` 存在） ②`f1_init.py` 退出码 ③套件退出码 ④`[FAIL]` 行数 ⑤汇总行是否为 0 通过；任一不符即计失败，末尾按失败数 `exit 1`。用假套件（输出 `[FAIL]`、`saved 0`、`exit 1`）自证：脚本确实报"失败 1 项"并 `exit 1`；把假套件改回通过后 `exit 0`。

## 2. 连带发现（本轮新暴露）

上一轮我用旧脚本宣称"32 套全绿"，新脚本一跑就暴露 4 套真失败：`r1r2`（9/14）、`r7r15`（32/37）、`r31r34`（12/13）、`r50`（3/7）。全部由本轮收紧引起，且**都是用例输入缺少新要求的信息**：
- `r1r2`/`r7r15`/`r50` 的基线提案没有批准引用 → 补 `approval`（这是机制稿 §3.4 的要求，不是放宽）。
- `r31r34` 的 `FakeCtx` 缺 `session()`/`profile()` → 补齐接口并让绑定带 `instance_id`。
- `cp5_b345` 的 B3 手写信封缺实例标识 → 携带绑定中的值。
- `r64` 的未知步骤用例靠注入 `TASK_STEP_SPECS`，义务改由清单决定后失效 → 改为让 `compute_P` 抛 `KeyError`。
F0 的基线提案同样补了批准引用。

这条记作 N-R45：**旧聚合脚本掩盖了真失败**，与评审第 4 条是同一件事的两面。

## 3. 未处理的后续阶段项（照评审建议不越过 P1/P2）

审查判定（旧锚点/阻塞发现/未声明 CLI/缺材料仍 pass）、`repair` 预览后清空新写者、`repair`/`uninstall` 接管已有空锁：三项维持未修，登记在此，待下一轮专项处理。本轮只在 §1 范围动手。
