# Agent Naming And Versioning

这份文档定义 `agents/` 源资产层的通用命名、范围切分和版本演进建议。

## Naming Rules

### 1. Directory Name

真实 agent 目录使用 `kebab-case`：

- `self-media-content-expert`
- `api-reviewer`
- `frontend-bug-fixer`

避免：

- 空泛名称：`assistant`、`helper`
- 平台绑定名称：`codex-writer`
- 任务过窄但无法复用的名称：`write-may-campaign-post`

### 2. Name Should Describe Role, Not One Prompt

优先按“稳定角色”命名，而不是按一次性需求命名。

好例子：

- `self-media-content-expert`
- `security-auditor`
- `migration-planner`

差例子：

- `xiaohongshu-post-writer`
- `feature-123-helper`
- `one-off-campaign-agent`

### 3. Keep Scope Single-Purpose

一个 agent 只解决一类稳定问题。

如果一个设计开始同时承担：

- research
- implementation
- review
- orchestration

就应该考虑拆分。

## Scope Design

在创建新 agent 前，先判断它属于哪一类：

### Role Agent

面向长期稳定角色，例如：

- 内容设计
- 代码审查
- 文档研究
- 安全审计

这是优先推荐的类型。

### Workflow Agent

面向重复流程，例如：

- 发布前检查
- 依赖升级评估
- 多平台 wrapper 生成

只有当流程本身足够稳定时才适合独立成 agent。

### Non-Agent Template

如果内容只是作者辅助材料，不应假装成真实 agent。

例如：

- `_template/`
- 独立的命名规范
- wrapper 说明

这类内容应放在文档或保留目录中，并明确写出“不是实际 agent”。

## Versioning Strategy

当前 `agents/` 源资产层默认不要求每个 agent 单独维护语义化版本号。

原因：

- 这些资产目前还不是独立发布包
- 当前更重要的是 source/deploy 一致性，而不是单独版本标签
- 过早加版本字段，通常只会增加维护噪音

### When To Add Version Metadata

只有在以下情况同时出现时，再考虑给 agent 引入显式版本：

1. 该 agent 被多个目标项目复用
2. 不同项目之间需要比较新旧版本
3. 变更需要明确升级说明

在那之前，优先通过 git 历史和 `README.md` 变更记录追踪演进。

## Change Types

### Minor Content Tuning

例如：

- 改 wording
- 补示例
- 增加说明

这类改动通常不需要显式版本记录。

### Behavioral Change

例如：

- 核心职责变化
- 权限需求变化
- 输出格式变化
- 从“稳定知识优先”变成“实时检索优先”

这类改动至少要在 `README.md` 或任务研究记录中注明。

### Compatibility Change

例如：

- Claude Code frontmatter 建议变化
- OpenCode `permission` 映射变化
- Codex custom agent schema 变化

这类改动应优先更新：

- agent 自身 `README.md`
- `DEPLOYMENT.md`
- 如有必要，`.trellis/spec/agents/index.md`

## Recommended Evolution Path

一个新 agent 的推荐演进顺序：

1. 建立 source asset：
   - `README.md`
   - `SYSTEM.md`
   - `TOOLS.md`
2. 增加最小示例
3. 增加跨平台部署说明
4. 再补多场景示例
5. 最后才考虑抽象公共模板或拆分子 agent

## Review Checklist

新增或修改 agent 时，至少检查：

- 名称是否稳定、清晰、可复用
- 角色边界是否单一
- 是否把模板类内容误放成真实 agent
- 是否需要同步更新部署说明
- 是否引入了与目标平台不兼容的建议字段
