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


## Session 90: 修正新项目开发工作流的项目级需求文档门禁

**Date**: 2026-04-07
**Task**: 修正新项目开发工作流的项目级需求文档门禁
**Branch**: `main`

### Summary

统一 Brainstorm 阶段的项目级双需求文档门禁，补齐三套 CLI 适配说明，并把目标项目边界规则沉淀到 .trellis/spec。

### Main Changes

| Area | Change |
|------|--------|
| Workflow docs | 将 Brainstorm 完成后的强制门禁明确为生成目标项目的双需求文档 |
| CLI adaptation | 同步 Claude Code / Codex / OpenCode 的原生指令口径 |
| Spec capture | 在 .trellis/spec 中补充 workflow 目标项目边界与 artifact 区分规则 |
| Validation | 运行 workflow installer 测试、trellis-library 校验与 CLI 基础 help 检查 |


### Git Commits

| Hash | Message |
|------|---------|
| `8bc94aa` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 91: 工作流 trellis 兼容升级与 spec 收口

**Date**: 2026-04-08
**Task**: 工作流 trellis 兼容升级与 spec 收口
**Branch**: `main`

### Summary

(Add summary)

### Main Changes

| 模块 | 变更 |
|------|------|
| 新项目工作流 | 在 `docs/workflows/新项目开发工作流/` 内完成 Trellis 兼容升级收口，明确 `patch-based baseline / overlay baseline / added commands` 三类资产模型 |
| 命令调整 | `brainstorm` 改为基于 Trellis 原生命令的合并方案；`self-review` 并入新 `check`；旧 `check` 更名为 `review-gate` |
| 升级机制 | `upgrade-compat.py` 增加对分发命令与 helper scripts 的 source-vs-deployed 内容一致性检测，不再只做存在性检查 |
| 验证 | 补充 `test_workflow_installers.py` 与 `test_check_quality.py`，并在 `/tmp/trellis-workflow-realtest` 完成 `trellis init -> install-workflow -> upgrade-compat --check/--merge/--force` 实测回归 |
| Spec | 新增 `.trellis/spec/scripts/workflow-installer-upgrade-contracts.md`，并同步更新 `scripts/index.md`、总 `spec index` 与 `cross-layer-thinking-guide.md` |

**本次结果**:
- workflow 与文档口径统一到新的 `check -> review-gate -> finish-work` 链路
- `brainstorm` / `check` 的 Trellis 同名命令处理方式收敛为“合并”
- 当前仓库内维护 workflow 兼容升级时，纯净 Trellis 基线统一以 `/tmp + trellis init` 为参考
- 已将任务 `04-07-workflow-trellis-upgrade` 归档到 `.trellis/tasks/archive/2026-04/`


### Git Commits

| Hash | Message |
|------|---------|
| `2096576` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete
