# Deployment Guide

这份文档说明如何把
`agents/software-solution-delivery-expert/` 里的源资产，适配到目标项目中的
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

- Claude Code: `https://code.claude.com/docs/en/sub-agents`
- Codex: `https://developers.openai.com/codex/subagents`
- OpenCode: `https://opencode.ai/docs/agents/`
- OpenCode permissions: `https://opencode.ai/docs/permissions`

## Source Files

适配时以这些文件为源：

- `README.md`：用途、边界、平台说明
- `SYSTEM.md`：跨平台共享的核心行为定义
- `TOOLS.md`：抽象权限需求
- `EXAMPLES/`：辅助理解输出风格

## Platform Targets

### Claude Code

- 目标路径：目标项目的
  `.claude/agents/software-solution-delivery-expert.md`
- 文件格式：Markdown + YAML frontmatter

最小模板：

```markdown
---
name: software-solution-delivery-expert
description: |
  Software project intake and delivery specialist for scoping, implementation
  planning, risk control, and evidence-backed execution decisions.
---
<SYSTEM.md content>
```

上面的最小模板只展示最基本可识别字段，故意省略 `tools`、`model`、`color`、
`permissionMode` 等可选增强项。

推荐字段：

- `tools`
- `model`
- `color`
- `permissionMode`：仅在目标项目明确接受更自动化权限时再加

推荐 `tools` 基线：

```yaml
tools: Read, Write, Edit, Glob, Grep, Bash, WebSearch, WebFetch
```

注意：

- Claude Code 当前官方 frontmatter 能力比最小模板更丰富，但这些增强项属于
  wrapper 层，而不是 `SYSTEM.md` 层。
- 如果目标环境没有 `WebSearch` / `WebFetch`，不要机械复制。
- `permissionMode` 不建议在通用模板里默认设成过宽权限，应由目标项目按风险
  偏好决定。

更多可选字段：

- `skills`
- `mcpServers`
- `hooks`

这些字段更适合在目标项目已经有成熟的 docs/browser/search MCP 体系、或已经有
稳定技能装配方案时再补，不建议默认塞进每个最小 wrapper。

### OpenCode

- 目标路径：目标项目的
  `.opencode/agents/software-solution-delivery-expert.md`
- 文件格式：Markdown + frontmatter
- agent 名默认来自文件名

最小模板：

```markdown
---
description: |
  Software project intake and delivery specialist for scoping, implementation
  planning, risk control, and evidence-backed execution decisions.
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
- `color`
- `hidden`：仅当该 agent 只希望被其他 agent 编排调用时使用

注意：

- `description` 是必填字段。
- `mode` 当前可设为 `primary`、`subagent`、`all`；缺省值是 `all`。
- 当前官方更推荐 `permission`，不要为新配置回退到旧 `tools`。
- 文件写入/修改由 `permission.edit` 覆盖，不需要单独 `write` 键。
- OpenCode 允许对 `bash` 等权限做更细粒度规则；如果目标项目风险较高，
  建议把 `bash` 从字符串权限升级为对象规则。
- 如果目标项目高度信任该 agent，且它主要承担 Mode 3 的 build / test /
  delivery 工作，可把 `bash: ask` 调整为 `bash: allow` 以减少确认摩擦。

### Codex

- 目标路径：目标项目的
  `.codex/agents/software-solution-delivery-expert.toml`
- 文件格式：TOML

最小模板：

```toml
name = "software-solution-delivery-expert"
description = "Software project intake and delivery specialist for scoping, implementation planning, risk control, and evidence-backed execution decisions."

developer_instructions = """
<SYSTEM.md content>
"""
```

推荐补充：

- `sandbox_mode = "workspace-write"`：当 agent 需要真正落文件时
- `model_reasoning_effort = "high"`：更适合需求澄清、方案权衡、复杂排查
- `nickname_candidates`：当目标项目会频繁并发运行该 agent 时
- `mcp_servers`：当目标项目有专门文档、浏览器或内部服务 MCP 时
- `skills.config`：当目标项目要为该 agent 预装特定技能时

注意：

- 当前官方 custom-agent 页面明确支持的基础字段是 `name`、
  `description`、`developer_instructions`。
- 可以额外使用当前支持的 `config.toml` 键，例如 `model`、
  `model_reasoning_effort`、`sandbox_mode`、`mcp_servers`、
  `skills.config`。
- 不要给这个 wrapper 添加未在当前官方 custom-agent 页面确认的
  自定义字段。

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
| `websearch` | `WebSearch` | `permission.websearch` | rely on session/tool support |
| `webfetch` | `WebFetch` | `permission.webfetch` | rely on session/tool support |

## Search Tool Availability

这个 agent 的价值高度依赖“能否拿到正确的检索通道”，部署前不要只检查文件格式，
还要检查搜索能力本身。

建议按 3 类证据分别确认：

1. 项目内部证据
   - 至少要有本地文件读取、内容搜索、路径搜索能力
   - 如果目标项目有语义搜索工具，可优先接入
2. 文档/API 证据
   - 至少要能访问官方文档或项目自己的 docs MCP
   - 如果目标项目已有 docs/search skill，优先复用
3. 最新外部事实
   - 至少要有 live web search / fetch 或等价通道
   - 如果目标项目使用 MCP 搜索栈，可在 wrapper 中声明 `mcpServers`
     或通过目标项目统一配置接入

如果目标项目沿用本仓库的搜索路由习惯，可把以下能力当作参考映射：

- 项目内部搜索：`ace.search_context` 一类语义搜索，配合 grep/read 回退
- 文档与库行为：官方文档链路或 `Context7` 一类 docs MCP
- 最新外部事实：`grok-search`、`exa` 或等价 live web 能力

如果这些能力都没有，就要预期该 agent 会频繁输出 `[Evidence Gap]`，此时应降低它
在“最新版本 / 最新价格 / 最新政策 / 最新安全状态”类任务中的使用范围。

## Real-Time Evidence Contract

这个 agent 只有在目标平台具备“可用的实时检索能力”时，才能完整发挥设计目标。

部署前要确认：

1. 平台是否真的能访问 web search / web fetch 或等价实时检索能力。
2. 目标项目是否允许该 agent 使用这些能力。
3. 若不允许联网，调用方是否接受 `[Evidence Gap]` 输出路径。
4. 库/API 查询是否能接到目标项目自己的 docs MCP 或官方文档链路。

## Verification Checklist

在目标项目部署后，至少做以下验证：

1. agent 文件能被平台识别。
2. agent 能读取本地项目文件。
3. agent 在需要时能创建或修改交付文件。
4. agent 在涉及“最新”信息时会先检索，而不是直接回答。
5. agent 在无法检索时会明确标记 `[Evidence Gap]`。
6. agent 不会把未确认的估算、版本或外部能力当成事实承诺。

## Change Management

如果后续修改了：

- `SYSTEM.md`
- `TOOLS.md`
- `README.md` 中的平台字段建议

则应重新检查目标项目中的 wrapper 是否需要同步。
