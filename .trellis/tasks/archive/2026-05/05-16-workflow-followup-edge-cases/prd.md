# audit follow-up workflow edge cases

## Goal

核实并收敛 `docs/workflows/新项目开发工作流/` 中上一轮修复后暴露的后续边界问题，只在目标目录内修复真实缺陷或真实死代码，并保证不引入新的状态机误判、安装器回归或兼容性破坏。

## What I already know

- 本轮修改范围严格限制在 `docs/workflows/新项目开发工作流/`。
- 已完成的改动集中在：
  - `commands/shell/workflow-state.py` 与 `commands/shell/test_workflow_state.py`
  - `commands/install-workflow.py`
  - `commands/upgrade-compat.py`
  - `commands/uninstall-workflow.py`
  - `commands/workflow_assets.py`
  - `commands/workflow-capability-audit.py`
  - `commands/test_workflow_installers.py`
  - `commands/test_workflow_capability_audit.py`
  - `CLI原生适配边界矩阵.md`
  - `结构性迁移设计.md`
- 已验证的核心方向：
  - 删除空列表驱动的 enhanced-agent 死代码与空调用
  - 保留 `managed_enhanced_agents: []` 作为安装记录兼容字段，并明确加注释
  - `repair` 优先识别 task-local `review-gate/` 正式产物
  - degraded fallback 只在没有任何 session `current_task` 时才允许兜底

## Assumptions (temporary)

- 当前 dirty worktree 中的目标目录改动都属于同一条工作流维护链，可以作为一个任务闭环提交。
- 现阶段不需要再扩展到 repo-local `.trellis/`、`.agents/`、`.claude/` 层做同步修复。

## Open Questions

- 无新的阻塞问题；剩余工作以验证和收尾为主。

## Requirements

- 任务闭环必须只影响 `docs/workflows/新项目开发工作流/`。
- 所有针对 `workflow-state`、installer、capability-audit 的改动都要有对应回归测试或现有测试覆盖。
- 不把“未来 schema bump 也许会做”的清理提前做成当前破坏性改动。

## Acceptance Criteria

- [x] 真实死代码与空分支已清理或明确降为兼容注释
- [x] `workflow-state.py` 的 `repair/route` 边界调整有回归测试
- [x] 只保留目标目录内改动
- [x] 相关测试通过

## Definition of Done

- 目标目录内代码与文档一致
- 回归测试全部通过
- 变更可进入提交计划

## Out of Scope

- `.trellis/`、`.agents/`、`.claude/` 的额外同步重构
- 新的 schema bump
- 非工作流目录的代码卫生清理

## Technical Notes

- 关键验证命令：
  - `/ops/softwares/python/bin/python3 docs/workflows/新项目开发工作流/commands/shell/test_workflow_state.py`
  - `PYTHONPATH=docs/workflows/新项目开发工作流/commands /ops/softwares/python/bin/python3 -m unittest docs.workflows.新项目开发工作流.commands.test_workflow_installers`
  - `PYTHONPATH=docs/workflows/新项目开发工作流/commands /ops/softwares/python/bin/python3 -m unittest docs.workflows.新项目开发工作流.commands.test_workflow_capability_audit`
