# workflow-audit: 新项目开发工作流路由强门禁对齐修复

## Goal

审计并修复 `docs/workflows/新项目开发工作流/` 中与强门禁路由协议、平台入口消费、安装补丁链相关的真实缺陷。判断依据以该工作流嵌入后的目标项目 `/tmp/trellis-0.5.17-2` 为主，修复动作只落在工作流源码目录和当前任务目录，确保后续嵌入目标项目时行为正确且不引入新的协议漂移。

## What I already know

* 用户给出了 4 组候选问题，重点集中在 `workflow-state.py route` 的 `action / stage_status / blockers` 协议未被入口层完整消费。
* 当前工作流兼容锚点 `COMPATIBLE_TRELLIS_VERSION` 为 `0.5.17`，当前 `trellis -v` 也是 `0.5.17`，版本门禁通过。
* `ace.search_context` 已定位到源码中的关键实现：`workflow-state.py`、`patch-inject-workflow-state.py`、`patch-session-start-strong-gate.py`、`trellis-start` / `trellis-continue` 等。
* 从静态证据看，`patch-inject-workflow-state.py` 仍以 `workflow-state.json.stage` 作为主要注入值，而不是以 route 结果为主。
* 当前任务是维护工作流产品源码，不是修当前仓库自身运行中的 Trellis 主链。

## Assumptions (temporary)

* `/tmp/trellis-0.5.17-2` 可作为 workflow-installed state 的证据来源。
* 如需 clean baseline，可在 `/tmp` 新建额外的 `trellis init` 项目做对照，但不会修改仓库源码目录之外的持久内容。
* 只要补丁链、文档、测试和安装器契约一致，即使不改当前仓库 `.claude/` / `.opencode/` / `.codex/` 实时副本，也符合本任务边界。

## Open Questions

* 无阻塞性待问问题；当前信息足以先完成审计与修复。

## Requirements (evolving)

* 逐项判断用户列出的候选问题是否在目标项目中真实存在。
* 对真实问题在 `docs/workflows/新项目开发工作流/` 内修复，并同步处理同类问题。
* 修复应保持安装后协议一致：源码文档、补丁脚本、测试、安装器契约不能互相漂移。
* 不修改除 `docs/workflows/新项目开发工作流/` 与当前任务目录以外的仓库文件。
* 优先保守修复强门禁闭环，不做无证据的“顺手优化”。

## Acceptance Criteria (evolving)

* [ ] 对每个候选问题都给出“真实存在 / 误报 / 证据不足”的结论与证据。
* [ ] 所有确认问题的修复都只发生在允许目录内。
* [ ] 相关补丁/文档/测试在工作流源码内保持同步。
* [ ] 至少完成与本次修复相关的静态或自动化验证，并如实记录 pass / fail / not run。

## Definition of Done (team quality bar)

* 相关脚本、命令文档、工作流文档、测试或断言同步更新
* 运行与本次改动直接相关的验证命令
* `audit-report.md` 记录审计证据、问题结论、修复范围与剩余风险

## Out of Scope (explicit)

* 修改当前仓库正在使用的 `.claude/`、`.opencode/`、`.codex/`、`.agents/` 运行副本
* 修改 `docs/workflows/新项目开发工作流/` 之外的工作流或通用 Trellis 源码
* 未经证据支持的跨平台“统一风格化”重构

## Technical Notes

* 审计目标固定为 `docs/workflows/新项目开发工作流/`
* 目标项目证据根目录：`/tmp/trellis-0.5.17-2`
* 关键源码候选：
  * `docs/workflows/新项目开发工作流/commands/shell/workflow-state.py`
  * `docs/workflows/新项目开发工作流/commands/shell/patch-inject-workflow-state.py`
  * `docs/workflows/新项目开发工作流/commands/shell/patch-session-start-strong-gate.py`
  * `docs/workflows/新项目开发工作流/commands/start-patch-phase-router.md`
  * `docs/workflows/新项目开发工作流/CLI原生适配边界矩阵.md`
