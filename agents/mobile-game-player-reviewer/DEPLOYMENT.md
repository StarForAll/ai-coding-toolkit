# Deployment Guide

这份文档说明如何把 `agents/mobile-game-player-reviewer/` 里的源资产，适配到目标
项目中的 Claude Code、OpenCode、Codex。

## Scope

适用场景：

- 你已经决定在目标项目里启用这个 agent
- 你希望保留当前源资产层设计，不在本仓库内直接安装
- 你需要明确不同平台的最小字段、推荐字段、权限映射和验证步骤

不适用场景：

- 只想阅读 agent 的角色定义
- 只需要 `SYSTEM.md` 里的提示词主体

## Verification Baseline

以下平台信息基于 2026-05-28 官方文档轻量核验：

- Claude Code: `https://code.claude.com/docs/en/sub-agents.md`
- OpenCode agents: `https://dev.opencode.ai/docs/agents/`
- OpenCode permissions: `https://dev.opencode.ai/docs/permissions/`
- Codex: `https://developers.openai.com/codex/multi-agent/`

## Refresh Policy

以下任一情况出现时，应重新核验本文件中的平台字段面与 wrapper 建议：

1. 距离上次核验超过 90 天
2. 目标平台发布 agents / subagents / permissions / custom agents 相关文档更新
3. 部署时发现字段解析失败、权限字段失效、或推荐模板与 UI/CLI 行为不一致
4. 目标项目准备启用新的增强字段，例如 `mcpServers`、`memory`、
   `background`、`isolation`、`skills.config`

最低重核验范围：

- Claude Code sub-agents 页面中的 frontmatter 字段
- OpenCode agents 与 permissions 页面中的当前 agent / permission 语法
- Codex custom agents / subagents 页面中的必填与可选字段

## Source Files

适配时以这些文件为源：

- `README.md`：用途、边界、平台说明
- `SYSTEM.md`：跨平台共享的核心行为定义
- `TOOLS.md`：抽象权限需求
- `EXAMPLES/`：辅助理解输出风格

## Platform Targets

### Claude Code

- 目标路径：目标项目的 `.claude/agents/mobile-game-player-reviewer.md`
- 文件格式：Markdown + YAML frontmatter

最小模板：

```markdown
---
name: mobile-game-player-reviewer
description: |
  Mass-market mobile game player reviewer for analyzing mobile game strengths,
  pain points, churn risks, monetization fairness, mobile experience, and
  concrete improvement priorities.
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
- `initialPrompt`

推荐 `tools` 基线：

```yaml
tools: Read, Glob, Grep, WebFetch, WebSearch
```

如果目标项目希望 agent 写入报告文件，可加入：

```yaml
tools: Read, Write, Edit, Glob, Grep, WebFetch, WebSearch
```

注意：

- 如果目标环境没有 `WebFetch` / `WebSearch`，不要机械复制。
- 如果只做用户提供材料分析，缺失 live web 能力是可接受的，但输出必须标记外部事实
  的 `[Evidence Gap]`。
- `permissionMode` 不建议在通用模板里默认设成过宽权限；应由目标项目按风险偏好决定。

### OpenCode

- 目标路径：目标项目的 `.opencode/agents/mobile-game-player-reviewer.md`
- 文件格式：Markdown + YAML frontmatter
- agent 名默认来自文件名

最小模板：

```markdown
---
description: |
  Mass-market mobile game player reviewer for analyzing mobile game strengths,
  pain points, churn risks, monetization fairness, mobile experience, and
  concrete improvement priorities.
mode: subagent
permission:
  read: allow
  glob: allow
  grep: allow
  webfetch: allow
  websearch: allow
  edit: deny
  bash: ask
---
<SYSTEM.md content>
```

如果目标项目希望 agent 写入报告文件：

```yaml
permission:
  read: allow
  edit: allow
  glob: allow
  grep: allow
  webfetch: allow
  websearch: allow
  bash: ask
