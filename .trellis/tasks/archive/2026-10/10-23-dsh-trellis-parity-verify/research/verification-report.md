# dsh-trellis 对等性与不足验证报告

- 日期：2026-10-23
- 任务：`.trellis/tasks/10-23-dsh-trellis-parity-verify`
- 运行时：DSH `0.2.1-rc.2`；Trellis `0.7.0-beta.4`；Codex CLI `0.163.0`；Node `v24.20.0`
- 插件：初检时本仓库 `dsh-plugins/dsh-trellis` `0.1.5`；web profile 安装 `0.1.5`；trellis-headless profile 安装 `0.1.4`。修复后源码与 trellis-headless 为 `0.1.6`（web 仍 0.1.5），见 §9
- 临时项目：`/tmp/dsh-trellis-parity-verify/{proj,proj-fresh,proj-nogit,plain}`（`proj` 用 `trellis init -y -u xzc --codex --dsh`）
- 证据目录：`/tmp/dsh-trellis-parity-verify/evidence/`
- 本报告不使用上一轮 `10-22-dsh-trellis-capability-verify-0-1-4` 的结论作为通过依据；所有“通过/失败”均来自本轮 S1/S2 证据，S3/S4 仅用于解释与回归。

## 1. 结论摘要

1. **主链路达到 Codex 同等效果**：workflow breadcrumb、no-task bootstrap、路径级 spec deny-once/ticket、子代理上下文 push、会话级任务身份、非 Trellis 零注入，均在真实 DSH 会话中复现；Codex 侧的 `UserPromptSubmit`、`PreToolUse`、`SubagentStart` 也用真实 `codex exec` 与真实 hook 复现并对照。
2. **补足了 plain DSH 的主要缺口**：无插件 DSH 只有 pull 技能；插件补上 breadcrumb、bootstrap、spec 注入、子代理 push、inline 守卫、`trellis_wait`、`/trellis-status`、`/trellis-finish`、`/trellis-doctor`、受管会话身份。
3. **本仓库可修复的 3 类实质问题**（均非 P0/P1，未造成主链路失败；0.1.6 已修复）：
   - **角色误判**：generic 子代理只要 prompt 提到 `trellis-agent-*`/`trellis-*` 就会被 push 角色上下文；无任务时还会被 dispatch guard 拒绝。
   - **子目录相对路径 spec 漏注入**：session cwd 是子目录、工具传 cwd 相对路径时，spec 匹配按项目根解析，漏掉 deny。
   - **默认模式与配置写入**：插件首次会话自动向被跟踪的 `.trellis/config.yaml` 写入 `dsh.dispatch_mode: inline`，与 Codex 默认 auto 不同，且会让 `trellis update` 把 config 标为“用户修改”。
4. **上游只读观察（不计入问题清单，不做修复）**：Codex-in-DSH 的身份优先级（上游 Trellis `resolve_context_key`）、Trellis 0.7.0-beta.4 的 DSH workflow/`DSH.md` 过期指令（`run_in_background`、“foreground” 文案、无 DSH-inline phase 变体）。按 `.trellis/spec/platforms/dsh-workflow-behavior.md` 的 *Upstream Trellis Is Read-Only* 政策，这些只作为边界记录；官方源码无修改权限，不提议上游补丁。
5. **安装状态**：初检时 `trellis-headless` 为 `0.1.4`（stale 旧文案）、web 为 `0.1.5`；0.1.6 修复后 trellis-headless 已更新，web 仍待更新（见 §9）。
6. **未发现 P0/P1 级崩溃、数据破坏或越权**；未发现插件在非 Trellis 目录、缺 `.git`、缺 config 等场景下的异常注入。

## 2. 证据等级

| 级别 | 手段 | 本轮使用 |
| --- | --- | --- |
| S1 | 真实 DSH headless 会话（真实 LLM、真实工具调用、会话 jsonl） | 主要结论 |
| S1 | 真实 `codex exec` / `codex exec resume` + rollout | Codex 对照 |
| S2 | 真实 hook 脚本 + 真实 payload 直调；直接加载已安装插件模块调用命令/doctor | 精确输出对照 |
| S3 | 插件 lib、Trellis 0.7.0-beta.4 模板/脚本、DSH 源码事件表 | 根因解释 |
| S4 | `node --test "test/*.test.js"` | 回归基线 |

> 真实 LLM 的“自述”只作为线索；所有关键结论以会话日志中的 `user/message.source` / tool 事件 / hook stdout 为准。

## 3. 对照矩阵

| 能力 | Codex 实际接线 | DSH + dsh-trellis | 判定 |
| --- | --- | --- | --- |
| 每轮 workflow-state | `UserPromptSubmit` 每轮注入 `<workflow-state>`；状态来自任务记录 | `agent/pre-step` 注入，按 projection 去重（同状态不重复）；状态变化即注入 | 对齐（频率不同，见 §6.1） |
| no-task bootstrap | 每个无任务轮次附 `<trellis-bootstrap>` | 每个根会话一次（独立消息家族）；stale 在 0.1.5 也补一次 | 对齐；频率差异为设计选择 |
| dispatch mode | `<codex-mode>` 读写 `codex.dispatch_mode`（默认 auto；非法→inline） | `<dsh-mode>` 仅 inline 时出现；读 `dsh.dispatch_mode`（默认 auto；非法→auto）；首次会话写 inline | 机制对齐；默认值/配置键不同 |
| 路径级 spec | `PreToolUse(Edit\|Write)`，FULL 时 deny-once；ticket 走 additionalContext；状态持久 | `tools/pre-execute` deny-once + `tools/post-execute` ticket；状态持久；compaction/end 重置 | 对齐 |
| spec 刷新 | sha 变化/窗口外/重置 → FULL；窗口内静默 | 同 | 对齐（实测） |
| 子代理上下文 | `SubagentStart` 按 agent_type 精确匹配；父指针解析任务；父指针缺失静默 | 子代理 step 1 按 prompt 角色 + `Active task:`/父指针 push；roles 来自 skill | 对齐；DSH 在“父指针缺失但 prompt 有任务”时更稳健 |
| 子代理面包屑 | Codex 子代理也会收到 UserPromptSubmit 的 no_task/父状态面包屑（实测矛盾） | 子代理不注入 no_task/bootstrap；只 push 任务上下文 | DSH 更优 |
| 角色定义/权限 | `.codex/agents/*.toml` 声明 `developer_instructions`、`sandbox_mode`、模型 | 无声明式 agent；push 角色 skill 正文；权限继承父会话 | 内容对齐；权限/模型声明为宿主限制 |
| 入口技能 | `.agents/skills` | `.agents/skills` + `.dsh/skills`（DSH 优先 `.dsh`） | 对齐 |
| 命令 | 无 Trellis 命令 | `/trellis-status`、`/trellis-finish`、`/trellis-doctor` | DSH 增强 |
| 会话身份 | `CODEX_THREAD_ID` → `codex_<id>` | `DSH_TRELLIS_CONTEXT_ID=dsh_<id>` + `DSH_SHELL/DSH_SESSION_ID` 原生支持 | 对齐；嵌套宿主有污染（§5.4） |
| 项目模式默认 | 不改项目文件；默认 auto | 首次会话写 `dsh.dispatch_mode: inline` | 有意差异/需决策（§5.3） |

## 4. 实测结果

### 4.1 DSH 主链路（S1）

会话 `session-a78a1e47-f11b-41a5-af00-cec8d5e9d5ea`（`proj`）：

