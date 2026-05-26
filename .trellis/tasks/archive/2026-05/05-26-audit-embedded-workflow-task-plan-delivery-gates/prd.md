# workflow-audit: 新项目开发工作流 task-plan / delivery gates

## Goal

基于 `docs/workflows/新项目开发工作流/` 的源码定义，以及 `/tmp/trellis-0.5.17-2` 这个已执行 `trellis init` 并嵌入工作流的目标项目，审计用户给出的 6 类候选问题及同类问题是否真实存在。若确认存在，则整理最小且安全的修复方向，但在用户明确同意前不修改工作流源码。

## What I already know

* 审计目标固定为 `docs/workflows/新项目开发工作流/`，不是当前仓库正在使用的 Trellis 原生流程。
* 允许把 `/tmp/trellis-$(trellis -v)-2` 作为运行态证据来源。
* 当前版本门禁通过：`docs/workflows/新项目开发工作流/commands/workflow_assets.py` 的 `COMPATIBLE_TRELLIS_VERSION` 为 `0.5.17`，`trellis -v` 也是 `0.5.17`。
* `validators_gates.py` 当前已实现 `validate_plan_gate`、`validate_project_audit_gate`、`validate_delivery_gate` 等关键门禁。
* `plan-validate.py` 当前会强制校验 `task_creation_checklist.md`、`task_plan.md`、推荐 leaf task 的最小 `prd.md`、Trellis Task 清单和依赖摘要。
* `/tmp/trellis-0.5.17-2` 已安装了工作流命令、共享技能和 `.trellis/scripts/workflow/*.py` 安装副本。

## Assumptions (temporary)

* 候选问题中至少部分会落在 `plan-validate.py` / `validators_gates.py` / `project-audit.md` / `delivery.md` 的契约不一致上。
* 如果需要最小复现，可以在 `/tmp/trellis-0.5.17-2` 中创建或编辑临时任务产物作为运行态证据；这不违反“源码改动只限 `docs/workflows/新项目开发工作流/`”的边界。

## Open Questions

* 第 1 类问题是否真的是“leaf 从 plan 切 implementation 必然失败”，还是“leaf 不应停留在 plan 阶段”的使用误解。
* 第 2/3/4/5/6 类问题在当前脚本里是否已经部分缓解，但仍存在不完整或误判边界。

## Requirements (evolving)

* 必须以源码和 `/tmp/trellis-0.5.17-2` 的运行态作为证据，不按用户候选点直接下结论。
* 必须检查同类问题，而不只回答 6 个显式候选点。
* 在用户确认修复方案前，不得修改 `docs/workflows/新项目开发工作流/`。
* 可以修改当前任务目录内的审计产物文件。

## Acceptance Criteria (evolving)

* [ ] 给出每个候选问题的真实结论：确认存在 / 不成立 / 部分成立
* [ ] 给出对应证据链：源码位置、安装副本位置、必要的运行态验证
* [ ] 给出同类问题列表和影响面
* [ ] 给出最小修复方案并停在用户确认边界

## Definition of Done (team quality bar)

* 结论与证据一致
* 不把非缺陷差异包装成优化项
* 修复建议说明传播范围和验证方法

## Out of Scope (explicit)

* 在本轮未经用户确认直接修改 `docs/workflows/新项目开发工作流/`
* 修改 `docs/workflows/新项目开发工作流/` 以外的源码目录
* 对 Trellis 原生上游仓库直接提补丁

## Technical Notes

* 关键源码候选：`docs/workflows/新项目开发工作流/commands/shell/validators_gates.py`
* 关键结构校验：`docs/workflows/新项目开发工作流/commands/shell/plan-validate.py`
* 关键文档契约：`docs/workflows/新项目开发工作流/commands/plan.md`、`project-audit.md`、`delivery.md`
* 运行态安装副本：`/tmp/trellis-0.5.17-2/.trellis/scripts/workflow/*.py`
