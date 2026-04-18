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

- [OK] `/ops/softwares/python/bin/python3 -m py_compile ...`
- [OK] `/ops/softwares/python/bin/python3 -m unittest discover -s docs/workflows/新项目开发工作流/commands -p 'test_*.py'`
- [OK] `/ops/softwares/python/bin/python3 trellis-library/cli.py validate --strict-warnings`

### Status

[OK] **Completed**

### Next Steps

- 等待用户确认是否按蓝图对目标项目执行实际兼容升级


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

完成新项目工作流兼容升级记录链的补全：一方面落地并验证了 `browser_bookmark_cleaner_rchiver` 的目标项目兼容升级与后续自适应修正，另一方面修复了当前 workflow source-of-truth 中的 `brainstorm` 错误示例，并把 `workflow_version` 正式接入安装/升级脚本与测试链。

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


## Session 92: 工作流目标项目兼容升级方案与结构性迁移设计

**Date**: 2026-04-09
**Task**: 工作流目标项目兼容升级方案与结构性迁移设计
**Branch**: `main`

### Summary

(Add summary)

### Main Changes

| Area | Description |
|------|-------------|
| 升级主链 | 将目标项目 workflow 升级主链收敛为 `A/B/C` 三态分析优先，`upgrade-compat.py` 仅处理低风险漂移修复 |
| 脚本调整 | 新增 `analyze-upgrade.py` 与 `workflow_assets.py`；安装、卸载、兼容修复脚本复用共享资产定义 |
| 文档补齐 | 新增《目标项目兼容升级方案指导》《结构性迁移设计》，并同步《工作流总纲》《命令映射》与 `.trellis/spec/scripts/workflow-installer-upgrade-contracts.md` |
| 回归验证 | 补充 `test_upgrade_analysis.py`，修复 `delete` 分类缺口；`py_compile`、`git diff --check`、`unittest` 均通过 |

**Key Decisions**:
- 缺失 `workflow_version / workflow_schema_version` 时按 `legacy/unknown` 处理，不阻塞当前兼容升级分析。
- 结构性迁移不是默认流程，只在兼容升级分析命中结构性 break 时进入。
- `workflow_assets.py` 作为 workflow 托管资产的单一来源，减少安装/卸载/升级脚本漂移。

**Verification**:
- `/ops/softwares/python/bin/python3 -m py_compile docs/workflows/新项目开发工作流/commands/install-workflow.py docs/workflows/新项目开发工作流/commands/uninstall-workflow.py docs/workflows/新项目开发工作流/commands/upgrade-compat.py docs/workflows/新项目开发工作流/commands/analyze-upgrade.py docs/workflows/新项目开发工作流/commands/workflow_assets.py docs/workflows/新项目开发工作流/commands/test_upgrade_analysis.py`
- `git diff --check -- .trellis/spec/scripts/workflow-installer-upgrade-contracts.md docs/workflows/新项目开发工作流`
- `/ops/softwares/python/bin/python3 -m unittest docs/workflows/新项目开发工作流/commands/test_upgrade_analysis.py docs/workflows/新项目开发工作流/commands/test_workflow_installers.py`


### Git Commits

| Hash | Message |
|------|---------|
| `a9e9c41` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 93: 分析 browser_bookmark_cleaner_rchiver 工作流兼容升级方案

**Date**: 2026-04-09
**Task**: 分析 browser_bookmark_cleaner_rchiver 工作流兼容升级方案
**Branch**: `main`

### Summary

完成兼容升级蓝图、两轮多 CLI 审查、round-2 审查命令与验证记录；本次为无关联 commit 的规划会话

### Main Changes

| 产物 | 说明 |
|------|------|
| `migration-blueprint.md` | 产出目标项目 workflow 兼容升级蓝图，补齐 source-of-truth、安装记录、语义迁移、验证与回退契约 |
| `summary-round-1.md` / `summary-round-2.md` | 汇总两轮多 reviewer 审查结论，完成去重、采纳与忽略决策 |
| `action.md` / `.processed.json` | 记录 multi-cli-review-action 执行结果与处理状态 |
| `reviewer-commands-round-2.md` | 生成第二轮 reviewer 命令包，支持复核 round-1 修订后的蓝图 |

**验证结果**

- `/ops/softwares/python/bin/python3 -m py_compile ...`：pass
- `/ops/softwares/python/bin/python3 -m unittest discover -s docs/workflows/新项目开发工作流/commands -p 'test_*.py'`：pass，`Ran 35 tests in 56.523s`，`OK`
- `/ops/softwares/python/bin/python3 trellis-library/cli.py validate --strict-warnings`：pass，仅 `2` 条 `INFO stale-related-asset`

**补充说明**

- 本次任务目标是“只做分析与可执行方案，不落地目标项目修改”，已按该边界完成。
- 由于用户明确要求忽略 commit 前置条件，本条 session 未绑定代码提交，按 planning session 记录。
- 当前剩余风险：`.opencode/package.json` 中 `@opencode-ai/plugin` 从 `1.4.0` 升到 `1.4.1` 仅做了 diff 检查，未做 Node 侧安装或构建验证。


### Git Commits

(No commits - planning session)

### Testing

- [OK] `/ops/softwares/python/bin/python3 -m py_compile ...`
- [OK] `/ops/softwares/python/bin/python3 -m unittest discover -s docs/workflows/新项目开发工作流/commands -p 'test_*.py'`
- [OK] `/ops/softwares/python/bin/python3 trellis-library/cli.py validate --strict-warnings`

### Status

[OK] **Completed**

### Next Steps

- 等待用户确认是否按蓝图对目标项目执行实际兼容升级


## Session 94: 工作流兼容升级机制补全

**Date**: 2026-04-10
**Task**: 工作流兼容升级机制补全
**Branch**: `main`

### Summary

完成新项目工作流兼容升级机制补全：在目标项目 `browser_bookmark_cleaner_rchiver` 上完成兼容升级与自适应修正，同时修复 workflow source-of-truth 中的 `brainstorm` 错误示例，并把 `workflow_version` 正式接入安装/升级脚本和测试链。

### Main Changes

| Item | Description |
|------|-------------|
| Target project compatibility | Completed browser_bookmark_cleaner_rchiver workflow compatibility upgrade and follow-up adaptive fixes |
| Source-of-truth repair | Fixed `docs/workflows/新项目开发工作流/commands/brainstorm.md` invalid `--slug <auto>` example and documented auto-slug behavior |
| Install record versioning | Added `workflow_version` write-back through workflow install/upgrade scripts with shared constant `1.1.19` |
| Validation hardening | Added latest-Trellis prerequisite handling and expanded workflow installer / upgrade tests |
| Review handling | Processed multi-review rounds, updated migration blueprint, and preserved target-project adaptive drift as an accepted exception |

**Verification**:
- `/ops/softwares/python/bin/python3 trellis-library/cli.py validate --strict-warnings`
- `/ops/softwares/python/bin/python3 -m py_compile docs/workflows/新项目开发工作流/commands/analyze-upgrade.py docs/workflows/新项目开发工作流/commands/install-workflow.py docs/workflows/新项目开发工作流/commands/upgrade-compat.py docs/workflows/新项目开发工作流/commands/workflow_assets.py docs/workflows/新项目开发工作流/commands/test_workflow_installers.py docs/workflows/新项目开发工作流/commands/test_upgrade_analysis.py`
- `/ops/softwares/python/bin/python3 -m unittest docs.workflows.新项目开发工作流.commands.test_workflow_installers docs.workflows.新项目开发工作流.commands.test_upgrade_analysis`

**Notes**:
- Accepted exception: target project keeps further adaptive edits, so downstream `upgrade-compat --check` drift can be treated as expected when judged against older deployed copies.
- Task `04-09-workflow-compat-plan-browser-bookmark-cleaner-rchiver` archived after manual commit and verification.


### Git Commits

| Hash | Message |
|------|---------|
| `9845ab6` | 工作流兼容升级机制补全 |

### Testing

- [OK] `/ops/softwares/python/bin/python3 trellis-library/cli.py validate --strict-warnings`
- [OK] `/ops/softwares/python/bin/python3 -m py_compile docs/workflows/新项目开发工作流/commands/analyze-upgrade.py docs/workflows/新项目开发工作流/commands/install-workflow.py docs/workflows/新项目开发工作流/commands/upgrade-compat.py docs/workflows/新项目开发工作流/commands/workflow_assets.py docs/workflows/新项目开发工作流/commands/test_workflow_installers.py docs/workflows/新项目开发工作流/commands/test_upgrade_analysis.py`
- [OK] `/ops/softwares/python/bin/python3 -m unittest docs.workflows.新项目开发工作流.commands.test_workflow_installers docs.workflows.新项目开发工作流.commands.test_upgrade_analysis`（`Ran 35 tests in 56.002s`, `OK`）

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 95: fix: 修正新项目开发工作流文档和脚本漂移问题

**Date**: 2026-04-11
**Task**: fix: 修正新项目开发工作流文档和脚本漂移问题
**Branch**: `main`

### Summary

(Add summary)

### Main Changes

| 变更 | 说明 |
|------|------|
| Bug fix | feasibility-check.py: TEMPLATE→ASSESSMENT_TEMPLATE 变量名修复 |
| Bug fix | metadata-autocommit-guard.py: record-session 模式不再要求 current task（archive 之后才需要） |
| 重写 | record-session-patch-metadata-closure.md: 收尾顺序改为 record-session→archive（安装器分发到目标项目的 patch 文件） |
| 文档修正 | delivery.md: Step10 主流程+底部表格收尾顺序一致化，新增 delivery-control-validate 验证 |
| 文档修正 | design.md: 必需/可选文件标注修正（AID/ODD 为可选） |
| 文档修正 | 工作流总纲、全局流转说明、命令映射、完整流程演练: 收尾顺序统一 |
| 文档修正 | claude/codex/opencode README: 部署映射表新增安装器管理列 |
| 测试 | test_workflow_installers.py: 新增 patch 内容顺序断言 |
| 新测试 | test_feasibility_check.py (10 cases), test_design_export.py (8 cases), test_delivery_control_validate.py (10 cases) |

**关键修复**:
- 收尾顺序从 archive→record-session 统一修正为 record-session→archive（跨 6+ 文件保持一致）
- 安装器分发的 patch 文件内 record-session-helper 必须在 task.py archive 之前

**验证**: 59 个测试全部通过，py_compile 全部通过


### Git Commits

| Hash | Message |
|------|---------|
| `9276d8a` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 96: 修复新项目开发工作流门禁与安装器契约

**Date**: 2026-04-12
**Task**: 修复新项目开发工作流门禁与安装器契约
**Branch**: `main`

### Summary

将新项目 main 分支门禁收敛为 workflow 首次入口判断，固定 sonar-scanner 为跨语言质量门禁，补强 install-workflow.py 失败边界与回归测试，并完成三轮 multi-cli review 收口。

### Main Changes

(Add details)

### Git Commits

| Hash | Message |
|------|---------|
| `942c5e3` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 97: 修复新项目工作流：禁用PR并新增project-audit

**Date**: 2026-04-14
**Task**: 修复新项目工作流：禁用PR并新增project-audit
**Branch**: `main`

