# workflow-audit active-task runtime alignment

## Goal

修正 `docs/workflows/新项目开发工作流/` 对 Trellis 当前活动任务机制的错误建模，使 workflow 阶段路由与状态校验重新对齐 Trellis 0.5 的 session-scoped active task runtime，并彻底移除 `.trellis/.current-task` 在阶段判定链中的角色。

## What I already know

* Trellis 0.5 当前活动任务真相源在 `.trellis/.runtime/sessions/`，由 `.trellis/scripts/common/active_task.py` 解析。
* 当前 workflow 文档和 `workflow-state.py` 仍把 `.trellis/.current-task -> 当前叶子任务 -> workflow-state.json` 写成唯一阶段判定链。
* `workflow-state.py route` 在 `.current-task` 缺失时会扫描 `assessment.md` 来猜下一步，这与 Trellis 的多会话隔离模型冲突。
* `brainstorm` 命令存在一部分对 Trellis 原生 task-first / PRD bootstrap 的重复封装，但当前首要修复面仍是 active-task 真相源对齐。
* 当前 workflow 的 `finish-work` close-out 已回到 Trellis 原生 `task.py archive + add_session.py`，这部分不是本任务主问题。

## Assumptions (temporary)

* 目标项目安装后的 `.trellis/scripts/common/active_task.py` 可以被 `.trellis/scripts/workflow/workflow-state.py` 安全复用。
* 旧目标项目兼容不在本轮考虑范围内，可以接受对 `.current-task` 主合同的硬切换。
* 本轮先修 active-task / route / 文档合同；若 `brainstorm` 重复封装仍需收缩，可作为同任务次级范围处理。

## Open Questions

* 已确认：`.current-task` 彻底从阶段判定链中移除。

## Requirements (evolving)

* `workflow-state.py` 的 `validate` / `route` 需要基于 Trellis session-scoped active task 解析当前任务。
* `.current-task` 不再参与当前 workflow 的阶段判定、恢复路由或校验合同。
* `route` 不得在缺少明确 active task 时扫描任务树、扫描 `assessment.md` 或猜测当前阶段。
* `阶段状态机与强门禁协议.md`、`工作流总纲.md`、`命令映射.md`、`start-patch-phase-router.md`、`start-skill-patch-phase-router.md` 等文档必须同步改口径。
* 相关脚本测试与安装器测试需更新，覆盖新的 active-task 真相源和“缺 active task 时进入恢复分支”语义。

## Acceptance Criteria (evolving)

* [ ] `workflow-state.py` 不再读取 `.trellis/.current-task` 作为阶段判定输入。
* [ ] 无明确 active task 时，`route` 返回恢复/澄清分支，而不是扫描 `assessment.md` 猜阶段。
* [ ] 所有主文档和 phase-router 入口文档不再声明 “`.current-task -> 当前叶子任务 -> workflow-state.json` 是唯一判定链”。
* [ ] 现有测试更新为新语义，并新增至少一个覆盖 session-scoped active task 解析的测试。
* [ ] 相关验证命令实际执行，结果如实记录。

## Definition of Done (team quality bar)

* Tests added or updated for changed routing/state contracts
* Relevant validation commands pass
* Workflow docs stay aligned with script behavior
* No unsupported claim about runtime behavior remains in active source docs

## Out of Scope (explicit)

* `/tmp` 目标项目完整安装验证
* `trellis-research` capability enhancement contract changes
* 非 active-task 主线的 workflow 大规模重构

## Technical Notes

* Candidate script files:
  * `docs/workflows/新项目开发工作流/commands/shell/workflow-state.py`
  * `docs/workflows/新项目开发工作流/commands/shell/test_workflow_state.py`
  * `docs/workflows/新项目开发工作流/commands/test_workflow_installers.py`
* Candidate docs:
  * `docs/workflows/新项目开发工作流/阶段状态机与强门禁协议.md`
  * `docs/workflows/新项目开发工作流/commands/start-patch-phase-router.md`
  * `docs/workflows/新项目开发工作流/commands/start-skill-patch-phase-router.md`
  * `docs/workflows/新项目开发工作流/命令映射.md`
  * `docs/workflows/新项目开发工作流/工作流总纲.md`
  * `docs/workflows/新项目开发工作流/工作流全局流转说明（通俗版）.md`
  * `docs/workflows/新项目开发工作流/多CLI通用新项目完整流程演练.md`
* Reference contracts:
  * `.trellis/scripts/common/active_task.py`
  * `.trellis/spec/scripts/workflow-installer-upgrade-contracts.md`
  * `.trellis/spec/scripts/workflow-command-doc-contracts.md`

## Implementation Plan

1. 让 `workflow-state.py` 直接复用 Trellis session-scoped active task 解析，而不是读取 `.current-task`。
2. 删除 `route` 中基于 `.current-task` 缺失时扫描 `assessment.md` 的猜测逻辑，统一改成恢复分支。
3. 批量更新阶段路由、状态机、总纲和 walkthrough 文档，把阶段判定链改写为 session runtime + 当前叶子任务 + `workflow-state.json`。
4. 更新脚本测试与相关合同文档，验证新语义。

## Research References

* Static audit findings from the current session
