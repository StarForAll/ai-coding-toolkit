# brainstorm: 修复新项目开发工作流的 design/plan 阶段边界

## Goal

修复 `docs/workflows/新项目开发工作流/` 对应工作流在 `design` 与 `plan` 阶段的边界定义和后续衔接方式，避免 UI 原型被误作为正式实现输入，避免 `plan` 阶段被误解释为执行阶段，并确保后续修正规则在 Claude Code / Codex / OpenCode 的原生 CLI 使用方式下都能成立，同时优先服从 Trellis 框架核心机制。

## What I already know

* 用户明确限定分析与后续修改范围都在 `docs/workflows/新项目开发工作流/` 目录内
* 用户要求先在 `/tmp` 创建临时项目并执行 `trellis init`，在涉及与 Trellis 联动的判断时以该干净初始化结果作为依据
* 优化点 A：`design` 阶段产出的 UI 原型可能是照片或网页源码，只能作为 UI / 交互参考资产，不应直接作为正式实现代码输入
* 优化点 B：`plan` 阶段只能解释为规划，不能在进入该阶段或重新进入该阶段时自动触发项目基础代码生成或具体任务执行
* 用户新增硬要求：`plan` 阶段必须强制禁止执行具体任务、禁止进行具体代码实现，只允许完成当前阶段的任务划分与规划动作
* 用户当前只要分析和修改方案，必须在用户确认后才进行具体修改
* `/tmp` 基线样本显示：Trellis 原生 `start` 负责“会话初始化 + 任务分类 + 进入 brainstorm / task workflow”，并不原生提供当前项目自定义的 `design` / `plan` 阶段
* 当前自定义 workflow 已经有“强门禁阶段状态机”文档，但 `design` / `plan` 的禁止动作还没有全部落成单义规则或工具校验

## Assumptions (temporary)

* 当前问题既存在于工作流总纲层，也可能传播到命令文档、演练文档、技能入口或校验脚本
* `design` / `plan` 阶段的误触发，可能来自文档表述、阶段路由规则、恢复上下文规则，或它们的组合
* Trellis 初始化后的原生约定可以作为“什么属于框架核心，什么属于当前项目自定义工作流”的判定基线
* 现有 `workflow-state.json` / `start` Phase Router 规则能承载这次修正，但还缺少对非法阶段跃迁的显式验证

## Open Questions

* 当前 `docs/workflows/新项目开发工作流/` 中哪些文件定义了 `design` 与 `plan` 的阶段进入、恢复、退出条件？
* 这些规则是否已经传播到平台 README、技能入口、校验脚本或示例文档中？
* 当前 Trellis 原生初始化后的工作流边界，是否支持把“规划”和“执行”完全拆开？

## Requirements (evolving)

* 分析 `docs/workflows/新项目开发工作流/` 中与 `design` / `plan` 阶段相关的现状与问题来源
* 在需要涉及 Trellis 联动判断时，先基于 `/tmp` 中的干净初始化项目验证 Trellis 原生机制
* 给出兼容 Claude Code / Codex / OpenCode 原生 CLI 使用格式的修正思路
* 方案必须明确区分“参考资产”“规划输出”“正式实现输入”“执行阶段触发”
* `plan` 阶段必须被定义为“只做任务拆分 / 依赖规划 / 门禁摘要 / 候选下一步说明”，不得生成基础代码、不得进入实现、不得代替 implementation / start / test-first
* 本轮不直接修改文件，只输出分析结论与可执行修正方案

## Acceptance Criteria (evolving)

* [ ] 明确列出当前工作流中与问题 A / B 直接相关的文件、段落和机制
* [ ] 明确区分 Trellis 原生机制与当前项目自定义工作流规则
* [ ] 至少给出 1 个推荐修正方案，并说明为何优于备选方案
* [ ] 方案中包含 `design` 阶段 UI 原型的禁止带入项与允许保留项
* [ ] 方案中包含 `plan` 阶段进入/恢复时禁止执行的规则，以及后续真正执行阶段的触发条件
* [ ] 方案中明确 `plan` 阶段的硬禁令列表，以及建议落到哪些文档 / helper / 测试层

## Definition of Done (team quality bar)

* 提供基于仓库现状与 `/tmp` 干净初始化样本的分析证据
* 给出建议修改点、影响范围、传播范围与验证思路
* 未经用户确认，不进行具体文件修改

## Out of Scope (explicit)

* 本轮不直接编辑 `docs/workflows/新项目开发工作流/` 内文件
* 本轮不修复其他无关工作流
* 本轮不提交 commit、不记录 session、不归档任务

## Technical Approach

采用“文档契约 + 状态机校验 + 回归测试”三层收紧方案：

