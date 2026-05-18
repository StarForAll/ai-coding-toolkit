# PRD: refine trellis 0.5.17 enhancement retention

## Goal

基于当前仓库实际生效的 Trellis runtime，对 0.5.17 升级残留做最小化收口：保留已经确认有效的本地增强，删除不必要的 `.new` 候选文件，不把当前 live contract 回退到 `/tmp/trellis-0.5.17` baseline。

## What I already know

- 当前仓库实际生效的 Trellis 运行面是 `.trellis/` 与 `.claude/`、`.codex/`、`.opencode/`、`.qoder/`、`.kiro/`。
- 当前 live runtime 保留 degraded active-task 行为、`[workflow-state:stale]`、Codex inline contract 注释、以及 enriched `trellis-research` 工具路由。
- 当前工作树存在 19 个 `.new` 候选，其中 17 个出现在 `git status`，2 个被忽略但仍在磁盘上：`.trellis/workflow.md.new`、`.trellis/scripts/common/__init__.py.new`。
- 这些 `.new` 基本等于 `/tmp/trellis-0.5.17` 对应 baseline 文件，不能自动视为正确升级内容。
- 已有回归测试当前全部通过，说明 live contract 当前一致。

## Requirements

- 只清理不必要的 `.new` 文件，不改坏当前通过验证的 live runtime。
- 保留以下确认有效的增强：
  - research agent 的 3 步 task 解析回退
  - Codex inline-mode carrier 注释
  - `.kiro/` research agent 的平台自适应路由
  - `workflow.md` 与 `change-task-lifecycle.md` 当前指向 live 测试/解析器的合约引用
- 删除所有当前已确认不应采用的 `.new` 候选。

## Acceptance Criteria

- [ ] 当前工作树中不再残留 `*.new` 文件
- [ ] 当前 live 文件仍保留前述增强
- [ ] Trellis runtime 回归测试继续通过

## Out of Scope

- 不重写 live runtime 逻辑
- 不把当前仓库切回 `/tmp/trellis-0.5.17` baseline
- 不处理 `docs/workflows/新项目开发工作流/` 产品源码

## Technical Notes

- 相关 live contract 与测试位于：
  - `.trellis/workflow.md`
  - `.trellis/scripts/common/tests/test_runtime_active_task_convergence.py`
  - `.trellis/scripts/common/tests/test_workflow_phase_contracts.py`
  - `.trellis/scripts/common/tests/test_runtime_upgrade_contracts.py`
- 相关历史审计与结论位于：
  - `.trellis/tasks/archive/2026-05/05-13-analyze-current-trellis-runtime-and-minor-upgrade-residue/research/runtime-upgrade-audit.md`
