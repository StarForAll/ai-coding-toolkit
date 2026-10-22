# 验证报告：dsh-trellis 0.1.4 与 Codex 使用 Trellis 的效果对照及缺口复核

- 日期：2026-10-22
- 任务：`.trellis/tasks/10-22-dsh-trellis-capability-verify-0-1-4`
- 环境：DSH `0.2.1-rc.2`；Trellis CLI `0.7.0-beta.4`；Codex CLI `0.163.0`；Node `v24.20.0`
- 插件：本仓库 `dsh-plugins/dsh-trellis`（`0.1.4`），隔离 profile 以 `link:` 直接挂载源码；
  宿主张包 `~/.dsh/profiles/{web,trellis-headless}` 同为 0.1.4（`diff -rq lib` 无差异）
- 临时项目：`/tmp/dsh-cap-verify/{proj,proj2,plain}`（`trellis init -u xzc --codex --dsh`；
  `proj2` 用于并发/隔离；`plain` 为非 Trellis 目录）
- 隔离运行：`DSH_HOME=/tmp/dsh-cap-verify/home`；`CODEX_HOME=/tmp/dsh-cap-verify/codex-home`
  （provider 用 `env_key` 引用环境变量，配置文件中无密钥）；真实 LLM：`deepseek-official`
  （api-key provider，禁用 account provider 后生效）
- 证据目录：`/tmp/dsh-cap-verify/evidence/`

## 证据等级

- **S1 真实会话**：真实 LLM（DSH jsonl / Codex rollout 逐事件）+ 真实工具调用。
- **S2 真实代码执行**：node 直载已安装插件模块、真实 hook 脚本 + 真实 payload、真实 CLI。
- **S3 源码比对**：插件 lib、Trellis 0.7.0-beta.4 模板/脚本、宿主源码。
- **S4 单元测试**：`node --test "test/*.test.js"`。

本报告“通过”结论均以 S1/S2 为准；README/旧报告不作为通过依据。

## 结论摘要

1. **主链路达到 Codex 同等效果**：workflow breadcrumb、no-task bootstrap、路径级 spec
   deny-once、子代理上下文 push、会话任务身份、非 Trellis 项目零干扰，全部在真实会话中复现，
   与 Codex 侧（真实 `codex exec` + 真实 hook payload）行为对齐；DSH 另有若干增强。
2. **补足了 plain DSH 的全部已知缺口**：无插件对照（`profile=plain`）确认
   breadcrumb/bootstrap/spec 注入/子代理 push/守卫/`trellis_wait`/命令 全部缺失，插件逐项补上。
3. **未发现 P1/P2 功能缺陷**；发现 **1 个 P3 体验/一致性缺陷**（stale 指针面包屑，见 D1），
   以及 3 项“平台形状/分布前置”差异（非缺陷，需用户决定是否处理）。
4. 单元测试 `362 tests / 358 pass / 0 fail / 4 skip`（skip 为 alpha 宿主 API 门槛用例，与既有记录一致）。

## R1 接口面与产物对照（S3 + S1）

`trellis init --codex --dsh` 在同一临时项目的产物：

| 面 | Codex 侧 | DSH 侧 | 判定 |
|---|---|---|---|
| 共享技能 | `.agents/skills/` 12 个 `trellis-*` | 同一目录同一批文件 | 对齐（同字节来源） |
| 平台入口技能 | 无 | `.dsh/skills/trellis-{start,continue,finish-work}` | DSH 平台形状 |
| 角色技能/代理 | `.codex/agents/trellis-{implement,check,research}.toml`（含 `sandbox_mode`、`developer_instructions`） | `.dsh/skills/trellis-agent-{implement,check,research}/SKILL.md`（角色指令，含 pull 兜底与递归守卫） | 角色内容对齐；**声明式 agent 配置 DSH 无对应物**（宿主限制） |
| hooks | `.codex/hooks.json`（UserPromptSubmit / SubagentStart / PreToolUse / SessionStart）+ 4 个 Python 脚本 | 无项目级 hooks，由 profile 插件接管 | 平台形状差异 |
| 配置 | `.codex/config.toml`（`agents.max_depth=1`） | `.trellis/config.yaml` 的 `dsh.dispatch_mode` | 对齐（各自职责） |
| 指南 | `AGENTS.md` TRELLIS 块 | 另加 `.dsh/DSH.md`（操作指南，非自动加载） | 对齐 |

**技能发现实测（S1）**：DSH 会话的 skill catalog 同时包含 `.agents/skills`（12 个共享技能）
与 `.dsh/skills`（6 个入口/角色技能）；plain profile 同样可见全部技能，说明技能来自项目而非插件。

## R2 主链路真实对照

### R2.1 workflow-state 面包屑

| 用例 | DSH（插件） | Codex | 判定 |
|---|---|---|---|
| 首轮 no_task | S1 `session-1a8a63e4`：`form=breadcrumb status=no_task`，正文含 Trellis 分诊规则 | S1 线程 `01a16414`：`<workflow-state>Status: no_task ...` | 对齐 |
| 状态迁移 | S1 `session-8f386730`：绑定任务后由 `no_task` → `in_progress-inline`；切 `auto` 后 → `in_progress` | S1 线程 `01a16419`：turn1 `no_task` → turn2 `in_progress` | 对齐 |
| 同轮内迁移 | S1 GUI 会话 `session-3b709400`：任务在 turn 1 step 2 创建，seq 184 即注入 `in_progress-inline`（**同轮下一步**） | Codex 仅在 `UserPromptSubmit` 注入，轮内状态变化要等下一轮 | **DSH 增强**（宿主事件更细） |
| task_error | S1 同会话：损坏 `task.json` 后 `status=task_error`，正文为修复指引 | 源码/S2：Codex hook 同样给 task_error 专用文案 | 对齐 |
| 去重 | 同状态重复轮不重复注入（projection；S1 `session-8f386730` turn4-6 仅一次） | 每轮都注入 | **有意差异（README 已声明）** |
| 跳过词 | S1 `session-75f4f761`：`no-trellis` + 2 步工具调用，breadcrumb/bootstrap **0 条**；spec-context 照常 | `UserPromptSubmit` 每轮判定 | 对齐 |
| 非 Trellis 项目 | S1 `/tmp/dsh-cap-verify/plain`：0 条插件消息 | Codex 无 `.trellis` 时 hook 静默 | 对齐 |

### R2.2 no-task bootstrap

- DSH：独立消息家族，每根会话一次；子代理永不注入；压缩移除后重投（S1：首轮 1 条；
  S1 子会话 `d9abeff6`/`b645232b`/`fc32b003` 均 0 条）。
- Codex：`UserPromptSubmit` 每轮附带，no_task 期间反复出现（S1 线程 `01a16414` 两轮各 1 次）。
- 结论：**有意差异**（README 第 31/54 行已声明“每会话一次”是设计选择），非缺陷。

### R2.3 路径级 spec 注入

| 检查 | DSH 证据 | Codex 证据 | 判定 |
|---|---|---|---|
| 首次触碰 deny-once | S1 `session-8f386730`：`write src/new.js` → `Error: Trellis injected governing specs. Review them, then retry...`；step2 重试成功 | S1 线程 `01a16417`：`Command blocked by PreToolUse hook: Trellis injected governing specs...`；同时注入 `<spec-context ... sha256>` developer 消息；重试后写入成功 | 对齐 |
| 已教不再拦 | 同会话后续 `write src/other.js` 未 deny | Codex 每事件独立判定 | 对齐 |
| read ticket（可选） | S1 `session-96b72b9e`：配置 `tools: [Read, Edit, Write]` 后 read 触发 `form=spec-context` 用户消息（不拦截） | Codex 无 read 触发 | **DSH 增强（可选）** |
| 持久化 | `.trellis/.runtime/spec-inject/session-8f386730....json` 记录 `mode:full` + sha256 | Codex 状态在 hook 侧 | 对齐 |
| 压缩重置 | S3 `lib/spec-policy.js` 监听 `compaction/end` 清内存 + 持久分片；未做真实压缩会话 | `SessionStart(clear/compact)` 重注入 | 实现对齐；**本轮未实测压缩**（限制） |

