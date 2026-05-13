# Research: platform-agent-compatibility

- **Query**: Claude Code、OpenCode、Codex 当前项目级 agent / subagent 的定义格式、目录位置、关键字段，以及哪些结论来自官方最新文档
- **Scope**: external + internal
- **Date**: 2026-05-13

## Findings

### Internal Repository Facts

| File Path | Description |
| --- | --- |
| `.trellis/spec/agents/index.md` | 仓库把 `agents/<agent-id>/` 定义为 source-of-truth 资产层，当前三平台部署仍未与其同步。 |
| `.trellis/spec/platforms/codex-workflow-behavior.md` | 当前仓库 Codex 默认 `inline`，主会话不得为了方便而临时派生 sub-agent。 |
| `.claude/agents/trellis-research.md` | Claude 侧现有 agent 用 Markdown + YAML frontmatter。 |
| `.opencode/agents/trellis-research.md` | OpenCode 侧现有 agent 用 Markdown + YAML frontmatter，权限用 `permission`。 |
| `.codex/agents/trellis-research.toml` | Codex 侧现有 agent 用 TOML，核心字段是 `name`、`description`、`developer_instructions`。 |

### External References

- [Claude Code Docs: Create custom subagents](https://docs.anthropic.com/en/docs/claude-code/sub-agents)
  - 2026-05-13 检索到的官方页面明确：项目级 subagent 放在 `.claude/agents/`。
  - 文件为 Markdown + YAML frontmatter。
  - 必填字段是 `name` 与 `description`；`tools`、`model`、`color`、`permissionMode`、`mcpServers` 等可选。
  - body 作为 subagent 的 system prompt。
- [OpenCode Docs: Agents](https://opencode.ai/docs/agents/)
  - 2026-05-13 检索到的官方页面明确：项目级 agent 放在 `.opencode/agents/`，也支持全局 `~/.config/opencode/agents/`。
  - Markdown agent 文件名就是 agent 名。
  - frontmatter 使用 `description`、`mode`、`model`、`temperature`、`permission` 等字段。
  - 官方说明 `mode` 可设为 `primary` / `subagent` / `all`，Markdown agent 默认仍建议明确写出。
- [OpenCode Docs: Permissions](https://dev.opencode.ai/docs/permissions)
  - 2026-05-13 检索到的官方页面明确：自 `v1.1.1` 起，旧 `tools` 布尔配置已废弃，建议使用 `permission`。
  - Agent 级权限可覆盖全局权限，并支持细粒度 pattern 匹配。
- [OpenAI Developers: Codex Subagents](https://developers.openai.com/codex/multi-agent/)
  - 2026-05-13 检索到的官方页面明确：项目级 custom agent 放在 `.codex/agents/`，个人级放在 `~/.codex/agents/`。
  - 每个 TOML 文件定义一个 agent。
  - 必填字段：`name`、`description`、`developer_instructions`。
  - 可选字段：`nickname_candidates`、`model`、`model_reasoning_effort`、`sandbox_mode`、`mcp_servers`、`skills.config`。
- [OpenAI Developers: Codex Config Reference](https://developers.openai.com/codex/config-reference/)
  - 2026-05-13 检索到的官方配置参考仍把 `AGENTS.md` 作为项目指令入口之一，并记录 `web_search = "live|cached|disabled"`、`sandbox_mode` 等 agent 可能继承的配置层。

## Synthesis

### Stable Cross-Platform Core

三平台都支持“项目级自定义 agent”。

- Claude Code: `.claude/agents/<name>.md`
- OpenCode: `.opencode/agents/<name>.md`
- Codex: `.codex/agents/<name>.toml`

三者都允许：

- 用简短描述声明“何时使用该 agent”
- 为 agent 提供独立的行为指令体
- 在项目级范围内随仓库分发

### Important Differences

1. Claude Code
   - `name` 是 frontmatter 内字段，文件名不一定是唯一来源。
   - 工具限制更偏向 `tools` allowlist / `disallowedTools`。

2. OpenCode
   - Markdown 文件名直接成为 agent 名。
   - 当前官方更推荐 `permission` 而非旧 `tools`。
   - `mode: subagent` 是最稳妥的跨会话写法。

3. Codex
   - 使用 TOML，不是 Markdown frontmatter。
   - `developer_instructions` 是核心 body。
   - custom agent 继承父会话的很多配置，除非 agent 文件显式覆盖。

### Design Implication for This Task

最适合当前仓库的实现方式是：

- 在 `agents/self-media-content-expert/` 中维护 tool-agnostic 源资产；
- 在 `README.md` 中给出三平台的部署映射和字段差异；
- 在 `SYSTEM.md` 中明确“凡涉及趋势、平台规则、热点、算法、价格、法律、版权、受众变化时，必须先做实时检索，再输出结论”，以满足用户的“最新实时有效信息”要求。

## Caveats / Not Found

- 本次未发现一个三平台共享的官方统一 schema，因此“单一源资产 + 各平台 wrapper”仍然是最稳妥方案。
- Claude Code 文档中支持字段较多，仓库现有 `agents` 规范里的字段映射表相对保守；这不是冲突，更像是 source-layer 设计尚未完全追平官方能力。
