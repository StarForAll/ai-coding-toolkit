# 修复新项目开发工作流在目标项目中的阶段路由与降级恢复问题

## Goal

修复 `docs/workflows/新项目开发工作流` 在嵌入目标项目后仍残留的强门禁收口缺陷，使 `/tmp/trellis-0.5.17-2` 这类已嵌入项目不再同时暴露 stage/status 双真相、Codex 启动面 legacy 路由、误导性的 no-task 首次入口，以及不稳定的 degraded 恢复行为。

## What I already know

- 修复范围只允许落在 `docs/workflows/新项目开发工作流`，其他源码目录不能改。
- 分析对象是目标项目 `/tmp/trellis-0.5.17-2`，不是当前仓库正在使用的 `.trellis/`。
- 当前版本门禁通过：`trellis -v` = `0.5.17`，`COMPATIBLE_TRELLIS_VERSION` = `0.5.17`。
- 已确认的候选问题包括：
  - `workflow-state.json.stage` 与 `task.json.status` 并存为两套进度语义
  - Codex `session-start.py` 仍走 legacy READY/NOT READY 路由，且完整性检查未强制覆盖
  - `workflow-state.py route` 的 no-task 场景缺少只读分析/元审计分支
  - degraded active-task 恢复文件命名与恢复判定策略不稳定
  - 旧任务运营视图和任务生命周期代码仍持续生产/放大 legacy status

## Requirements

- 只修改 `docs/workflows/新项目开发工作流` 下的源工作流资产、补丁脚本、测试和文档。
- 先验证问题真实存在，再做修复；如果发现同类问题，一并修复。
- 对 Trellis 原生缺陷只能在工作流合适位置打补丁，供安装器嵌入目标项目时修复。
- 修复应覆盖：
  - 安装器部署逻辑
  - runtime helper / patch script
  - 完整性检查
  - 测试夹具与回归测试
  - 必要的工作流文档与维护说明
- 不引入新的路由/阶段/补丁漂移问题。

## Acceptance Criteria

- [ ] 在源工作流中，Codex `session-start` 与 `inject-workflow-state` 都纳入一致的强门禁补丁与完整性校验。
- [ ] 目标项目的 no-task route 不再把只读分析/元审计默认误导成直接进入 feasibility。
- [ ] degraded 恢复逻辑对无关旧 session 不再全局失效，文档与实现保持一致。
- [ ] 任务运营视图不再继续放大 legacy `planning/in_progress` 语义，相关展示/过滤/进度统计改为 strong-gate 友好模型。
- [ ] 补丁脚本、安装器、upgrade 检查、测试夹具和文档全部同步更新。
- [ ] 相关自动化测试通过。

## Out of Scope

- 不修改当前仓库根级 `.trellis/`、`.codex/`、`.claude/` 的实际运行实现。
- 不改动 `docs/workflows/新项目开发工作流` 之外的作者仓源码。
- 不处理与本次 5 类问题无关的新功能扩展。

## Technical Notes

- 分析基准目标项目：`/tmp/trellis-0.5.17-2`
- 关键源文件初判：
  - `commands/install-workflow.py`
  - `commands/upgrade-compat.py`
  - `commands/workflow_assets.py`
  - `commands/shell/workflow-state.py`
  - `commands/shell/patch-session-start-strong-gate.py`
  - `commands/shell/patch-task-start-strong-gate.py`
  - `commands/test_workflow_installers.py`
  - `commands/shell/test_workflow_state.py`
