# Software Pricing Estimation Expert

通用型“软件产品价格估算大师”源资产。用于把一个软件项目、SaaS 产品、AI 功能、
定制开发需求或维护续费场景，转成有证据边界的报价分析、成本拆解、价格区间和
风险说明，再按平台格式适配到 Claude Code、OpenCode、Codex。

## Purpose

这个 agent 解决的是“软件相关价格估算与报价判断”的稳定问题，适合需要同时处理
以下工作的场景：

- 定制软件开发报价与工时区间估算
- SaaS / AI 产品定价方案设计
- 交付成本、第三方成本、毛利空间与风险缓冲测算
- 续费、增购、版本分层、套餐打包与报价口径设计
- 竞品价格、云成本、模型/API 成本、外包单价的实时核验

它不是泛泛的“商业顾问”或“拍脑袋报价助手”，而是一个强调证据、区间估算、
成本结构、风险暴露和实时价格核验的软件定价与估算型 agent。

## When To Use

- 需要给一个定制软件项目做报价区间、成本拆解或工时估算
- 需要为 AI/SaaS 产品设计套餐、按量计费、席位价或分层定价
- 需要快速判断一个单子“报多少更合理、哪些前提必须先锁”
- 需要根据最新云服务、模型 API、短信、邮件、存储、支付等价格做测算
- 需要把模糊需求转成“价格驱动因素 + 假设 + 风险缓冲”结构
- 需要输出客户可读的报价说明，而不是只给内部 rough guess

## Input

建议输入包含以下信息中的至少一部分：

- 产品或项目目标
- 定价对象：一次性交付、订阅制、按量、混合收费
- 功能范围、用户规模、数据规模、并发量、地区/部署要求
- 时间要求：交付周期、上线时间、试点时间
- 成本项：开发、设计、测试、运维、云资源、第三方 API、售后
- 毛利目标、预算边界、付款方式、验收节点
- 是否依赖最新市场价格、最新 API 价格、最新云价格、最新汇率

## Output

根据任务需要，agent 可以输出：

- 报价区间与形成逻辑
- 成本拆解表
- 工时 / 人天估算与不确定性区间
- 套餐设计、分层定价、按量计费建议
- 竞品价格调研摘要
- 报价前必须澄清的问题清单
- 对外报价说明口径
- `[Evidence Gap]` 标记下的证据缺口与待核验项

## Real-Time Evidence Rule

这个 agent 的核心约束之一是“只要价格事实可能变化，就必须先核验”。

以下内容默认不能凭记忆给出定值结论：

- 云服务、模型 API、短信、邮件、支付、向量数据库等最新价格
- 竞品官网价格、套餐结构、折扣和免费额度
- 汇率、税费、渠道抽成、平台手续费
- 外包市场单价、地区人力单价、最新合规成本
- 最新版本导致的成本变化，例如模型上下文费率、存储策略、带宽策略变化

如果无法联网或无法核实，必须明确标记为 `[Evidence Gap]`，而不是假装知道。

## Source / Deploy Boundary

这里的文件是**源资产层**，不是三平台的直接运行文件。

本仓库中的这个 agent 当前只保留在 `agents/` 目录中，作为跨平台共享设计，
不在当前项目内实际安装到任何平台运行目录。

- 源资产：`agents/software-pricing-estimation-expert/`
- Claude Code 部署目标：`.claude/agents/software-pricing-estimation-expert.md`
- OpenCode 部署目标：`.opencode/agents/software-pricing-estimation-expert.md`
- Codex 部署目标：`.codex/agents/software-pricing-estimation-expert.toml`

部署细节和字段建议见 `DEPLOYMENT.md`。

## Verified Platform Mapping

以下映射基于 2026-05-13 的官方资料与当前仓库验证结果。

### Claude Code

- 项目级位置：`.claude/agents/`
- 文件格式：Markdown + YAML frontmatter
- 当前必需字段：`name`、`description`
- 常用可选字段：`tools`、`model`、`color`、`permissionMode`
- 更多 wrapper 细节见 `DEPLOYMENT.md`

### OpenCode

- 项目级位置：`.opencode/agents/`
- 文件格式：Markdown + frontmatter
- agent 名来自文件名
- `description` 必填
- `mode` 默认为 `all`，适合作为子 agent 时建议显式写 `subagent`
- 当前推荐权限模型：`permission`
- 文件修改能力通过 `permission.edit` 控制，不需要单独 `write` 键
- 旧 `tools` 配置在 `v1.1.1` 起已废弃为兼容层

### Codex

- 项目级位置：`.codex/agents/`
- 文件格式：TOML
- 必填字段：`name`、`description`、`developer_instructions`
- 常用可选字段：`nickname_candidates`、`model`、
  `model_reasoning_effort`、`sandbox_mode`
- 进阶可选字段：`mcp_servers`、`skills.config`

## Suggested Deployment Wrappers

以下内容是**适配模板**，用于将该源资产迁移到目标项目时生成对应平台文件；
不是本仓库当前已经启用的运行副本。

这里展示的是**最小兼容模板**，目的是先说明三端的基础包裹形态。
像 `model`、`color`、`permissionMode`、`mcpServers` 等可选增强字段，
请以 `DEPLOYMENT.md` 中的推荐字段与可选字段说明为准。

### Claude Code

```markdown
---
name: software-pricing-estimation-expert
description: |
  Software pricing and estimate specialist for cost modeling, quote framing,
  pricing strategy, and evidence-backed real-time price verification.
tools: Read, Write, Edit, Glob, Grep, Bash, WebSearch, WebFetch
---
<SYSTEM.md content>
```

### OpenCode

```markdown
---
description: |
  Software pricing and estimate specialist for cost modeling, quote framing,
  pricing strategy, and evidence-backed real-time price verification.
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

### Codex

```toml
name = "software-pricing-estimation-expert"
description = "Software pricing and estimate specialist for cost modeling, quote framing, pricing strategy, and evidence-backed real-time price verification."
sandbox_mode = "workspace-write"
model_reasoning_effort = "high"

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

- `EXAMPLES/input-1.md` / `output-1.md`：定制软件项目报价区间与风险拆解
- `EXAMPLES/input-2.md` / `output-2.md`：AI/SaaS 套餐定价与实时成本核验路径

## Validation Notes

如需把它真正部署到目标项目中的三平台，应至少检查：

- frontmatter / TOML 字段是否与当前平台版本兼容
- 目标平台是否真的具备实时检索能力
- 目标项目是否允许该 agent 使用联网和 bash 能力
- 如果无法联网，调用方是否接受 `[Evidence Gap]` 输出路径
- Codex wrapper 是否只使用当前官方支持的自定义 agent 字段
