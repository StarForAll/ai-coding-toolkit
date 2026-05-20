# 修复 runtime patch helper 合同与安装记录不对齐

## 背景

`/tmp/trellis-0.5.17-2/WORKFLOW_QUESTIONS.md` 报告 `critical_runtime_patches`
中存在 `task-status-view-strong-gate` 与 `workflow-phase-strong-gate` 两个
关键补丁名，但目标项目磁盘上没有同名 helper script 文件。

复核后确认：

- 目标项目真实运行行为并非完全缺失补丁
- 问题在于 workflow source 把这两个补丁能力名写进 install record /
  validator / tests
- 但 source 只分发了 `patch-workflow-phase.py` 这个 helper，而
  `task-status-view-strong-gate` 仍直接内嵌在 installer/upgrade 逻辑中

这会让 scan 把“合同命名与 helper 载体不一致”误判成 P0 缺失。

## 目标

在不改变目标项目既有强门禁行为的前提下，把 runtime patch 能力名与
workflow source 实际分发的 helper script 载体重新对齐，消除该类误报。

## 范围

- `docs/workflows/新项目开发工作流/commands/workflow_assets.py`
- `docs/workflows/新项目开发工作流/commands/install-workflow.py`
- `docs/workflows/新项目开发工作流/commands/upgrade-compat.py`
- `docs/workflows/新项目开发工作流/commands/shell/*.py`
- 相关回归测试

## 非目标

- 不重命名 `trellis-spec-bootstarp`
- 不清理 `.backup-original/`
- 不调整 Codex `SessionStart` 合同
