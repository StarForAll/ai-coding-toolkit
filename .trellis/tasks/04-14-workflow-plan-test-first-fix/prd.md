# brainstorm: 修复新项目开发工作流 plan 与 test-first

## Goal

对 `docs/workflows/新项目开发工作流/` 中现有 workflow 进行分析，明确 `plan` 阶段与 `Test-First` 阶段相对于目标规则的偏差，并提出一套兼容 Claude Code / Codex / OpenCode 原生入口、同时以 Trellis task 机制为核心的修正方案。在用户确认前，不执行具体文档与脚本修改。

## What I already know

* 分析和后续修改范围限定在 `docs/workflows/新项目开发工作流/`
* 目标一：`plan` 阶段不再把 `task_plan.md` 作为主要承载面，而是使用 Trellis task 机制做任务拆解与任务图规划
* 目标二：`task_plan.md` 仅保留总览、依赖关系、门禁和任务图摘要
* 目标三：任务过大、跨上下文时必须继续拆分为多个串行 task；同一项目内的任务默认串行执行，不等于自动续跑
* 目标四：多端项目不需要全局强制串行，但单个项目域内仍要求串行
* 目标五：Test-First 应在每个具体任务执行前自动补充，不应继续要求用户显式提示
* 新边界：`before-dev` 在 Trellis 基线中的原生职责保持为“开发前读规范/注入项目知识”，但在当前 workflow 中应由主链自动调用，而不是要求用户显式输入 `before-dev`
* 当前 `commands/plan.md` 明确将 `/trellis:plan` 定义为“任务拆解与生成 task_plan.md”
* 当前多处文档仍引用 `推荐并行组`、`串行主链`、`task_plan.md` 执行矩阵，以及显式 `/trellis:test-first` 路由

## Assumptions (temporary)

* 本轮优先修正 workflow 规则、阶段职责和路由口径，不先扩展 `.trellis/scripts/task.py` 的底层能力
* CLI 原生适配优先意味着：Claude Code / OpenCode 继续保留命令文档入口，Codex 继续以自然语言路由到对应 skill / AGENTS 语义，但三者共享同一套阶段语义
* 若现有验证脚本强绑定 `task_plan.md` 结构，需要改为验证“task_plan 摘要 + Trellis task 真实拆分结果”的组合契约

## Open Questions

* 现有 `plan` / `test-first` / `start` / `project-audit` / `delivery` 之间哪些联动必须同步调整，哪些可以留到第二轮
* 是否需要保留 `/trellis:test-first` 作为显式可选入口，仅将其从“默认必经阶段”调整为“调试/补证据/手动重入入口”
* `before-dev` 的自动调用边界应定义为“每次进入 task 实现都执行”，还是“首次进入该 task / 切换 task / spec 变化时执行”

## Requirements (evolving)

* 产出当前 workflow 中与 `plan`、`task_plan.md`、串行执行、`Test-First`、CLI 适配相关的现状分析
* 给出一套面向 Trellis task 机制的改造方案，并说明每一类文档/脚本需要如何调整
* 明确哪些规则属于主链行为变化，哪些属于引用传播与验证脚本适配
* 每个具体任务的测试门禁补充必须发生在该任务真正实现前，不能在项目级阶段提前虚构
* 每个具体任务在进入实现前都应先执行对应的 `before-dev`
* `before-dev` 需要在保持其 Trellis 基线语义的前提下，由 workflow 主链自动调用；其读取结果再承接该任务的测试门禁补充
* 用户不应被要求显式调用 `before-dev` 命令
* 若某类测试要求对项目中的每个任务都统一强制适用，则允许作为项目级全局测试要求在上游阶段设置
* 在用户确认前不进行具体修改

## Acceptance Criteria (evolving)

* [ ] 已定位 `plan` 现状、`test-first` 现状及其主要引用链
* [ ] 已说明当前实现与目标规则的核心差距
* [ ] 已提出可落地的修改方案，覆盖主命令文档、总纲/演练/映射/思维导图/脚本等传播面
* [ ] 已说明 CLI 原生适配如何保持一致

## Definition of Done (team quality bar)

* 方案按 Trellis workflow 主链而非局部文案修补来组织
* 引用传播面明确，不遗漏关键验证脚本和 walkthrough 文档
* 若存在证据边界或未确认假设，显式标注

## Out of Scope (explicit)

* 未经用户确认直接修改 workflow 文档、脚本或部署产物
* 本轮直接实现新的 `.trellis/scripts/task.py` 功能或安装器行为
* 与本次问题无关的 workflow 阶段重写

## Technical Notes

* 重点现状文件：`commands/plan.md`、`commands/test-first.md`、`commands/start-patch-phase-router.md`、`commands/brainstorm.md`、`commands/design.md`
* 传播层文件：`工作流总纲.md`、`命令映射.md`、`工作流全局流转说明（通俗版）.md`、`完整流程演练.md`、`多CLI通用新项目完整流程演练.md`、`工作流思维导图.html`
* 脚本层文件：`commands/shell/plan-validate.py`、`commands/shell/delivery-control-validate.py`、`commands/shell/test_plan_validate.py`
* CLI 适配层文件：`CLI原生适配边界矩阵.md`、`commands/codex/README.md`、`commands/opencode/README.md`

## Research Notes

### Current workflow behavior

* `plan.md` 仍将 `/trellis:plan` 明确定义为“任务拆解与生成 `task_plan.md`”，并要求 `task_plan.md` 承载执行安排、推荐并行组、串行主链、任务执行矩阵
* `工作流总纲.md` 和 `工作流全局流转说明（通俗版）.md` 也把 `task_plan.md` 当成实施前后的主执行介质，并多次强调并行候选组
* `start-patch-phase-router.md` 仍以“存在 `task_plan.md` + 无测试文件 => 路由到 `/trellis:test-first`”作为主链判定
* `design.md` 仍要求用户在设计阶段显式确认 `test-first` 阶段的测试/验证命令与目录约定
* `test-first.md` 仍把 Test-First 定义为独立阶段，且默认作为 `plan` 后的推荐下一步
* `project-audit.md`、`delivery-control-validate.py`、`完整流程演练.md` 等下游文件仍直接消费 `task_plan.md` 中的执行矩阵和交付控制任务拆分

### Trellis baseline findings from real `trellis init`

基于 `/tmp/trellis-init-audit.XTAGC5` 的真实初始化结果：

* Trellis 基线初始化产物以 `.trellis/` 为运行时核心，包含 `workflow.md`、`scripts/`、`spec/`、`tasks/`、`workspace/`
* Trellis 的原生开发主链是 **task-first**
  - `task.py create` 创建真实 task 目录与 `task.json`
  - `task.py init-context` 为 task 生成 `implement.jsonl` / `check.jsonl` / `debug.jsonl`
  - `task.py start` 将 task 写入 `.trellis/.current-task`
  - hooks 与 session-start 再基于 `.current-task + jsonl + prd.md` 注入上下文
* `start` 基线 skill/command 的 Task Workflow 是：`brainstorm -> research -> init-context -> start -> implement -> check -> complete`
* 基线 `start` / `workflow.md` 中没有把 `task_plan.md` 作为执行真源，真实执行状态靠 task 目录、`task.json`、`.current-task` 和 jsonl 上下文文件承载
* 基线 `brainstorm` 明确支持复杂任务拆成 child task / subtask
  - `task.py create --parent ...`
  - `task.py add-subtask <parent> <child>`
* `task.json` 自带 `next_action` / `current_phase`，说明 Trellis 原生已经有“阶段推进附着在 task 上”的机制
* 多 CLI 适配不是把所有平台压成同一种协议，而是通过 CLI adapter 将同一阶段语义映射到原生载体
  - Claude / OpenCode：命令文件
  - Codex：`AGENTS.md` + hooks + skills
