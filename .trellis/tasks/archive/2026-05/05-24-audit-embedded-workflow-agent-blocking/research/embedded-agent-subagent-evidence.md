# 嵌入后 agent/subagent 证据摘录

## 1. 目标项目版本与安装状态

- `docs/workflows/新项目开发工作流/commands/workflow_assets.py`
  - `COMPATIBLE_TRELLIS_VERSION = "0.5.17"`
- `trellis -v`
  - `0.5.17`
- `/tmp/trellis-0.5.17-2/.trellis/workflow-installed.json`
  - `cli_types = ["claude", "opencode", "codex"]`
  - `critical_runtime_patches` 含 `inject-workflow-state`、`session-start-strong-gate`、`opencode-inject-subagent-context`

## 2. Claude Code：活跃 carrier 仍默认 dispatch 子代理

- `/tmp/trellis-0.5.17-2/.claude/settings.json:5-70`
  - `SessionStart -> python3 .claude/hooks/session-start.py`
  - `PreToolUse(Task|Agent) -> python3 .claude/hooks/inject-subagent-context.py`
  - `UserPromptSubmit -> python3 .claude/hooks/inject-workflow-state.py`
- `/tmp/trellis-0.5.17-2/.claude/hooks/session-start.py:726-737`
  - 明确写着 agent-capable platforms 默认应 dispatch `trellis-implement` / `trellis-check`
- `/tmp/trellis-0.5.17-2/.claude/hooks/inject-subagent-context.py:677-718`
  - 对 `implement/check/research` 直接构造上下文，不存在 workflow 级统一阻断

## 3. OpenCode：startup 指引默认 dispatch，subagent patch 只做条件放行

- `/tmp/trellis-0.5.17-2/.opencode/lib/session-utils.js:260-265`
  - 明确要求主会话不要直接编辑，而是 dispatch `trellis-implement` / `trellis-check`
- `/tmp/trellis-0.5.17-2/.opencode/plugins/inject-subagent-context.js`
  - `shouldAllowTaskInjection()` 允许部分阶段放行 `implement/check/research`
  - route 不允许时才回退主会话，并非 workflow 级禁用

## 4. Codex：默认 inline，但仍缺少显式阻断

- `/tmp/trellis-0.5.17-2/.codex/hooks.json:2-14`
  - 活跃 hook 是 `UserPromptSubmit -> .codex/hooks/inject-workflow-state.py`
- `/tmp/trellis-0.5.17-2/.codex/hooks/inject-workflow-state.py:355-381`
  - 仍支持 `codex.dispatch_mode` 在 `inline` 和 `sub-agent` 间切换
- `/tmp/trellis-0.5.17-2/.trellis/config.yaml:82-90`
  - 注释文本保留 `sub-agent` opt-in 路径
- `/tmp/trellis-0.5.17-2/AGENTS.md:30-35,58`
  - 路由表只说“不建议把 agent/subagent 当默认主路径”
  - 对 Codex 的“调研”仍允许显式触发 `trellis-research` skill / agent（若项目允许）

## 5. 源码侧直接导致上述行为的位置

- `commands/install-workflow.py:296-345`
  - 生成 `AGENTS.md` 的 NL 路由表
- `commands/check.md:42-44`
  - 仍把 implementation 内部 Trellis agent 链写成默认存在
- `多CLI通用新项目完整流程演练.md:620`
  - 明确写 `continue` 默认先执行 Trellis agent 链
- `commands/shell/patch-opencode-inject-subagent-context.py:35-57`
  - 按阶段放行 OpenCode subagent
- `commands/codex/README.md:268-343`
  - 保留 `subagents` 兼容承载与内部角色链口径

## 结论

问题不是“平台不支持”，而是“当前 workflow 产品层没有把这些平台能力收口为 main-session-only”，并且多处 source docs / installer template / runtime patch 互相强化了 agent/subagent 路径。
