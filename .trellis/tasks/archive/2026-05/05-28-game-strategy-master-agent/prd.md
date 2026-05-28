# 新增游戏策略大师 Agent

## Goal

基于 `tmp/游戏策略大师Agent-System-Prompt.md` 的内容，在 `agents/` 源资产层新增
一个可长期复用的“游戏策略大师” agent，用于分析手机游戏 APP，并给出专业、可落地、
有证据边界的新游戏策略和版本行动方案。

## Requirements

- 新增 `agents/game-strategy-master/` 源资产目录。
- 提供 `README.md`，说明用途、适用场景、输入、输出、原提示词适用性评估、优化点、
  source/deploy 边界、文件说明和验证注意事项。
- 提供 `SYSTEM.md`，作为跨平台共享系统提示词，不包含 Claude/OpenCode/Codex 专属
  frontmatter、TOML 或工具字段。
- 提供 `TOOLS.md`，定义抽象权限、推荐权限姿态、禁止操作和证据缺口规则。
- 提供 `DEPLOYMENT.md`，说明如何适配 Claude Code、OpenCode、Codex，并记录平台
  字段刷新策略。
- 增加至少一个 `EXAMPLES/` 示例，展示输入与期望输出格式。
- 优化原提示词：保留品类权重、评分锚点、交叉影响矩阵、杠杆点、冲突检测和版本路线图，
  但补充证据分层、实时核验、信息不足降级、推荐格式和边界约束。
- 当前任务只新增 source agent，不在本仓库同步创建 `.claude/agents/`、
  `.opencode/agents/`、`.codex/agents/` 的运行副本。

## Acceptance Criteria

- [x] `agents/game-strategy-master/README.md` 存在，并清楚回答原提示词是否合适、
  为什么需要优化。
- [x] `agents/game-strategy-master/SYSTEM.md` 存在，内容是完整、可直接作为共享角色
  prompt 使用的系统提示词。
- [x] `agents/game-strategy-master/TOOLS.md` 存在，包含 read/write/edit/search/web
  等抽象权限建议与禁止操作。
- [x] `agents/game-strategy-master/DEPLOYMENT.md` 存在，包含 Claude Code、OpenCode、
  Codex 的最小 wrapper 模板和验证清单。
- [x] 示例文件存在，并标注是期望输出格式示例而非真实 live verification 结果。
- [x] Markdown 文件路径、命名、source/deploy 边界与 `.trellis/spec/agents/index.md`
  及 `agents/README.md` 保持一致。
- [x] 相关验证命令已运行并记录结果。

## Definition of Done

- 新 agent 文件已创建并通过仓库相关校验。
- 原提示词的适用性与优化理由已写入 README。
- 跨 CLI 适配只放在部署说明中，未污染共享 SYSTEM prompt。
- 没有无证据的“已验证 live 分析”或“已真实部署”表述。

## Technical Approach

采用现有 `agents/mobile-game-player-reviewer/` 的 source-agent 结构作为主要参考：

- `README.md` 用中文说明源资产用途和边界。
- `SYSTEM.md` 使用英文主体，保持跨 CLI、工具无关和系统提示词风格一致。
- `TOOLS.md` 描述抽象能力，不绑定具体 CLI 字段。
- `DEPLOYMENT.md` 负责平台 wrapper 模板和字段刷新策略。
- `EXAMPLES/` 提供最小输入/输出样例。

## Decision (ADR-lite)

**Context**: 用户要求 agent 存放在当前项目的 `agents/` 目录，并适应多种 CLI。仓库规范显示
`agents/` 是源资产层，平台运行副本属于 `.claude/agents/`、`.opencode/agents/`、
`.codex/agents/` 等部署层。

**Decision**: 本任务只新增 `agents/game-strategy-master/` source agent，并在
`DEPLOYMENT.md` 给出 Claude Code、OpenCode、Codex wrapper 生成建议，不直接写入运行副本。

**Consequences**: 该 agent 可作为多 CLI 共同源提示词使用；真正部署到目标项目时仍需按目标
CLI 当前文档核验 wrapper 字段。

## Out of Scope

- 不实际分析某一款具体手游。
- 不生成或提交 `.claude/agents/`、`.opencode/agents/`、`.codex/agents/` 运行副本。
- 不修改 `tmp/` 下原始提示词文件。
- 不提供法律、合规、版号、投资或确定性营收预测。

## Research References

- `research/platform-agent-compatibility.md` — 官方平台文档核验、source/deploy 边界、
  原提示词适用性与优化点。

## Technical Notes

- 实际输入文件为 `tmp/游戏策略大师Agent-System-Prompt.md`，用户给出的
  `tmp/游戏策略大师Agent提示词-SystemPrompt.md` 在当前工作区不存在。
- `tmp/游戏策略大师Agent提示词.md` 是元提示词，不是最终可部署的 system prompt。
- 相关规范：`.trellis/spec/agents/index.md`、`.trellis/spec/docs/index.md`、
  `.trellis/spec/guides/cross-layer-thinking-guide.md`、
  `.trellis/spec/guides/code-reuse-thinking-guide.md`、`agents/NAMING-AND-VERSIONING.md`。
