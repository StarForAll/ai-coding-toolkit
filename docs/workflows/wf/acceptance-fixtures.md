# wf 验收夹具登记面

> 本文件是设计稿 §8.2 与机制稿 §12.3 在**实现侧**的登记面：把"场景行 → 夹具 → 初态 → 触发 → 预期输出 → 实跑证据"放在一处，供复审逐行核对。
> 只登记**已被实际断言覆盖**的行；未覆盖的行在 §4 单列，不写成"预期应该如此"。
> 维护规则：新增或改动夹具场景时，本表、夹具脚本与 `validation.md` 三处同批更新；预期输出只能抄实际断言，不得按设计意图补写。

## 1. 夹具与构造方式

| 夹具 | 语义（机制稿 §12.3） | 构造脚本 | 备注 |
|---|---|---|---|
| F0 | 全新项目：无 Git / 无基线 | `payload/install.py` 从打包发行树安装（`refs/tags/wf-vX.Y.Z`），随后人执行 `confirm-executor --scope system` | 安装器即夹具构造器；实跑见 `validation.md` §1 |
| F1 | 存量无流程 | 同一安装 + 空仓库初始提交；具体用例脚本 `scripts/tests/wf_runtime/full/f1_init.py`、`f1_ordinary.py` | 初始化任务 → 普通任务闭环 |
| F2 | 存量有其他流程 | `scripts/tests/wf_runtime/full/f2_setup.sh`（`.trellis/` 残留言据 + 一条与本任务无交集的外部提交） | 共存、Trellis 互斥、卸载期提交 |
| F1v | F1 的身份能力变体 | 同 F1，`installation.platforms` 置空/恢复（R93 起没有 `capability` 状态） | 会话身份轴，实跑见 §3 |

## 2. 场景行 → 夹具 → 初态 / 触发 / 预期输出

三档取值：`pass` / `blocked`（含原因码）/ `needs_decision`（含原因码）；预期列只写实跑观察到的形态，多条用 `；` 分隔。