### Summary

(Add summary)

### Main Changes

| Area | Description |
|------|-------------|
| Workflow Routing | Removed default `parallel/worktree/dispatch/create-pr` path and unified direct-in-project execution model |
| Project Audit | Added `project-audit` as a project-level final code audit stage with formal mode and manual pre-audit mode |
| Install/Upgrade | Updated installer, uninstall, upgrade, and asset registry to distribute `project-audit`, disable `parallel`, and keep install-record schema consistent |
| Planning Model | Added `任务域` to task matrix and enforced `PROJECT-AUDIT` gating in `plan-validate.py` |
| Docs | Synced main workflow docs, command mapping, CLI README files, walkthrough docs, and mindmap HTML |
| Review Loop | Processed multi-cli review rounds and folded accepted findings back into code and docs |

**Verification**:
- `/ops/softwares/python/bin/python3 docs/workflows/新项目开发工作流/commands/test_workflow_installers.py`
- `/ops/softwares/python/bin/python3 docs/workflows/新项目开发工作流/commands/test_upgrade_analysis.py`
- `/ops/softwares/python/bin/python3 docs/workflows/新项目开发工作流/commands/shell/test_plan_validate.py`
- `/ops/softwares/python/bin/python3 -m py_compile docs/workflows/新项目开发工作流/commands/install-workflow.py docs/workflows/新项目开发工作流/commands/uninstall-workflow.py docs/workflows/新项目开发工作流/commands/upgrade-compat.py docs/workflows/新项目开发工作流/commands/analyze-upgrade.py docs/workflows/新项目开发工作流/commands/workflow_assets.py docs/workflows/新项目开发工作流/commands/test_workflow_installers.py docs/workflows/新项目开发工作流/commands/test_upgrade_analysis.py docs/workflows/新项目开发工作流/commands/shell/plan-validate.py docs/workflows/新项目开发工作流/commands/shell/test_plan_validate.py`


### Git Commits

| Hash | Message |
|------|---------|
| `50a5bbd9aa8d30534d3d8778d25fcd826e47e617` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 98: 文档规则多轮修正与跨文档传播

**Date**: 2026-04-14
**Task**: 文档规则多轮修正与跨文档传播
**Branch**: `main`

### Summary

sonar-scanner条件化、L0轻量化、review-gate条件触发、record-session→archive顺序、project-audit条件生成等规则在19个文件中完成跨文档传播统一，并在spec/docs/index.md新增Workflow Rule Propagation检查清单

### Main Changes

(Add details)

### Git Commits

| Hash | Message |
|------|---------|
| `5078fce` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 99: 收敛 project-audit 与 review-gate 阶段边界

**Date**: 2026-04-14
**Task**: 收敛 project-audit 与 review-gate 阶段边界
**Branch**: `main`

### Summary

修订 docs/workflows/新项目开发工作流 中的 project-audit、review-gate、check、start phase router、命令映射、通俗版与 walkthrough 文档，完成四轮 multi-cli-review 收敛并同步记录 task/tmp/workspace 元数据。

### Main Changes

(Add details)

### Git Commits

| Hash | Message |
|------|---------|
| `3887c77` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 100: 修复新项目开发工作流 task-first 与 before-dev 主链

**Date**: 2026-04-14
**Task**: 修复新项目开发工作流 task-first 与 before-dev 主链
**Branch**: `main`

### Summary

将新项目开发工作流收敛为 Trellis task-first 主链，task_plan.md 降为摘要层，start 自动执行 before-dev 并补 task 级门禁。

### Main Changes

| 项目 | 说明 |
|------|------|
| 主链收敛 | 将 `plan -> test-first -> start` 收敛为 `plan -> start` 默认主链，`test-first` 改为手动入口 |
| task-first | `plan` 以真实 Trellis task 为主执行单元，`task_plan.md` 仅保留总览、依赖、门禁、任务图摘要 |
| before-dev | 保持 Trellis 基线语义不变，但在当前 workflow 中由 `start` 自动执行，并约定 `$TASK_DIR/before-dev.md` 为 task 级门禁快照 |
| 传播修复 | 同步更新总纲、命令映射、通俗版、walkthrough、思维导图、平台 README，避免 `task_plan.md` 旧执行矩阵语义残留 |
| 校验契约 | 重写 `plan-validate.py` 与相关单测，交付控制校验改为读取 task 图摘要；多轮 `multi-cli-review` 收敛后补齐剩余中优先级问题 |

**验证**
- `git diff --check`
- `python3 -m py_compile docs/workflows/新项目开发工作流/commands/workflow_assets.py docs/workflows/新项目开发工作流/commands/install-workflow.py docs/workflows/新项目开发工作流/commands/shell/plan-validate.py docs/workflows/新项目开发工作流/commands/shell/delivery-control-validate.py docs/workflows/新项目开发工作流/commands/shell/test_plan_validate.py docs/workflows/新项目开发工作流/commands/shell/test_delivery_control_validate.py`
- `python3 -m unittest docs.workflows.新项目开发工作流.commands.shell.test_plan_validate docs.workflows.新项目开发工作流.commands.shell.test_delivery_control_validate`
- `python3 trellis-library/cli.py validate --strict-warnings`
- `python3 -m unittest trellis-library/tests/test_cli.py`
- `python3 trellis-library/cli.py --help`
- `python3 trellis-library/cli.py validate --help`
- `python3 trellis-library/cli.py assemble --help`
- `python3 trellis-library/cli.py sync --help`

