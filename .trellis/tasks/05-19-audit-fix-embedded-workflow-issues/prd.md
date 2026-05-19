# audit and fix embedded workflow issues in 新项目开发工作流

## Goal

以 `/tmp/trellis-0.5.17-2` 这个已执行 `trellis init` 并嵌入 `docs/workflows/新项目开发工作流/` 的目标项目为证据对象，审计当前工作流产品源资产中与强门禁、close-out、degraded 恢复、补丁死代码、文档/脚本契约漂移相关的问题；对确认存在的真实问题在 `docs/workflows/新项目开发工作流/` 内实施修复，并尽量一起修复同类入口，避免后续再次嵌入时重复出现同类问题。

## What I already know

- 用户限定判断对象是 `/tmp/trellis-0.5.17-2`，修复落点必须是 `docs/workflows/新项目开发工作流/`
- 其他目录不能修改，但当前任务目录可以修改
- 当前仓库是工作流作者仓库，不是目标项目；若问题落在 Trellis 原生行为，需要在工作流安装/补丁层修正，而不是直接改当前仓库运行时
- `docs/workflows/新项目开发工作流/commands/workflow_assets.py` 的 `COMPATIBLE_TRELLIS_VERSION` 为 `0.5.17`
- `trellis -v` 实际输出为 `0.5.17`，同版本门禁已通过
- 已定位的候选问题主要落在：
  - `commands/shell/workflow-state.py`
  - `commands/brainstorm.md`
  - `commands/record-session.md`
  - `commands/install-workflow.py`
  - `commands/shell/patch-session-start-strong-gate.py`
  - 以及这些源文件安装到目标项目后的对应副本

## Candidate Issues To Audit

1. `brainstorm -> implementation/test-first` 是否缺少 `L0` 硬门禁，导致高复杂度任务可绕过 `design/plan`
2. `record-session` 是否仍作为可直接执行的一等入口暴露，导致命令层绕过 `delivery`
3. degraded 模式下 `.trellis/.runtime/degraded-active-task.json` 是否是 repo 级共享 fallback，存在错路由
4. `session-start` 强门禁补丁是否在目标项目中保留不可达旧逻辑残留
5. `brainstorm` 文档与 `workflow-state.py` 对出口快照字段的门禁语义是否漂移
6. 上述问题是否存在同类入口、并在命令文档、安装器补丁、测试中同时需要同步修复

## Requirements

- 只基于证据确认问题，不把用户给出的候选项直接当成已证实缺陷
- 若问题存在，修复时要同时检查同类入口，避免只修一处
- 修复必须限制在 `docs/workflows/新项目开发工作流/` 下
- 若是目标项目中的原生 Trellis 缺口，需要通过该工作流的安装器、补丁脚本、命令文档或测试层修复
- 修改前先补失败测试或等价验证，证明问题真实存在
- 修改后需要运行相关测试/验证命令，真实报告通过/失败/未运行状态

## Acceptance Criteria

- [ ] 每个候选问题都被分类为 confirmed issue / false alarm / evidence gap
- [ ] 确认存在的问题在工作流源目录内完成修复，并覆盖同类入口
- [ ] 至少新增或更新对应测试，能在源码层防止问题回归
- [ ] 相关命令文档、补丁脚本、安装器逻辑、测试之间保持一致
- [ ] 审计结论与验证结果记录进 `audit-report.md`

## Out of Scope

- 不直接修当前仓库 `.trellis/`、`.claude/`、`.codex/`、`.opencode/` 的作者仓库运行时行为
- 不修改 `docs/workflows/新项目开发工作流/` 之外的产品源资产
- 不做跨版本兼容审计；本次仅处理同版本 `0.5.17`

## Verification Plan

- `python3 docs/workflows/新项目开发工作流/commands/shell/test_workflow_state.py` 的相关用例
- `python3 -m unittest docs/workflows/新项目开发工作流/commands/test_workflow_installers.py`
- 必要时补充针对补丁脚本或文档契约的测试

## Technical Notes

- 审计模式采用 `workflow-audit` 的 task-based runtime 路径
- 证据模型：`source repo` vs `generated target project` baseline vs `generated target project` workflow-installed state vs `runtime command output`
