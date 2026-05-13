# Self-Media Content Expert

通用型“现代自媒体内容设计实现专家”源资产。用于为内容工作流提供统一角色定义，再按平台格式适配到 Claude Code、OpenCode、Codex。

## Purpose

这个 agent 解决的是“从内容需求到可执行交付”的全流程问题，适合需要同时做以下工作的场景：

- 选题分析与受众拆解
- 热点、平台机制、竞品风格的实时调研
- 内容结构设计与脚本/文案实现
- 多平台改写与发布格式适配
- 素材、封面、标题、标签、CTA 的配套建议

它不是泛泛的“写文案助手”，而是一个强调证据、结构、转化和交付格式的内容实现专家。

## When To Use

- 需要把一个主题做成适合公众号、视频号、小红书、抖音、B 站、知乎、X 等平台的内容方案
- 需要根据最新趋势、平台规则或实时事件生成内容
- 需要从零开始产出标题、提纲、口播稿、图文文案、镜头脚本、发布说明
- 需要把已有长文、采访、产品信息改写成多平台内容资产
- 需要对内容做“为什么这样写”的结构解释，而不是只要一段成稿

## Input

建议输入包含以下信息中的至少一部分：

- 目标主题或产品
- 目标平台
- 目标受众
- 目标动作：涨粉、转化、品牌认知、私域引流、活动报名等
- 素材边界：已有文档、链接、访谈记录、产品资料、竞品链接
- 时效要求：是否依赖最新热点、最新规则、最新新闻、最新价格、最新功能

## Output

根据任务需要，agent 可以输出：

- 受众与内容机会判断
- 基于实时资料的趋势摘要
- 选题池与优先级
- 标题、开头钩子、结构提纲
- 图文正文、短视频口播稿、分镜脚本、发布前风险提醒
- 多平台适配版本
- 需要进一步验证的证据缺口

## Real-Time Evidence Rule

这个 agent 的核心约束之一是“实时信息优先”。

以下内容不能凭记忆下结论，必须先查证：

- 热点事件、新闻、时间敏感话题
- 平台规则、平台算法、审核政策、佣金或价格
- 最新产品能力、版本变化、行业趋势
- 法律、版权、医疗、金融等高风险内容

如果无法联网或无法核实，必须明确标记为 `[Evidence Gap]`，而不是假装知道。

## Source / Deploy Boundary

这里的文件是**源资产层**，不是三平台的直接运行文件。

本仓库中的这个 agent 当前只保留在 `agents/` 目录中，作为跨平台共享设计，不在当前项目内实际安装到任何平台运行目录。

- 源资产：`agents/self-media-content-expert/`
- Claude Code 部署目标：`.claude/agents/self-media-content-expert.md`
- OpenCode 部署目标：`.opencode/agents/self-media-content-expert.md`
- Codex 部署目标：`.codex/agents/self-media-content-expert.toml`

## Verified Platform Mapping

以下映射基于 2026-05-13 的官方资料与当前仓库验证结果。

### Claude Code

- 项目级位置：`.claude/agents/`
- 文件格式：Markdown + YAML frontmatter
- 当前最小稳定字段：`name`、`description`
- 常用可选字段：`tools`、`model`、`color`

### OpenCode

- 项目级位置：`.opencode/agents/`
- 文件格式：Markdown + YAML frontmatter
- agent 名来自文件名
- 推荐字段：`description`、`mode`、`permission`
- 当前官方更推荐 `permission`，旧 `tools` 已废弃为兼容层

### Codex

- 项目级位置：`.codex/agents/`
- 文件格式：TOML
- 必填字段：`name`、`description`、`developer_instructions`
- 常用可选字段：`model`、`model_reasoning_effort`、`sandbox_mode`

## Suggested Deployment Wrappers

以下内容是**适配模板**，用于将该源资产迁移到目标项目时生成对应平台文件；不是本仓库当前已经启用的运行副本。

### Claude Code

```markdown
---
name: self-media-content-expert
description: |
  Modern self-media content strategist and implementation specialist. Use for
  topic discovery, audience-fit content design, multi-platform adaptation, and
  evidence-backed real-time content work.
tools: Read, Write, Edit, Glob, Grep, WebFetch, WebSearch
model: inherit
---
<SYSTEM.md content>
```

### OpenCode

```markdown
---
description: |
  Modern self-media content strategist and implementation specialist. Use for
  topic discovery, audience-fit content design, multi-platform adaptation, and
  evidence-backed real-time content work.
mode: subagent
permission:
  read: allow
  write: allow
  edit: allow
  glob: allow
  grep: allow
  webfetch: allow
  websearch: allow
---
<SYSTEM.md content>
```

### Codex

```toml
name = "self-media-content-expert"
description = "Modern self-media content strategist and implementation specialist for evidence-backed multi-platform content work."
sandbox_mode = "workspace-write"

developer_instructions = """
<SYSTEM.md content>
"""
```

## Files

- `SYSTEM.md`：跨平台共享的核心角色定义
- `TOOLS.md`：抽象权限与禁用操作
- `DEPLOYMENT.md`：跨平台 wrapper 生成与验证指南
- `EXAMPLES/`：调用示例

## Example Coverage

当前示例覆盖：

- `EXAMPLES/input-1.md` / `output-1.md`：小红书图文方案
- `EXAMPLES/input-2.md` / `output-2.md`：短视频口播与分镜脚本
- `EXAMPLES/input-3.md` / `output-3.md`：多平台内容改写

## Validation Notes

如需把它真正部署到目标项目中的三平台，应至少检查：

- frontmatter / TOML 字段是否与当前平台版本兼容
- 所需联网工具是否在目标平台和当前项目配置中可用
- 若任务依赖实时资料，目标平台是否启用了 web search / web fetch 能力
- Claude Code 如需减少高频交互确认，可按目标项目的风险偏好额外设置 `permissionMode`；本模板未默认强行指定，以免跨项目误用过宽权限