### R2.4 子代理上下文 push 与守卫

| 用例 | 证据 | 判定 |
|---|---|---|
| implement push（`Active task:` 前奏） | S1 子会话 `d9abeff6`（depth=1）：`form=subagent-context role=implement task=.trellis/tasks/10-22-spec-deny-smoke`，含角色 skill 全文、`was prepared by dsh-trellis`、递归守卫、`## Curated Context`（prd.md） | 对齐 Codex `SubagentStart`（S2 真实 payload 直调 hook 输出同构内容） |
| 无前奏、靠父指针 | S1 子会话 `fc32b003`（check）：提示词无 `Active task:`，push 仍解析出任务 | 对齐（Codex 以 parent session 解析） |
| research | S1 子会话 `b645232b`：`role=research`，任务路径正确 | 对齐 |
| 子代理不注入面包屑/bootstrap | 上述 3 个子会话均为 0 条 | 对齐（Codex 子代理仅 SubagentStart） |
| inline 守卫 | S1 `session-8f386730`：`Error: Trellis inline mode: ... trellis-agent-implement dispatch is refused...`，文案明确“退出 inline 是用户决定” | Codex 无此拦截（只文档化） | **DSH 增强（提示性闸门）** |
| 父会话收尾 | S1：父会话 step3.2 调用 `trellis_wait`，返回 `subagent d9abeff6... completed; settlement notice delivery is unverified...` | Codex 原生 `wait_agent` | 对齐（能力等价，DSH 额外提供事件驱动等待） |

### R2.5 会话身份与任务隔离

- S1（本 GUI 会话 `session-3b709400` 的托管 shell）：
  `DSH_SESSION_ID=session-3b709400...`、`DSH_SHELL=1`、
  `DSH_TRELLIS_CONTEXT_ID=dsh_session-3b709400...`；
  `task.py current --source` → `Current task: .trellis/tasks/10-22-dsh-trellis-capability-verify-0-1-4`
  / `Source: session:dsh_session-3b709400...`。插件注入的上下文与会话指针闭环。
- Codex：S1 在 codex 内执行 `task.py start` 后生成 `codex_01a16419....json`，hook 后续解析正确。
- 跨项目隔离（S2）：同一 session id 在 `proj` 解析到 `10-22-spec-deny-smoke`，在 `proj2`
  解析到 `10-22-second-task`，互不串扰；指针文件位于各自 `.trellis/.runtime/sessions/`。
- 子目录启动（S2）：从 `proj/src` 向上解析根目录 = `proj`，状态 `in_progress`。

### R2.6 命令与增强项

| 项 | 证据 | 结果 |
|---|---|---|
| `/trellis-status` | S2 `readCurrentTask` 实跑：`Current task: ... / Status: in_progress / Source: session:dsh_...` | 可用 |
| `/trellis-finish` | S2 同一模块（只读清单；不改状态） | 可用 |
| `/trellis-doctor` | S2 `collectDoctorReport`：root / Trellis 版本 / 8 个 workflow 块 / dispatch mode / spec 1 项 / active task | 可用 |
| doctor 的 conflicts | 真实 ctx 才有 loader；S2 用 fake loader 验证：`checked` 且正确排除 self/disabled，发现 `dsh-trellis-alt` | 可用（真实 GUI 未触发） |
| 版本监控 | S2 真实网络：GitHub commit/release + npm dist-tags 均 200；上游最新 `0.1.13`（本地 0.1.4） | 可用 |
| 安全边界 | S2：`sec-fetch-site: cross-site` → 403 `cross-site request refused` | 正确 |
| Web 设置页 | 未在本轮 GUI 实测（仅 S4/源码）；client bundle 版本 0.1.4 | 限制 |

## R3 对 plain DSH 的补足矩阵

