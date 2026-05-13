# Platform Wrapper Baseline

日期：2026-05-13

## Refresh Trigger

以下任一情况出现时，应重新核验本研究：

1. 距离本次核验超过 90 天
2. Claude Code / OpenCode / Codex 发布了 agents / subagents / permissions /
   custom agents 相关文档更新
3. 实际部署时发现字段解析失败、权限语法失效、或推荐 wrapper 与当前平台行为不一致
4. 计划把本研究中的建议字段直接用于新的 source agent 或目标项目 wrapper

## Purpose

记录本次 source agent 设计所依赖的三平台官方 agent / subagent 字段面基线，
避免 `DEPLOYMENT.md` 写成过期约定。

## Sources

- Claude Code: `https://code.claude.com/docs/en/sub-agents.md`
- Codex: `https://developers.openai.com/codex/multi-agent/`
- OpenCode agents: `https://dev.opencode.ai/docs/agents/`
- OpenCode permissions: `https://dev.opencode.ai/docs/permissions`

## Claude Code

结论：

- 项目级自定义 subagent 仍使用 `.claude/agents/*.md`
- 文件格式为 Markdown + YAML frontmatter
- 必填最小字段仍是：
  - `name`
  - `description`
- body 即系统提示词主体

当前官方额外支持的常见 frontmatter 字段包括：

- `tools`
- `disallowedTools`
- `model`
- `permissionMode`
- `mcpServers`
- `hooks`
- `maxTurns`
- `skills`
- `memory`
- `effort`
- `background`
- `isolation`
- `initialPrompt`
- `color`

设计含义：

- source asset 的 `SYSTEM.md` 应保持 tool-agnostic
- 上述字段属于 wrapper 层增强项，不应写进 `SYSTEM.md`

## Codex

结论：

- 自定义 agent 存放在 `.codex/agents/*.toml`
- 必填字段仍是：
  - `name`
  - `description`
  - `developer_instructions`
- 可额外复用普通 `config.toml` 支持的字段，例如：
  - `nickname_candidates`
  - `model`
  - `model_reasoning_effort`
  - `sandbox_mode`
  - `mcp_servers`
  - `skills.config`

设计含义：

- source asset 层只需要定义共享角色主体
- Codex wrapper 可按目标项目风险偏好补 `sandbox_mode`
- 不应发明官方未确认的自定义字段

## OpenCode

结论：

- 可使用 `.opencode/agents/*.md` 作为 Markdown agent 形态
- `description` 为关键字段
- `mode` 可用 `primary` / `subagent` / `all`，默认 `all`
- 当前新配置应优先使用 `permission`，而不是旧 `tools`
- `permission.edit` 统一覆盖文件修改能力（`edit` / `write` / `patch`）

权限位点官方当前明确包含：

- `read`
- `edit`
- `glob`
- `grep`
- `bash`
- `task`
- `skill`
- `lsp`
- `question`
- `webfetch`
- `websearch`
- `external_directory`
- `doom_loop`

设计含义：

- source asset 的 `TOOLS.md` 里若写 `write` / `edit` 抽象需求，映射到 OpenCode
  时应合并到 `permission.edit`
- 对高风险 agent，`bash` 最好默认 `ask`

## Cross-Platform Notes

- 三平台都能承载“共享正文 + 平台 wrapper”的 source/deploy 分层设计
- “必须依赖最新实时信息”的能力在 source 层只能写成行为约束，不能假装每个平台
  天然自带 live web
- 部署说明里必须单独检查：
  - 目标项目是否真的有 web search / web fetch 或等价 MCP
  - 目标项目是否允许 agent 使用这些能力
  - 若没有 live search，调用方是否接受 `[Evidence Gap]`
