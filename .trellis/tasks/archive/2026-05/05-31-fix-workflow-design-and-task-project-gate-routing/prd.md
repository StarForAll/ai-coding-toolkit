# fix workflow design and task-project gate routing

## Goal

修复 `docs/workflows/新项目开发工作流/` 中两个已确认的阶段门禁缺陷：一是 design 阶段在存在 UI 视觉落地链路时，不能只因为 A/B/C/D 完成就直接把下一步提示到 `plan`，而必须显式卡住并引导外部 UI 原型设计与结构化结论回收；二是任务级 `review-gate` 不能再作为通向项目级 `project-audit` / `delivery` 的阶段承载面，项目级流转必须保持在项目级语义内，任务级 gate 只负责任务级闭环。

## What I Already Know

* 已完成 lightweight `workflow-audit`，两处问题都已被静态证据确认。
* 当前 design 退出判断主要依赖 `completed_blocks = A/B/C/D`，未把 UI 原型外部执行链路作为条件门禁。
* 当前 `state_utils.py` 允许 `review-gate -> project-audit` 与 `review-gate -> delivery`，而文档与强门禁边界又强调 `review-gate` 是任务级、`project-audit` / `delivery` 是项目级。
* 相关变更会同时影响命令文档、状态机/validator、以及 `test_workflow_state.py` 等回归测试。

## Assumptions (Temporary)

* 不新增全新的大状态机阶段，只在现有 design / project-audit / check / review-gate / delivery 语义内修正门禁。
* UI 原型链路的 design 退出门禁优先复用现有 `ui_lane_decision`、`design/STITCH-PROMPT.md`、`design/pages/*.md` / `design/specs/*.md` 等现有资产，而不是另起一套完全独立的产物体系。
* 本次不做 `/tmp` 嵌入运行时验证，先以 repo source、validator 与测试回归为完成标准。

## Open Questions

* 当前无阻塞用户问题；若实现中发现 UI 原型门禁必须引入新的结构化字段且现有资产无法承载，再单独收口设计。

## Requirements (Evolving)

* 当 `ui_lane_decision` 表示存在 UI/前端视觉落地链路时，design 阶段必须在退出前显式要求：
  * 外部 UI 工具执行链路已被引导；
  * `design/STITCH-PROMPT.md` 满足基线；
  * 已有可复用的结构化设计结论沉淀，而不是只剩 A/B/C/D 文档存在。
* design 的命令文档、状态机校验、相关 walkthrough / mapping 文档要保持同一口径。
* 任务级 `review-gate` 不能再承担项目级 `project-audit` / `delivery` 的默认或合法阶段流转。
* 项目级 `project-audit -> delivery` 仍保留，但必须继续依赖项目级证据与任务级 `check` 双门禁，不能通过任务级 `review-gate` 复用该语义。
* 更新相关测试，先看到失败，再以最小实现让测试转绿。

## Acceptance Criteria (Evolving)

* [ ] 新增/更新的测试先失败，再因修复通过。
* [ ] `workflow-state`/validator 在 UI 链路存在但 design 证据不足时阻断离开 design。
* [ ] `workflow-state`/validator 不再允许把任务级 `review-gate` 当作进入项目级 `project-audit` / `delivery` 的阶段承载面。
* [ ] 受影响的 workflow 文档与状态机/测试口径一致。

## Out of Scope

* 额外新增 unrelated workflow 优化点。
* `/tmp` 目标项目运行时审计、嵌入、handoff 测试。
* 修改当前仓库 Trellis 原生 workflow，而不是 `docs/workflows/新项目开发工作流/` 产品源。

## Technical Notes

* 关键文件预计包括：
  * `docs/workflows/新项目开发工作流/commands/design.md`
  * `docs/workflows/新项目开发工作流/commands/review-gate.md`
  * `docs/workflows/新项目开发工作流/commands/project-audit.md`
  * `docs/workflows/新项目开发工作流/commands/check.md`
  * `docs/workflows/新项目开发工作流/commands/delivery.md`
  * `docs/workflows/新项目开发工作流/命令映射.md`
  * `docs/workflows/新项目开发工作流/工作流全局流转说明（通俗版）.md`
  * `docs/workflows/新项目开发工作流/阶段状态机与强门禁协议.md`
  * `docs/workflows/新项目开发工作流/commands/shell/state_utils.py`
  * `docs/workflows/新项目开发工作流/commands/shell/validators_core.py`
  * `docs/workflows/新项目开发工作流/commands/shell/validators_gates.py`
  * `docs/workflows/新项目开发工作流/commands/shell/design-export.py`
  * `docs/workflows/新项目开发工作流/commands/shell/test_workflow_state.py`
  * `docs/workflows/新项目开发工作流/commands/shell/test_design_export.py`
* 需要遵守 workflow rule propagation，避免只改单一命令文档。

## 阶段出口快照
- `complexity_decision`: `L1`
- `ui_lane_decision`: `no-ui`（当前任务本身不是前端任务，但要修 UI 链路门禁）
- `cross_platform_scope`: `claude + opencode + codex workflow source`
- `estimate_refresh_result`: `无需重估`
- `kill_criteria`: `若修复需要重写阶段模型或扩大到 runtime handoff，再暂停收口范围`
- `open_items`: `none`

## Workflow Decisions
- Accuracy Status: Confirmed by static audit
- Complexity: Simple-to-moderate workflow repair
- Need More Divergence: No
- Need Sub Tasks: No
- Next Step: Read specs, add failing tests, implement minimal cross-layer fix
