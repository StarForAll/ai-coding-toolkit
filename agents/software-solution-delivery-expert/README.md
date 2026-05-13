# Software Solution Delivery Expert

通用型“软件项目接单与交付专家”源资产。用于把一个模糊的软件需求、外包单子、
救火请求或内部开发委托，转成可澄清、可评估、可执行、可验收的交付方案，
再按平台格式适配到 Claude Code、OpenCode、Codex。

## Purpose

这个 agent 解决的是“软件项目从接入到交付”的一类稳定问题，适合需要同时处理
以下工作的场景：

- 需求澄清与范围收敛
- 可行性判断与技术路线选择
- 风险、依赖、验收条件和交付边界识别
- 实施计划、里程碑、工时区间与优先级拆分
- 存量项目救火、修复、重构、验收与交接说明

它不是泛泛的“会写代码的助手”，而是一个强调证据、范围控制、交付约束与真实
风险暴露的软件交付型 agent。

## When To Use

- 需要判断一个软件项目值不值得接、怎么接、先做什么
- 需要把模糊需求整理成 MVP、里程碑、验收标准和风险清单
- 需要基于现有代码库快速定位可改范围、实现路径和验证方案
- 需要对 AI/LLM、SaaS、Web、后端、自动化等项目给出可执行交付建议
- 需要在“先调研再承诺”前提下输出方案、任务拆解、修复计划或交付说明
- 需要明确哪些信息必须实时核验，哪些可以基于稳定知识先推进

## Input

建议输入包含以下信息中的至少一部分：

- 项目目标或客户需求原话
- 目标平台或技术栈
- 现有代码、仓库、接口文档、原型、数据库结构或错误现象
- 时间约束：上线时间、演示时间、验收时间
- 资源约束：预算、工时、人数、已有系统、第三方依赖
- 风险边界：合规、安全、权限、数据、性能、稳定性要求
- 是否依赖最新版本、最新价格、最新政策、最新 API 行为

## Output

根据任务需要，agent 可以输出：

- 需求澄清清单
- 可接/暂缓/拒绝建议与理由
- MVP 范围与阶段计划
- 架构选项、依赖清单与实施路线
- 风险登记表与假设清单
- 代码修改计划、修复方案、验证步骤
- 验收标准、交接说明、客户沟通要点
- 需要进一步实时核验的证据缺口

## Real-Time Evidence Rule

这个 agent 的核心约束之一是“最新版和最新外部事实必须先核验，再结论化”。

以下内容默认不能凭记忆下结论：

- 框架、SDK、API、模型、插件、云服务的当前版本行为
- 云服务价格、额度、限流、配额、地区可用性
- 平台政策、合规要求、审核规则、上架要求
- 安全公告、已知漏洞、弃用说明、兼容性变化
- 第三方能力是否“现在还能这样做”

如果无法联网或无法核实，必须明确标记为 `[Evidence Gap]`，而不是假装知道。

## Source / Deploy Boundary

这里的文件是**源资产层**，不是三平台的直接运行文件。

本仓库中的这个 agent 当前只保留在 `agents/` 目录中，作为跨平台共享设计，
不在当前项目内实际安装到任何平台运行目录。

- 源资产：`agents/software-solution-delivery-expert/`
- Claude Code 部署目标：`.claude/agents/software-solution-delivery-expert.md`
- OpenCode 部署目标：`.opencode/agents/software-solution-delivery-expert.md`
- Codex 部署目标：`.codex/agents/software-solution-delivery-expert.toml`

部署细节、平台字段、wrapper 模板与刷新策略见 `DEPLOYMENT.md`。

## Files

- `SYSTEM.md`：跨平台共享的核心角色定义
- `TOOLS.md`：抽象权限与禁用操作
- `DEPLOYMENT.md`：跨平台 wrapper 生成与验证指南
- `EXAMPLES/`：调用示例

## Example Coverage

当前示例覆盖：

- `EXAMPLES/input-1.md` / `output-1.md`：新单 intake、MVP 收敛与风险判断
- `EXAMPLES/input-2.md` / `output-2.md`：存量项目故障救火、修复与验收准备

说明：

- 当前 `EXAMPLES/output-*.md` 是**期望输出格式示例**，用于展示这个 agent 的
  目标报告形态，不代表本仓库内已经真实执行过 live verification。

## Validation Notes

如需把它真正部署到目标项目中的三平台，应至少检查：

- frontmatter / TOML 字段是否与当前平台版本兼容
- 目标平台是否真的具备实时检索能力
- 目标项目是否允许该 agent 使用联网和 bash 能力
- 如果无法联网，调用方是否接受 `[Evidence Gap]` 输出路径
- Codex wrapper 是否只使用当前官方支持的自定义 agent 字段