```

推荐补充：

- `model`
- `temperature`
- `steps`
- `color`

注意：

- 当前官方更推荐 `permission`，不要为新配置回退到旧 `tools`。
- 文件写入/修改由 `permission.edit` 覆盖，不需要单独 `write` 键。
- `bash` 建议默认 `ask`，除非目标项目只开放明确安全的命令模式。

### Codex

- 目标路径：目标项目的 `.codex/agents/mobile-game-player-reviewer.toml`
- 文件格式：TOML

最小模板：

```toml
name = "mobile-game-player-reviewer"
description = "Mass-market mobile game player reviewer for mobile game strengths, pain points, churn risks, monetization fairness, mobile experience, and improvement priorities."

developer_instructions = """
<SYSTEM.md content>
"""
```

推荐补充：

```toml
sandbox_mode = "read-only"
model_reasoning_effort = "high"
```

如果目标项目希望 agent 写入报告文件：

```toml
sandbox_mode = "workspace-write"
```

可选字段按目标项目需要再加：

- `nickname_candidates`
- `model`
- `model_reasoning_effort`
- `sandbox_mode`
- `mcp_servers`
- `skills.config`

注意：

- 当前官方 custom-agent 页面明确要求 `name`、`description`、
  `developer_instructions`。
- 可以额外使用当前支持的通用配置字段，例如 `model`、
  `model_reasoning_effort`、`sandbox_mode`、`mcp_servers`。
- 不要给 wrapper 发明未被当前官方确认的字段，例如独立的
  `web_search = "live"`。

## Permission Mapping

将 `TOOLS.md` 中的抽象权限映射到平台时，优先保持“够用即可”。

| Abstract Need | Claude Code | OpenCode | Codex |
| --- | --- | --- | --- |
| `read` | `Read` | `permission.read` | default + sandbox |
| `write` | `Write` | `permission.edit` | `workspace-write` |
| `edit` | `Edit` | `permission.edit` | `workspace-write` |
| `glob` | `Glob` | `permission.glob` | default tool availability |
| `grep` | `Grep` | `permission.grep` | default tool availability |
| `bash` | `Bash` | `permission.bash` | default tool availability |
| `websearch` | `WebSearch` | `permission.websearch` | 依赖目标 Codex 会话的 Web/MCP 能力 |
| `webfetch` | `WebFetch` | `permission.webfetch` | 依赖目标 Codex 会话的 Web/MCP 能力 |

## Evidence Capability Contract

这个 agent 可以离线分析用户提供的试玩信息，但以下任务高度依赖 live evidence：

- 当前商店评分、评论趋势、最近差评主题
- 竞品当前机制、活动、付费策略或概率披露
- 游戏最新版本、公告、概率公示、隐私政策
- 当前平台政策或外部争议

部署前至少确认：

1. 是否能读取项目内反馈材料
2. 是否能检索公开网页
3. 是否能打开关键来源页面
4. 无法核验时是否允许输出 `[Evidence Gap]`

## Verification Checklist

- agent 文件能被目标平台发现
- frontmatter / TOML 字段通过目标平台当前版本解析
- 只读场景下不会尝试写文件
- 写报告场景下具备明确 workspace 写入权限
- live evidence 缺失时会输出 `[Evidence Gap]`
- 不会把用户提供的体验描述误报为“公开事实”
- 竞品引用包含做法、差异、适配性和证据状态

## Change Management

如果后续修改了：

- `SYSTEM.md`
- `TOOLS.md`
- `README.md` 中的能力边界
- 本文件中的平台字段建议

则应重新检查目标项目中的 wrapper 是否需要同步，并确认是否要补一次平台文档重核验。

## Platform Coverage Boundary

本源资产的当前适配文档只覆盖 Claude Code、OpenCode、Codex 这 3 个目标平台，
因为它们是本次 source-agent 设计的主目标。

本仓库里虽然也存在其他 live deployment surface，但它们目前不在这个 source
agent 的 wrapper 说明范围内。
