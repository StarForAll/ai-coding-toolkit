# 技术设计：dsh-trellis 对等性与不足验证

## 1. 验证对象与边界

| 层 | 对象 | 位置 |
| --- | --- | --- |
| 插件源码 | `dsh-plugins/dsh-trellis` 0.1.5 | 本仓库 |
| 已安装 web 插件 | `dsh-trellis` 0.1.5 | `~/.dsh/profiles/web/node_modules/dsh-trellis` |
| 已安装 headless 插件 | `dsh-trellis` 0.1.4 | `~/.dsh/profiles/trellis-headless/node_modules/dsh-trellis` |
| 宿主 | DSH 0.2.1-rc.2 | 全局安装 |
| Trellis | 0.7.0-beta.4 | 临时项目 `.trellis/` 与本仓库 |
| 对照平台 | Codex CLI 0.163.0 + `.codex/hooks.json` + `.codex/agents/*.toml` | 临时项目 |

验证只读插件源码/已安装包，运行行为在临时项目 `/tmp/dsh-trellis-parity-verify/` 中进行；本仓库只新增本任务目录。

## 2. 对照模型

### 2.1 Codex 的 Trellis 接线（源码事实）

- `UserPromptSubmit` → `inject-workflow-state.py`：每轮 `<workflow-state>` + no-task `<trellis-bootstrap>` + `<codex-mode>`（读 `codex.dispatch_mode`，默认 auto）。
- `PreToolUse`（`Edit|Write`，Codex 实际是 `apply_patch`）→ `inject-spec-context.py`：FULL 时 deny-once，正文随拒绝原因；ticket 走 additionalContext；状态在用户级目录；`SessionStart(clear|compact)` 追加 reset。
- `SubagentStart`（matcher `trellis-implement|check|research`）→ `inject-subagent-context.py`：以父 session 指针解析任务，输出角色 header + `Active task` + curated context；父指针缺失则静默。
- 角色定义：`.codex/agents/*.toml`（含 `developer_instructions`、`sandbox_mode`、可选模型）。
- 技能：`.agents/skills/` 共享技能（含入口技能），Codex 原生发现。
- 身份：shell 内 `CODEX_THREAD_ID`（Codex 注入），脚本解析为 `codex_<thread>`。
- 命令：Codex 无 Trellis 专用命令；入口是技能/提示词。

### 2.2 DSH + dsh-trellis 的接线（源码事实）

- `agent/pre-step` → `session-composer`：每步解析项目/任务/模式，注入 `source.kind=dsh-trellis` 的 breadcrumb（`form=breadcrumb`）与一次性 bootstrap（`form=bootstrap`），按 projection 去重；skip 词按 turn 生效；子代理不注入 no_task/bootstrap。
- `tools/pre-execute` → `spec-policy`：`edit`/`write` 的 FULL 直接 deny（reason 携带 spec）；ticket 通过 `tools/post-execute` 的 `additionalContexts`；状态持久化 `.trellis/.runtime/spec-inject/<session>.json`；`compaction/end` 清状态。
- `agent/pre-step`（子代理 step 1）→ `subagent-context`：从 dispatch prompt 的 `Active task:` 或父指针解析任务；角色来自 prompt 或 descriptor label；注入角色 skill 正文 + curated context。
- `tools/pre-execute` → `dispatch-guard`：`subagent`/`subagent_fork` 无任务（或 inline 模式）拒绝 implement/check；research 放行并附提示。
- `trellis_wait` 工具：监听 `subagent/end`，返回 settled 状态。
- 命令：`/trellis-status`、`/trellis-finish`、`/trellis-doctor`。
- 身份：`shellEnv` 贡献 `DSH_TRELLIS_CONTEXT_ID=dsh_<session>`；命令子进程也显式注入。
- 项目默认：首次解析项目时向 `.trellis/config.yaml` 补 `dsh.dispatch_mode: inline`（缺键时）。
- 客户端：设置页、doctor、版本监控、冲突通知。

### 2.3 Trellis 0.7.0-beta.4 的 DSH 契约（上游事实）

- `trellis init --dsh` 写 `.agents/skills` + `.dsh/skills` + `.dsh/DSH.md`；不写 hooks/settings/agent 定义。
- `.trellis/scripts/common/active_task.py` 原生识别 `DSH_SESSION_ID`/`DSH_SHELL`，也优先读 `DSH_TRELLIS_CONTEXT_ID`。
- `workflow.md` 的 DSH 块包含 `trellis_wait`/`run_in_background: false` 提示；`get_context.py --platform dsh` 渲染这些块。
- `DSH.md` 声明插件为可选伴侣；表格只列 breadcrumb/wait/commands/identity，未列 spec 注入与 subagent push。
- `task.py start` 的 JSONL 闸门读 `codex.dispatch_mode`；Trellis 核心没有 `dsh.dispatch_mode` 概念。

## 3. 证据分级与采集

| 级别 | 手段 | 用途 |
| --- | --- | --- |
| S1 | 真实 DSH headless 会话（真实 LLM、真实工具调用）+ 会话 jsonl | 主链路、注入内容、状态迁移、子代理 |
| S1 | 真实 `codex exec` / `codex exec resume` + rollout | Codex 对照、hook 实际投递 |
| S2 | 直接运行真实 hook 脚本（真实 payload、清除 DSH 继承环境变量） | 精确对照输出；避免模型叙述噪声 |
| S2 | Node 直接加载已安装插件模块，调用命令/doctor/handler | 命令面 |
| S3 | 插件 lib、Trellis 模板/脚本、DSH 源码契约 | 解释机制与根因 |
| S4 | `node --test` | 回归基线 |