| plain DSH 缺口 | 证据（同一临时项目、无插件 profile） | 插件后 |
|---|---|---|
| workflow breadcrumb | S1 `session-2dda6bb3`：0 条 | 有 |
| no-task bootstrap | 同上 0 条 | 有 |
| 路径级 spec 注入 | 同项目 `write src/plain.js` 直接成功，无 deny | 有（deny-once + ticket） |
| 子代理上下文 push | 无（仅项目内 skill 由子代理自行加载） | 有（推送角色 skill + 任务上下文） |
| inline 派发守卫 | 无 | 有（fail-closed，research 放行） |
| `trellis_wait` | 无（只能 `run_in_background:false`） | 有（事件驱动） |
| `/trellis-status`/`finish`/`doctor` | 无命令面 | 有 |
| 会话身份 | `DSH_SESSION_ID` 由宿主提供，但无 `DSH_TRELLIS_CONTEXT_ID` 转发 | 有 |
| 技能/工作流本身 | 有（`.agents/skills` + `.dsh/skills`） | 不变 |

**仍只部分补足 / 宿主限制**：

1. **read 不能先阻断**：DSH 事件形状决定只读工具无 deny 路径，插件退化为 post-execute ticket
   （S1 `session-96b72b9e` 验证 ticket 可达；Codex 无 read 触发）。这是宿主限制，非插件缺陷。
2. **角色权限不可声明**：Codex agent toml 可声明 `sandbox_mode`/模型；DSH 无声明式 agent 定义，
   插件只能推送角色指令，无法强制工具/沙箱边界（宿主限制）。
3. **项目级零安装**：Codex 的 hooks/config 随项目走；DSH 插件必须装在 profile。`trellis init --dsh`
   不会安装插件（Trellis `DSH.md` 明示“optional companion plugin”），因此**未装插件的新项目仍是 plain DSH**。
   这是分布前置差异，不是插件行为缺陷。

## R4 新角度扫描

| 角度 | 结果 | 证据 |
|---|---|---|
| 并发/多项目 | 通过：同 session id 跨项目解析各自任务；指针/分片按项目根隔离 | S2 `s2-concurrency.mjs`、`proj2` |
| 异常 task.json | 通过：`task_error` 面包屑 + 修复指引 | S1 `session-8f386730` |
| 异常 config.yaml | 通过：无崩溃，面包屑继续；spec/模式回退安全（配置损坏时未观察到注入异常） | S1 `session-8f386730` turn |
| 指针指向已消失任务 | **缺陷候选 D1**：输出 `state: stale` + “no matching [workflow-state] block” + 无 bootstrap | S1 `session-202baae0`、S2 渲染 |
| 升级路径 | `trellis update --skip-all`（0.7.0-beta.4 → 同版本）：`.dsh/.agents/.codex` 哈希零变化；插件读取契约不变 | S2 `hashes-before/after-update.txt`、`update-diff.txt` |
| 长会话/压缩 | 未实测：headless 无 `/compact` 入口；源码确认 `compaction/end` 清 spec 状态、projection 负责重投 | S3 + S4 |
| 非 Git Trellis 项目 | 源码与既有 S2：`.trellis` 优先于 `.git` | S3 |
| 环境限制 | 隔离 profile 的 bash 工具稳定失败（`subprocess scope exited...`）；**plain profile 同样失败**，故为临时 DSH_HOME/profile 环境现象，不是插件引入 | S1 `plain-bash` 对照 |

## 问题清单（待用户确认后才修复）

### D1（P3，体验/一致性缺陷）：stale 指针的面包屑正文误导且缺 bootstrap

- **现象（S1）**：指针指向已不存在的任务目录时，DSH 注入
  ```
  Trellis workflow state: stale
  Active task: .trellis/tasks/10-22-does-not-exist

  Refer to `.trellis/workflow.md` for the current workflow step (no matching [workflow-state] block found).
  ```
  该正文在说“workflow 里没有匹配块”，但实际原因是活动任务指针失效；没有修复指引，
  且不再注入 bootstrap（`session-composer` 只对 `no_task` 追加 bootstrap）。