**任务处理**
- 已归档：`04-14-workflow-plan-test-first-fix`
- 多 CLI 审查目录：`tmp/multi-cli-review/04-14-workflow-plan-test-first-fix/`
- 收敛状态：第 4 轮后无中高优先级残余问题，剩余仅低优先级文档润色项


### Git Commits

| Hash | Message |
|------|---------|
| `d773ca2` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 101: 当前项目补充 record-session 自动提交失败恢复机制

**Date**: 2026-04-14
**Task**: 当前项目补充 record-session 自动提交失败恢复机制
**Branch**: `main`

### Summary

将当前项目实际生效的隐藏目录工作流 record-session 链路切换到 helper，并补齐只读/受限写入失败后的 resume 恢复机制。

### Main Changes

| 项目 | 说明 |
|------|------|
| 运行态 helper | 新增 `.trellis/scripts/workflow/record-session-helper.py`，将 record-session 收敛为 pre-check → add_session.py --no-commit → metadata commit-only → post-check |
| 元数据守卫 | 新增 `.trellis/scripts/workflow/metadata-autocommit-guard.py`，负责 record-session 的 pre/post 检查与 metadata commit-only |
| 实际入口切换 | 将 `.claude/commands/trellis/record-session.md`、`.opencode/commands/trellis/record-session.md`、`.agents/skills/record-session/SKILL.md` 从直接调用 `add_session.py` 改为统一调用 helper |
| 失败恢复 | helper 在检测到只读文件系统、权限错误、`.git/index.lock` 等写入失败时，输出 `--resume` 恢复命令，而不是要求整条 record-session 重跑 |
| pending 修复 | 修正 pending 状态文件落点，改为 `.trellis/.pending-record-session/`，避免恢复后污染 `.trellis/workspace` |
| 实际演练 | 完成成功链路与只读失败+resume 链路两组临时仓库 smoke test，确认 helper/resume 在当前项目运行态可用 |

**验证**
- `python3 -m py_compile .trellis/scripts/workflow/record-session-helper.py .trellis/scripts/workflow/metadata-autocommit-guard.py`
- `python3 .trellis/scripts/workflow/record-session-helper.py --help`
- `python3 .trellis/scripts/workflow/metadata-autocommit-guard.py --help`
- 临时仓库 1：正常成功链路，session 写入 + metadata commit-only + post-check 全部通过
- 临时仓库 2：将 `.git` 调整为只读后触发失败，正确生成 `.trellis/.pending-record-session/*.pending.json` 与 `--resume` 命令；恢复可写后 `--resume` 成功提交并清理 pending 文件

**任务处理**
- 已归档：`04-14-record-session-escalation-analysis`
- 落地对象：当前项目隐藏目录中的实际生效工作流资产，而非 `docs/workflows/新项目开发工作流/` 源文档


### Git Commits

| Hash | Message |
|------|---------|
| `6a37368` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 102: 修复 task archive 自动提交缺口

**Date**: 2026-04-14
**Task**: 修复 task archive 自动提交缺口
**Branch**: `main`

### Summary

修复 task.py archive 在自动提交失败时仍返回成功的问题，确保归档后的 .trellis/tasks 元数据能正确进入后续 record-session 闭环。

### Main Changes

| 项目 | 说明 |
|------|------|
| 问题定位 | 归档 `04-14-record-session-escalation-analysis` 后，`.trellis/tasks` 仍然 dirty，导致新的 `record-session-helper.py` pre-check 正常阻断后续记录 |
| 根因 | `.trellis/scripts/common/task_store.py` 中 `_auto_commit_archive()` 忽略 `git add` 失败，`cmd_archive()` 也不根据自动提交结果返回失败 |
| 修复内容 | 将 `_auto_commit_archive()` 改为返回 `bool`，在 `git add` / `git commit` 失败时明确返回 `False`；`cmd_archive()` 在自动提交失败时返回非零，而不是表面归档成功 |
| 行为验证 | 先在当前仓库手动验证 `git add -A .trellis/tasks` 能把归档识别为 rename，再通过内部自动提交流程生成 `chore(task): archive 04-14-record-session-escalation-analysis`，最终解除 record-session pre-check 阻断 |
| 效果 | 当前项目实际生效的 record-session helper + resume 机制，终于能与 task archive 自动提交链路闭环配合 |

**验证**
- `python3 -m py_compile .trellis/scripts/common/task_store.py`
- 手工验证：`git add -A .trellis/tasks` 后，归档变更被正确识别为 rename
- 内部自动提交流程成功提交：`2b167d1 chore(task): archive 04-14-record-session-escalation-analysis`
- 后续 `record-session-helper.py` 恢复执行成功，说明归档链路阻断已解除

**说明**
- 这次记录的是后续补出的 archive 自动提交修复，因此单独对应 commit `d16e572`
- 当前项目运行态的 record-session helper/guard 机制已在前一条 session 中记录，本次只补充 archive 链路修复


### Git Commits

| Hash | Message |
|------|---------|
| `d16e572` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 103: 修复新项目开发工作流设计阶段与前端视觉边界

**Date**: 2026-04-15
**Task**: 修复新项目开发工作流设计阶段与前端视觉边界
**Branch**: `main`

### Summary

完成新项目开发工作流的设计阶段文档矩阵收口、Codex 前端视觉禁区约束、Stitch Prompt 固定模板与 design-export 校验增强，并通过 4 轮 multi-cli-review 收敛后归档本次 brainstorm 任务

### Main Changes

(Add details)

### Git Commits

| Hash | Message |
|------|---------|
| `c76a4e1` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 104: 强化新项目工作流强门禁状态机

**Date**: 2026-04-15
**Task**: 强化新项目工作流强门禁状态机
**Branch**: `main`

### Summary