真实会话以会话日志中的 `user/message.source`（`kind=dsh-trellis`, `form=...`）为准；Codex 以 rollout 的 developer/user 消息或 hook stdout 为准。

## 4. 测试矩阵

### 4.1 DSH（临时项目 `proj`，Trellis init `--codex --dsh`）

| # | 用例 | 期望 | 证据 |
| --- | --- | --- | --- |
| D1 | 首轮 no_task | breadcrumb + bootstrap 各 1 | session a78a |
| D2 | 同状态 resume | 不重复注入 | session a78a turn2 |
| D3 | 创建任务（planning） | planning-inline + dsh-mode；无 bootstrap | turn3 |
| D4 | 启动任务 | in_progress-inline；task 路径正确 | turn4 |
| D5 | shell 身份 | `DSH_SESSION_ID`/`DSH_TRELLIS_CONTEXT_ID`/task.py 一致 | turn4 bash |
| D6 | spec write | 首次 deny + 正文；重试成功 | src/app.js |
| D7 | spec 静默重触 | 窗口内无 deny | src/b.js |
| D8 | spec 内容变化 | 重新 FULL deny | src/c.js |
| D9 | 子代理 push | implement 角色 + Active task + prd | child 6ca4 |
| D10 | label 角色 | description 命中也 push | child 7053 |
| D11 | inline 守卫 | implement 拒绝 | turn7 |
| D12 | auto 无任务守卫 | 无任务 implement 拒绝 | 新会话 |
| D13 | trellis_wait | settled completed | turn8 |
| D14 | 子目录启动 | 根发现 + 任务状态 | src 会话 |
| D15 | 跳过词 | 0 注入 | 新会话 |
| D16 | task_error | 专用正文 | 破损 task.json |
| D17 | stale（0.1.4 vs 0.1.5） | 0.1.4 旧文案；0.1.5 专用正文 | 两 profile |
| D18 | 非 Trellis 目录 | 0 注入 | plain |
| D19 | 非 Git Trellis | 正常注入 | proj-nogit |
| D20 | 普通子代理 mention 角色 | 0.1.5 被 push/guard；0.1.6 修复为 generic | child 0351、新会话 |
| D21 | 子目录相对路径写 spec 文件 | 0.1.5 未 deny；0.1.6 修复 | src/d.js |
| D22 | 命令与 doctor（S2） | 正确输出 | s2-register |
| D23 | 项目默认写入 | 0.1.5 首次会话改 config；0.1.6 不写 | proj-fresh |
| D24 | trellis update | 0.1.6 不再产生插件造成的 config 修改 | proj |
| D25 | 单测 | 350/346 pass/0 fail/4 skip（0.1.6） | unit-tests |

### 4.2 Codex 对照（同一 `proj`）

| # | 用例 | 期望 | 证据 |
| --- | --- | --- | --- |
| X1 | 首轮 workflow-state | 模型可引用 no_task | thread 01a1661c |
| X2 | 任务 create/start | `codex_<thread>` 指针 | thread 01a16620-c537 |
| X3 | planning/in_progress | 状态正确 | resume |
| X4 | spec deny-once | 首次拒绝，重试成功 | rollout 01a1661d |
| X5 | SubagentStart（父有任务） | hook 输出 + 子上下文 | hook 输出 1160B |
| X6 | SubagentStart（父无任务） | 静默（空） | hook 输出 0B |
| X7 | 子代理自身 breadcrumb | 实测子代理收到 no_task/planning 面包屑 | child rollout |
| X8 | 身份嵌套 | DSH shell 内 codex 解析成 DSH key | codex-07 vs clean |
| X9 | 子目录 spec | hook 对 cwd 相对路径不匹配 | 直调 hook |

## 5. 已知限制

- 真实压缩（DSH `/compact` / 自动压缩）未触发；压缩后的重投仅由源码/单测支撑。
- DSH Web GUI 需要 `dsh web` 打印的鉴权 URL；在不泄露凭据的前提下未能进入，因此设置页与命令的 GUI 交互未实测。
- Windows 路径、Codex 交互式 TUI 的 hooks 未实测。
- 真实 LLM 行为有波动；关键结论均以会话日志/工具结果为准，不以模型自述为准。
- 临时项目与证据目录在 `/tmp`，不属于交付物。

## 6. 修复方案设计（仅在设计层面，未执行）

- 所有修复候选都必须先由用户确认；按“插件可独立修复 / 上游 Trellis 修复 / 宿主限制”分类。
- 插件内修复遵循现有分层：纯逻辑在 `lib/*.js`，单测在 `test/*.test.js`，真实复测用独立 profile + 临时项目。
- 任何影响注入契约的修改都要同步 `README.md`、`docs/validation-*.md` 与 `.trellis/spec/platforms/dsh-workflow-behavior.md`。

## 7. Upstream boundary

Trellis official upstream (e.g. `~/projects/other/Trellis`) is a read-only
reference in this environment. Any design/fix in this task must stay inside this
repository's own surfaces (`dsh-plugins/`, `.trellis/spec/`, docs/workflow
sources). Upstream findings (identity precedence, DSH workflow/DSH.md staleness)
are observations only — not issues, not work items, and not upstream patches.