- **对照（已勘误）**：同一场景 Codex hook 输出 `Task: 10-22-gone (stale_session)` + 通用兜底
  行，且不附 bootstrap（S2：真实 payload 直调 `.codex/hooks/inject-workflow-state.py`，清除
  继承的 `DSH_*` 环境变量）。此前写成“降级为 no_task + bootstrap”是假阳性：`active_task.py`
  的 `resolve_context_key` 让继承的 `DSH_TRELLIS_CONTEXT_ID`（第 1 优先）或 `DSH_SHELL=1` +
  `DSH_SESSION_ID`（第 2 优先）用环境变量值构造 context key（`dsh_session-3b709400…`），先于
  payload 的 `session_id`；该 key 在临时项目里没有指针 → no_task + bootstrap。`_detect_platform`
  并不识别 DSH，payload 的 `session_id` 也没有被构造成 `dsh_<id>`。因此 DSH 的专用正文与
  bootstrap 是**增强**，不是 parity 对齐。
- **影响**：模型可能误判为 workflow 文件缺块；用户看到“stale”却得不到如何清理指针的指引。
  只影响异常路径，不影响正常主链路。
- **可选方案**：
  1. **推荐**：在 `resolveTrellisState` 中为 `stale` 提供专用正文（例如“活动任务指针指向不存在的
     目录：检查 `.trellis/.runtime/sessions/<key>.json` 并 `task.py finish` 或修正指针"),
     并在 stale 时也补 bootstrap；或在正文里明确“这是失效指针，不是 workflow 缺块”。
  2. 对齐 Codex 的 `stale_session` + 通用兜底行且不补 bootstrap（会丢失当前 DSH 的诊断与提醒增强）。
  3. 不改行为，仅补 README/spec 说明（维持现状）。
- **推荐**：方案 1（保留 stale 诊断，同时给出可执行修复指引），同步补一条单测 + 文档。

### 差异项（非缺陷，需用户决定是否处理）

| # | 差异 | 事实 | 说明 |
|---|---|---|---|
| A1 | bootstrap 频率 | DSH 每根会话一次；Codex 每轮 | README 已声明为设计选择；无功能损失 |
| A2 | 默认 dispatch mode | 插件首次进入项目自动补 `dsh.dispatch_mode: inline`；Codex 默认 `auto`（派发 implement/check 子代理） | 真实会话中两者审批链路都可用（S1 auto 派发 + push + wait）；若要求“默认工作形态与 Codex 完全一致”，可考虑默认 auto 或首次提示用户选择 |
| A3 | 角色权限模型 | Codex agent toml 可声明 sandbox/model；DSH 无声明式 agent | 宿主限制，插件无法等价实现；可在 DSH.md/README 标注 |
| A4 | 安装形态 | Codex 项目自带 hooks；DSH 需 profile 装插件 | 新项目未装插件时仍是 plain DSH；可在 Trellis init/DSH.md 中强化提示 |

## 未覆盖/限制

- Web 设置页、命令的 GUI 交互未实测（headless 无命令面；S2 验证 handler 与注册逻辑）。
- 真实压缩（`/compact`）未触发；压缩后重投由源码与单测支撑。
- 隔离 profile 的 bash 工具失败（plain 对照同样失败），因此“会话内跑 `task.py start` 后同轮
  面包屑切换”用真实 GUI 会话（S1，`session-3b709400`）取证；隔离环境内的 finish-work 全流程
  未跑通。
- Codex hooks 使用 `--dangerously-bypass-hook-trust` 以规避交互审批；hooks 本身真实执行
  （UserPromptSubmit / PreToolUse 均有事件证据）。

## 修复闸门

以上 D1 与差异项 A1–A4 均未做任何代码修改。等待用户逐条确认：

- D1 选方案 1 / 2 / 3（或不做）；
- A2 是否调整默认 dispatch mode（或仅文档化）；
- 是否需要在 README/spec/DSH.md 补充 A3/A4 说明。

确认后再进入修复与回归（含真实会话复测 + 单测）。

