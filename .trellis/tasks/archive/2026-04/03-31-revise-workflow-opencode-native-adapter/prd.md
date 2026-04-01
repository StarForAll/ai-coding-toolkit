# 重写 OpenCode 原生适配说明

## Goal

基于 OpenCode 当前官方能力，重写 `docs/workflows/新项目开发工作流/commands/opencode/README.md`，将其从“instructions 降级兼容说明”升级为“原生适配说明”。

## Requirements

* 说明 `.opencode/commands/`、`.opencode/agents/`、rules、permissions、skills 的承载方式
* 保留 `instructions`，但将其定位为规则来源之一，而非唯一入口
* 写清与 Claude 的关键差异，尤其是 hook/subagent 注入限制
* 回填到共享文档中需要引用 OpenCode 能力的地方

## Acceptance Criteria

* [x] `opencode/README.md` 不再包含“命令系统 TBD”这类过时表述
* [x] 文档能独立说明 OpenCode 如何承载 workflow 命令、规则和 agents
* [x] 文档明确写出当前已知限制，而不是过度乐观

## Out of Scope

* OpenCode 插件或 hook 的代码实现
* 其他平台的适配文档


## Session Handoff

### Current State

* 已将 `docs/workflows/新项目开发工作流/commands/opencode/README.md` 从 `instructions` 降级兼容说明改写为 OpenCode 原生命令 / rules / agents / skills 适配说明。
* 文档已补充 `.opencode/commands/`、`.opencode/agents/`、`AGENTS.md`、`opencode.json.instructions`、通用脚本层的部署映射。
* 文档已写明与 Claude 的关键差异，尤其是 subagent hook 注入链路不能默认等价。

### Verification Evidence

* `/tmp/opencode-workflow-smoke/run-report.md` 存在。
* 当前 README 已包含 `/tmp` 最小验证建议、CLI 基础可执行验证建议、以及已知限制说明。
* 当前工作区 diff 已显示旧的 “命令系统 TBD / 仅 instructions 注入” 口径被整体替换。

### Remaining Closure

* 尚未进行人工测试后的 commit。
* 尚未执行正式 `$record-session`。
* 子任务应视为“文档已落地，待人工收尾”。
