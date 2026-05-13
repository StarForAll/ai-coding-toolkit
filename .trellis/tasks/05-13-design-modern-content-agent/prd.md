# 设计现代自媒体内容实现专家 agent

## Goal

在当前仓库的 `agents/` 源资产层中新增一个通用 agent，定位为“现代自媒体内容设计实现专家”。该 agent 需要能作为跨平台共享源提示词使用，并明确映射到 Claude Code、OpenCode、Codex 三个平台的当前 agent 机制。

## What I already know

- 用户要求：放在当前项目的 `agents/` 目录中，可用于 `Claude Code / Codex / OpenCode`。
- 用户额外要求：必须根据最新实时有效的信息进行分析、总结、处理。
- 当前仓库把 `agents/` 定义为未来的 source-of-truth 资产层；当前运行中的 agent 仍主要存在于 `.claude/agents/`、`.opencode/agents/`、`.codex/agents/`。
- 当前仓库的 Codex 工作模式默认为 inline，不应在主会话中为了实现此任务临时派生 Codex sub-agent。

## Assumptions (temporary)

- 本次先实现 `agents/<agent-id>/` 源资产与部署说明，不强制同步生成三个平台的实际部署副本，除非检查到仓库规范要求本任务必须同步。
- 该 agent 以“内容策划 + 素材分析 + 结构设计 + 多平台改写 + 交付规范”为核心，不包含平台账号登录、真实发稿、图片生成或外部系统自动发布。
- “最新实时有效信息”在 agent 行为上表现为：遇到平台规则、趋势、算法变化、热点、价格、法务/版权规则时，必须先检索实时资料再作结论。

## Open Questions

- 当前无需向用户追加阻塞问题。需求足以先实现通用版本。

## Requirements

- 在 `agents/` 下新增一个语义清晰、可复用的 agent 目录。
- 目录内必须包含 `README.md`、`SYSTEM.md`、`TOOLS.md`。
- `SYSTEM.md` 必须 tool-agnostic，不写特定平台 frontmatter 或调用语法。
- 内容必须体现“实时信息优先、证据优先、内容设计与实现并重”的工作方式。
- `README.md` 必须说明用途、适用场景、输入输出、三平台部署映射。
- 文档必须标注当前三平台最新已验证的 agent 文件形态与放置路径。
- 至少提供一组示例输入输出，帮助后续生成平台落地文件。
- 更新 `agents/README.md`，使目录层说明包含新 agent 与 source/deploy 边界。

## Acceptance Criteria

- [x] `agents/self-media-content-expert/README.md` 存在且说明清楚用途、输入输出、兼容平台。
- [x] `agents/self-media-content-expert/SYSTEM.md` 存在且包含职责、边界、流程、输出模板。
- [x] `agents/self-media-content-expert/TOOLS.md` 存在且定义抽象权限需求与禁用操作。
- [x] 至少有一组 `EXAMPLES/` 示例文件。
- [x] `agents/README.md` 已更新并保持与仓库 source-asset 语义一致。
- [x] 任务目录内有实时研究记录文件，明确三平台 agent 机制的外部证据来源与日期。

## Definition of Done

- 相关文件已创建或更新。
- 变更符合 `.trellis/spec/agents/index.md` 与文档规范。
- 已运行相关验证命令并据实报告结果。

## Out of Scope

- 同步生成 `.claude/agents/`、`.opencode/agents/`、`.codex/agents/` 的最终部署副本。
- 为其他平台（Kiro、Qoder 等）补充部署文件。
- 实现自动同步脚本或 manifest 注册流程。
- 真实抓取社媒平台私有后台数据或执行发布。

## Technical Notes

- 相关仓库规范：
  - `.trellis/spec/agents/index.md`
  - `.trellis/spec/docs/index.md`
  - `.trellis/spec/platforms/index.md`
  - `.trellis/spec/platforms/codex-workflow-behavior.md`
- 实时外部资料将写入 `research/platform-agent-compatibility.md`。