---

# 修复记录（用户确认后执行）

- 确认时间：2026-10-22
- 确认结论：D1 采用**方案 1**（stale 专用正文 + bootstrap）；A2 **保持 inline，仅文档化**；
  A1/A3/A4 不改变行为。

## 实现

| 文件 | 变更 |
| --- | --- |
| `lib/workflow.js` | 新增 `STALE_BREADCRUMB`：明确“失效指针，不是缺少 workflow 状态块”，给出检查 `.trellis/.runtime/sessions/` 与 `task.py finish` 的修复路径；项目自定义 `[workflow-state:stale]` 块优先；即使 workflow.md 没有任何状态块也保留该诊断。 |
| `lib/session-composer.js` | `stale` 与 `no_task` 一样追加一次性 bootstrap（子代理仍不注入）。 |
| `test/workflow.test.js` | stale 无项目块 → `STALE_BREADCRUMB`；workflow 无状态块 → 仍显式诊断。 |
| `test/session-composer.test.js` | stale 指针 → 面包屑 + bootstrap。 |
| `README.md` | 0.1.5 changelog、stale 语义、默认 `inline` 与 Codex `auto` 的差异说明。 |
| `.trellis/spec/platforms/dsh-workflow-behavior.md` | stale 契约（专用诊断 + bootstrap，不降级为 no_task）。 |
| `LOCAL_CHANGES.md`、`docs/validation-0.1.5-local.md` | 发布记录与验证记录。 |
| `package.json`、`lib/client.js` | `0.1.4` → `0.1.5`；client bundle 重建（diff 仅 `PLUGIN_VERSION`）。 |

## 验证

| 检查 | 结果 |
| --- | --- |
| `node --test "test/*.test.js"` | **364 tests / 360 pass / 0 fail / 4 skip** |
| 真实会话复测（`proj2`，`session-202baae0` resume） | 新正文生效：`The active task pointer ... This is a stale pointer, not a missing [workflow-state] block. Inspect ... task.py finish ...`；状态仍为 `stale` |
| bootstrap | 该会话已有可见 bootstrap（projection 去重），故未重复；新会话路径由 composer 单测覆盖（stale → 2 条消息） |
| 项目自定义 stale 块 | 单测：项目文案优先 |
| 版本一致性 | package.json / README / LOCAL_CHANGES / validation doc 均为 0.1.5；client bundle 仅版本戳变化 |

## 边界

- 已安装的 profile（web / trellis-headless）仍为 0.1.4 快照；需要重装插件或改 `link:` 并重启 DSH 才会加载 0.1.5。
- 本轮未提交任何 git 变更（按会话约定，提交需用户明确要求）。

---

# 第二轮：已安装 0.1.5 的实际使用校验（2026-10-22 23:18）

- 安装事实：`~/.dsh/profiles/web/node_modules/dsh-trellis` 为 **0.1.5**；复测当时 `lib/**`
  与仓库源码逐文件 sha256 一致；`lib/client.js` 的 `PLUGIN_VERSION = "0.1.5"`。本轮勘误只改
  注释/文档，安装目录与仓库此后存在文本差异（运行逻辑不变），重装可同步。
- 运行事实：DSH web 进程启动时间 `23:15:18`，晚于插件安装时间 `23:15:12`，即当前 GUI
  宿主加载的是 0.1.5（不是旧进程）。
- 校验方式：隔离 `DSH_HOME=/tmp/dsh-recheck/home`，profile 的 `dsh-trellis` **指向安装目录**
  （`~/.dsh/profiles/web/node_modules/dsh-trellis`，非源码 link），真实 LLM 会话。

## 复测矩阵（安装版）

