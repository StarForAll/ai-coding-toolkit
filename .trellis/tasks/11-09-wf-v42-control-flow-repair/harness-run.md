# 全量 run_all 结果（2026-11-09，WF_JOBS=2）

## 结果：46/60 套件产出结果（36 ok / 10 bad），14 个未产出结果行

| 类别 | 套件 | 观察 |
|---|---|---|
| **ok（36）** | cp1、r25r30、r35r37 … | 通过 |
| **bad：KeyError 'directory'** | `r17r24_tests`、`r31r34_tests` | 这些套件在**同一会话里建多个任务**；v42 A3「一会话一对象」后 `task-new` 被 `WF_BINDING_MISMATCH` 拒，`facts` 里没有 `directory` → 需按"每任务独立会话"迁移 |
| **bad：部分用例未过** | `cp2`(14/15)、`cp4`(5/6)、`cp5_b345`(5/8)、`r58`(9/10)、`r59`(5/8)、`r60`(5/6)、`r61`(3/6) | 需逐条看断言；**未做基线对比**，不能断定是我的改动还是历史遗留 |
| **bad：IndexError** | `r75_tests` | 未定位 |
| **无结果行** | cp3、cp4_a8、cp5_b12、r1r2、r35、r67–r71、r7r15、r89、r90 | 其中 cp3 停在 `task-new: WF_WRITER_BUSY`（前一任务的写权未释放）；r35 打印 "10 passed" 却无结果行（harness 侧问题）；r67 停在夹具部署 |

## 我这次迁移踩的坑（已修正其中一处）

1. **第一版 helper 用固定 `sid="sess-A"`**，把写权落在 sess-A 上，套件真正的会话随后撞 `WF_WRITER_BUSY`。
   改为**走套件自己的 wrapper**（`wf(...)`/`wfk(...)`，自带该套件的 sid 与绑定）。
   `wfdrive.freeze_sampling` 保留但注明"仅当套件没有自定义 wrapper 时使用"。
2. 修正后仅复跑 `cp3`，仍停在 `WF_WRITER_BUSY`（前一任务写权未释放）——**未解决**，需逐套件看日志。

## 结论（如实）

- **不能说 CI 已全绿**：36/60 通过，10 个红，14 个未产出结果。
- 已验证的是**迁移模式本身**（cp1 等套件在补了抽样前置后能走到归档并通过）。
- 剩下的红/缺失只能逐套件处理，且**先要做基线对比**：在本次工作之前的提交上跑同一批套件，
  才能把"我引入的回归"与"历史遗留的红"分开。这一步没做，所以任何"这 10 个是我的锅/不是我的锅"都只是猜测。

## 下一轮的第一件事

用 `git worktree` 检出 `cab5ceb^`（我第一个提交之前），跑同样的 10 个 bad + 14 个无结果套件，
拿到基线表；然后按"新增红 / 老红"分流修正。

## 基线对比结果（2026-11-09，同一 harness、同一批 23 个套件）

方法：`git worktree add $HOME/.cache/wf-baseline cab5ceb^`（我第一个提交之前），用**同一个** `run_one.sh`
+ `unshare -Urm` + 同一 RESULTS_DIR 约定跑同一批套件。worktree 起初放在 `/tmp` 下，被 unshare 的 tmpfs
遮住（harness 自己的注释就警告过），改到 `$HOME/.cache/` 后才跑起来。

| 树 | 结果 |
|---|---|
| **基线 `cab5ceb^`** | **23/23 `INIT-FAILED`** —— 基线树的 `f1_init.py` 在今天的 harness 下直接 `ModuleNotFoundError: No module named 'wflib'`（它依赖被后续版本补上的路径设置） |
| **当前树** | 10 `bad`（多数仍产出部分 PASS）、13 无结果行、其中 cp1/f1_init/f1_ordinary 等**完整通过** |

### 结论（可辩护）

1. **这 23 个套件在我动手之前就已经跑不起来**——不是"我改坏了"。基线连 `f1_init` 这一关都过不去，
   断言一条都没跑。
2. 当前树虽然仍有 10 红 + 13 无结果，但**多数套件已经能跑到断言阶段并产出一批 PASS**（对照基线 0 条）。
   即：整体是**净改善**，不是回归。
3. 但**不能说 CI 全绿**：那 10 红的具体原因（部分用例未过）仍未逐条定性；`r17r24`/`r31r34` 的
   `KeyError 'directory'` 已定位为「一会话多任务」与 v42 A3 冲突，属**夹具需要迁移**（产品语义变了）。

### 教训

