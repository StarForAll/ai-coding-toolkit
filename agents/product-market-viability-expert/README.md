# Product Market Viability Expert

通用型“产品市场前景判断专家”源资产。用于把一个个人产品、独立产品、微型 SaaS、
AI 工具、小团队新产品或新功能方向，转成基于**当前时间**的市场前景分析、竞争态势
判断、需求信号汇总、变现与分发风险说明，再按平台格式适配到 Claude Code、
OpenCode、Codex。

## Purpose

这个 agent 解决的是“一个产品在**现在**到底有没有市场前景”的稳定问题，特别适合：

- 个人产品 / 独立开发产品立项前判断
- 已有想法但不确定现在还值不值得做
- 想判断某个赛道是否过热、过冷、还是存在切入口
- 想把模糊的“感觉有需求”拆成有证据边界的市场判断
- 想快速得到 go / no-go / narrow-scope / reposition 这类决策支持

它不是泛泛的“商业顾问”或“创业鸡汤助手”，而是一个强调**实时证据、当前时间窗、
需求 / 竞争 / 变现 / 分发 / 时间窗口与约束五类核心信号**的市场前景分析型 agent。

## When To Use

- 你准备做一个个人产品，想判断当前市场是否还有空间
- 你已经做了 MVP，但不确定是继续加码、缩范围、换定位还是停止
- 你想分析某个垂直赛道是否仍有切入机会
- 你想基于最新竞品、搜索趋势、用户讨论、定价和渠道态势做判断
- 你需要输出一份可读的市场前景结论，而不是散乱的搜索结果

## Input

建议输入包含以下信息中的至少一部分：

- 产品一句话描述
- 目标用户是谁
- 解决什么问题
- 当前产品阶段：想法 / MVP / 已上线 / 要转型
- 目标地区或语言市场
- 你担心的问题：
  - 是否还有需求
  - 是否竞品过多
  - 是否难以获客
  - 是否难以收费
- 是否明确要求基于“当前时间”的最新市场事实

## Output

根据任务需要，agent 可以输出：

- 当前市场前景结论
- `promising now` / `conditional` / `weak now` / `[Evidence Gap]` 市场判断
- 需求信号摘要
- 竞争与定位压力摘要
- 变现与定价可行性判断
- 分发与获客难度判断
- 当前时间窗口与外部约束判断
- 需要进一步核验的证据缺口
- 下一步验证动作清单

## Real-Time Evidence Rule

这个 agent 的核心约束之一是：

> 只要用户要判断“当前市场有没有前景”，就默认必须依赖 live evidence。

以下内容默认不能凭记忆直接下结论：

- “最近这个方向很火 / 没人做 / 已经过气”
- 搜索热度变化
- 当前竞品数量与活跃度
- 最新定价、套餐、免费策略
- 最新平台政策、分发环境、生态变化
- 当前用户社区中对该问题的讨论强度
- 当前 AI / API / SaaS 基础设施成本变化

如果无法联网或无法核实，必须明确标记为 `[Evidence Gap]`，而不是假装知道。

## Source / Deploy Boundary

这里的文件是**源资产层**，不是三平台的直接运行文件。

本仓库中的这个 agent 当前只保留在 `agents/` 目录中，作为跨平台共享设计，
不在当前项目内实际安装到任何平台运行目录。

- 源资产：`agents/product-market-viability-expert/`
- Claude Code 部署目标：`.claude/agents/product-market-viability-expert.md`
- OpenCode 部署目标：`.opencode/agents/product-market-viability-expert.md`
- Codex 部署目标：`.codex/agents/product-market-viability-expert.toml`

部署细节、平台字段、wrapper 模板与刷新策略见 `DEPLOYMENT.md`。

## Files

- `SYSTEM.md`：跨平台共享的核心角色定义
- `TOOLS.md`：抽象权限与禁用操作
- `DEPLOYMENT.md`：跨平台 wrapper 生成与验证指南
- `EXAMPLES/`：调用示例

## Example Coverage

当前示例覆盖：

- `EXAMPLES/input-1.md` / `output-1.md`：个人 AI SaaS 的当前市场前景判断
- `EXAMPLES/input-2.md` / `output-2.md`：无法实时联网时的 `[Evidence Gap]` 输出路径
- `EXAMPLES/input-3.md` / `output-3.md`：拥挤市场中的定位与差异化判断
- `EXAMPLES/input-4.md` / `output-4.md`：已上线产品的 go / pause / pivot 决策
- `EXAMPLES/input-5.md` / `output-5.md`：`promising now` 的当前市场验证输出形态

说明：

- 当前 `EXAMPLES/output-*.md` 是**期望输出格式示例**，用于展示这个 agent 的
  目标报告形态，不代表本仓库内已经真实执行过 live search。
- 只要示例中出现 `Verified live`，都应理解为“如果该 agent 在具备实时检索能力的
  目标环境中运行，预期应输出的格式”，不是当前仓库内一次真实运行的证据记录。

## Validation Notes

如需把它真正部署到目标项目中的三平台，应至少检查：

- frontmatter / TOML 字段是否与当前平台版本兼容
- 目标平台是否真的具备实时检索能力
- 目标项目是否允许该 agent 使用联网和 bash 能力
- 如果无法联网，调用方是否接受 `[Evidence Gap]` 输出路径
- live source 的优先级是否以第一方、当前、可归因为主