| 轮次 | 事件 | 证据 |
| --- | --- | --- |
| turn1 | `breadcrumb`（status=no_task）+ `bootstrap` 各 1 条；随后 `AGENTS.md`/runtime/skill catalog 正常 | session log seq 10/11 |
| turn2 | 同状态 resume，无重复注入 | 无新增 dsh-trellis 消息 |
| turn3 | 创建任务后 `planning-inline` + `Active task: .trellis/tasks/10-23-demo-feature` + `<dsh-mode>inline…`；无 bootstrap | seq 41 |
| turn4 | 启动任务后 `in_progress-inline`；shell 内 `DSH_SESSION_ID`/`DSH_TRELLIS_CONTEXT_ID` 与 `task.py current --source` 一致 | seq 53/57/60 |
| turn5 | `write src/app.js` 首次被 deny，拒绝原因含 `<spec-context … sha256=…>` 全文；读取 spec 后重试成功 | tool call 76 / result 77 / call 88 |
| turn6 | 窗口内 `write src/b.js` 不再 deny | call 152 |
| turn7 | spec 内容变化后 `write src/c.js` 再次 FULL deny（新 sha） | result 236 |
| turn8 | auto 模式 breadcrumb 为 `in_progress`（无 dsh-mode banner），正文含 DSH/trellis_wait 指引 | in_progress 消息 |
| turn9 | 子代理 implement：`subagent-context` role=implement，含 Active task、角色 skill 正文、prd.md；父会话 `trellis_wait` 返回 settled completed | child 6ca4 / wait result |
| turn10 | description 以 `trellis-agent-check` 开头、prompt 不提角色 → 仍 push role=check | child 7053 |
| turn11 | inline 模式 dispatch implement → guard 拒绝，文案明确“退出 inline 是用户决定” | turn7 结果 |
| turn12 | auto 模式、无任务 dispatch implement → guard 拒绝“no readable active task” | 新会话结果 |
| 其它 | skip 词 0 注入；task_error 专用正文；stale 专用正文（0.1.5）与旧文案（0.1.4）；非 Trellis 0 注入；非 Git Trellis 正常注入；子目录启动根发现正常 | 见证据目录 |

### 4.2 Codex 对照（S1/S2）

| 用例 | 证据 |
| --- | --- |
| `UserPromptSubmit` 注入 | thread `01a1661c`：模型被要求引用时输出 `Status: no_task…`；直调 hook 输出 `<trellis-bootstrap>` + `<codex-mode>auto…` + `<workflow-state>` |
| 任务生命周期 | thread `01a16620-c537`：`task.py create` → `codex_01a16620-c537….json`；resume 后 `Task: codex-demo2 (planning)`；start 后 `Task: codex-demo2 (in_progress)` |
| spec deny-once | rollout `01a1661d`：`Trellis injected governing specs… Command: *** Begin Patch` + `<spec-context …>`；模型读 spec 后重试成功 |
| SubagentStart（父有任务） | 真实 payload 输出 1160B：`# Trellis Native Implement Subagent` + `Active task` + `## Curated Context`（含 prd.md）；子 rollout 收到该 developer 消息 |
| SubagentStart（父无任务） | 真实 payload 输出 0B；即使 dispatch prompt 有 `Active task:` 也不注入（Codex 只认父指针） |
| 子代理自身面包屑 | 子 rollout 同时收到 `<trellis-bootstrap>` + `<workflow-state>Status: no_task`（与其角色任务矛盾）以及父会话历史中的 `Task: codex-demo2 (planning)` |
| 子目录 spec | 直调 hook：`cwd=proj/src` + `d.js` → 无输出；`cwd=proj` + `src/d.js` → deny + spec 正文 |

### 4.3 DSH 对 plain DSH 的补足（S1/S3）

| plain DSH 缺口 | 证据 | 插件后 |
| --- | --- | --- |
| 无 workflow breadcrumb/bootstrap | 无插件会话 0 条 dsh-trellis 消息 | 有 |
| 无路径级 spec deny-once | 直接 write 成功 | 有（deny-once + ticket） |
| 无子代理上下文 push | 仅靠 child pull | 有（角色 skill + curated context） |
| 无 inline/无任务守卫 | 无 | 有（fail-closed，research 放行） |
| 无事件驱动等待 | 只能依赖宿主通知/轮询（禁止） | `trellis_wait` |
| 无命令面 | 无 | `/trellis-status`、`/trellis-finish`、`/trellis-doctor` |
| 无受管会话身份 | 仅 `DSH_SESSION_ID`（Trellis 0.7 原生已识别） | 额外 `DSH_TRELLIS_CONTEXT_ID`，命令子进程一致 |

## 5. 问题清单（待用户确认后才修复）

> P2-3 / U1 / U2 的源码级与选项级展开见 `research/remaining-issues-analysis.md`。

### P0/P1

无。

### P2-1 角色误判：generic 子代理被 push/拒绝

- **现象**
  - 子代理 prompt 出现 `.dsh/skills/trellis-agent-implement/SKILL.md`（只是要读该文件）时，插件 push 了 `role=implement` + 父任务 prd.md，并声称“你是被派发的 implement 角色”。证据：child `0351f9c3-e6ef-4c63-966a-d1e29c8256f6`（description `docs reader`）。
  - 无任务会话中，同样只含 `trellis-agent-check` 的 generic 委派被 dispatch guard 拒绝（“no readable active task for trellis-agent-check”）。证据：`headless-14`。
- **根因**：`subagent-context.js` 的 `roleFrom(text)` 扫描整个 prompt（`AGENTS_ROLE`/`BARE_ROLE`），`dispatch-guard.js` 的 `ROLE_RE` 同；Codex 用 `agent_type` matcher，不存在此问题。`description` 的严格前缀规则只覆盖 label，不覆盖 prompt。
- **影响**：错误角色契约/任务上下文注入；合法 generic 委派被拒；可能让子代理误以为自己应直接改代码。
- **候选**：见 `implement.md` C1（专用角色标记/首行、忽略路径限定提及、或只用 description；或仅文档化）。

### P2-2 子目录相对路径导致 spec 漏注入（与 Codex 共同）

- **现象**：session cwd=`proj/src`，`write` 参数 `file_path=d.js` 成功且无 deny；同样内容在 cwd=`proj`、`file_path=src/d.js` 会 deny。证据：`session-20cda846…`（`d.js` 成功）；Codex hook 直调（`cwd=proj/src` 无输出，`cwd=proj` 有输出）。
- **根因**：`spec-glob.normalizeRepoRelative(root, filePath)` 把相对路径按项目根解析，忽略 agent 当前工作目录；Codex hook 的 `normalize_repo_relative(root, raw_path)` 同。
- **影响**：子目录启动的会话可能静默跳过 spec 校验；这是“specs injected, not remembered”核心契约的 correctness 缺口。
- **候选**：见 `implement.md` C2（插件按 cwd 解析 + root 兜底取并集；或上游统一修）。

### P2-3 默认 inline + 自动写 tracked config

- **现象**：fresh 项目首次 DSH 会话后 `git status` 出现 `M .trellis/config.yaml`；diff 为插件追加的 `dsh: dispatch_mode: inline` 注释块。`trellis update --dry-run` 把 config 列为 “Modified by you (need your decision)”。证据：`proj-fresh`、`proj`。
- **补充证据**：`trellis update -f` 会覆盖掉该段（实测 diff 删除 6 行），下一次 DSH 会话又写回；`task.py start` 的 JSONL 闸门把 `.dsh` 无条件视为 sub-agent-capable（`_SUBAGENT_CONFIG_DIRS` 含 `.dsh`），即使 `dsh.dispatch_mode: inline` 仍要求 curated jsonl 或 `--allow-empty-context`；`get_context.py --mode phase --step 2.1 --platform dsh` 在 inline 下仍输出 “Spawn the implement sub-agent…”，Trellis 0.7.0-beta.4 没有 DSH-inline 的 phase 变体。
- **影响**：与 Codex 默认 auto 不同；用户未操作却产生待提交改动；每次 `trellis update` 都可能提示 config 冲突；共享仓库中每个 DSH 用户首次运行时都会写同一段；inline 只在面包屑层成立（phase detail 仍教派发）。
- **候选**：见 `implement.md` C3 与 `research/remaining-issues-analysis.md` §A/D（不写 tracked config/改默认 auto/用户确认后写）。

### U1（上游只读观察，不计入问题）Codex-in-DSH 身份优先级

- **现象**：从当前 DSH 托管 shell 启动 `codex exec`，codex 内 `task.py create` 解析为 `Source: session:dsh_session-d9b7dd5b…`；清除 `DSH_*` 后解析为 `Source: session:codex_01a16620-c537…`。控制实验：仅 `DSH_SHELL=1`+`DSH_SESSION_ID`（无插件变量）+`CODEX_THREAD_ID` 仍解析为 DSH key。
- **归属**：Trellis 官方 `common/active_task.py#resolve_context_key` 的优先级；DSH 只清理自己的托管 shell，不清理任意子进程。
- **处理**：按 *Upstream Trellis Is Read-Only* 政策，仅记录为边界；不在本仓库修复，不提议上游补丁，不作为待办项。

### U2（上游只读观察，不计入问题）Trellis DSH workflow/DSH.md 过期

- **现象**：`get_context.py --mode phase --platform dsh` 仍输出 “Without `trellis_wait`, dispatch that child with `run_in_background: false`”；实测 DSH 0.2.1-rc.2 的 `subagent` schema 无该参数，传入被静默忽略，仍立即返回 child ID（`headless-19-runbg`）。`DSH.md` 同时写 “Without companion plugin: Foreground native sub-agent”，也已过期；且 DSH 的 phase detail 没有 inline 变体（`dsh.dispatch_mode: inline` 仍显示派发文本）。
- **处理**：按 *Upstream Trellis Is Read-Only* 政策，仅记录为边界；本仓库只通过插件 banner/文档缓解，不修改上游文件，不作为问题或修复项。

### P3-1 trellis-headless 安装版本漂移

- **现象**：web profile `0.1.5`，trellis-headless `0.1.4`；stale 指针会话仍输出旧文案 `Refer to ... (no matching [workflow-state] block found)`，而 web 0.1.5 输出专用诊断。证据：`session-977c6271…`（0.1.4）、`session-d939701b…`（隔离 0.1.5）。
- **影响**：使用 headless profile 的用户得到较差/误导的 stale 文案。
- **修复**：更新 trellis-headless profile 到 0.1.5（见 `implement.md` C6）。

### P3-2 配置契约分裂

- **现象**：`dsh.dispatch_mode` 只被插件读取；Trellis 的 `task.py start` JSONL 闸门由 `_has_subagent_platform()` 决定，`.dsh` 目录被无条件视为 sub-agent-capable（与 mode 无关），`workflow_phase.py` 只认识 `codex.dispatch_mode`。inline 项目 `task.py start` 无 `--allow-empty-context` 会因空 jsonl 被拒；插件靠 `<dsh-mode>` banner 提示绕过。证据：本任务自身 `task.py start` 需 `--allow-empty-context`；`proj-mode` 实测 `.dsh` 单独存在即触发闸门。
- **影响**：共享 Codex+DSH 项目可能出现两套模式语义；用户可能困惑。
- **候选**：见 `implement.md` C7（上游支持 `dsh.dispatch_mode`；或仅文档）。

### P3-3 文档缺口/声明不一致

- Trellis `DSH.md` 表格未列 spec 注入、subagent push、dispatch guard；用户可能低估插件。
- 插件 README 的 “generic 子代理保持静默” 与实测 prompt 提及角色的情况不符（label 规则严格，prompt 规则宽泛）。
- 这两个站点应在修复 P2-1/C1 时同步。

### 观察项（非缺陷）

- **bootstrap 每会话一次 vs Codex 每轮**：README 明确为设计选择；实测符合。
- **DSH 面包屑同状态去重**：Codex 每轮；DSH 依据 projection。改变状态会立即注入；本轮未发现丢失。
- **重复入口技能**：`.agents/skills/trellis-start` 与 `.dsh/skills/trellis-start` 同名但平台参数不同；DSH 实测加载 `.dsh` 版本（`--platform dsh`）。若未来解析顺序变化会引入平台提示错误，建议在文档中固定优先级。
- **子代理已内联角色 skill，但 dispatch prompt 仍要求“load exactly once”**：实测子代理仍会读一次（token 浪费，无功能错误）。属于提示词冲突，可在 C1 模板修复时一起收敛。
- **Codex 子代理的 no_task 面包屑**：Codex 侧问题，DSH 已避免；不是 DSH 缺口。

## 6. 限制与未覆盖