* `task_context.py` 会按当前 CLI adapter 自动把 `check` / `finish-work` 等平台入口注入到 jsonl，说明“官方原生格式承载 + Trellis 核心语义一致”本身就是 Trellis 的基线设计

### Gap against target rule

* 目标要求是“真实执行单元优先拆成多个 Trellis task”，而当前文档体系仍把 `task_plan.md` 视作执行真源
* 目标要求“复杂任务继续拆分为多个串行 task”，而当前 plan 口径仍保留较强的并行规划心智与字段
* 目标要求“串行不等于自动续跑”，但当前路由和演练文档容易把矩阵推进理解成默认顺延
* 目标要求“Test-First 在具体任务执行前自动补充”，而当前 design / plan / start / test-first 体系仍以用户显式进入 `/trellis:test-first` 为默认主链
* 与真实 Trellis 基线相比，当前 workflow 对 `plan` 的改造方向已经偏离“task-first, current-task-driven, jsonl-injected”主模型，转而把执行控制中心放到了 `task_plan.md`
* 当前 workflow 中 `before-dev` 只被当作“读规范/开发前准备”的显式入口，还没有承担“每个 task 进入实现前补充测试门禁”的职责
* 当前 `design` / `test-first` 口径把 task 级测试门禁和 project 级测试基线混在一起，不符合“task 前补充、全局项单独保留”的新要求

### Recommended direction

**Approach A: 保留阶段名，重写阶段职责**（Recommended）

* `plan` 保留为显式阶段入口，但改成“创建/拆分/关联 Trellis task + 写摘要型 `task_plan.md`”
* `before-dev` 保持 Trellis 基线语义不变，但在当前 workflow 中改为“由主链自动调用的必经前置”
* `test-first` 保留为显式可选入口，但从默认主链降级为“手动重入 / 补验证证据 / 某个 task 需要显式先测”
* 默认主链改为：`plan -> start`，其中 `start` 选定具体 task 后，自动执行该 task 对应的 `before-dev`，然后补该 task 的测试门禁，再进入实现
* project 级阶段只保留所有任务都统一强制适用的测试/验证要求，不再在项目级阶段替每个 task 预造具体门禁
* 优点：CLI 入口稳定、三端适配成本最低、与现有安装器/技能映射兼容最好
* 风险：需要同步修改较多传播文档和校验脚本

**Approach B: 弱化 `/trellis:test-first`，把其几乎完全并入 `/trellis:start`**

* 主链更短，但会让现有 `test-first.md` 退化为说明性文档
* 优点：用户感知更简单
* 风险：与当前 workflow 已安装资产、命令映射和平台文档的差异过大，传播面更广

## Decision (ADR-lite)

**Context**: 需要在不破坏 Claude Code / OpenCode / Codex 原生入口模型的前提下，把当前 workflow 从“`task_plan.md` 中心”迁移到“Trellis task 中心”，并把 Test-First 从显式主链动作改为具体任务执行前的自动补充门禁。

**Decision**: 推荐采用 Approach A。保留 `plan` / `test-first` 的阶段入口与三端适配形式，但重写语义：`plan` 负责 Trellis task 拆解与任务图摘要，`before-dev` 保持“规范注入”原义但由 workflow 主链自动调用，`start` 在选定 task 后先自动执行 `before-dev`、再补该 task 的测试门禁、再进入实现，`test-first` 只保留为手动入口。

**Consequences**:

* 需要同步改 `plan/test-first/start/design/brainstorm` 主命令文档
* 需要同步改 `before-dev` 在当前 workflow 中的调用方式与它在 `start`/路由中的位置
* 需要同步更新总纲、命令映射、通俗版、walkthrough、思维导图
* 需要重写 `plan-validate.py` 与对应单测，使其从验证“执行矩阵完整性”转为验证“task 摘要契约”