| 设计稿 §8.2 场景行 | 夹具 | 初态 | 触发 | 预期输出 | 证据 |
|---|---|---|---|---|---|
| 初始化自举 | F0 | 无 `.wf/`、无 HEAD、无基线/配置 | `task-new(kind=initialize)` → `task-approve` → `task-start` | 无 HEAD 时 `blocked/WF_CAPABILITY_UNAVAILABLE`；授权建 HEAD 后 `pass`；基线/配置/spec 骨架可落盘 | `validation.md` §1（9/9） |
| Git 就绪 | F0 | 仓库无 HEAD | 人执行 `git add .wf .gitignore` 并提交 | `pass`：`git rev-parse HEAD` **退出 0**、`HEAD^{commit}` 可解析，且 `git ls-tree -r HEAD` 的路径只有 `.wf/` 与 `.gitignore`（**已断言提交树只含骨架**）；「README/LICENSE 不卷入」由上述 `ls-tree` 断言覆盖；实现入口不代为 init/add，属人执行动作 | `validation.md` §1、`p5_f0.py:64-71` |
| 无 MCP 全流程 | F1 | 无任何 MCP 服务、无索引 | 初始化任务全链 + spec 新增/更新/改名/合并/删除 | 全链 `pass`，删除未解除依赖时 `needs_decision/WF_SEMANTIC_DECISION` 并给三个出口；解除后 `pass` | `validation.md` §2、§2.1（13/13） |
| 机械修订不重复批准 | F1 | 任务已批准开工，PRD 只改排版 | 登记 `equivalences` 后 Check/Finish | 等价链归一，旧 pass 与回执不失效、不重批 | `validation.md` §13（A2） |
| 机读触碰面 | F1 | 批准 glob 与实际改动混合 | 改同目录另一文件 | 不可证包含即 `WF_SCOPE_UNRESOLVED`；补具体条目后通过 | `validation.md` §23–§25（R7b 等） |
| 执行器三级解析与确认 | F0 | 项目键/全局键/系统 python3 | `confirm-executor --scope system`；构造元组失配 | 元组匹配直接用；失配 `WF_EXECUTOR_UNCONFIRMED`；非法值拒绝 | `validation.md` §14（A9） |
| 日常收工（暂停 + 释放） | F1 | 有未提交改动的已绑定任务 | `stop --decision <keep>` → `writer release` | `pass`，writer 空闲；WIP 留痕于 handoff | `validation.md` §15（A22） |
| 暂停后换会话恢复 | F1v | 已暂停并释放写权 | 新会话 `bind` 同一任务 | `pass` 并回显新代次 | `validation.md` §3、`p5_v1.py` |
| 拆分的停用分支 | F1 | 一条 active 规则待拆成两条 | `spec-update` 一批：新增两条 + `disable` 旧文件 | `pass` 且 applied=3；旧文件保留、`status=disabled`、索引换新；**先以 `src/calc.py` 正对照命中 combined.md，停用后同一候选不再命中**（候选必须是规则 `paths` 的真实取值） | `validation.md` §16.6 |
| 知识删除与依赖解除 | F1 | spec 被活动任务策展引用 | 直接删除 | `needs_decision/WF_SEMANTIC_DECISION`；记录"已解除依赖"后删除 `pass` | `validation.md` §2.1 |
| 会话固定绑定 | F1v | 已部署、`.wf/` 无绑定、`writer` idle、`installation.platforms=[dsh]` | `enable` → `task-new`（一次完成写权、首次绑定、建任务）；再重复 `enable`；实例标识不符时 `bind`；暂停并 `writer release` 后由另一个会话 `bind` 接续 | 首次 `pass`；重复 `enable` 幂等；实例标识不符 → `WF_BINDING_MISMATCH`/`WF_IDENTITY_UNRESOLVED` 拒绝（未释放时不能抢占）；**释放后的新会话 `bind` 成功**（回显新代次）；已绑定会话再建对象不产生第二个任务 | `validation.md` §3、`p5_v1.py:60-82` |
| 无稳定会话身份 | F1v | 把 `installation.platforms` 置空（模拟平台未声明） | `enable` | `WF_IDENTITY_UNRESOLVED`（facts 记 `installation declares no platforms`）；只读诊断仍 `WF_OK` | `validation.md` §3、`p5_v1.py:20-44` |
| 压缩与新会话 | F1v | 已有绑定 | 压缩后调用、新会话接续 | 压缩沿用同一身份与绑定；新会话不继承绑定 | `validation.md` §3、§85（压缩轴部分） |
| 释放与显式交接（两段） | F1 | 任务已暂停、写权持有中 | `writer-handover begin --to <接收者 session-key> --decision <交接决定>` → 旧会话尝试写 → 接收者 `writer-handover accept`（不收 --decision）→ 新代次推进 | begin 后 `state=recovering` 且代次递增；旧代次写入被 `WF_WRITER_BUSY`/`WF_GENERATION_STALE` 拒；接收者 accept 得新代次并可推进 | `validation.md` §93、`r71 第 4 组` |
| TDD 红绿证据（code 适用） | F2 | TDD 开启且 `tdd_applicability=code` | 同一验证 id 先 `--run-verification` 跑红，再在 Check 跑绿；review-notes 顶层写 `tdd_evidence` | Check pass；缺段/跨验证项/验证定义摘要不符 → `WF_CHECK_FAILED` | `repro/tdd-evidence-identity.py`（跨验证项/docs 适用性）；缺段与定义摘要见 `test_sixth_round_guards.py`、`test_single_verification.py` |
| 所有权中断恢复 | F1 | 归档已提交但进程未报告；随后同一实例文件被另一合法动作推进 | 独立进程重入 `status` / `archive` | `pass` 且报告"归档已持久化"，派生可达提交查证；无重复归档、无重复提交 | `validation.md` §4（V2） |
| 维护写者 | F1 | `repair` 完整应用并留回执、无提交授权 | 不重叠任务开工并归档 → 重叠任务开工 → 人处置维护组 | 不重叠 `pass`；重叠 `blocked/WF_WIP_UNRESOLVED` 并给路径组；处置后 `pass`；writer 整文件未被无授权提交 | `validation.md` §5（V3） |
| 审查与正常完成（charter T4） | F2 | 复杂任务 Check pass，锚点已固定 | `review-launch` → 两份异种 reviewer 报告 → `review-import` → `review-decide` → `finish` | 全链 `pass`；同 CLI 双槽位 `blocked`（人数不合格，拒绝且不落 verdict）；改交付后重导旧报告 `blocked/WF_REVIEW_INVALID` | `validation.md` §6（V4）、§92/§93、`r71` 3g |
| 审查回执锚定 | F2 | 已导入报告 | 改一个交付文件后重导 | `blocked/WF_REVIEW_INVALID`（锚点失配） | `validation.md` §6 |
| 审查 CLI 身份确认 | F2 | 声明实施 CLI + 两槽位 | `review-decide` | 人数/差异不满足 → 拒绝输入、不产生 verdict（`WF_REVIEW_INVALID` 且 result 不新增）；`source-cli` 与声明矛盾 → 拒绝（`validation.md` §92/§93、`r71` 3f/3g；§19 为旧口径的历史记录） | `validation.md` §19 |
| 审查不可用 | F2 | 只有一个可用 reviewer CLI | `review-launch`（单槽位）→ `review-decide --unavailable` | 复杂任务正常归档被拒；异常退出成立 | `validation.md` §6、§19 |
| TDD 开关 | F1 | 项目默认关闭、任务未覆盖 | 批准规划 | 取值写入批准记录；未设置按项目默认 | `validation.md` §2 |
| 调试双源合并 / 复盘后再触发 | F1 | 失败事实分处 `check_history` 与 Execute 期声明 | 合并累计跨阈值；复盘后出现新触发 | 跨倍数 `needs_decision/WF_SEMANTIC_DECISION`；裁定后触发复盘；复盘后新事实须补做 | `validation.md` §7（V5，12/12） |
| 仓位/共存：共存与重装 | F2 | 其他流程资产 + 无交集外部提交 | wf 恢复推进；再制造相关路径变化 | 无交集可继续；相关变化使旧检查失效并重检 | `validation.md` §16 |
| Trellis 互斥 | F2 | `.trellis/` 残留言据（非激活） | `enable` | 仅残留且人核实后可启用；有效指令存在时 `blocked/WF_FLOW_CONFLICT` | `validation.md` §16 |
| 执行器配置可信 / 确认记录身份 | F0/F1 | 首次使用系统 `python3` | `confirm-executor --scope system` | 写入确认元组；元组失配 `blocked/WF_EXECUTOR_UNCONFIRMED` | `validation.md` §1、§21+ |