将新项目工作流收敛为强门禁阶段状态机，新增 workflow-state helper 与测试，重写 phase router 与 design 阶段规则，并完成多轮多 CLI 审查收敛。

### Main Changes

(Add details)

### Git Commits

| Hash | Message |
|------|---------|
| `2a6b3b3` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 105: 修复新项目开发工作流 design-plan 阶段边界

**Date**: 2026-04-16
**Task**: 修复新项目开发工作流 design-plan 阶段边界
**Branch**: `main`

### Summary

收紧 design/UI 原型参考资产边界与 plan 纯规划态门禁，补齐 execution_authorized 状态机传播、helper 校验与回归测试，并完成两轮 multi-cli review 收敛。

### Main Changes

| Area | Outcome |
|------|---------|
| Design boundary | 明确 UI 原型仅为参考资产，禁止直接带入正式实现 |
| Plan boundary | 明确 plan 只做任务拆分/规划，禁止生成基础代码或进入具体实现 |
| State machine | 新增并传播 `execution_authorized` 门禁，阻断未确认的 plan -> implementation/test-first 跃迁 |
| Helper/tests | `workflow-state.py` 拒绝非法执行态写入，`test_workflow_state.py` 扩展到 13 条测试 |
| Review closure | 两轮 `multi-cli-review-action` 收敛；第 2 轮无新增问题并提前关闭 |

**Updated Source Files**:
- `docs/workflows/新项目开发工作流/阶段状态机与强门禁协议.md`
- `docs/workflows/新项目开发工作流/commands/design.md`
- `docs/workflows/新项目开发工作流/commands/plan.md`
- `docs/workflows/新项目开发工作流/commands/test-first.md`
- `docs/workflows/新项目开发工作流/commands/start-patch-phase-router.md`
- `docs/workflows/新项目开发工作流/commands/shell/workflow-state.py`
- `docs/workflows/新项目开发工作流/commands/shell/test_workflow_state.py`
- `docs/workflows/新项目开发工作流/工作流总纲.md`
- `docs/workflows/新项目开发工作流/工作流全局流转说明（通俗版）.md`
- `docs/workflows/新项目开发工作流/命令映射.md`
- `docs/workflows/新项目开发工作流/多CLI通用新项目完整流程演练.md`
- `docs/workflows/新项目开发工作流/CLI原生适配边界矩阵.md`
- `docs/workflows/新项目开发工作流/commands/claude/README.md`
- `docs/workflows/新项目开发工作流/commands/opencode/README.md`
- `docs/workflows/新项目开发工作流/commands/codex/README.md`
- `docs/workflows/新项目开发工作流/工作流思维导图.html`

**Verification**:
- `git diff --check`
- `/ops/softwares/python/bin/python3 -m py_compile docs/workflows/新项目开发工作流/commands/shell/workflow-state.py docs/workflows/新项目开发工作流/commands/shell/test_workflow_state.py`
- `/ops/softwares/python/bin/python3 docs/workflows/新项目开发工作流/commands/shell/test_workflow_state.py` (`13 tests`, `OK`)


### Git Commits

| Hash | Message |
|------|---------|
| `83a9cf7` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 106: 让自动任务状态变更一起自动提交

**Date**: 2026-04-16
**Task**: 让自动任务状态变更一起自动提交
**Branch**: `main`

### Summary

修复任务归档自动提交范围，让 .trellis/.current-task 与 .trellis/tasks 一起进入自动 metadata commit，并补归档回归测试。

### Main Changes

| Area | Outcome |
|------|---------|
| Archive auto-commit | 归档自动提交范围从仅 `.trellis/tasks` 扩展到同时包含 `.trellis/.current-task` |
| Runtime behavior | 归档当前任务时，自动清理当前任务指针的变更会与任务归档一起进入同一条 metadata commit |
| Regression test | 新增归档自动提交回归测试，验证 `.trellis/tasks` 与 `.trellis/.current-task` 会一起被提交 |

**Updated Files**:
- `.trellis/scripts/common/task_store.py`
- `.trellis/scripts/common/tests/test_task_store_archive_autocommit.py`
- `.trellis/tasks/04-16-auto-commit-task-state/prd.md`

**Verification**:
- `git diff --check -- .trellis/scripts/common/task_store.py .trellis/scripts/common/tests/test_task_store_archive_autocommit.py .trellis/tasks/04-16-auto-commit-task-state/prd.md`
- `/ops/softwares/python/bin/python3 -m py_compile .trellis/scripts/common/task_store.py .trellis/scripts/common/tests/test_task_store_archive_autocommit.py`
- `/ops/softwares/python/bin/python3 .trellis/scripts/common/tests/test_task_store_archive_autocommit.py` (`1 test`, `OK`)


### Git Commits

| Hash | Message |
|------|---------|
| `9fcb49c` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 107: 修复新项目开发工作流门禁与任务说明

**Date**: 2026-04-16
**Task**: 修复新项目开发工作流门禁与任务说明
**Branch**: `main`

### Summary

收紧 feasibility 阶段门禁、前置法律风险分析、补充任务说明卡并完成多 CLI 审查闭环

### Main Changes

| 变更主题 | 内容 |
|---------|------|
| Feasibility 门禁 | 首次进入 workflow 必经 feasibility；已存在且仍有效的 assessment 可复用但不算跳过 |
| 法律风险分析 | 调整为 feasibility 起始硬门禁，并补充 assessment 校验项 |
| 任务说明卡 | 在 plan -> start 交接处增加并绑定“当前推荐执行任务（待确认）”说明卡 |
| 文档与安装器传播 | 同步更新总纲、命令映射、walkthrough、AGENTS 路由与思维导图 |
| 多 CLI 审查 | 完成 round 1 / round 2 汇总，收口低优先级一致性问题 |

