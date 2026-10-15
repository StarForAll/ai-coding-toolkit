# ZCode 平台 Trellis 冒烟测试报告

- 测试日期：2026-10-15（证据采集时间约 23:00–23:10 本地）
- 平台：zcode（ZCode CLI，Claude 兼容形态）
- 仓库：`/home/xzc/projects/personal/ai-coding-toolkit`
- 主会话上下文键：`claude_sess_65981aab-0813-44b2-87f9-444fa7b81e51`（会话文件 `.trellis/.runtime/sessions/claude_sess_65981aab-0813-44b2-87f9-444fa7b81e51.json`）
- 本报告撰写者：`trellis-implement` 子代理（经主会话 Agent 工具调度，subagent 会话标识推断为 `sess_subagent_agent_9f1fa91e-c105-4d77-ad4a-2f7645feda8b`，来源：子代理 exec 日志目录名 `/home/xzc/.zcode/cli/exec/sess_subagent_agent_9f1fa91e-c105-4d77-ad4a-2f7645feda8b/`）
- 解释器：`/softwares/python/bin/python3`（按调度指令）
- 证据边界：除标注"主会话观察（待复核）"的条目外，以下所有证据均为本子代理在本次会话内直接运行命令/读取文件所得。

## 子代理调度观察（本报告关键一节）

1. **未收到 hook 注入标记**：本子代理的输入中**不含** `<!-- trellis-hook-injected -->` 标记，也没有任何预注入的任务工件（prd.md / implement.jsonl / spec 文件均未出现在输入中）。本子代理按协议自行加载了上下文：`implement.jsonl` → 其列出的 `.trellis/workflow.md` → `prd.md` → `task.json` → `check.jsonl`（任务目录无 design.md / implement.md）。
2. **活动任务解析**：能从调度 prompt 首行 `Active task: .trellis/tasks/10-15-zcode-trellis-smoke-test` 正确解析活动任务。
3. **子代理内运行 `task.py current --source` 的结果**（自行运行两次，均一致）：
   ```
   Current task: (none)
   Source: none
   （exit 1）
   ```
   原因有二，均有实证：
   - 子代理 Bash 调用**不触发** PreToolUse Bash 会话票据（见验证矩阵第 4 行），task.py 拿不到任何会话身份；
   - 会话绑定是按上下文键隔离的：绑定写在主会话键下，本子代理的键无对应会话文件，解析为空属于 per-session 语义的设计内行为。
4. **注入断点定位**（只读模拟，未修改任何文件；`inject-subagent-context.py` 只读 stdin、只打印 JSON、不写文件）：
   - 输出通道确认：该脚本对 ZCode 走 `hookSpecificOutput.updatedInput` 重写子代理 prompt（`.zcode/hooks/inject-subagent-context.py` 第 1188–1196 行），若生效，子代理 prompt 会被整体替换为带标记的版本。
   - 合成 **camelCase 载荷**（`{"toolName":"Agent","toolInput":{...}}`——正是该脚本 docstring 第 1056 行自述的 ZCode 形态）+ 有效 session_id（`sess_65981aab-…`）：脚本 **exit 0 且零输出**（静默 no-op）。
   - 分步调用定位：`_parse_hook_input` 在该载荷上返回 `subagent_type: ''`。根因在第 1060–1064 行：
     ```python
     tool_input = input_data.get("tool_input", {})
     if not isinstance(tool_input, dict):
         tool_input = input_data.get("toolInput", {})
     ```
     键缺失时 `.get("tool_input", {})` 的默认值 `{}` 本身就是 dict，`toolInput` 回退分支**永远不可达**（死回退）→ 随后在第 1117–1118 行 `subagent_type not in AGENTS_ALL` 静默退出。
   - 对照实验：**snake_case 载荷**（`{"tool_name":"Agent","tool_input":{...}}`）解析正常，返回 `'trellis-implement'`。
   - 同一 camelCase 载荷下，链路其余环节全部正常：`_detect_platform` 返回 `zcode`；`get_current_task` 解析出 `.trellis/tasks/10-15-zcode-trellis-smoke-test`；`get_implement_context` 产出 **34,696 字符**上下文。
   - 结论：观察到的"未注入"与两种情形相容——(a) ZCode 实际发送 camelCase 载荷，钩子脚本的死回退缺陷吞掉注入；(b) ZCode 未对该 Agent 调用触发 PreToolUse 钩子。**从子代理内部无法进一步区分**，待主会话复核（建议：在钩子中临时加 stderr 日志，或查看 ZCode 钩子执行日志）。
5. **兜底链路有效性**：即使注入失效，workflow.md 2.1 要求的调度 prompt 首行 `Active task:` 前奏在位，子代理按协议自行加载仍可获得完整上下文（本次实际如此，链路未完全断，但注入能力本身未通过验证）。

## 验证矩阵

| # | 验证项 | 期望 | 实际证据 | 结论 |
|---|--------|------|----------|------|
| 1 | SessionStart 注入（主会话） | compact 上下文 + first-reply-notice | 主会话输入中观察到（待复核：子代理无法直接观测主会话输入） | ✓（主会话观察） |
| 2 | UserPromptSubmit breadcrumb | 随任务状态切换 | 主会话观察：初始 `no_task`。本子代理模拟带 session_id 的载荷：返回 `hookSpecificOutput.additionalContext`，正文 `Task: zcode-trellis-smoke-test (in_progress)`；无身份载荷降级为 `Status: no_task`（设计内降级） | ✓ |
| 3 | PreToolUse Bash 会话票据（主会话） | `task.py start/current/finish` 前写票据 | 主会话观察到票据 `1792076362291-6a455ae87ce860f7.json`（`"platform": "zcode"`，context_key `claude_sess_65981aab-…`）。本子代理在运行窗口内于 `.trellis/.runtime/shell-tickets/` 看到后续票据 `1792076476348-7fdb5028f50a02d3.json`（942 B，created_at epoch 1792076476.348 = 15:01:16Z），随后消失；主会话文件 `last_seen_at: 2026-10-15T15:01:21Z` 与之相差 5 秒，与"钩子写票据 → task.py 消费"时序吻合（票据归属主会话运行，推断依据见第 4 行） | ✓ |
| 4 | PreToolUse Bash 会话票据（子代理 Bash） | 同上 | 决定性探针：含 `task.py current --source` 的命令启动时，`shell-tickets/` 目录为空（`find … -name '*.json'` 零输出；票据若写入应先于 shell 执行存在）。票据桥对子代理 Bash 调用不生效（钩子未触发或载荷无会话身份，内部无法区分） | ✗ |
| 5 | `task.py create` | 任务目录与 task.json 生成 | `.trellis/tasks/10-15-zcode-trellis-smoke-test/` 存在，含 task.json（status 字段等完整） | ✓ |
| 6 | create 阶段会话绑定 | workflow.md：create "when session identity is available" 时 auto-bind | 主会话观察到 create 后 `current --source` 返回 `(none)`（待复核原文）。机制核实：`inject-shell-session-context.py` 第 38 行 `SESSION_SUBCOMMANDS = {"start", "current", "finish"}` **不含 create**——ZCode 上 create 永远拿不到会话身份，auto-bind 结构性不可达 | ✗（结构性缺口） |
| 7 | `add-context` | implement.jsonl / check.jsonl 各含真实条目 | 两文件各 1 条：`{"file": ".trellis/workflow.md", "reason": "…"}`（本子代理已按其加载） | ✓ |
| 8 | `task.py start` | status planning→in_progress + 会话绑定 | `task.json`：`"status": "in_progress"`；会话文件：`current_task: ".trellis/tasks/10-15-zcode-trellis-smoke-test"`；主会话输出 `Source: session:claude_sess_65981aab-…`（待复核原文）；`task.py list --status in_progress` 列出本任务（Total: 1） | ✓ |
| 9 | Agent 调度上下文注入 | 子代理收到 `<!-- trellis-hook-injected -->` | **本子代理实测未收到标记**（见"子代理调度观察"第 1、4 条）；模拟定位 camelCase 死回退缺陷或钩子未触发 | ✗ |
| 10 | ZCode 部署资产 | agents/skills/commands/hooks/config 齐备 | `ls` 清点（见下） | ✓ |

### 部署资产清点（验证矩阵第 10 行证据）

- `.zcode/config.json`：4 类钩子事件——SessionStart（matcher `startup|clear|compact`）→ session-start.py；UserPromptSubmit → inject-workflow-state.py；PreToolUse（matcher `Agent|Task`）→ inject-subagent-context.py；PreToolUse（matcher `Bash`）→ inject-shell-session-context.py。
- `.zcode/agents/`：`trellis-check.md`、`trellis-implement.md`、`trellis-research.md`（3 个）。
- `.zcode/skills/`（9 个）：trellis-before-dev、trellis-brainstorm、trellis-break-loop、trellis-channel、trellis-check、trellis-meta、trellis-session-insight、trellis-spec-bootstrap、trellis-update-spec。
- `.zcode/commands/trellis/`：`continue.md`、`finish-work.md`。
- `.zcode/hooks/`：4 个脚本（session-start.py 36,260 B、inject-workflow-state.py 20,748 B、inject-subagent-context.py 39,597 B、inject-shell-session-context.py 10,183 B）。
- 任务产物：`prd.md`（2,812 B，含 Goal/Scope/Acceptance Criteria/Non-Goals）、`task.json`、`implement.jsonl`、`check.jsonl`；无 design.md / implement.md（轻量任务，PRD-only 合法）。

## 发现的问题 / 偏差（open items）

1. **【缺陷 · 高】子代理上下文注入未生效**：本次 `trellis-implement` 调度未收到注入（实证）。模拟定位到 `.zcode/hooks/inject-subagent-context.py` `_parse_hook_input`（第 1060–1064 行）对 camelCase 载荷（`toolName`/`toolInput`）的死回退缺陷；或 ZCode 未触发该钩子。二者从子代理内部无法区分，**待主会话复核**。影响：注入失效时子代理退化为自行加载，完全依赖调度 prompt 的 `Active task:` 前奏（本次前奏在位，兜底有效）。
2. **【缺陷 · 中】子代理 Bash 无会话票据桥**：PreToolUse Bash 钩子对子代理 Bash 调用不写票据（探针实证），子代理内 `task.py start/current/finish` 无法解析会话身份，`current --source` 返回 `(none)`。影响：子代理内无法做需要会话绑定的任务操作；子代理也不应做（dispatch 协议本就由主会话持有绑定），但 `current` 的 none 返回与主会话视图不一致，排查时易误判。
3. **【缺口 · 中】create 的 auto-bind 在 ZCode 上不可达**：票据桥 `SESSION_SUBCOMMANDS` 不含 create（代码实证），主会话"create 后 current 为 (none)"的观察符合机制而非偶发。Workaround：create 后立即手动 `task.py start <task-dir>`（本次流程即如此）。
4. **【预警 · 中】branch == base_branch == main**：`task.json` 已核实 `"branch": "main"`、`"base_branch": "main"`。主会话报告 `task.py start` 警告 archive 将拒绝该状态（警告原文待复核）。归档前需 `task.py set-branch` 或调整，否则 Phase 3 归档会被阻断。
5. **【待办】冒烟测试剩余步骤**：`trellis-check` 子代理调度（对 report.md 的检查）、`task.py archive`、journal 追加（finish-work / add_session.py）尚未执行。
6. **【观察 · 非缺陷】** UserPromptSubmit 钩子在无会话身份载荷下降级为 `no_task` breadcrumb——设计内降级路径，非故障。

## 结论

- **可用**：任务生命周期主链 create → add-context → start（状态切换与会话绑定均实证）；主会话侧注入链 SessionStart / UserPromptSubmit / Bash 票据桥（主会话观察 + 本子代理模拟交叉印证，in_progress breadcrumb 正确反映）；ZCode 部署资产静态齐备（4 hooks + 3 agents + 9 skills + 2 commands + config）。
- **未通过**：子代理上下文注入（本子代理实测未收到标记；钩子脚本存在 camelCase 载荷死回退缺陷的模拟实证，或钩子未触发，待复核）；子代理 Bash 票据桥（实证不生效）；create auto-bind（结构性不可达，机制实证）。
- **合规**：全程仅新增本报告文件（`.trellis/tasks/10-15-zcode-trellis-smoke-test/report.md`），未改动 `docs/`、`trellis-library/`、`.zcode/`、`.agents/` 等源资产，未运行任何 git 命令；`.trellis/.runtime/` 下的运行时状态变化均由钩子与 task.py 自身产生。