## 3. 夹具特有覆盖对照（机制稿 §12.3 的绑定表）

| 夹具 | 机制稿要求的专属场景 | 当前状态 |
|---|---|---|
| F0 | `初始化自举`、`Git 就绪`、`无 MCP 全流程`（至少一次） | 已覆盖（§2） |
| F0 | `准备定义与自举`、`验证分时解析` | **未覆盖**：依赖 `definition`/`run`，属第二轮；第二轮交付后须补，缺这两行时 F0 不能算完整通过（机制稿 §12.3 原文） |
| F1 | `extracted 生命周期`、`无 MCP 全流程`、spec 新增/更新/拆分/合并/改名/删除各至少一次正反断言 | 全部覆盖：`extracted`、新增/更新/合并/改名/删除见 `validation.md` §2.1；拆分的「原文件移除」分支见 §16.1（B5），「旧文件停用并保留」分支见 §16.6（2026-11-05 补跑，`p5_spec` 6 条用例，含拆分前 active 正对照） |
| F2 | `共存与重装`、`Trellis 互斥`（有效指令/纯残留两分支）、卸载期提交、相关路径外部变更 | 已覆盖（`validation.md` §16） |

## 4. 未覆盖清单（不得当作已通过）

| 项 | 归属 | 出口 |
|---|---|---|
| F0 的 `准备定义与自举`、`验证分时解析` | 第二轮 | 第二轮交付 `definition`/`run` 后补跑 |
| 真实压缩的"绑定仍可读"增量观察 | 环境触发 | 下一次真实压缩后按 `d1-compaction-checkpoint.md` §1 补记 |
| 与旧模块共存/迁移路径 | 不适用范围 | 旧内嵌模块 2026-10-28 退役，无迁移路径；见设计稿 §3 共存策略 |
| 执行器确认的集合语义与失效传播负例（多 clone 并存不覆盖、目录移动不失效、venv 重建沿用、purge 后须重确认、repair 重建 project_id 时旧记录失效） | **已覆盖**（`repro/d21-executor-set-multi-clone.py`、`d21-executor-set-move.py`、`d21-executor-set-venv-rebuild.py`、`d21-executor-set-purge-reconfirm.py`，2026-11-06 人裁后补，双模可证伪）；其中 purge 用 project_id 重建的等价构造（`uninstall --purge` 入口第三轮），**repair 重建 project_id 时旧记录失效仍留第三轮** | 已按设计稿 §8.2「执行器配置可信」行补齐夹具用例；repair 重建标识第三轮交付后另补失效负例（`pending-decisions.md` §6） |
| spec 多文件预算降级阶梯（缩小策展→退索引→短提醒→汇总、截断标记可见） | 设计稿 §6.2；实现只有单文件路径；**2026-11-06 人裁延期** | **延至第三轮，该轮交付后核**（见 `pending-decisions.md` §6）；未补前不得宣称该行覆盖 |
| 读取留痕完整性的负例（截断条目标记 `complete=false`） | 单文件读取恒 `complete=true` | **延至第三轮，该轮交付后核**（与 budget 一并，见 `pending-decisions.md` §6）；当前负例不可构造 |
| 历史锚点不可达（**轮次：首轮适用**） | 构造：任务开工后 `git commit --amend` 重写基线 | **已覆盖**（`repro/history-anchor-unreachable.py`，2026-11-06 人裁后补）：负例 `WF_HISTORY_UNRESOLVED` 带三出口，正例 `git reset --soft` 恢复可达后重检通过；双模可证伪 |
| 未提交记录存在性的负例（**轮次：首轮适用**） | 构造：提交任务记录后从工作树删除该文件 | **已覆盖**（`repro/record-missing-in-worktree.py`，2026-11-06 人裁后补）：`task-check` 报 `WF_RECORD_INVALID`（JSON 带出口）、`inspect` 列 `broken_task_dirs`、恢复文件后正常；双模可证伪 |
