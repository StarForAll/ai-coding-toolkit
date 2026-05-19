# 审计并修复新项目开发工作流状态门禁缺陷

## Goal

基于 `/tmp/trellis-0.5.17-2` 这个已执行 `trellis init` 并嵌入当前工作流的目标项目样本，证据化审计 `docs/workflows/新项目开发工作流/` 的强门禁状态机、close-out 链路与安装补丁是否仍存在假阳性、越级、fail-open 与 repair 污染问题；若问题真实存在，则仅在该工作流源目录内修复，并补齐同类缺陷与回归测试。

## What I already know

- 用户限定修复范围为 `docs/workflows/新项目开发工作流/` 与当前任务目录。
- `/tmp/trellis-0.5.17-2` 是目标项目样本，审计对象是其嵌入后的行为，而不是本仓库当前正在使用的 Trellis 工作流。
- `docs/workflows/新项目开发工作流/commands/shell/workflow-state.py` 现有 `route` 的 `awaiting_user_confirmation` 退出门禁仅覆盖 `brainstorm/design/plan/check/finish-work/delivery`。
- `docs/workflows/新项目开发工作流/commands/shell/check-quality.py` 现有实现对未提供验证命令返回 `None`，主流程只在出现 `False` 时非零退出，存在 fail-open 风险。
- `workflow-state.py set` 当前先信任 `allowed_next_stages`，未强制校验 `current_stage -> target_stage` 是否属于 `STAGE_TRANSITIONS` 的 canonical 边。
- `workflow-state.py repair` 当前会保留 `allowed_next_stages`、`awaiting_user_confirmation`、`last_confirmed_transition`、`checkpoints` 等语义字段，未重建一致性。

## Assumptions (temporary)

- 对 `project-audit` / `review-gate` / `record-session` 的最小证据门禁，应直接从对应命令文档与 skill 的输出契约中提炼，而不是额外发明新产物。
- `workflow-state.py validate` 与 `route` 应共享阶段退出证据校验逻辑，避免再次漂移。
- 若某些问题已经在源资产中部分修复，需要以当前源码和测试结果为准，不重复改动。

## Open Questions

- `record-session` 是否只需要在 `route`/`set` 层确保前置 delivery 产物齐备，还是还要新增终态元数据闭环证据文件门禁？
- `project-audit` 和 `review-gate` 的最小可机审产物契约，应该要求哪些文件必须存在、哪些章节/字段必须出现，才能既收紧假阳性又不引入过度阻塞？

## Requirements (evolving)

- 逐项核实用户列出的 6 类问题在当前源资产与 `/tmp/trellis-0.5.17-2` 中是否真实存在。
- 修复真实存在的问题，并主动搜索同类结构性缺陷一起处理。
- 所有修复仅允许修改 `docs/workflows/新项目开发工作流/` 下资产与当前任务目录。
- 对脚本行为变更先补失败测试，再实现修复。
- 相关命令文档/协议若与脚本级契约不一致，需要同步更新到同一工作流目录内的源文档。

## Acceptance Criteria (evolving)

- [ ] `workflow-state.py` 对真实需要强门禁的阶段具备一致、可机审的退出证据校验，不再出现“awaiting_user_confirmation 但证据未齐”的假阳性。
- [ ] `workflow-state.py set` 不允许仅凭脏 `allowed_next_stages` 越过 canonical transition graph。
- [ ] `workflow-state.py repair` 不再无条件继承脏语义字段，重建结果必须经过强一致性校验。
- [ ] `check-quality.py` 在未提供任何验证命令时不再返回成功假象，并有相应测试覆盖。
- [ ] 新增/更新的测试能覆盖本轮修复的问题与关键同类场景。
- [ ] 相关验证命令实际执行，结果真实记录为 pass / fail / not run。

## Definition of Done (team quality bar)

- 相关 Python 单测已补齐并先失败后通过
- 相关工作流测试集运行完成
- 结论、风险、未覆盖点写入任务记录
- 不修改工作流源目录以外的仓库资产

## Out of Scope (explicit)

- 修改本仓库当前生效的 `.trellis/` 运行时代码
- 修改 `docs/workflows/新项目开发工作流/` 之外的任意工作流或平台目录
- 为目标项目样本 `/tmp/trellis-0.5.17-2` 直接打补丁作为最终修复

## Technical Notes

- 证据源：`/tmp/trellis-0.5.17-2`
- 主要实现面：`docs/workflows/新项目开发工作流/commands/shell/workflow-state.py`
- 辅助实现面：`docs/workflows/新项目开发工作流/commands/shell/check-quality.py`
- 主要回归测试：`docs/workflows/新项目开发工作流/commands/shell/test_workflow_state.py`、`test_check_quality.py`