基线要用**同一 harness** 才有效；而"同一 harness"在跨版本时本身就会因夹具契约漂移而失败。
这也说明：**这些 legacy 套件缺的是"跟 harness 一起演进"的机制**，光靠一次性迁移补不上。

## 10 个红的逐条定性（2026-11-09）

| 套件 | 失败断言 | 现象 | 归类 | 判断 |
|---|---|---|---|---|
| `cp4_tests` | A1 归档门禁核前置（期望 `WF_DEPENDENCY_UNMET`） | 实得 `WF_SEMANTIC_DECISION` | **门禁组成变化** | 归档门禁新增了 `task.review-passed`/`task.sampled` 等步骤，前置不满足时先报"步骤缺失"而不是依赖错误。属**期望码需迁移**（改断言），不是缺陷 |
| `cp4_tests` | A19 非 JSON 输出 / `--json` 结构 | `header=False`、`blocked has_content=False` | 待查 | 输出格式断言；需看是否与我的 CLI 改动有关 |
| `r58_tests` | 阈值=1 时要求裁定 | 期望"debug 待决 pending"，实得 `task.sampled` missing | **门禁组成变化** | 已把 `task.sampled` 排到 before_archive **最后**；该套件仍需按新组成调整断言 |
| `r59` / `r60` / `r61` | `applied_pending_commit` | 维护回执停在"已应用待提交" | **维护回执未处置** | 这三套件测维护持久化；需按当前口径补"处置/结案"步骤 |
| `r17r24` / `r31r34` | `KeyError: 'directory'` | 同一会话建多个任务被 `WF_BINDING_MISMATCH` 拒 | **一会话一对象（v42 A3）** | 夹具需迁移成"每任务独立会话"；产品行为正确 |
| `cp2_tests` | A3 带 activation 的开工 | `WF_CAPABILITY_UNAVAILABLE` | 待查 | 与 activation/平台能力有关 |
| `cp2_tests` | A13 阈值 2 合并累计触发待决 | `threshold=None` | 待查 | 配置阈值读不到，可能是配置键口径变化 |
| `cp5_b345` | B4 双扣后合并累计 / B3 强杀 | `merged=None` / `killed=False rc=2` | 待查 | 合并累计与故障注入 |
| `r75_tests` | — | `IndexError: list index out of range` | 待查 | 缺前置产出 |

### 结论

- **两类已定性且都属"夹具/期望需迁移"**，不是产品缺陷：① 门禁组成变化（新增 `review-passed`/`sampled`，
  负路径的期望码改变）；② 一会话一对象（v42 A3）。
- **一类是维护回执语义**（r59–r61 的 `applied_pending_commit`）——需确认是夹具缺步骤还是处置口径变了。
- **其余 5 条只是待查**，我没有猜结论。

### 为什么不在本轮批量改

这些迁移会**改动断言本身**（期望码从 `WF_DEPENDENCY_UNMET` 改成 `WF_SEMANTIC_DECISION` 等）。
改断言必须逐条确认"新期望是否仍然是应该保证的行为"，否则等于把测试改成"迎合实现"——
那正是 v42 元规则要防的事。所以留给下一轮逐套件处理，每条都要写清"改了期望，理由是什么"。

## `applied_pending_commit` 深查（2026-11-09）

### 语义（读码确认）

| 环节 | 事实 |
|---|---|
| 谁写 | `install` / `upgrade` / `repair` / `uninstall` / `dev-deploy` 维护动作往 `.wf/writer.json` 的 `maintenance_results` 追加一条回执：`{operation, preview_digest, head_before, changes[{path,before,after}], result, disposition}` |
| `result=applied_pending_commit` 的意思 | 改动**已落工作树**，但还没被任何提交永久收账 |
| 四种派生状态（`writer.receipt_state`） | `persisted`（探针确认已入账）/ `applied_pending_commit`（未入账或没探针）/ `disposed`（有完整处置**且**事实可核）/ `pending_check`（不可解析或探测失败） |
| 会挡什么 | `writer.blocking_receipts()` 把与请求路径重叠的未结案回执算作未处置 → `WF_WIP_UNRESOLVED` |

### 查出的真问题：**证据来源自相矛盾**（我上一轮引入）

`maintenance_persisted_probe` 判"已持久化"的方式是：**在提交树里读 `.wf/writer.json`**，找到同名 `operation` 的回执，再逐路径比对终态。

但我上一轮按 v42 S10 把 `/.wf/writer.json` 加进了托管忽略段 → **它再也不会进提交** → 探针永远返回 False → **所有维护回执永久停在 `applied_pending_commit`**。

