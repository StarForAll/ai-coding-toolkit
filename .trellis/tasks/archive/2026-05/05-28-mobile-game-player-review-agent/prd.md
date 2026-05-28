# 大众玩家手机游戏分析 Agent

## Goal

基于 `tmp/大众玩家游戏评论Agent-SystemPrompt.md` 的已有内容，在 `agents/`
源资产层新增一个可复用的大众玩家手机游戏分析 agent。它用于从普通手游玩家视角
分析一款手机游戏 APP 的优劣、流失风险与改进优先级，并提供跨 Claude Code、
OpenCode、Codex 的部署适配说明。

## What I Already Know

- 用户希望判断原有系统提示词是否适合做 agent，以及是否需要优化。
- 原提示词已经具备大众玩家口吻、移动端专项维度、付费公平性、痛点 TOP 5、
  优化建议和示例输出。
- 当前仓库的 `agents/` 是 source asset 层，不是三方 CLI 的直接运行目录。
- 现有 agent 源资产通常包含 `README.md`、`SYSTEM.md`、`TOOLS.md`、
  `DEPLOYMENT.md` 和 `EXAMPLES/`。
- `.trellis/spec/agents/index.md` 要求 `SYSTEM.md` 保持工具无关，不嵌入
  frontmatter、TOML 或平台专用字段。
- 跨 CLI wrapper 细节应归入 `DEPLOYMENT.md`，并保留平台文档刷新策略。

## Requirements

- 新增真实 agent 源资产目录，目录名使用 kebab-case。
- 新 agent 必须面向“手机游戏 APP 优劣分析与改进建议”，不是泛用游戏闲聊助手。
- `SYSTEM.md` 需要保留原提示词的玩家语气和核心维度，但优化为可复用、证据边界明确、
  可降级输出的跨平台系统提示词。
- Agent 输出必须服务于游戏改进，包含亮点、痛点、流失风险、优化建议、优先级和证据缺口。
- 必须区分已实际游玩体验、用户提供信息、公开资料、竞品参考和推测。
- 信息不足时不能假装玩过，必须输出初步印象或 `[Evidence Gap]`。
- 必须保留手机端专项：耗电发热、弱网/离线、推送骚扰、单手操作、横竖屏适配。
- 必须保留付费公平性专项：Pay-to-Win、Pay-to-Progress、Cosmetic-only、抽卡/开箱风险。
- `README.md` 说明用途、触发场景、输入、输出、文件边界和部署指针。
- `TOOLS.md` 说明抽象工具/权限需求和禁用操作。
- `DEPLOYMENT.md` 说明 Claude Code、OpenCode、Codex wrapper 模板与验证策略。
- `EXAMPLES/` 至少提供一个输入和一个期望输出格式示例。

## Acceptance Criteria

- [x] `agents/<agent-id>/README.md` 存在，且清楚说明 source/deploy 边界。
- [x] `agents/<agent-id>/SYSTEM.md` 存在，且不包含平台专用 frontmatter/TOML。
- [x] `agents/<agent-id>/TOOLS.md` 存在，且权限边界最小化、无危险默认。
- [x] `agents/<agent-id>/DEPLOYMENT.md` 存在，且覆盖 Claude Code、OpenCode、Codex。
- [x] `agents/<agent-id>/EXAMPLES/input-1.md` 和 `output-1.md` 存在。
- [x] 示例输出明确标注为期望输出格式示例，不伪造成真实运行结果。
- [x] 文档说明原提示词“适合但需要优化”的判断与优化方向。
- [x] 运行相关校验命令，至少覆盖技能结构校验；如不适用，说明边界。

## Definition Of Done

- 新 agent 源资产已创建并符合当前 `agents/` 结构。
- 已根据官方平台文档和本仓库 spec 更新跨 CLI 部署说明。
- 已运行必要校验并报告真实结果。
- 没有修改 `.claude/agents/`、`.opencode/agents/` 或 `.codex/agents/` 运行副本，
  除非后续明确要求部署。

## Technical Approach

采用 source-only agent 资产方式：

- `agents/mobile-game-player-reviewer/` 作为源资产目录。
- `SYSTEM.md` 基于原始中文提示词重写为更稳定的 agent 系统提示词，重点补强：
  证据状态、信息不足降级、竞品引用核验、改进优先级、敏感风险处理和输出结构。
- `DEPLOYMENT.md` 只放 wrapper 模板和平台字段，不污染 `SYSTEM.md`。
- 暂不生成平台运行副本，避免当前仓库 source/deploy 同步边界混淆。

## Decision (ADR-lite)

**Context**: 用户要求 agent 存放在 `agents/`，并适应多种 CLI。当前仓库规范规定
`agents/` 是源资产层，平台运行副本仍是独立部署层。

**Decision**: 本任务只新增 `agents/mobile-game-player-reviewer/` 源资产，并在
`DEPLOYMENT.md` 提供 Claude Code、OpenCode、Codex wrapper 模板。

**Consequences**: 这个 agent 可被后续目标项目按需部署到不同 CLI；当前仓库不会因为
新增一个 source agent 而产生未同步的 live agent 副本。

## Out Of Scope

- 不把该 agent 安装到当前项目的 `.claude/agents/`、`.opencode/agents/`、
  `.codex/agents/`。
- 不新增自动同步脚本。
- 不真实评测某一款手机游戏。
- 不做 App Store / Google Play 评论抓取器或数据分析脚本。

## Research References

- [`research/platform-agent-docs.md`](research/platform-agent-docs.md) — 跨 CLI
  wrapper 字段官方文档轻量核对。
- [`research/verification-results.md`](research/verification-results.md) — 校验命令、
  JSONL 上下文边界和剩余验证边界记录。

## Technical Notes

- 源提示词：`tmp/大众玩家游戏评论Agent-SystemPrompt.md`
- 源资产模板：`agents/_template/`
- 相关规范：`.trellis/spec/agents/index.md`
- 官方平台核对日期：2026-05-28