| 用例 | 结果 | 证据 |
| --- | --- | --- |
| no_task 首轮 | breadcrumb + bootstrap 各 1 条 | `s1-spec` 会话 `session-4b691545` |
| spec deny-once | write 先 deny，重试成功 | 同上，tool/result 含 `<spec-context>` |
| stale 指针正文 | 0.1.5 专用诊断（`stale pointer, not a missing [workflow-state] block`） | `s2-stale` 同会话 resume |
| stale bootstrap | 安装版 composer：root stale → 2 条（breadcrumb + bootstrap），子代理不注入 bootstrap | `s2-stale-composer.mjs` |
| stale 自定义块 | 项目 `[workflow-state:stale]` 优先；inline 时追加 `<dsh-mode>` | `s2-stale-custom.mjs` |
| in_progress / inline / task_error | 状态变化后分别注入 `in_progress`、`in_progress-inline`、`task_error` | `s3-push`、`s6-guard`、`s8-taskerror` |
| 子代理 push | implement 子会话收到 `role=implement` + 任务路径；父会话调用 `trellis_wait` | `s3-push` 子会话 `0b56a7b2` |
| inline 守卫 | 拒绝 implement 派发，文案含“退出 inline 是用户决定” | `s6-guard` |
| skip 词 | 仅 `spec-context` 送达，breadcrumb/bootstrap 0 条 | `s4-skip` |
| 非 Trellis 目录 | 0 条插件消息 | `s5-plain` |
| read ticket | breadcrumb + bootstrap + `spec-context`（不拦截） | `s7-read` |
| 命令/doctor | 注册 `trellis-status` / `trellis-finish` / `trellis-doctor`；doctor 显示 0.1.5、8 个状态块 | `s2-commands.mjs` |
| 单元测试 | 364 / 360 pass / 0 fail / 4 skip；`node --check` 通过 | `unit-tests.log` |

## 结论

- D1 修复在**已安装 0.1.5** 上真实生效，行为与确认方案一致（专用正文 + bootstrap，自定义块优先）。
- 主链路无回归；未发现由本次修复引入的新问题、崩溃或越权行为。
- trellis-check 循环未发现需要修改代码的新问题；仅更新了 `docs/validation-0.1.5-local.md`
  的“安装后复核”记录（未提交）。

## 环境/交付备注

- `trellis-headless` profile 仍为 **0.1.4**；若使用该 profile，需要单独更新。
- 未提交项：`.trellis/spec/platforms/dsh-workflow-behavior.md`（含既有未提交内容 + 本次 stale
  契约）、`docs/validation-0.1.5-local.md` 的安装后复核段、本任务目录。提交需用户明确要求。

---

# 勘误：Codex stale 行为

- 原文（D1 对照段、README、spec、LOCAL_CHANGES、两处代码注释）称“Codex 在 stale 场景降级为
  `no_task` 并附 bootstrap”，**不成立**。
- 真实行为（S2，清除 `DSH_*` 后真实 payload 直调）：`Task: <dir> (stale_session)` +
  `Refer to workflow.md for current step.`，bootstrap 仅在完全没有任务指针时追加。
- 假阳性成因（源码 + 控制变量复核）：`common/active_task.py#resolve_context_key` 先看继承的
  DSH 身份——`DSH_TRELLIS_CONTEXT_ID`（第 1 优先），或 `DSH_SHELL=1` + `DSH_SESSION_ID`
  （第 2 优先）——并用**环境变量的值**构造 context key（`dsh_session-3b709400…`），先于
  payload 的 `session_id`。该 key 在临时项目中没有指针 → no_task + bootstrap。
  `_detect_platform` 只识别其它平台的 `*_PROJECT_DIR` 与脚本路径，不识别 DSH；payload 的
  `session_id` 也没有被构造成 `dsh_<id>`。早期勘误中的 `dsh_staletest` 是虚构的重建，
  原始环境已不可考，无法核实。
- 控制变量结果：clean env / 仅 `DSH_SESSION_ID` → `stale_session`；`DSH_SHELL=1` +
  `DSH_SESSION_ID` / `DSH_TRELLIS_CONTEXT_ID` → `no_task` + bootstrap。
- 处理：保留 0.1.5 行为（DSH 专用正文 + bootstrap 为增强）；更正 README、spec、LOCAL_CHANGES、
  validation 记录、代码注释与本报告表述。未改运行时代码逻辑。