**关键文件**:
- `docs/workflows/新项目开发工作流/commands/feasibility.md`
- `docs/workflows/新项目开发工作流/commands/brainstorm.md`
- `docs/workflows/新项目开发工作流/commands/plan.md`
- `docs/workflows/新项目开发工作流/commands/start-patch-phase-router.md`
- `docs/workflows/新项目开发工作流/commands/install-workflow.py`
- `docs/workflows/新项目开发工作流/commands/shell/feasibility-check.py`
- `docs/workflows/新项目开发工作流/工作流总纲.md`
- `docs/workflows/新项目开发工作流/多CLI通用新项目完整流程演练.md`

**验证**:
- `python3 -m unittest docs.workflows.新项目开发工作流.commands.shell.test_feasibility_check docs.workflows.新项目开发工作流.commands.shell.test_plan_validate docs.workflows.新项目开发工作流.commands.test_workflow_installers`
- `python3 trellis-library/cli.py validate --strict-warnings`
- `python3 -m unittest trellis-library/tests/test_cli.py`
- `/tmp` 目标项目 `trellis init` + `install-workflow.py` 端到端安装验证


### Git Commits

| Hash | Message |
|------|---------|
| `b962127` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 108: 修复 archive auto-commit pathspec 失败

**Date**: 2026-04-16
**Task**: 修复 archive auto-commit pathspec 失败
**Branch**: `main`

### Summary

修复 task archive 在 .current-task 已不存在时 git add pathspec 失败的问题，并补回归测试

### Main Changes

| 变更主题 | 内容 |
|---------|------|
| 根因修复 | `_auto_commit_archive()` 只对存在或已被 Git 跟踪的 metadata 路径执行 `git add -A -- ...`，避免 `.trellis/.current-task` 缺失时 pathspec 失败 |
| 回归测试 | 新增“`.current-task` 从未存在也能成功 archive auto-commit”的测试场景 |
| 影响范围 | 归档任务时的 metadata auto-commit 更稳，不再因已删除的 `.current-task` 路径失败 |

**关键文件**:
- `.trellis/scripts/common/task_store.py`
- `.trellis/scripts/common/tests/test_task_store_archive_autocommit.py`

**验证**:
- `/ops/softwares/python/bin/python3 .trellis/scripts/common/tests/test_task_store_archive_autocommit.py`
- `git diff --check -- .trellis/scripts/common/task_store.py .trellis/scripts/common/tests/test_task_store_archive_autocommit.py`


### Git Commits

| Hash | Message |
|------|---------|
| `57f1897` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 109: 明确 workflow 对 Trellis 基线 close-out 的依赖边界

**Date**: 2026-04-16
**Task**: 明确 workflow 对 Trellis 基线 close-out 的依赖边界
**Branch**: `main`

### Summary

补充新项目开发工作流对 Trellis 基线 archive 行为的依赖说明，并同步到总纲、矩阵、安装器与平台 README

### Main Changes

| 变更主题 | 内容 |
|---------|------|
| 分层边界 | 明确 `record-session` 会被 workflow 增强，但 `archive` 仍直接调用目标项目 Trellis 基线 `task.py` |
| 安装前提 | 补充说明：目标项目最好先升级到当前最新 Trellis，否则 close-out 仍可能继承旧基线 archive bug |
| 单一事实源 | 将该依赖补入 `CLI原生适配边界矩阵.md` 的“收尾基线依赖”小节 |
| 平台传播 | 同步更新 `claude/opencode/codex` README、通用 walkthrough、总纲、delivery 与 record-session patch 说明 |

**关键文件**:
- `docs/workflows/新项目开发工作流/工作流总纲.md`
- `docs/workflows/新项目开发工作流/多CLI通用新项目完整流程演练.md`
- `docs/workflows/新项目开发工作流/CLI原生适配边界矩阵.md`
- `docs/workflows/新项目开发工作流/commands/install-workflow.py`
- `docs/workflows/新项目开发工作流/commands/delivery.md`
- `docs/workflows/新项目开发工作流/commands/record-session-patch-metadata-closure.md`
- `docs/workflows/新项目开发工作流/commands/claude/README.md`
- `docs/workflows/新项目开发工作流/commands/opencode/README.md`
- `docs/workflows/新项目开发工作流/commands/codex/README.md`

**验证**:
- `/ops/softwares/python/bin/python3 -m py_compile docs/workflows/新项目开发工作流/commands/install-workflow.py`
- `git diff --check -- docs/workflows/新项目开发工作流/...`
- `rg -n "archive 仍直接|当前最新 Trellis 基线|收尾基线依赖" docs/workflows/新项目开发工作流/...`


### Git Commits

| Hash | Message |
|------|---------|
| `d97d712` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 110: 工作流补充项目级水印

**Date**: 2026-04-17
**Task**: 工作流补充项目级水印
**Branch**: `main`

### Summary

为新项目开发工作流补充源码水印与归属证明链，新增校验脚本、回归测试，并完成多轮 reviewer 收敛。

### Main Changes

| Area | Description |
|------|-------------|
| Workflow docs | 将源码水印与归属证明链纳入 feasibility/design/plan/delivery、总纲、命令映射、通俗版、walkthrough 与三套平台 README |
| Validator | 新增 `ownership-proof-validate.py`，校验水印策略冻结、设计计划、任务拆分与交付证明 |
| Tests | 新增并扩充 `test_ownership_proof_validate.py`，同步更新 `test_workflow_installers.py` 覆盖 helper 分发与安装记录 |
| Review closure | 连续完成 round-1 到 round-4 的多 CLI 审查汇总，收敛 validator 行为、文档口径与测试保护 |

