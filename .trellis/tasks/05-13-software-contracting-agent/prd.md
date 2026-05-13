# 设计通用软件接单能手 agent 源资产

## Goal

在 `agents/` 源资产层新增一个可复用的“软件程序相关接单能手”agent，
用于在 Claude Code、Codex、OpenCode 中以同一份核心角色定义适配使用。
该 agent 不在本仓库内实际安装到三端运行目录，只提供跨平台共享的
`README.md`、`SYSTEM.md`、`TOOLS.md`、`DEPLOYMENT.md` 和示例资产。

## What I already know

- 用户要求该 agent 具备通用性，面向软件程序相关接单场景。
- 用户明确要求资产放在当前项目的 `agents/` 目录中。
- 用户明确要求不要在当前项目里实际安装到 `.claude/agents/`、
  `.opencode/agents/`、`.codex/agents/`。
- 本仓库 `agents/` 目录已经是 source asset 层，现有真实样例为
  `agents/self-media-content-expert/`。
- 当前仓库规范要求 `SYSTEM.md` 保持 tool-agnostic，平台差异写入
  `README.md` / `DEPLOYMENT.md`。
- 2026-05-13 已核验三端官方资料，确认：
  - Claude Code 项目级 subagents 位于 `.claude/agents/`，使用 Markdown
    + YAML frontmatter，`name` 与 `description` 必填。
  - Codex 项目级 custom agents 位于 `.codex/agents/`，使用 TOML，`name`、
    `description`、`developer_instructions` 必填，`model`、
    `model_reasoning_effort`、`sandbox_mode`、`mcp_servers`、
    `skills.config` 等为可选。
  - OpenCode 项目级 agents 位于 `.opencode/agents/`，使用 Markdown +
    frontmatter，`description` 必填；`mode` 可设为 `subagent`，Markdown
    文件名就是 agent 名；`permission` 是当前推荐权限模型，旧 `tools`
    已在 `v1.1.1` 起废弃为兼容层。

## Assumptions (temporary)

- 该 agent 默认定位为“软件项目接单与交付专家”，覆盖需求澄清、可行性分析、
  技术方案、风险识别、实现推进、验收交付，不负责法律合同审阅或纯销售话术。
- 该 agent 面向外包、自由职业、顾问式开发、内部需求接入等共通软件交付场景，
  而不是仅绑定某个行业或某个技术栈。
- 当任务涉及最新框架版本、API 行为、云服务价格、政策、合规或安全漏洞时，
  必须先做实时核验，不能凭记忆作答。

## Resolved Decisions

- 报价/工时估算不作为“固定承诺报价”输出；允许输出带假设前提的区间估算，
  并优先给出风险分级、里程碑拆分和影响因素。
- agent 保持一般软件项目优先，同时兼容 AI/LLM、SaaS、Web、后端、自动化等
  常见软件交付场景，不额外偏向单一技术域。

## Requirements (evolving)

- 新增一个稳定、可复用、kebab-case 命名的真实 agent 目录。
- 目录至少包含：
  - `README.md`
  - `SYSTEM.md`
  - `TOOLS.md`
  - `DEPLOYMENT.md`
- 至少提供 1 组可读示例；优先提供 2 组覆盖不同接单场景的示例。
- `SYSTEM.md` 必须保持跨平台共享，不嵌入 Claude Code / Codex / OpenCode
  的专有 frontmatter/TOML 语法。
- `README.md` 和 `DEPLOYMENT.md` 必须反映 2026-05-13 核验过的三端官方格式。
- 输出角色必须强调：
  - 先澄清需求再承诺
  - 先验证实时事实再下结论
  - 交付结果要结构化、可执行、可验收
  - 不虚构工时、成本、依赖、第三方能力或最新版本结论
- 明确边界：
  - 不替代法律/财务/税务建议
  - 不把未核验的最新信息当作事实
  - 不为拿单而隐瞒风险
  - 不在缺少关键约束时做不可逆实现承诺

## Acceptance Criteria (evolving)

- [x] `agents/<agent-id>/` 已创建且结构完整
- [x] `README.md` 明确用途、触发场景、输入输出、source/deploy 边界
- [x] `SYSTEM.md` 明确职责、工作流、实时核验规则、输出格式、禁止事项
- [x] `DEPLOYMENT.md` 提供三端适配说明，但不要求在本仓库实际安装
- [x] 至少 1 组示例可展示该 agent 如何处理软件接单场景
- [x] `agents/README.md` 已更新，能发现这个新 agent
- [x] 至少运行相关验证命令并据实记录结果

## Definition of Done (team quality bar)

- 相关文档与示例已补齐
- 结构与命名符合 `agents/` 目录规范
- 验证命令已执行并记录 pass/fail/not run

## Out of Scope (explicit)

- 在 `.claude/agents/`、`.opencode/agents/`、`.codex/agents/` 中创建真实运行副本
- 实现自动同步脚本
- 处理法律合同文本审核本身
- 处理非软件类接单场景（设计、营销、短视频等）

## Technical Notes

- 相关本地规范：
  - `agents/README.md`
  - `agents/NAMING-AND-VERSIONING.md`
  - `.trellis/spec/agents/index.md`
- 现有参考样例：
  - `agents/self-media-content-expert/`
- 外部研究记录：
  - `research/platform-agent-compatibility.md`
- 验证记录：
  - `verification.md`
