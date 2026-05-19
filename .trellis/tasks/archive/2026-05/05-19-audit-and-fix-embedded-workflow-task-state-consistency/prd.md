# 修复嵌入式工作流任务状态一致性与降级恢复缺口

## Goal

基于 `docs/workflows/新项目开发工作流/` 源资产，核实你列出的任务状态机/文档漂移/回归缺口问题哪些在当前工作流中仍真实存在，并只在该工作流目录内做补丁式修复，使后续嵌入到目标项目时行为一致、可恢复、且不引入新的状态分裂问题。

## What I already know

* 当前仓库的 workflow 版本锚点是 `docs/workflows/新项目开发工作流/commands/workflow_assets.py` 中的 `COMPATIBLE_TRELLIS_VERSION = 0.5.17`，本机 `trellis -v` 也是 `0.5.17`，版本门禁通过。
* `/tmp/trellis-0.5.17-2` 并非已完成嵌入的纯净样本：缺少 `.trellis/workflow-installed.json`，`.trellis/workflow.md` 仍是 Trellis 基线三阶段内容，`.claude/commands/trellis/continue.md` 仍是旧 status 路由，说明它最多能证明 `trellis init` 基线/bootstrap 残留问题，不能直接代表“安装当前 workflow 后”的真实运行态。
* 源工作流已经包含以下前序修复资产：
  * `commands/shell/patch-task-start-strong-gate.py`
  * `commands/shell/patch-session-start-strong-gate.py`
  * `commands/shell/patch-task-create-preserve-active.py`
  * `commands/start-patch-phase-router.md`
  * `commands/install-workflow.py` 中对应补丁接入
  * `commands/test_workflow_installers.py` 中已有 bootstrap 清理、phase-router、补丁接入相关测试
* 仍看到一条未闭合缺口：`workflow-patch-projectization.md` 已声明“degraded mode 下 `task.py start` 必须留下 `.trellis/.runtime/degraded-active-task.json` 供恢复”，但当前 `patch-task-start-strong-gate.py` 只处理 `workflow-state.json` 存在时跳过 status flip，并未给 `task.py` 增加 degraded fallback 持久化能力。
* `/tmp/trellis-0.5.17-2/.trellis/scripts/task.py` 仍会在无 session identity 时把 `planning -> in_progress`，这证明 Trellis 基线本身存在降级分裂状态风险；当前工作流若要在目标项目修补该问题，只能通过安装器补丁路径实现，不能改 Trellis 原生源码。

## Assumptions

* 修复范围严格限定在 `docs/workflows/新项目开发工作流/`，不改仓库其他目录。
* 允许通过安装器补丁目标项目 Trellis 基线脚本来修复 Trellis 原生缺口。
* 若某候选问题已被当前工作流覆盖，则不再重复修“旧问题本身”，而是只补剩余漂移、文档误导或缺失测试。

## Confirmed / Suspected Issues

1. 已确认：强门禁 no-task 文档要求 degraded `task.py start` 留下 recoverable fallback，但实际补丁未实现，文档与脚本不一致。
2. 已确认：当前工作流缺少覆盖 degraded fallback 行为的安装器/补丁回归测试。
3. 待复核：是否还有其他文档或安装器断言仍把“无 session identity 时 start 会失败”当成当前嵌入后语义。
4. 待复核：是否还有同类“强门禁文档已更新，但实际 patch / test 未跟上”的位置。

## Requirements

* 只修真实存在且可由当前 workflow 源资产负责的问题。
* 优先修复“文档承诺了可恢复降级路径，但补丁未实现”的真实断链。
* 若存在同类遗漏，连带一并修复。
* 保持 installer、patch 脚本、源文档、测试断言一致。

## Acceptance Criteria

* [ ] `patch-task-start-strong-gate.py` 在无 session identity 的 degraded `task.py start` 路径下，能为目标项目写入可恢复的 fallback 记录，并避免强门禁任务继续制造不可恢复的“status in_progress + no current task”分裂状态。
* [ ] `install-workflow.py` 继续正确接入该补丁，不引入新的路径/兼容问题。
* [ ] 相关源文档表述与补丁真实行为一致。
* [ ] 至少补齐针对该行为的自动化测试。
* [ ] 相关验证命令在本仓库中可运行并给出真实结果。

## Out of Scope

* 直接修改 `/tmp/trellis-0.5.17-2` 或当前仓库根 `.trellis/` 基线源码。
* 修改 `docs/workflows/新项目开发工作流/` 之外的任何源目录。
* 对用户列出的每个历史问题都机械性重复修补，即使它已被当前 workflow 覆盖。

## Technical Notes

* 主要证据文件：
  * `docs/workflows/新项目开发工作流/commands/install-workflow.py`
  * `docs/workflows/新项目开发工作流/commands/workflow-patch-projectization.md`
  * `docs/workflows/新项目开发工作流/commands/shell/patch-task-start-strong-gate.py`
  * `docs/workflows/新项目开发工作流/commands/test_workflow_installers.py`
  * `/tmp/trellis-0.5.17-2/.trellis/scripts/task.py`
  * `/tmp/trellis-0.5.17-2/.trellis/workflow.md`
* `/tmp/trellis-0.5.17-2` 当前更适合作为“Treillis init 基线/残留现场”证据，而不是“当前 workflow 已嵌入完成后的结果”证据。
