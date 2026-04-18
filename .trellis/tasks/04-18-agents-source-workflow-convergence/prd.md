# agents 源资产层：收敛 workflow agents 为仓库级 source-of-truth

## Goal

将当前散落在 `docs/workflows/新项目开发工作流/commands/{claude,opencode,codex}/agents/` 下的 workflow agent 定义，收敛为仓库级 `agents/` 源资产层的一部分，建立统一的 source-of-truth、部署映射和同步规则，避免 workflow 子目录与仓库主 agents 定义长期双轨。

## What I already know

* 仓库当前已有一个上层任务：`.trellis/tasks/03-19-implement-agents-source/`，本任务已作为其子任务创建。
* 当前仓库的 `.claude/agents/`、`.opencode/agents/` 是 live deployment，不是 `agents/` 源资产层同步产物。
* `spec/agents` 已明确目标架构是：`agents/<agent-id>/README.md + SYSTEM.md + TOOLS.md + EXAMPLES/` 作为 source-of-truth，再部署到各 CLI 目录。
* 刚完成的 workflow 兼容修复，已经在 `docs/workflows/新项目开发工作流/commands/{claude,opencode,codex}/agents/` 下建立了 workflow 管理的 `research / implement / check` agent 源文件。
* 当前 workflow 已将 `research -> implement -> check-agent` 定义为 implementation 内部链；`plan / dispatch agent` 明确不采用。
* research agent 已确定统一规则：
  * 外部技术搜索优先 `exa`
  * 第三方库 / 框架 / SDK 官方文档必须先 `Context7`
  * 未经过 `Context7` 不得输出 API / 配置 / 版本结论
* Codex 的 `check.toml` 已确定需要按官方 `subagents` / `hooks` 边界对齐为可修复 check-agent 语义。

## Problem

当前仓库存在至少两层“agent 源定义”：

1. 仓库目标架构里的 `agents/` 源资产层（尚未真正落地）
2. workflow 子目录内为了兼容修复临时建立的 `docs/workflows/.../commands/*/agents/`

如果不继续收敛：

* agent 定义会继续双轨
* workflow 变更与仓库级 agent 规范可能再次漂移
* 安装器 / 升级分析脚本与未来 `agents/` 源层之间的 source-of-truth 会冲突

## Scope

本任务未来应覆盖：

* 设计 workflow agents 如何映射进仓库级 `agents/` 源资产层
* 明确 source-of-truth 与 deploy target 的边界
* 明确 `research / implement / check` 这组 agents 是否以仓库通用能力存在，还是以 workflow 变体存在
* 明确 Claude / OpenCode / Codex 三端 deployment adapter 的字段映射
* 明确从 workflow 子目录迁移到 `agents/` 源层的步骤和防漂移策略

## Out of Scope

* 当前 turn 不执行任何实现
* 当前 turn 不修改 `agents/`、`.claude/agents/`、`.opencode/agents/`、`.iflow/agents/`
* 当前 turn 不回滚或删除 `docs/workflows/新项目开发工作流/commands/*/agents/`

## Key Inputs From Previous Task

来自 `.trellis/tasks/04-18-trellis-native-workflow-compat/` 的已确认结论：

* workflow 不采用 `plan / dispatch agent`
* `research / implement / check-agent` 是 implementation 内部角色链
* `.codex/agents/*.toml` 需要纳入 workflow 兼容治理
* Codex 不能照搬 Claude 的 hook 注入机制，但应对齐 agent 角色语义
* 三端 managed agents 目前已在 workflow 层形成 install / analyze-upgrade / upgrade-compat / uninstall / test 的闭环

## Expected Deliverables

* 一份清晰的收敛方案：
  * `agents/` 源资产层目录结构
  * workflow agents 与仓库级 agents 的关系
  * 迁移顺序
  * 部署与同步策略
  * 风险与回滚思路
* 必要时，再拆成后续实现子任务

## Technical Notes

关键参考路径：

* `agents/` 目标规范：`.trellis/spec/agents/index.md`
* 当前 workflow agents：
  * `docs/workflows/新项目开发工作流/commands/claude/agents/`
  * `docs/workflows/新项目开发工作流/commands/opencode/agents/`
  * `docs/workflows/新项目开发工作流/commands/codex/agents/`
* 当前 live deployments：
  * `.claude/agents/`
  * `.opencode/agents/`
* 兼容治理脚本：
  * `docs/workflows/新项目开发工作流/commands/install-workflow.py`
  * `docs/workflows/新项目开发工作流/commands/workflow_assets.py`
  * `docs/workflows/新项目开发工作流/commands/analyze-upgrade.py`
  * `docs/workflows/新项目开发工作流/commands/upgrade-compat.py`

## Current Status

* 任务已创建
* 仅完成 PRD 落盘
* 未开始实现
