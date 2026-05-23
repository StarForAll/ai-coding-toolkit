# audit and fix workflow patch field mapping and related issues

## Goal

针对 `docs/workflows/新项目开发工作流/` 做同版本维护审计，基于 `/tmp/trellis-0.5.17-2` 这个已 `trellis init` 且已嵌入工作流的目标项目，确认候选问题是否真实存在；若存在，则在用户确认后仅修改 `docs/workflows/新项目开发工作流/` 内的源资产，修复安装后目标项目中的真实行为缺陷，并尽量一起修复同类问题。

## What I already know

* 兼容锚点版本来自 `docs/workflows/新项目开发工作流/commands/workflow_assets.py`：`COMPATIBLE_TRELLIS_VERSION = "0.5.17"`
* 当前运行时 `trellis -v` 为 `0.5.17`，版本门禁通过
* `/tmp/trellis-0.5.17-2/.trellis/tasks/05-23-test-task-2/workflow-state.json` 使用新字段 `status: "in_progress"`，没有 `stage_status`
* `/tmp/trellis-0.5.17-2/.trellis/scripts/workflow/workflow-state.py route` 实际输出字段包含 `stage` 与 `status`，不输出 `stage_status`
* 工作流源资产中的 `commands/shell/patch-inject-workflow-state.py` 仍从 route JSON 读取 `stage_status`
* 同类逻辑还存在于 `commands/shell/patch-session-start-strong-gate.py`
* 相邻问题还存在于 `commands/shell/patch-task-status-view-strong-gate.py`：它直接读取 `workflow-state.json.stage_status`，未兼容新字段 `status`

## Assumptions (temporary)

* 当前目标项目中的 `.claude/.codex/.opencode` 相关载体均由 `docs/workflows/新项目开发工作流/commands/shell/*.py` 源补丁生成
* 修复应落在工作流源资产与其测试，而不是直接修改 `/tmp/trellis-0.5.17-2` 生成物
* 如果测试中缺少对上述字段迁移的断言，应一并补上，以避免后续再次回归

## Open Questions

* 用户是否确认按当前已识别的 3 类真实问题一起修复：
  * route 输出字段读取错误
  * session-start header 同类错误
  * task status 视图直接读取旧字段导致摘要丢失

## Requirements (evolving)

* 只分析 `/tmp/trellis-0.5.17-2` 的实际行为，不把当前仓库自身运行态当作判定对象
* 只修改 `docs/workflows/新项目开发工作流/` 内的源资产；其他目录不改
* 若需要修 Trellis 原生行为，只能通过该工作流内合适位置打补丁来实现
* 先给出证据与修正方案，待用户同意后再实施修复
* 需要连带排查同类问题，尽可能一次修完整，避免继续引入新问题

## Acceptance Criteria (evolving)

* [ ] 列出真实存在的问题、误报项、以及同类连带问题
* [ ] 每个确认问题都有源码层和 `/tmp` 目标项目层证据
* [ ] 用户确认后，修复仅发生在 `docs/workflows/新项目开发工作流/`
* [ ] 修复后相关测试或验证命令能覆盖字段迁移场景

## Definition of Done (team quality bar)

* Tests added/updated where needed
* Relevant validation commands executed and results reported truthfully
* No edits outside `docs/workflows/新项目开发工作流/` except this task directory

## Out of Scope (explicit)

* 不直接修补 `/tmp/trellis-0.5.17-2` 生成物
* 不修改当前仓库其他源码目录
* 不做跨版本兼容性审计；本次是 `0.5.17` 同版本维护

## Technical Notes

* 关键证据文件：
  * `docs/workflows/新项目开发工作流/commands/shell/patch-inject-workflow-state.py`
  * `docs/workflows/新项目开发工作流/commands/shell/patch-session-start-strong-gate.py`
  * `docs/workflows/新项目开发工作流/commands/shell/patch-task-status-view-strong-gate.py`
  * `docs/workflows/新项目开发工作流/commands/shell/workflow-state.py`
  * `/tmp/trellis-0.5.17-2/.claude/hooks/inject-workflow-state.py`
  * `/tmp/trellis-0.5.17-2/.claude/hooks/session-start.py`
  * `/tmp/trellis-0.5.17-2/.opencode/plugins/inject-workflow-state.js`
  * `/tmp/trellis-0.5.17-2/.trellis/scripts/common/tasks.py`
