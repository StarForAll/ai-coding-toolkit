# Review Gate - Round 1

## Decision

- result: `required`
- round: `1`
- task-id: `04-17-workflow-external-delivery-hardening`
- protocol: `task-level`

## Why This Review Gate Is Required

当前改动命中了 review-gate 的多项硬条件：

- 跨层 contract 变更：`feasibility -> start -> workflow-state -> plan -> delivery` 的门禁链被修改
- 高 blast radius：同时修改了 source workflow、helper validators、installer version record、repo-local `.trellis/spec` 规则
- 外包交付关键路径：新增 `project_engagement_type`、`kickoff_payment_ratio`、`kickoff_payment_received`
- 版本治理变更：新增“未正式可用版本不得大于 1.0”的规则，并把当前 workflow 生效版本统一调整为 `0.1.24`

## Scope Reviewed In Round 1

- `docs/workflows/新项目开发工作流/commands/shell/feasibility-check.py`
- `docs/workflows/新项目开发工作流/commands/shell/delivery-control-validate.py`
- `docs/workflows/新项目开发工作流/commands/shell/workflow-state.py`
- `docs/workflows/新项目开发工作流/commands/feasibility.md`
- `docs/workflows/新项目开发工作流/commands/plan.md`
- `docs/workflows/新项目开发工作流/commands/delivery.md`
- `docs/workflows/新项目开发工作流/commands/start-patch-phase-router.md`
- `docs/workflows/新项目开发工作流/工作流总纲.md`
- `docs/workflows/新项目开发工作流/命令映射.md`
- `docs/workflows/新项目开发工作流/工作流全局流转说明（通俗版）.md`
- `docs/workflows/新项目开发工作流/多CLI通用新项目完整流程演练.md`
- `docs/workflows/新项目开发工作流/完整流程演练.md`
- `docs/workflows/新项目开发工作流/commands/workflow_assets.py`
- `docs/workflows/自定义工作流制作规范.md`
- `.trellis/spec/docs/index.md`

## Current Evidence

- 已完成本地单测：
  - `docs.workflows.新项目开发工作流.commands.shell.test_feasibility_check`
  - `docs.workflows.新项目开发工作流.commands.shell.test_delivery_control_validate`
  - `docs.workflows.新项目开发工作流.commands.shell.test_workflow_state`
  - `docs.workflows.新项目开发工作流.commands.test_workflow_installers`
- 已完成脚本语法检查：
  - `python3 -m py_compile` 针对三份 shell validator
- 已完成 `git diff --check`

## Review Focus For External Reviewers

本轮 reviewer 只检查高价值问题，不做代码修改，重点审查：

1. 外包项目门禁是否误伤非外包项目的正常路径
2. `kickoff_payment_*` 与 `delivery_control_*` 的判定是否在 `feasibility / workflow-state / plan / delivery` 间保持一致
3. “所有项目都先经过 feasibility，但只有外包项目强制执行首/尾款控制”是否仍有残留冲突表述
4. 版本规则是否已经完整收敛：
   - 当前生效版本为 `0.1.24`
   - 未正式可用版本不得大于 `1.0`
   - source docs / generated docs / installer assertions 是否仍有活动引用漂移

## Exit Rule

- 若 reviewer 报告无新的高价值问题，可直接进入 `multi-cli-review-action`
- 若 reviewer 报告发现跨文档矛盾、规则未完全传播或回归风险，则先修复，再重新验证
