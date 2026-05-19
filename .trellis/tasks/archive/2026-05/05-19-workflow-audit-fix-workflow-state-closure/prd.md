# workflow-audit: 修复新项目开发工作流状态机与恢复闭环

## Goal

基于 `docs/workflows/新项目开发工作流/` 的源资产，结合 `/tmp/trellis-0.5.17-2` 这个已执行 `trellis init` 并嵌入该工作流的目标项目样本，审计并修复真实存在的工作流问题。重点核实用户列出的 6 类问题及同类问题；若问题真实存在，则只在 `docs/workflows/新项目开发工作流/` 内实施修复，确保后续目标项目嵌入后行为闭环、恢复链路可用、且不引入新的明显回归。

## What I already know

* 本次审计目标固定为 `docs/workflows/新项目开发工作流/`，不是当前仓库自用的 `.trellis/` 工作流。
* 用户明确要求分析判断对象应以 `/tmp/trellis-0.5.17-2` 的实际嵌入结果为准，并允许在当前任务目录写入任务文件。
* 只能修改 `docs/workflows/新项目开发工作流/`；其他目录不能改动。
* `docs/workflows/新项目开发工作流/commands/workflow_assets.py` 中 `COMPATIBLE_TRELLIS_VERSION = "0.5.17"`，当前 `trellis -v` 也是 `0.5.17`，版本门禁通过。
* `workflow-audit` 技能要求本次走 task-based runtime 路径：用户显式要求 `/tmp` 验证，且需要保留 `audit-report.md`。

## Assumptions (temporary)

* `/tmp/trellis-0.5.17-2` 保留了足够的已嵌入证据，可用于确认问题是否真实存在。
* 若问题属于 Trellis 原生缺口，但会影响该工作流安装结果，则应优先在该工作流目录内通过补丁脚本、安装器或文档契约修复，而不是修改仓库根层 Trellis 运行时。
* 除用户已列 6 项外，还可能存在同类闭环缺失，例如状态恢复、路由强门禁、降级恢复、legacy 逻辑残留、测试空洞和多载体语义漂移。

## Open Questions

* 当前无需向用户追加阻塞问题，先通过源资产与 `/tmp` 样本取证；仅在出现证据分叉无法归因时再询问。

## Requirements (evolving)

* 必须按证据判断用户列出的 6 类问题是否真实存在，不能把候选问题直接当结论。
* 若真实存在，修复范围必须限制在 `docs/workflows/新项目开发工作流/`。
* 需要主动排查相邻同类问题，而不是只修用户点名的行号。
* 修复方案要优先保证闭环、可恢复、安装后可用、跨文档/补丁/脚本一致，不引入新的明显行为漂移。
* 需要维护任务内 `audit-report.md`，记录 source repo、generated target project、runtime command output 三类证据。
* 最终需要对修改后的工作流运行相关验证，至少覆盖静态校验与可执行的运行时/测试验证。

## Acceptance Criteria (evolving)

* [ ] `audit-report.md` 中对 6 类候选问题逐项给出 confirmed / unconfirmed / false alarm / blocked 结论。
* [ ] 所有实际修复均落在 `docs/workflows/新项目开发工作流/` 内。
* [ ] 若存在同类闭环问题，修复范围覆盖到位而非只修一个入口。
* [ ] 至少有一组验证可以证明修复后的工作流源资产通过相应校验或测试。
* [ ] 最终结论明确区分已完成、未完成、风险与剩余验证边界。

## Definition of Done (team quality bar)

* 相关测试或校验已运行并记录结果
* 工作流源资产的文档、脚本、补丁、测试保持一致
* 不修改 `docs/workflows/新项目开发工作流/` 之外的非任务文件
* 若发现值得沉淀的维护规则，评估是否需要后续 spec 更新

## Out of Scope (explicit)

* 不直接修当前仓库根层 `.trellis/`、`.codex/`、`.claude/`、`.opencode/` 的运行时代码
* 不把跨版本兼容性升级审计扩展成 `workflow-capability-audit`
* 不处理与 `docs/workflows/新项目开发工作流/` 无关的普通业务代码问题

## Technical Notes

* 固定审计目标：`docs/workflows/新项目开发工作流/`
* 版本锚点：`docs/workflows/新项目开发工作流/commands/workflow_assets.py`
* 运行时样本：`/tmp/trellis-0.5.17-2`
* 需要重点审视的语义面：`workflow-state.py`、安装器/升级脚本、CLI 边界文档、隐藏目录托管边界、任务与 active-task 降级恢复、legacy 状态残留、测试覆盖