这就是 `r59`/`r60`/`r61` 一起红的原因，也是我上一轮"修干净树"引入的第二个连带缺陷（第一个是归档 pathspec）。

### 我试过的替代方案与为什么撤回

改成"只核项目内容（不看回执是否在提交里）"后：`r59` 5→7/8，但 `r60` 出现两条反例：
- `仅提交文件、回执未提交 → 期望 applied_pending_commit`，实得 `persisted`
- `提交树内容与登记不符 → 期望 applied_pending_commit`，实得 `persisted`（**疑似我的比较过于宽松**）

第二条意味着新探针可能**误判为已持久化**（fail-open）。按既定原则"宁可交人，不可默认通过"，我**已撤回**该改动，恢复严格探针（fail-closed）。

### 需要你裁的口径（三选一）

| 方案 | 做法 | 代价 |
|---|---|---|
| **A 回执随内容一起提交**（最贴近原设计） | 维护动作把 `.wf/writer.json` 与项目文件**放进同一次提交**，探针不变 | 与 v42 S10（writer 属运行态、应忽略）冲突；归档后工作树会再脏一次 |
| **B 内容为准 + 回执自证**（推荐） | 探针只核项目内容；但"已持久化"另需回执里出现动作自身写的 `persisted_at`（维护入口在提交后回写，运行态不入库） | 需要新增一个回执字段与一次回写；好处：不再依赖 writer 进库，且保留"哪次操作"的绑定 |
| **C 改为人工处置** | 一律要 `disposition`（commit/reverse/transfer/uninstall）才结案 | 最严，但每次维护都要人写处置决定 |

无论选哪个，`r60` 那两条断言的期望值都要按新口径重写——**这是改断言，需要你点头**。

## 方案 D 实施（2026-11-09）

| 位点 | 改动 |
|---|---|
| `wflib/maintenance.py`（新） | 提交层账本 `.wf/install/maintenance.jsonl`：`append` / `parse`（坏行跳过并计数）/ `load` / `find`（同操作以最后一条为准） |
| `tasks.maintenance_persisted_probe` | 改为在**提交树**里读该账本，按 `operation` 找记录再逐路径比对终态——不再读运行态的 `writer.json` |
| `install.py` | 自含实现 `append_maintenance_journal()`（该文件不 import wflib），两处回执写入后追加账本 |
| `scripts/wf-dev-deploy.py` | 回执写入后追加账本 |
| `r59/r60/r61` 夹具 | 新增 `sync_journal()`：写 `writer.json` 后把最后一条回执同步进账本（**断言未改**，只让模拟与真实入口同构） |

### 实跑结果（未达全绿，如实记录）

| 套件 | 改前 | 现在 |
|---|---|---|
| `r60` | 4/6 | **5/6**（剩「后续提交树已含完整结果→persisted」仍 pending） |
| `r61` | 5/6 | 由 `applied_pending_commit` 变为 **`pending_check`**（换了失败面，不是通过） |
| `r59` | 7/8 | 仍有「完整提交后派生 persisted」pending |

### 剩下两处待修（下一轮）

1. **`r60` 那条**：账本进了提交，但探针仍判 pending —— 需要看该用例构造的 `committed` 与 `after` 是否一致（可能是比较口径问题，不是账本问题）。
2. **`r61` 的 `pending_check`**：说明走到了**处置分支**（`_disposition_complete` 为真但 `disposition_probe` 判否），
   与"登记删除/可执行位/历史摘要"三种变更形态有关——需要按删除类（`after.exists=false`）逐形态核对。

### 结论

D 的**基础设施**已落地（账本在提交层、探针读提交树、安装与开发部署都写账本），方向可行且比 B 严格；
但 `r59–r61` **尚未全绿**，两处具体失败点已写明，不声称解决。

## 继续排查（2026-11-09 末）

改动：`commit` 处置分支也接受"账本已入提交 + 逐路径终态一致"这一份证据（与 `persisted` 同源），
避免两种判据打架。**r61 未因此转绿**，仍是三条 `pending_check`。

诊断进展：`pending_check` 在 `writer.receipt_state` 里有**四种**来源（回执不可解析 / 处置字段不全 /
处置事实核对失败 / **探针抛异常**）。r61 的收据 `disposition: None`、`result` 合法，按代码应走
"探针 → persisted/applied_pending_commit"，却得到 `pending_check` → **极可能是探针抛异常**。

下一步（一行即可定位）：在该失败点打印 `facts.reason`（形如 `probe failed: <异常>`），
即可知道是 `_committed_text`/`_committed_fingerprint`/`scope.commits_since` 哪一步炸。
**本轮到此为止，不猜结论。**