* `design`：新增 UI 原型资产隔离规则，明确原型只能作为参考资产，不能直接作为正式实现输入
* `plan`：新增硬禁令清单与执行授权等待点，明确该阶段只做任务拆分和规划，不得进入实现
* `start` / `workflow-state`：补充阶段切换合法性约束，阻断 `plan -> implementation` 的未确认跃迁
* 传播层：同步到总纲、命令映射、通俗版、walkthrough、CLI README、思维导图
* 校验层：补 `workflow-state.py` / `test_workflow_state.py` / `test_plan_validate.py`

## Decision (ADR-lite)

**Context**:
用户要求先只做分析与方案。当前 workflow 已有强门禁状态机，但 `design` 与 `plan` 的关键禁止动作仍有歧义，且 helper 未把非法跃迁编码化。

**Decision**:
选择 Approach A：同时修改文档契约、状态 helper 与测试，不采用“只改文档”或“新增独立 execution-authorization 子阶段”的方案。

**Consequences**:
* 优点：既能减少模型误读，也能减少状态漂移和手工误操作
* 成本：修改面覆盖多份文档和部分 helper / tests，需要做一次传播式更新
* 保留：不改变当前 workflow 的主模型，仍保留 `task-first + start 自动 before-dev`

## Implementation Plan (small PRs)

* PR1：收紧 `design` / `plan` / `状态机协议` 的核心契约，补 UI 原型隔离规则与 `plan` 硬禁令
* PR2：同步传播到 `工作流总纲`、`命令映射`、`通俗版`、`多CLI walkthrough`、各 CLI README、思维导图
* PR3：更新 `workflow-state.py` 与相关测试，增加 `plan -> implementation` 非法跃迁回归

## Technical Notes

* 已核查：`docs/workflows/新项目开发工作流/工作流总纲.md`、`阶段状态机与强门禁协议.md`、`命令映射.md`、`工作流全局流转说明（通俗版）.md`、`多CLI通用新项目完整流程演练.md`
* 已核查：`commands/design.md`、`commands/plan.md`、`commands/start-patch-phase-router.md`、`commands/codex/README.md`、`commands/opencode/README.md`
* 已核查：`commands/shell/workflow-state.py` 与 `commands/shell/test_workflow_state.py`
* 已核查：`/tmp/trellis-workflow-baseline-k5bZDm/` 中 `trellis init --claude --opencode --codex -y -u xzc` 的基线产物

## Research Notes

### Trellis 原生基线

* `trellis init` 生成的原生骨架以 `start / brainstorm / before-dev / finish-work / record-session` 为主，不包含当前项目自定义的 `design` / `plan` 阶段
* 原生 `start` 的职责是会话初始化、读取上下文、分类任务、把复杂任务先送进 brainstorm，而不是直接执行代码实现

### 当前 workflow 已有可复用规则

* `阶段状态机与强门禁协议.md` 已明确：`/trellis:start` 只重入当前已确认阶段，不自动把 `plan` 推到 `implementation`
* `commands/plan.md` 已明确：`plan` 只负责拆真实 Trellis task 与生成摘要型 `task_plan.md`
* `commands/design.md` 与各 CLI README 已明确：Codex 不能作为 `UI 原型生成` 与 `UI -> 首版代码界面` 的主执行器

### 当前仍存在的冲突 / 缺口

* `工作流总纲.md` 仍出现 “导出可开发的组件代码” 这类表述，会把原型资产误导成实现输入
* 当前文档尚未把“照片 / 网页源码 / 原型导出代码不得直接带入正式实现”写成统一禁令
* `plan` 的下一步推荐虽然声明“不是自动跳转”，但仍以“开始做某个具体 task”作为默认推荐，容易在恢复会话时被误读为进入执行
* `workflow-state.py` 目前只校验状态结构、当前任务指针、叶子任务约束和 design 文档边界，未校验 `plan -> implementation` 的非法跃迁
* 当前 `plan` 文档虽然说“只负责拆任务”，但尚未把“禁止生成基础代码 / 禁止编写实现代码 / 禁止执行具体 task”展开成硬禁令清单

### Feasible approaches here

**Approach A: 文档契约 + 状态机校验一起收紧** (Recommended)

* How it works:
  * 给 `design` 增加“UI 原型资产隔离规则”
  * 给 `plan` 增加“执行授权等待点”与显式切换协议，并新增“硬禁令列表”
  * 给 `workflow-state.py` / tests 增加对非法阶段跃迁的校验
* Pros:
  * 同时解决模型误读和状态漂移
  * 保留现有 task-first + start 自动 before-dev 主模型
* Cons:
  * 传播面较大，需要同步多份文档和测试

**Approach B: 只修文档表述，不改 helper / tests**

* How it works:
  * 仅修改总纲、阶段命令、演练和 README 的文字
* Pros:
  * 变更小，落地快
* Cons:
  * 之后仍可能因为状态文件被手动写错而再次误触发

**Approach C: 新增独立“execution-authorization”子阶段**

* How it works:
  * 在 `plan` 与 `implementation` 之间插入额外阶段
* Pros:
  * 语义最强
* Cons:
  * 改动面过大，偏离当前 workflow 既有状态机，不适合作为本轮最小修复