**Updated Files**:
- `docs/workflows/新项目开发工作流/commands/feasibility.md`
- `docs/workflows/新项目开发工作流/commands/design.md`
- `docs/workflows/新项目开发工作流/commands/plan.md`
- `docs/workflows/新项目开发工作流/commands/delivery.md`
- `docs/workflows/新项目开发工作流/commands/install-workflow.py`
- `docs/workflows/新项目开发工作流/commands/workflow_assets.py`
- `docs/workflows/新项目开发工作流/commands/test_workflow_installers.py`
- `docs/workflows/新项目开发工作流/commands/shell/ownership-proof-validate.py`
- `docs/workflows/新项目开发工作流/commands/shell/test_ownership_proof_validate.py`
- `docs/workflows/新项目开发工作流/工作流总纲.md`
- `docs/workflows/新项目开发工作流/命令映射.md`
- `docs/workflows/新项目开发工作流/工作流全局流转说明（通俗版）.md`
- `docs/workflows/新项目开发工作流/多CLI通用新项目完整流程演练.md`
- `docs/workflows/新项目开发工作流/完整流程演练.md`
- `docs/workflows/新项目开发工作流/CLI原生适配边界矩阵.md`
- `docs/workflows/新项目开发工作流/源码水印与归属证据链执行卡.md`


### Git Commits

| Hash | Message |
|------|---------|
| `be1431f` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 111: 工作流补充项目总工时估算

**Date**: 2026-04-17
**Task**: 工作流补充项目总工时估算
**Branch**: `main`

### Summary

为新项目开发工作流补充不可跳过的项目总工时粗估门禁，并完成两轮 multi-cli 审查收敛。

### Main Changes

| Area | Description |
|------|-------------|
| Workflow | 将项目级粗估前移到 brainstorm 收口，并通过 workflow-state.py 将 design 及后续阶段门禁硬化 |
| Validation | 补充 workflow-state 回归测试，覆盖 brainstorm、L0 implementation、test-first 等关键路径 |
| Review | 完成两轮 multi-cli review，收敛误伤 brainstorm、L0 门禁歧义、传播清单遗漏、test-first 文档缺口等问题 |

**Verification**:
- `/ops/softwares/python/bin/python3 -m py_compile docs/workflows/新项目开发工作流/commands/shell/workflow-state.py docs/workflows/新项目开发工作流/commands/shell/test_workflow_state.py`
- `/ops/softwares/python/bin/python3 -m unittest docs.workflows.新项目开发工作流.commands.shell.test_workflow_state docs.workflows.新项目开发工作流.commands.shell.test_plan_validate docs.workflows.新项目开发工作流.commands.shell.test_feasibility_check`
- `git diff --check`

**Commit**:
- `8f4dbc7 工作流补充项目总工时估算`


### Git Commits

| Hash | Message |
|------|---------|
| `8f4dbc7` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 112: 工作流补充外包项目门禁与版本治理

**Date**: 2026-04-17
**Task**: 工作流补充外包项目门禁与版本治理
**Branch**: `main`

### Summary

补充外包项目类别判断、开工款与最终移交门禁，统一预正式 workflow 版本规则到 0.1.24，并完成两轮 multi-cli review 收敛。

### Main Changes

(Add details)

### Git Commits

| Hash | Message |
|------|---------|
| `f3805c1` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 113: 工作流兼容升级链修正

**Date**: 2026-04-17
**Task**: 工作流兼容升级链修正
**Branch**: `main`

### Summary

(Add summary)

### Main Changes

| Area | Outcome |
|------|---------|
| Workflow upgrade chain | 修复 `analyze-upgrade.py`、`upgrade-compat.py`、`workflow_assets.py` 在 Codex 多 skills 目录场景下的分析与修复一致性 |
| Install record schema | 补齐 `workflow_schema_version`、`bootstrap_cleanup_status` 等记录字段的实现与契约同步 |
| Tests | 新增并通过 workflow 安装/升级分析相关回归测试，完整运行 `test_workflow_installers` 与 `test_upgrade_analysis` |
| Multi-review closeout | 完成 3 轮 `multi-cli-review` / `multi-cli-review-action` 收敛，第三轮判定剩余问题均为低优先级说明项并关闭审查 |

**Summary**:
- 修正 `docs/workflows/新项目开发工作流` 的安装、升级兼容与多 CLI 文档口径漂移
- 补强 Codex 多目录 skills 的 install / merge / force / analyze 行为一致性
- 同步 `.trellis/spec/scripts/workflow-installer-upgrade-contracts.md` 契约
- 运行 workflow 相关测试 47 项通过、trellis-library CLI/测试通过


### Git Commits

| Hash | Message |
|------|---------|
| `52a983a` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 114: workflow: absorb target-project strengths into source workflow

**Date**: 2026-04-18
**Task**: workflow: absorb target-project strengths into source workflow
**Branch**: `main`

### Summary

Strengthened workflow source contracts, added shared .trellis/workflow.md patching across install/uninstall/upgrade/analyze paths, synchronized propagation docs, processed multi-cli review rounds, and verified with trellis-library validation, CLI tests, py_compile, and 45 workflow installer tests.

### Main Changes

(Add details)

### Git Commits

| Hash | Message |
|------|---------|
| `2a72162` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 115: 当前项目 Trellis 版本升级

**Date**: 2026-04-18
**Task**: 当前项目 Trellis 版本升级
**Branch**: `main`

### Summary

升级当前项目实际使用的 Trellis 基线与入口：同步 record-session 元数据闭环顺序，优化 session-start hooks 为 workflow 索引注入，更新状态栏编码处理、CLI adapter 平台支持与根目录 workflow 收尾说明，并完成 check/finish-work 验证。

### Main Changes

(Add details)

### Git Commits

| Hash | Message |
|------|---------|
| `73397c4` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 116: 工作流与 Trellis 0.4.0 兼容升级

**Date**: 2026-04-18
**Task**: 工作流与 Trellis 0.4.0 兼容升级
**Branch**: `main`

### Summary

验证并修复 docs/workflows/新项目开发工作流 在 Trellis 0.4.0 初始化目标项目中的嵌入兼容性，补齐 Codex start skill Phase Router 补丁、schema v2 安装记录、legacy 兼容、目标项目路径清理、feasibility 首次任务目录流程、plan-validate help 行为，以及多轮 multi-cli-review 记录与测试覆盖。

### Main Changes

(Add details)

### Git Commits

| Hash | Message |
|------|---------|
| `19b16ec` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 117: 工作流补充 trellis 原生 subagent 能力

**Date**: 2026-04-18
**Task**: 工作流补充 trellis 原生 subagent 能力
**Branch**: `main`

### Summary

(Add summary)

### Main Changes

| Area | Summary |
|------|---------|
| Workflow model | 明确当前 workflow 不采用 Trellis 原生 `plan / dispatch agent`，并将 `research -> implement -> check-agent` 定义为 implementation 内部链 |
| Managed agents | 将 Claude / OpenCode / Codex 的 `research` / `implement` / `check` 纳入 workflow 兼容治理，新增 workflow source-of-truth agent 文件并接入 install / uninstall / upgrade / analyze 链路 |
| Codex parity | 将 Codex `check.toml` 对齐为 workspace-write 的可修复 check-agent，并保留 hooks / config 为 verify-only 边界 |
| Research rules | 统一 research agent 外部搜索能力：外部技术搜索优先 `exa`，第三方库 / 框架 / SDK 文档必须先 `Context7`，无官方文档证据时必须标记 `[Evidence Gap]` |
| Verification | 补齐 upgrade-analysis、installer、uninstall、round-1/2 reviewer 修复对应的回归测试，并验证通过 |

**Updated Files**:
- `.trellis/spec/scripts/workflow-installer-upgrade-contracts.md`
- `docs/workflows/新项目开发工作流/commands/workflow_assets.py`
- `docs/workflows/新项目开发工作流/commands/install-workflow.py`
- `docs/workflows/新项目开发工作流/commands/uninstall-workflow.py`
- `docs/workflows/新项目开发工作流/commands/analyze-upgrade.py`
- `docs/workflows/新项目开发工作流/commands/upgrade-compat.py`
- `docs/workflows/新项目开发工作流/commands/test_upgrade_analysis.py`
- `docs/workflows/新项目开发工作流/commands/test_workflow_installers.py`
- `docs/workflows/新项目开发工作流/commands/claude/README.md`
- `docs/workflows/新项目开发工作流/commands/opencode/README.md`
- `docs/workflows/新项目开发工作流/commands/codex/README.md`
- `docs/workflows/新项目开发工作流/CLI原生适配边界矩阵.md`
- `docs/workflows/新项目开发工作流/命令映射.md`
- `docs/workflows/新项目开发工作流/工作流总纲.md`
- `docs/workflows/新项目开发工作流/工作流全局流转说明（通俗版）.md`
- `docs/workflows/新项目开发工作流/多CLI通用新项目完整流程演练.md`
- `docs/workflows/新项目开发工作流/目标项目兼容升级方案指导.md`
- `docs/workflows/新项目开发工作流/commands/check.md`
- `docs/workflows/新项目开发工作流/commands/start-patch-phase-router.md`
- `docs/workflows/新项目开发工作流/commands/start-skill-patch-phase-router.md`
- `docs/workflows/新项目开发工作流/commands/claude/agents/research.md`
- `docs/workflows/新项目开发工作流/commands/claude/agents/implement.md`
- `docs/workflows/新项目开发工作流/commands/claude/agents/check.md`
- `docs/workflows/新项目开发工作流/commands/opencode/agents/research.md`
- `docs/workflows/新项目开发工作流/commands/opencode/agents/implement.md`
- `docs/workflows/新项目开发工作流/commands/opencode/agents/check.md`
- `docs/workflows/新项目开发工作流/commands/codex/agents/research.toml`
- `docs/workflows/新项目开发工作流/commands/codex/agents/implement.toml`
- `docs/workflows/新项目开发工作流/commands/codex/agents/check.toml`

**Validation**:
- `/ops/softwares/python/bin/python3 -m py_compile docs/workflows/新项目开发工作流/commands/workflow_assets.py docs/workflows/新项目开发工作流/commands/install-workflow.py docs/workflows/新项目开发工作流/commands/uninstall-workflow.py docs/workflows/新项目开发工作流/commands/upgrade-compat.py docs/workflows/新项目开发工作流/commands/analyze-upgrade.py docs/workflows/新项目开发工作流/commands/test_workflow_installers.py docs/workflows/新项目开发工作流/commands/test_upgrade_analysis.py`
- `/ops/softwares/python/bin/python3 -m unittest docs.workflows.新项目开发工作流.commands.test_upgrade_analysis`
- `/ops/softwares/python/bin/python3 docs/workflows/新项目开发工作流/commands/test_workflow_installers.py`

**Follow-up**:
- 新建后续子任务：`04-18-agents-source-workflow-convergence`，仅落盘 PRD，未开始实现


### Git Commits

| Hash | Message |
|------|---------|
| `aaa20b4` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete
