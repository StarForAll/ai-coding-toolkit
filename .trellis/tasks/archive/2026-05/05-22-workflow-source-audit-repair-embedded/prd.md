# workflow-audit: 修复嵌入式临时项目暴露的新项目开发工作流问题

## Goal

基于 `docs/workflows/新项目开发工作流/` 的源资产，结合 `/tmp/trellis-0.5.17-2` 这个已执行 `trellis init` 并嵌入该工作流的目标项目样本，审计并修复真实存在的工作流问题。重点核实用户列出的“过度修改 / 虚构问题 / 目标偏移 / 庞杂混乱 / 双状态系统 / 6 个 critical runtime patches / 禁用 parallel”等候选问题及同类变体；若问题真实存在，则只在 `docs/workflows/新项目开发工作流/` 内实施修复，确保后续目标项目嵌入后行为更稳定、闭环更完整、且不引入新的明显回归。

## What I already know

* 本次审计目标固定为 `docs/workflows/新项目开发工作流/`，不是当前仓库自用的 `.trellis/` 工作流。
* 用户明确要求分析判断对象应以 `/tmp/trellis-0.5.17-2` 的实际嵌入结果为准，并允许在当前任务目录写入任务文件。
* 只能修改 `docs/workflows/新项目开发工作流/`；其他目录不能改动。
* `docs/workflows/新项目开发工作流/commands/workflow_assets.py` 中 `COMPATIBLE_TRELLIS_VERSION = "0.5.17"`，当前 `trellis -v` 也是 `0.5.17`，版本门禁通过。
* 当前工作流源码中仍然保留 `OPTIONAL_DISABLED_BASELINE_COMMANDS = ["parallel"]`、`workflow-state.py`、`CRITICAL_RUNTIME_PATCHES` 六项强门禁补丁等结构，用户质疑点具备可核实的源侧证据入口。
* `workflow-audit` 技能要求本次走 task-based runtime 路径：用户显式要求 `/tmp` 验证，并需要保留 `audit-report.md`。

## Assumptions (temporary)

* `/tmp/trellis-0.5.17-2` 的当前状态足以作为“已嵌入后真实结果”的主要证据源，不必为了本轮判断重新执行一次正式嵌入。
* 用户给出的候选问题全部都应视为“待证实假设”，不能直接按既有结论落刀。
* 若发现问题根因位于安装器、升级检查、命令文档、helper 脚本、测试或映射文档之间的传播不一致，必须在 `docs/workflows/新项目开发工作流/` 范围内同步修正，而不是只做单点补丁。

## Open Questions

* 当前无阻塞性问题；若 `/tmp/trellis-0.5.17-2` 的实际状态与源码契约存在冲突，再回填为明确分支。

## Requirements (evolving)

* 对用户列出的每一类问题做 evidence-first 审计，区分真实缺陷、设计取舍、假警报和证据不足。
* 审计对象必须以 `/tmp/trellis-0.5.17-2` 的实际嵌入结果为主，并结合源工作流、安装器、升级检查、文档和测试做交叉验证。
* 如果问题真实存在，只能修改 `docs/workflows/新项目开发工作流/` 内的源资产进行修复。
* 修复时要检查并处理同类变体，避免“修一处漏一片”。
* 不能为了消除“复杂感”而做无证据的大重构；只有在能证明当前实现真的产生缺陷、维护漂移或错误契约时才修改。
* 如果发现的是 Trellis 原生问题对当前工作流的影响，应在该工作流合适位置打补丁，使安装器后续嵌入时自动修复目标项目。
* 修改后必须运行与当前改动相关的验证命令，只能据实报告 `pass / fail / not run`。

## Acceptance Criteria (evolving)

* [ ] 当前任务目录中存在更新后的 `audit-report.md`，明确记录版本门禁、证据动作、确认问题、假警报和阻塞项。
* [ ] 所有确认存在的问题都在 `docs/workflows/新项目开发工作流/` 内得到源侧修复或被明确记录为当前轮次不宜自动修复的原因。
* [ ] 与改动相关的命令文档、脚本、安装器/升级契约、测试或映射文档已按传播范围同步更新。
* [ ] 相关验证命令已执行，结果被真实记录。

## Definition of Done (team quality bar)

* 真实缺陷已修复，假警报未被误改。
* 相关测试或静态验证已运行并记录结果。
* 审计结论和修复范围可回溯到具体证据。
* 未越界修改 `docs/workflows/新项目开发工作流/` 之外的工作流源文件。

## Out of Scope (explicit)

* 不修改当前仓库正在使用的 `.trellis/`、`.codex/`、`.claude/`、`.opencode/` 运行时文件。
* 不删除当前任务目录中的任务文件。
* 不在没有证据的情况下，把整个工作流重写成全新架构。

## Technical Notes

* 相关技能/规范：
  * `.trellis/spec/skills/workflow-audit.md`
  * `.trellis/spec/skills/workflow-repair.md`
  * `.trellis/spec/platforms/codex-workflow-behavior.md`
  * `.trellis/spec/scripts/workflow-installer-upgrade-contracts.md`
  * `.trellis/spec/scripts/workflow-command-doc-contracts.md`
  * `.trellis/spec/docs/index.md`
* 主要源文件入口：
  * `docs/workflows/新项目开发工作流/commands/workflow_assets.py`
  * `docs/workflows/新项目开发工作流/commands/install-workflow.py`
  * `docs/workflows/新项目开发工作流/commands/upgrade-compat.py`
  * `docs/workflows/新项目开发工作流/commands/shell/workflow-state.py`
  * `docs/workflows/新项目开发工作流/阶段状态机与强门禁协议.md`
  * `docs/workflows/新项目开发工作流/工作流总纲.md`