- **压缩**：未触发真实 DSH compaction；插件 `compaction/end` 重置逻辑仅有源码/单测支撑。Codex `SessionStart(clear|compact)` 同理。
- **GUI**：`dsh web` 需要启动时打印的鉴权 URL；在不将凭据放入命令行/URL 的前提下未进入，设置页、`/trellis-*` 命令的 GUI 交互未实测；命令 handler 已用 S2 真实模块执行验证。
- **Windows**：未验证路径/编码分支。
- **Codex 交互式 TUI**：仅 `codex exec`；TUI 的 hooks 信任流程未验证。
- **真实 LLM 波动**：个别模型自述可能夸大/遗漏；本报告以会话日志与 hook stdout 为准。

## 7. 安全附带发现（与本任务范围无关，未改动）

- `~/.codex/config.toml` 中存在明文凭据：`model_providers.custom.experimental_bearer_token` 与多个 `mcp_servers.*` 的 API key/header。本会话的工具输出已包含这些值（剩余暴露面为当前会话记录/日志）。按规则不复述值；建议轮换，并改为 `env_key`/受控凭据引用。本次未修改该文件。

## 8. 待确认的修复方案

见 `implement.md` §C（C1–C7）。本轮未改任何插件代码、未提交、未推送；等待用户逐项确认后再进入实现与回归。

## 9. 修复实施与复测（0.1.6，2026-10-23）

用户确认范围：C1、C2、C3、C6、C7；模式选择 **B**（默认 inline、不写 tracked config、
补 inline 契约）；配置写入策略“不写任何 tracked config”；上游 `~/projects/other/Trellis`
本轮不改。

### 9.1 已改

| 项 | 变更 | 证据 |
| --- | --- | --- |
| C1 | `role-contract.js` 新增声明式 `roleFromPrompt`；`subagent-context.js` 与 `dispatch-guard.js` 改用它；路径/普通叙述不再触发 push/guard | `test/role-contract.test.js`、`test/subagent-context.test.js`、`test/dispatch-guard.test.js` |
| C2 | `spec-glob.js` 新增 cwd 相对解析；`spec-policy.js` union cwd/root 候选 | `test/spec-policy.test.js` 子目录 deny 用例 |
| C3 | `dshDispatchMode` 缺省/非法 → inline；删除 `project-defaults.js` 与其测试；`session-composer.js` 只读；banner 增加 phase-detail 覆盖与 `.dsh` 闸门说明 | `test/workflow.test.js`、`test/session-composer.test.js`、`test/breadcrumb-skip-turn.test.js` |
| C6 | `~/.dsh/profiles/trellis-headless` 安装 0.1.6（旧 0.1.4 备份在 `/tmp/dsh-trellis-parity-verify/headless-dsh-trellis-0.1.4`） | 真实安装会话 `session-78559178…` stale 专用正文 |
| C7 | README / LOCAL_CHANGES / manual-verification / `.trellis/spec/platforms/dsh-workflow-behavior.md` 更新 | 见 diff |

### 9.2 复测结果

| 检查 | 结果 |
| --- | --- |
| 单测 | **350 tests / 346 pass / 0 fail / 4 skip** |
| 新项目首会话（无 `dsh:` 段） | 面包屑带 `<dsh-mode>`；`git status` 无 config 改动（`proj-016` / `proj-016b`） |
| generic 子代理（只读 role skill 路径） | 子会话 0 条 `dsh-trellis` 消息（child `eef038cf…`） |
| 声明式角色（`Role: trellis-agent-implement`） | 子会话收到 `form=subagent-context role=implement`（child `52ab6a48…`） |
| 子目录 spec（cwd=`src`，`d.js`） | deny + `<spec-context file="src/d.js">`，重试成功（`session-67f8651d…`） |
| 已安装 headless 0.1.6 stale | 专用正文 + 修复指引（`session-78559178…`） |
| 真实安装默认可写性 | `proj-016b` 首会话后 `git status` 为空 |

### 9.3 仍需处理 / 边界

- **Web profile 仍是 0.1.5**：当前 Web 会话未加载 0.1.6；需要用户确认后更新 web profile
  并重启 DSH。
- **U1/U2 按用户政策忽略**：上游 Trellis 只读，identity 优先级与 DSH workflow/DSH.md 过期指令只作为边界观察，不再视为本仓库问题或待办项。
- 未提交、未推送；本轮没有提交任何 git 变更。
- 真实 compaction、Web GUI、Windows 仍未实测。
