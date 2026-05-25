# 审计并修复嵌入式新项目开发工作流缺陷

## Goal

基于 `/tmp/trellis-0.5.17-2` 这个已执行 `trellis init` 并嵌入 `docs/workflows/新项目开发工作流/` 的目标项目样本，证据化确认用户列出的工作流门禁、收尾与文档契约问题哪些真实存在；对真实缺陷仅在 `docs/workflows/新项目开发工作流/` 内完成修复，并补齐同类旁路，避免后续嵌入时继续出现相同问题或引入新的问题。

## What I already know

- 修复范围只允许落在 `docs/workflows/新项目开发工作流/` 与当前任务目录。
- 分析对象是目标项目 `/tmp/trellis-0.5.17-2` 的嵌入后行为，不是当前仓库运行中的 `.trellis/`。
- 版本门禁已通过：`docs/workflows/新项目开发工作流/commands/workflow_assets.py` 中 `COMPATIBLE_TRELLIS_VERSION = 0.5.17`，本机 `trellis -v` 也是 `0.5.17`。
- 已静态确认的真实问题：
  - brainstorm 直达 implementation 的 L0 门禁判断使用了可污染的候选集合来源
  - project-audit 缺少覆盖范围、聚合证据与 pre-audit/formal 语义校验
  - review-gate 只验章节标题，不验判定值、reviewer 证据与回归闭环
  - delivery 文档契约校验过浅
  - finish-work-checklist 门禁函数存在但未接入实际关闭路径
  - `task.py archive` 可以绕过 close-out 门禁
  - workflow 阶段总览与真实分支模型表达不一致
  - `workflow-state.py --help` 文档承诺与实际输出不一致
- 当前不成立的候选问题：
  - Codex 仍会主动把用户引到旧 agent/sub-agent 路径，这在当前版本已被 trellis-start、trellis-brainstorm 的 Codex 例外和 session-start hook 禁用。

## Assumptions (temporary)

- 需要同时修脚本契约、安装补丁、命令文档和测试，否则容易产生“脚本已收紧但文档/安装面仍漂移”的新问题。
- 对 `project-audit` / `review-gate` / `delivery` 的门禁收紧应采用“最小可机审且与现有文档模板一致”的标准，避免过度阻塞。
- `task.py archive` 的绕过问题不能直接修改当前仓库 Trellis 基线，应通过工作流 patch 在目标项目嵌入时修复。

## Open Questions

- `project-audit` 的正式模式是否需要强制校验任务覆盖矩阵中的“代码相关任务已完成”字段，还是允许带例外清单的 formal 出口。
- `review-gate` 是否要求 `recommended/full` 和 `required/full` 两类模式都必须有聚合摘要，还是仅 `full` 模式强制。

## Requirements (evolving)

- 仅修改 `docs/workflows/新项目开发工作流/` 与当前任务目录。
- 先补失败测试，再实现修复。
- 修复真实缺陷，并主动搜索同类结构性旁路一并处理。
- 若脚本级契约改变，同步更新对应命令文档、补丁模板和安装器测试。
- 对目标项目样本只用于分析和验证，不直接把 `/tmp/trellis-0.5.17-2` 作为最终修复落点。

## Acceptance Criteria (evolving)

- [ ] brainstorm 退出门禁在任何候选集合污染场景下都不会让非 `L0` 需求直达 implementation。
- [ ] project-audit / review-gate / delivery / finish-work 的最小文档证据契约被脚本真实校验，而不是只看标题存在。
- [ ] 通过 workflow 安装补丁后，目标项目中的 `task.py archive` 无法绕过强门禁 close-out 前置条件。
- [ ] `.trellis/workflow.md` 与相关命令文档准确反映真实阶段分支与 close-out 边界。
- [ ] `workflow-state.py --help` 与文档承诺一致，或文档改为真实边界描述。
- [ ] 新增或更新的测试覆盖本轮修复的问题与关键同类场景。
- [ ] 相关验证命令实际执行，结果真实记录为 pass / fail / not run。

## Definition of Done (team quality bar)

- 相关 Python 单测先失败后通过
- 安装器/工作流测试集运行完成
- 文档、脚本、补丁和测试保持一致
- 不修改工作流目录之外的仓库产品资产

## Out of Scope (explicit)

- 修改当前仓库正在运行的 `.trellis/` 基线实现作为最终修复
- 修改 `docs/workflows/新项目开发工作流/` 之外的任何工作流或平台目录
- 直接修补 `/tmp/trellis-0.5.17-2` 并把它当成最终交付

## Technical Notes

- 主要修复落点预计包括：
  - `docs/workflows/新项目开发工作流/commands/shell/state_utils.py`
  - `docs/workflows/新项目开发工作流/commands/shell/validators_gates.py`
  - `docs/workflows/新项目开发工作流/commands/shell/delivery-control-validate.py`
  - `docs/workflows/新项目开发工作流/commands/shell/workflow-state.py`
  - `docs/workflows/新项目开发工作流/commands/install-workflow.py`
  - `docs/workflows/新项目开发工作流/commands/workflow_assets.py`
  - `docs/workflows/新项目开发工作流/commands/*` 中相关命令文档
  - `docs/workflows/新项目开发工作流/commands/shell/test_workflow_state.py`
  - `docs/workflows/新项目开发工作流/commands/shell/test_delivery_control_validate.py`
  - `docs/workflows/新项目开发工作流/commands/test_workflow_installers.py`
