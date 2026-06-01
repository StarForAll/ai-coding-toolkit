# fix workflow implementation task closeout routing

## Goal

修正 `docs/workflows/新项目开发工作流/` 中 implementation 阶段的任务级收尾路由，确保 implementation 子任务可以单独收尾，不被错误引导到项目级 `project-audit` / `delivery`，并同步修正状态机、命令文档、安装器示例与回归测试。

## What I already know

- 当前状态机把 `implementation` 的 canonical next stages 定义为 `check` 和 `project-audit`。
- 当前 workflow 文档存在“implementation 可手动进入 project-audit 预审模式”的表述。
- 当前 close-out 文档口径把 native `finish-work` 的主链顺序绑定为 `delivery -> finish-work`，不适合 implementation 子任务单独收尾。
- 用户确认的正确流程是：
  - implementation 阶段的子任务可以单独收尾，不需要执行项目级 `project-audit` / `delivery`
  - 执行 implementation 阶段的子任务不会流转到项目级 `project-audit` / `delivery`
  - `implementation -> check`
  - `implementation -> check -> review-gate`
  - `project-audit -> check`
  - `project-audit -> check -> review-gate`

## Assumptions (temporary)

- 这里的“单独收尾”指任务级 `check` / 条件 `review-gate` 闭环后，可进入 native Trellis `finish-work` 完成当前 active task 的归档与 session 记录。
- 项目级 `delivery` 仍然只属于项目级 owner / project-level closeout 场景，不扩展到普通 implementation 子任务。

## Open Questions

- 无阻塞问题；按用户确认后的目标直接修正。

## Requirements

- 收紧 workflow-state canonical transitions，使 `implementation` 只能正式进入 `check`。
- 保留并验证 `project-audit -> check -> review-gate` 路径，禁止 `project-audit -> review-gate` 直接切换。
- 调整命令文档、映射文档、补丁文档、安装器断言，使其与新的任务级/项目级边界一致。
- 不把项目级 `delivery -> finish-work` 口径继续错误套用到普通 implementation 子任务。

## Acceptance Criteria

- [ ] `STAGE_TRANSITIONS` 与门禁校验不再允许 `implementation -> project-audit`
- [ ] 文档不再把 implementation 子任务导向项目级 `project-audit` / `delivery`
- [ ] 文档明确普通 implementation 子任务可在任务级闭环后进入 native `finish-work`
- [ ] 相关测试覆盖并通过

## Definition of Done (team quality bar)

- 相关测试已更新并通过
- 受影响文档和安装器断言已同步
- 不引入与当前 formal `PROJECT-AUDIT` 双门禁模型相冲突的新语义

## Out of Scope (explicit)

- 不重构整个 workflow 的阶段体系
- 不变更 `project-audit` 与 `delivery` 的项目级职责
- 不做 `/tmp` 运行时嵌入审计

## Technical Notes

- 重点文件预计包括：
  - `docs/workflows/新项目开发工作流/commands/shell/state_utils.py`
  - `docs/workflows/新项目开发工作流/commands/shell/validators_gates.py`
  - `docs/workflows/新项目开发工作流/commands/shell/test_workflow_state.py`
  - `docs/workflows/新项目开发工作流/commands/*.md`
  - `docs/workflows/新项目开发工作流/命令映射.md`
  - `docs/workflows/新项目开发工作流/阶段状态机与强门禁协议.md`
  - `docs/workflows/新项目开发工作流/工作流全局流转说明（通俗版）.md`
  - `docs/workflows/新项目开发工作流/commands/test_workflow_installers.py`
