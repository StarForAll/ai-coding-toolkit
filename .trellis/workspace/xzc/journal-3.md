# Journal - xzc (Part 3)

> Continuation from `journal-2.md` (archived at ~2000 lines)
> Started: 2026-04-07

---



## Session 89: 修正新项目开发工作流

**Date**: 2026-04-07
**Task**: 修正新项目开发工作流
**Branch**: `main`

### Summary

收敛新项目开发工作流的前置校验、初始 spec 导入、`finish-work` 项目化补丁、安装/卸载/升级链路，以及 3 轮 multi-cli review 闭环。

### Main Changes

| 项目 | 说明 |
|------|------|
| workflow 前置校验 | 明确目标项目必须是 Git 项目，且 `origin` 至少配置两个 push URL，并已执行 `trellis init` |
| 初始资产导入 | 安装脚本改为自动导入 `pack.requirements-discovery-foundation`，不再走手工提示安装 |
| Trellis 基线处理 | 安装后删除 `00-bootstrap-guidelines`，并对 `finish-work` 注入项目化补丁 |
| 生命周期脚本 | 补齐 `install-workflow.py`、`uninstall-workflow.py`、`upgrade-compat.py` 的多 CLI 行为与恢复链路 |
| 回归测试与文档 | 增补 installer/upgrade/uninstall 回归测试，统一 Claude Code / OpenCode / Codex 文档口径，并完成 3 轮 multi-cli review 收敛 |

**Updated Files**:
- `docs/workflows/新项目开发工作流/commands/install-workflow.py`
- `docs/workflows/新项目开发工作流/commands/uninstall-workflow.py`
- `docs/workflows/新项目开发工作流/commands/upgrade-compat.py`
- `docs/workflows/新项目开发工作流/commands/test_workflow_installers.py`
- `docs/workflows/新项目开发工作流/commands/finish-work-patch-projectization.md`
- `docs/workflows/新项目开发工作流/commands/claude/README.md`
- `docs/workflows/新项目开发工作流/commands/opencode/README.md`
- `docs/workflows/新项目开发工作流/commands/codex/README.md`
- `docs/workflows/新项目开发工作流/多CLI通用新项目完整流程演练.md`
- `docs/workflows/新项目开发工作流/命令映射.md`
- `tmp/multi-cli-review/04-07-fix-new-project-workflow/summary-round-1.md`
- `tmp/multi-cli-review/04-07-fix-new-project-workflow/summary-round-2.md`
- `tmp/multi-cli-review/04-07-fix-new-project-workflow/summary-round-3.md`
- `tmp/multi-cli-review/04-07-fix-new-project-workflow/action.md`


### Git Commits

| Hash | Message |
|------|---------|
| `8769fa2` | (see git log) |
| `9683551` | (see git log) |
| `5b2adb8` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete
