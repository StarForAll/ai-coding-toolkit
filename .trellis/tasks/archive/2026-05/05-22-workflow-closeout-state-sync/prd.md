# 修复新项目开发工作流收尾链漂移与状态机配套合同同步

## Goal

基于 `docs/workflows/新项目开发工作流/` 的现有源资产和 `/tmp/trellis-0.5.17-1`、`/tmp/trellis-0.5.17-2` 的实际嵌入证据，修复当前工作流在强门禁状态机外围产生的真实偏移，重点收敛 close-out 链、`finish-work` 原生边界、`record-session` 相关漂移、`test-first` 阶段残留和 `workflow-state` 配套补丁的合同不一致问题。修复必须只落在 `docs/workflows/新项目开发工作流/`，并要求所有相关工作流文档、脚本、测试、说明材料同步更新，不引入新的合同冲突。

## What I already know

* 用户已经明确确认：`workflow-state.json` 作为额外状态源不是问题，应视为当前工作流的合理前提。
* 用户已经明确确认：`finish-work` 应直接复用 Trellis 原生能力，Trellis 原生负责 `archive + add_session`，当前工作流不应额外重复发明第二套终态收尾流程。
* 当前修复对象固定为 `docs/workflows/新项目开发工作流/`，不是本仓库自用 `.trellis/` 工作流。
* 分析证据应以 `/tmp/trellis-0.5.17-1`（纯 Trellis baseline）和 `/tmp/trellis-0.5.17-2`（已嵌入当前 workflow）为主。
* `docs/workflows/新项目开发工作流/commands/workflow_assets.py` 中 `COMPATIBLE_TRELLIS_VERSION = "0.5.17"`，当前 `trellis -v` 也是 `0.5.17`，所以这不是跨版本兼容审计，而是同版本工作流源自身收敛问题。
* baseline Trellis `finish-work` 的真实语义是：在 `finish-work` 内执行 `task.py archive`，再执行 `add_session.py`，不需要额外 `record-session` 阶段。
* 当前 workflow source 与嵌入结果里存在 close-out 语义分叉：
  - `finish-work-patch-projectization.md` 与嵌入后的 `finish-work` 把 close-out 改成 `finish-work -> delivery -> record-session`
  - `delivery.md` 和部分 walkthrough / 说明文档又把 close-out 写成回到 Trellis 原生 `finish-work`
  - `record-session` 被多份文档、测试、NL 路由视为正式终态入口，但当前 source `commands/` 目录里并没有 `record-session.md`，`workflow_assets.py` 的 `DISTRIBUTED_COMMANDS` 也没有它，实际嵌入结果同样未落盘该 carrier
* 强门禁状态机外围还存在两类配套漂移：
  - `workflow-state` schema 当前主字段是 `status`，但任务视图补丁仍读取过时的 `stage_status`
  - `test-first` 在《阶段状态机与强门禁协议》中已并入 `implementation`，但多个 workflow 文档、patch 文本、命令说明仍把它当独立阶段
* 已跑的仓库内测试与手工比对表明，当前至少存在 matrix / walkthrough / source contract 彼此不一致的问题。

## Assumptions (temporary)

* 当前最优修复方向不是撤回 `workflow-state.json`，而是收缩和同步其外围配套，恢复 `finish-work` 的原生边界。
* `delivery` 阶段可继续保留为验收和交付阶段，但不应再承担或改写 Trellis 原生 close-out 语义。
* `record-session` 如果保留，只能作为 legacy 兼容表述或历史升级兼容入口；不能继续作为当前 fresh baseline 主链的正式终态阶段。
* `test-first` 的最终处理应以《阶段状态机与强门禁协议》为准；若保留为显式入口，也必须与状态机主合同保持一致，不再以独立阶段口径四处扩散。

## Open Questions

* 是否需要在当前修复里彻底删去 `record-session` 的 fresh-baseline 主链表述，只保留 legacy upgrade / compatibility 语境。
* `test-first` 在当前工作流产品里的最终定位应是：
  - 完全并入 `implementation`，仅保留“测试先行模式”表述
  - 还是保留命令入口，但不作为 `workflow-state` 独立阶段
* 修复时需要判断哪些历史测试应更新为原生 `finish-work` 新口径，哪些应直接删除，避免继续为错误模型背书。

## Requirements (evolving)

* 必须保留 `workflow-state.json + workflow-state.py route` 作为当前 workflow 的阶段真相来源，不把状态机本身当作问题回退。
* 必须恢复并统一 `finish-work` 的原生边界：当前 fresh baseline 语义下，`finish-work` 负责 `archive + add_session`。
* 必须排查并修复 close-out 链相关的所有主文档、命令文档、patch 源、walkthrough、矩阵说明、安装器注释、升级检查逻辑和测试预期，避免同一主题出现多套口径。
* 必须修复 `record-session` 的合同漂移：
  - 不能继续在 fresh baseline 主链中把它描述成正式分发命令，除非 source、installer、assets、embedded result 和 tests 全部一致支持
  - 若改回原生 `finish-work` 收尾，则应把 `record-session` 收缩到 legacy / compatibility 边界
* 必须修复 `workflow-state` 配套补丁的 schema 漂移，至少包括 `status` / `stage_status` 的不一致。
* 必须修复 `test-first` 在协议与各载体之间的定位偏移，保证阶段合同唯一。
* 所有源改动必须同步更新全文档和测试，不允许只改脚本或只改某一处说明。
* 修复时必须遵循 source/deployed/target-project 三层边界，明确哪些是 source repo 文档、哪些是 installer 生成物、哪些是目标项目运行时合同。

## Acceptance Criteria (evolving)

* `docs/workflows/新项目开发工作流/` 内关于 close-out 的所有主入口文档、patch 源、walkthrough、矩阵说明与脚本注释都统一回到同一合同，不再同时存在 `finish-work -> delivery -> record-session` 和 “原生 finish-work 收尾” 两套口径。
* `finish-work` 的 source patch 和嵌入后语义不再否定原生 `archive + add_session`。
* `record-session` 的 source contract、installer deployment list、upgrade drift checks、matrix docs、walkthrough docs、tests、实际嵌入结果不再互相矛盾。
* `workflow-state` 配套补丁不再依赖过时字段名，运行时视图与 `workflow-state.json` 当前 schema 一致。
* `test-first` 的阶段/入口语义在《阶段状态机与强门禁协议》、`workflow-state.py`、workflow patch text、阶段命令文档和说明材料中保持一致。
* 修改后至少应补跑与当前修复面直接相关的测试；若部分测试当前无法通过，需要在任务说明里清楚记录阻塞原因和下一步。

## Definition of Done

* 相关 source 文件已完成修改并保持跨文档一致
* 相关测试已更新并执行到位，结果真实记录
* 新旧合同边界在任务内有清晰说明，下一对话可直接继续实现和验证
* 不把未验证成功的推测描述成“已修复”

## Out of Scope (explicit)

* 不修改 `docs/workflows/新项目开发工作流/` 之外的正式 source 目录
* 不把本仓库自用 `.trellis/` 工作流改造成和产品 workflow 一样
* 不做跨 Trellis 版本兼容升级审计
* 不在本轮直接实施用户目标项目上的真实安装/升级操作

## Technical Notes

* 关键 baseline 证据：
  - `/tmp/trellis-0.5.17-1/.claude/commands/trellis/finish-work.md`
  - `/tmp/trellis-0.5.17-1/.agents/skills/trellis-finish-work/SKILL.md`
  - `/tmp/trellis-0.5.17-1/.trellis/workflow.md`
* 关键 source 证据：
  - `docs/workflows/新项目开发工作流/commands/finish-work-patch-projectization.md`
  - `docs/workflows/新项目开发工作流/commands/delivery.md`
  - `docs/workflows/新项目开发工作流/commands/workflow-patch-projectization.md`
  - `docs/workflows/新项目开发工作流/commands/workflow_assets.py`
  - `docs/workflows/新项目开发工作流/commands/install-workflow.py`
  - `docs/workflows/新项目开发工作流/commands/upgrade-compat.py`
  - `docs/workflows/新项目开发工作流/阶段状态机与强门禁协议.md`
* 关键嵌入结果证据：
  - `/tmp/trellis-0.5.17-2/.claude/commands/trellis/finish-work.md`
  - `/tmp/trellis-0.5.17-2/.claude/commands/trellis/delivery.md`
  - `/tmp/trellis-0.5.17-2/.trellis/workflow.md`
  - `/tmp/trellis-0.5.17-2/.trellis/scripts/common/tasks.py`
  - `/tmp/trellis-0.5.17-2/.trellis/scripts/workflow/workflow-state.py`
* 关键测试入口：
  - `docs/workflows/新项目开发工作流/commands/test_workflow_installers.py`
  - `docs/workflows/新项目开发工作流/commands/shell/test_workflow_state.py`
