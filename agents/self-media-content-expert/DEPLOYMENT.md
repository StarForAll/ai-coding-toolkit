# Deployment Guide

这份文档说明如何把 `agents/self-media-content-expert/` 里的源资产，适配到目标项目中的 Claude Code、OpenCode、Codex。

## Scope

适用场景：

- 你已经决定在目标项目里启用这个 agent
- 你希望保留当前源资产层设计，不在本仓库内直接安装
- 你需要明确不同平台的最小字段、推荐字段、权限映射和验证步骤

不适用场景：

- 只想阅读 agent 的角色定义
- 只需要 `SYSTEM.md` 里的提示词主体

## Source Files

适配时以这些文件为源：

- `README.md`：用途、边界、平台说明
- `SYSTEM.md`：跨平台共享的核心行为定义
- `TOOLS.md`：抽象权限需求
- `EXAMPLES/`：辅助理解输出风格

## Platform Targets

### Claude Code

- 目标路径：目标项目的 `.claude/agents/self-media-content-expert.md`
- 文件格式：Markdown + YAML frontmatter

最小模板：

```markdown
---
name: self-media-content-expert
description: |
  Modern self-media content strategist and implementation specialist. Use for
  topic discovery, audience-fit content design, multi-platform adaptation, and
  evidence-backed real-time content work.
---
<SYSTEM.md content>
```

推荐字段：

- `tools`
- `model`
- `color`
- `permissionMode`：仅在目标项目明确接受更自动化权限时再加

更多可选字段存在于 Claude Code 官方 agent/frontmatter 能力中，例如：

- `disallowedTools`
- `maxTurns`
- `mcpServers`
- `hooks`
- `skills`
- `memory`
- `effort`
- `background`
- `isolation`

这里不全部展开，只保留与当前 agent 最常相关的一组推荐字段。

推荐 `tools` 基线：

```yaml
tools: Read, Write, Edit, Glob, Grep, WebFetch, WebSearch
```

注意：

- 如果目标环境没有 `WebFetch` / `WebSearch`，不要机械复制。
- 如果任务会创建文件，必须保留 `Write`。
- `permissionMode` 不建议在通用模板里默认设成过宽权限；应由目标项目按风险偏好决定。

### OpenCode

- 目标路径：目标项目的 `.opencode/agents/self-media-content-expert.md`
- 文件格式：Markdown + YAML frontmatter
- agent 名默认来自文件名

最小模板：

```markdown
---
description: |
  Modern self-media content strategist and implementation specialist. Use for
  topic discovery, audience-fit content design, multi-platform adaptation, and
  evidence-backed real-time content work.
mode: subagent
permission:
  read: allow
  edit: allow
  glob: allow
  grep: allow
  webfetch: allow
  websearch: allow
---
<SYSTEM.md content>
```

推荐补充：

- `model`
- `temperature`
- `steps`
- `color`

OpenCode 还支持更多可选字段，例如：

- `disable`
- `prompt`
- `hidden`
- `top_p`
- `task`

本节保留的是当前最常用于这个 agent 的推荐补充，而不是完整字段清单。

注意：

- 当前官方更推荐 `permission`，不要为新配置回退到旧 `tools`。
- 文件写入/修改由 `permission.edit` 覆盖，不需要单独 `write` 键。
- 如果目标环境依赖 MCP 搜索工具，可在目标项目中追加对应 permission。

### Codex

- 目标路径：目标项目的 `.codex/agents/self-media-content-expert.toml`
- 文件格式：TOML

最小模板：

```toml
name = "self-media-content-expert"
description = "Modern self-media content strategist and implementation specialist for evidence-backed multi-platform content work."

developer_instructions = """
<SYSTEM.md content>
"""
```

推荐补充：

- `sandbox_mode = "workspace-write"`
- `model`
- `model_reasoning_effort`

注意：

- 如果任务只允许只读分析，可把 `sandbox_mode` 调成 `read-only`，但这会削弱“落文件交付”能力。
- 当前官方 custom-agent 页面没有单独确认 `web_search = "live"` 这类
  agent 级字段；如果需要联网检索，优先依赖当前会话的 web/tool 能力，或通过
  当前官方支持的 `mcp_servers` / `skills.config` 等方式补充能力。

## Permission Mapping

将 `TOOLS.md` 中的抽象权限映射到平台时，优先保持“够用即可”。

| Abstract Need | Claude Code | OpenCode | Codex |
| --- | --- | --- | --- |
| `read` | `Read` | `permission.read` | default + sandbox |
| `write` | `Write` | `permission.edit` | `workspace-write` |
| `edit` | `Edit` | `permission.edit` | `workspace-write` |
| `glob` | `Glob` | `permission.glob` | default tool availability |
| `grep` | `Grep` | `permission.grep` | default tool availability |
| `websearch` | `WebSearch` | `permission.websearch` | 依赖当前 Codex web/tool 能力 |
| `webfetch` | `WebFetch` | `permission.webfetch` | 依赖当前 Codex web tool 能力 |

## Search Tool Availability

这个 agent 同样依赖实时资料核验，部署时要单独检查搜索通道是否真的可用。

建议至少确认：

1. 本地项目内容可被读取与搜索
2. 平台规则、产品能力、新闻事件等外部资料可被 live search / fetch
3. 如果目标项目依赖 MCP 搜索栈，Claude Code / Codex wrapper 是否已通过
   `mcpServers` 或目标项目统一配置接入，OpenCode 是否已通过项目侧能力提供

如果目标项目沿用本仓库的搜索路由习惯，可参考：

- 项目内部搜索：`ace.search_context` 一类语义搜索
- 文档与库行为：官方文档链路或 `Context7` 一类 docs MCP
- 最新外部事实：`grok-search`、`exa` 或等价 live web 能力

缺少这些通道时，应预期该 agent 会更多返回 `[Evidence Gap]`。

## Real-Time Evidence Contract

这个 agent 只有在目标平台具备“可用的实时检索能力”时，才能完整发挥设计目标。

部署前要确认：

1. 平台是否真的能访问 web search / web fetch。
2. 目标项目是否允许该 agent 使用这些能力。
3. 若不允许联网，调用方是否接受 `[Evidence Gap]` 输出路径。

## Verification Checklist

在目标项目部署后，至少做以下验证：

1. agent 文件能被平台识别。
2. agent 能读取本地项目文件。
3. agent 在需要时能创建或修改交付文件。
4. agent 在涉及“最新”信息时会先检索，而不是直接回答。
5. agent 在无法检索时会明确标记 `[Evidence Gap]`。

## Change Management

如果后续修改了：

- `SYSTEM.md`
- `TOOLS.md`
- `README.md` 中的平台字段建议

则应重新检查目标项目中的 wrapper 是否需要同步。
