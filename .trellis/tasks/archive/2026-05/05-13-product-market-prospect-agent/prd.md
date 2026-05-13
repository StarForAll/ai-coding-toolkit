# 设计个人产品市场前景调研通用agent

## Goal

在 `agents/` 源资产层新增一个可复用于 Claude Code、OpenCode、Codex 的通用
agent，用于判断一个个人产品 / 独立产品 / 小团队产品在**当前时间**是否具备市场前景。
该 agent 必须默认要求使用最新实时有效信息做分析，不能靠静态常识直接下结论。

## What I already know

- 用户要的是一个 **通用性 agent 设计**，不是本仓库内立即启用的运行副本。
- 目标存放位置是当前仓库 `agents/` 目录。
- 该 agent 需要可适配 Claude Code、OpenCode、Codex。
- 用户明确要求：分析必须基于**最新实时有效信息**。
- 当前仓库 `agents/` 已采用 source asset 结构：
  - `README.md`
  - `SYSTEM.md`
  - `TOOLS.md`
  - `DEPLOYMENT.md`
  - `EXAMPLES/`
- 当前仓库已有同类源资产示例：
  - `agents/self-media-content-expert/`
  - `agents/software-solution-delivery-expert/`
  - `agents/software-pricing-estimation-expert/`
- 已核验 2026-05-13 的三平台官方 agent 文档：
  - Claude Code sub-agents
  - Codex subagents / custom agents
  - OpenCode agents / permissions

## Assumptions (temporary)

- 该 agent 的稳定角色应是“产品市场可行性 / 市场前景判断”，而不是一次性提示词。
- 命名应偏稳定角色，不应绑定某个具体产品名或单一平台。
- 本次任务只交付 source asset，不同步生成 `.claude/agents/`、
  `.opencode/agents/`、`.codex/agents/` 运行副本。
- 示例可以展示“已实时核验”与“证据缺口”两类输出路径，但真实部署时必须优先走
  live evidence 路径。

## Open Questions

- 无阻塞问题。当前需求已足够进入实现。

## Requirements (evolving)

- 在 `agents/` 下新增一个新 agent 目录，名称稳定、可复用、kebab-case。
- `README.md` 必须说明用途、适用场景、输入、输出、source/deploy 边界。
- `SYSTEM.md` 必须 tool-agnostic，且明确：
  - 角色定义
  - 核心职责
  - 严格边界
  - 实时信息强制核验规则
  - 工作模式
  - 工作流
  - 输出格式
- `TOOLS.md` 必须表达：
  - 需要 websearch / webfetch
  - 禁止伪造“最新”结论
  - 权限与平台映射提示
- `DEPLOYMENT.md` 必须记录 2026-05-13 核验过的三平台适配基线。
- 至少提供示例输入/输出，覆盖“市场前景分析”的典型调用。
- 更新 `agents/README.md` 中的当前已落地源资产示例列表。

## Acceptance Criteria (evolving)

- [x] 新 agent 目录位于 `agents/<agent-id>/`
- [x] 包含 `README.md`、`SYSTEM.md`、`TOOLS.md`、`DEPLOYMENT.md`
- [x] `SYSTEM.md` 明确规定：若任务依赖当前市场事实，必须先做 live verification
- [x] `DEPLOYMENT.md` 明确 Claude Code / OpenCode / Codex 的最小 wrapper 形态
- [x] `agents/README.md` 已纳入该 agent
- [x] 已记录研究材料到 `research/`
- [x] 已运行至少一轮相关验证命令，并如实记录结果

## Verification Record

- 2026-05-13:
  - 已运行 `/ops/softwares/python/bin/python3 trellis-library/cli.py validate --strict-warnings`
  - 结果：pass with informational notes only
  - 信息项：`stale-related-asset` x5
  - 当前未运行三平台安装级验证，因为本任务明确只交付 source asset，不在本仓库内实际安装

## Definition of Done (team quality bar)

- Source asset 结构完整
- 角色边界单一且稳定
- README / SYSTEM / TOOLS / DEPLOYMENT 之间不冲突
- 验证结果真实记录为 pass / fail / not run

## Out of Scope (explicit)

- 不在本仓库直接安装或启用该 agent
- 不同步生成三平台运行副本
- 不对某个具体用户产品做一次性的市场分析交付

## Technical Notes

- 相关规范：
  - `.trellis/spec/agents/index.md`
  - `agents/NAMING-AND-VERSIONING.md`
- 参考源资产：
  - `agents/software-pricing-estimation-expert/`
  - `agents/self-media-content-expert/`
- 研究文件：
  - `research/platform-wrapper-baseline.md`
  - `research/market-signal-framework.md`
