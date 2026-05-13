# Deployment Guide

这份文档说明如何把
`agents/product-market-viability-expert/` 里的源资产，适配到目标项目中的
Claude Code、OpenCode、Codex。

## Scope

适用场景：

- 你已经决定在目标项目里启用这个 agent
- 你希望保留当前源资产层设计，不在本仓库内直接安装
- 你需要明确不同平台的最小字段、推荐字段、权限映射和验证步骤

不适用场景：

- 只想阅读 agent 的角色定义
- 只需要 `SYSTEM.md` 里的提示词主体

## Verification Baseline

以下平台信息基于 2026-05-13 官方文档核验：

- Claude Code: `https://code.claude.com/docs/en/sub-agents.md`
- Codex: `https://developers.openai.com/codex/multi-agent/`
- OpenCode agents: `https://dev.opencode.ai/docs/agents/`
- OpenCode permissions: `https://dev.opencode.ai/docs/permissions`

## Refresh Policy

以下任一情况出现时，应重新核验本文件中的平台字段面与 wrapper 建议：

1. 距离上次核验超过 90 天
2. 目标平台发布了 agents / subagents / permissions / custom agents 相关文档更新
3. 部署时发现字段解析失败、权限字段失效、或推荐模板与 UI/CLI 行为不一致
4. 目标项目准备启用新的增强字段，例如 `mcpServers`、`memory`、
   `background`、`isolation`、`nickname_candidates`

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

- 目标路径：目标项目的
  `.claude/agents/product-market-viability-expert.md`
- 文件格式：Markdown + YAML frontmatter

最小模板：

```markdown
---
name: product-market-viability-expert
description: |
  Product market viability specialist for evidence-backed current market
  prospect analysis, demand validation, competition assessment, and go/no-go
  judgment.
---
<SYSTEM.md content>
```

推荐字段：

- `tools`
- `model`
- `color`
- `permissionMode`

当前官方还支持更多可选字段，例如：

- `disallowedTools`
- `maxTurns`
- `skills`
- `mcpServers`
- `hooks`
- `memory`
- `effort`
- `background`
- `isolation`
- `initialPrompt`

推荐 `tools` 基线：

```yaml
tools: Read, Write, Edit, Glob, Grep, Bash, WebSearch, WebFetch
```

注意：

- 这些增强项属于 wrapper 层，不应写回 `SYSTEM.md`
- 如果目标环境没有 `WebSearch` / `WebFetch`，不要机械复制
- 如果这个 agent 在目标项目只需要只读研究，可删除 `Write` / `Edit`

### OpenCode

- 目标路径：目标项目的
  `.opencode/agents/product-market-viability-expert.md`
- 文件格式：Markdown + frontmatter
- agent 名默认来自文件名

最小模板：

```markdown
---
description: |
  Product market viability specialist for evidence-backed current market
  prospect analysis, demand validation, competition assessment, and go/no-go
  judgment.
mode: subagent
permission:
  read: allow
  edit: allow
  glob: allow
  grep: allow
  bash: ask
  websearch: allow
  webfetch: allow
---
<SYSTEM.md content>
```

推荐补充：

- `model`
- `temperature`
- `steps`
- `hidden`
- `bash` 的对象语法规则：当目标项目需要更安全的命令边界时，优先把
  `bash: ask` 升级为对象语法，而不是直接放宽成全量 `allow`

注意：

- 新配置默认优先 `permission`，不要回退到旧 `tools`
- `permission.edit` 统一覆盖文件修改能力，不需要额外声明 `write`
- `bash` 建议默认 `ask`
- 更细粒度的更安全写法例如：

```yaml
permission:
  bash:
    "*": ask
    "git diff*": allow
    "git log*": allow
    "rg *": allow
```

- 如果目标项目对 live research 非常信任，可把 `bash` 提升为 `allow`

### Codex

- 目标路径：目标项目的
  `.codex/agents/product-market-viability-expert.toml`
- 文件格式：TOML

最小模板：

```toml
name = "product-market-viability-expert"
description = "Product market viability specialist for evidence-backed current market prospect analysis, demand validation, competition assessment, and go/no-go judgment."

developer_instructions = """
<SYSTEM.md content>
"""
```

推荐补充：

- `sandbox_mode = "workspace-write"`：当 agent 需要实际写研究文件时
- `model_reasoning_effort = "high"`：更适合权衡市场信号与证据冲突
- `nickname_candidates`
- `mcp_servers`
- `skills.config`

注意：

- 当前官方 custom-agent 页面明确支持的基础字段是 `name`、
  `description`、`developer_instructions`
- 可以额外使用当前支持的通用配置字段，例如 `model`、
  `model_reasoning_effort`、`sandbox_mode`、`mcp_servers`
- 不要给 wrapper 发明未被当前官方确认的字段

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
| `websearch` | `WebSearch` | `permission.websearch` | 依赖目标项目在当前 Codex 会话中启用的 Web/MCP 检索能力 |
| `webfetch` | `WebFetch` | `permission.webfetch` | 依赖目标项目在当前 Codex 会话中启用的 Web/MCP 页面读取能力 |

## Real-Time Evidence Contract

这个 agent 的价值高度依赖“能否核实当前市场事实”，部署前不要只检查文件格式，
还要检查 live evidence 能力是否真的存在。

建议至少确认 3 类能力：

1. 项目内部证据
   - 本地文件读取、内容搜索、路径搜索
2. 官方文档 / 第一方页面
   - 竞品官网、定价页、更新日志、政策页、帮助页
3. 最新外部事实
   - web search / web fetch 或等价 MCP

如果目标项目沿用本仓库的搜索路由习惯，可把以下能力当作参考：

- 项目内部搜索：`ace.search_context` 一类语义搜索，配合 grep/read 回退
- 文档与库行为：官方文档链路或 docs MCP
- 最新外部事实：live web search + page fetch

如果目标环境具备更强的 MCP / web 工具链，建议在 wrapper 增强层补充以下路由提示：

1. 项目内部证据优先走语义搜索，再回退到 grep/read
2. 第三方库/API/SDK 证据优先走官方文档或 docs MCP
3. 最新市场事实优先走 live search，再对关键来源做 page fetch
4. 无法验证时必须显式输出 `[Evidence Gap]`

如果这些能力都没有，就要预期该 agent 会频繁输出 `[Evidence Gap]`，此时应降低它在
“当前市场是否有前景”类任务中的使用范围。

## Signal Coverage Checklist

部署后至少要确认该 agent 能覆盖以下实时信号：

- 需求信号：搜索趋势、相关搜索、用户问题讨论
- 竞争信号：竞品官网、定价页、更新日志、发布动态
- 变现信号：付费方案、免费策略、评价中的付费反馈
- 分发信号：渠道拥挤度、社区活跃度、平台依赖度
- 时间窗口信号：政策、生态、成本或平台变化

## Verification Checklist

- agent 文件能被目标平台发现
- frontmatter / TOML 字段通过目标平台当前版本解析
- agent 实际具备 web search / web fetch 或等价能力
- agent 在无 live evidence 时会输出 `[Evidence Gap]`
- agent 不会把旧资料误报为“当前市场事实”

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
