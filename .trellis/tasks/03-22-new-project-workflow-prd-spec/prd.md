# brainstorm: 新项目开发工作流补充 spec 接入与完善门禁

## Goal

在 `docs/workflows/新项目开发工作流/` 的具体工作流实现中，补充一条明确可执行的要求：当技术架构已经被用户明确确认后，目标项目必须按严格顺序新增两个任务：

1. 根据技术架构，从 `trellis-library` 中挑选并导入合适的 spec 到当前项目 `.trellis/spec/`
2. 基于当前项目的作用/背景/技术架构，对当前项目 `.trellis/spec/` 做分析完善，去除错误内容并补齐缺失内容

同时，需要让这两个任务与现有“首次嵌入后先补需求发现基础资产”的门禁区分开，避免初始化阶段与架构确认后的项目定制阶段混在一起。

## What I already know

* `docs/workflows/新项目开发工作流/工作流总纲.md` 的 `1.4 项目确认与初始化` 已要求：若已嵌入对应自定义工作流，需要立即补充 `pack.requirements-discovery-foundation`，也就是需求发现阶段的基础资产门禁。
* `docs/workflows/新项目开发工作流/commands/start-patch-phase-router.md` 已实现与上述初始化门禁一致的检测逻辑：检查 `.trellis/workflow-installed.json` 与 `.trellis/library-lock.yaml`，要求至少补齐需求发现核心 spec、PRD spec、template、checklist。
* `docs/workflows/新项目开发工作流/工作流总纲.md` 的 `2.2`、`2.3`、`2.4` 主要覆盖 PRD 形成、确认与冻结；其中开发人员需求说明书已包含技术约束，但还没有“技术架构经用户确认后，将通用 spec 投影到项目 `.trellis/spec/` 并做项目化修订”的动作。
* `docs/workflows/新项目开发工作流/工作流总纲.md` 的 `3.5 技术方案设计` 与 `3.6 详细规划文档` 说明了技术架构/TAD/详细规划，但尚未在设计完成到任务拆解之间加入“项目 spec 接入与完善”的显式门禁。
* `docs/workflows/新项目开发工作流/commands/design.md` 当前输出设计文档后，下一步直接推荐 `/trellis:plan`、`/trellis:test-first` 或 `/trellis:start`，未体现“架构确认后先完善项目 `.trellis/spec/`”。
* `docs/workflows/自定义工作流制作规范.md` 已定义“通过工作流子目录分发并注入 start patch”的制作方式，但目前仍聚焦首次嵌入后的需求发现基础资产，不包含架构稳定后的二次 spec 落地。
* 当前仓库已有一个相关 planning 任务 `03-22-new-project-workflow-prd-spec/`，可直接扩展，不必新建重复任务。
* `docs/workflows/新项目开发工作流/工作流总纲.md` 的 `3.1.3 设计确认循环` 已定义“设计方案 → 客户审核 → 反馈修改 → 最终确认”，可以作为“技术架构被用户确认”这一触发条件的上游语境。

## Assumptions (temporary)

* 本次主要是补充工作流文档、命令说明和任务门禁，不要求立即新增新的 `trellis-library` 资产内容。
* “根据技术架构选择合适 spec” 的动作，应发生在技术架构经过用户确认之后，而不是首次嵌入工作流时。
* 这两个新增任务更像“技术架构确认后到任务拆解/实现之前”的项目化治理动作，而不是需求发现初始化动作。

## Open Questions

* （已确认）这两个串行任务完成后，应作为进入 `/trellis:plan` 前的强制门禁。

## Requirements (evolving)

* 保留现有“首次嵌入后补需求发现基础资产”的初始化门禁，不与本次新增要求混淆。
* 在“技术架构已被用户明确确认”后，新增两个必须串行执行的任务。
* 任务 1 必须明确：根据技术架构，从 `trellis-library` 中挑选适配当前项目的 spec，并添加到当前项目 `.trellis/spec/`。
* 任务 2 必须明确：在任务 1 完成后，基于项目作用、背景、技术架构等因素，对当前项目 `.trellis/spec/` 进行分析完善，删除错误内容并补齐缺失内容。
* 文档需要明确说明二者顺序不可交换，必须先完成导入/选型，再做项目化修订。
* 工作流读者需要看得出：这是一个项目级 spec 定制步骤，发生在技术架构经用户确认之后，并在进入后续计划/实现前完成。
* `/trellis:plan` 的职责需要保持清晰：它负责把已确认的需求/设计拆成 `task_plan.md`，不负责替代 spec 导入或 spec 修订动作。
* 因此，这两个新增任务必须作为进入 `/trellis:plan` 前的强制门禁，而不是 `/trellis:plan` 的内部步骤。

## Acceptance Criteria (evolving)

* [ ] `docs/workflows/新项目开发工作流/` 中出现“技术架构经用户确认后”的明确节点说明。
* [ ] 文档中明确列出两个新增任务及其严格先后顺序。
* [ ] 文档能区分“首次嵌入后的基础资产门禁”和“架构稳定后的项目 spec 接入/完善门禁”。
* [ ] 读者能够看出这两个任务与后续 `/trellis:plan`、`/trellis:test-first`、实施阶段之间的关系。
* [ ] 文档中明确：未完成这两个任务时，不进入 `/trellis:plan`。
* [ ] 如引用 `trellis-library`，文档能说明任务 1 的来源是 `trellis-library`，任务 2 的目标是当前项目 `.trellis/spec/`。

## Definition of Done (team quality bar)

* Tests added/updated (unit/integration where appropriate)
* Lint / typecheck / CI green
* Docs/notes updated if behavior changes
* Rollout/rollback considered if risky

## Out of Scope (explicit)

* 不改写整套 AI Workflow 方法论。
* 不把“架构确认后的 spec 接入/完善”误写成“首次安装工作流就必须完成”的动作。
* 不在本次 brainstorm 阶段直接重写 `trellis-library` 具体规范正文。
* 不新增与本次需求无关的 workflow 命令。

## Research Notes

### What similar workflow points already do

* `1.4 项目确认与初始化` 负责“工作流刚嵌入后”的最低资产基线补齐。
* `2.4 需求冻结` 负责冻结业务意图、验收证据、接口契约。
* `3.5 技术方案设计` 与 `3.6 详细规划文档` 负责技术架构/TAD/详细规划输出。
* `3.1.3 设计确认循环` 已有“设计方案 → 客户审核 → 反馈修改 → 最终确认”，可承接“用户确认技术架构”这一触发信号。
* `4.1 AI 驱动的任务自动拆解` 直接依赖已经稳定的技术约束与关联文档，职责是生成 `task_plan.md`，不是补项目 spec。

### Constraints from our repo/project

* 现有文档已经把“需求发现基础资产补齐”前置到了初始化门禁，因此新要求不能再复用同一个节点，否则语义会混乱。
* 新要求的输入是“已被用户明确确认的技术架构”，因此应依附显式确认节点，而不是只靠内部判断“已经稳定”。
* 任务 1 的目标路径是目标项目 `.trellis/spec/`，不是回写 `trellis-library` 本身；任务 2 则是在目标项目内做项目化修订。

### Feasible approaches here

**Approach A: 作为技术架构经用户确认后的阶段切换门禁** (Recommended)

* How it works:
  * 在 `阶段三：设计与规划` 末尾或 `阶段四：任务分解与准备` 开头增加一个“技术架构经用户确认后的 spec 接入与完善”小节。
  * 明确先做任务 1，再做任务 2，完成后才能进入 `/trellis:plan`。
* Pros:
  * 与“技术架构经用户明确确认”这个触发条件最一致。
  * 不会和首次嵌入后的需求发现基础资产门禁混淆。
  * 能自然衔接 task_plan.md 的生成，因为 `/trellis:plan` 正需要稳定的项目级 spec 约束。
* Cons:
  * 需要在现有阶段衔接说明中增加一个新的过渡门禁。

**Approach B: 作为需求冻结或设计确认文案中的补充说明**

* How it works:
  * 在 `2.4 需求冻结` 或 `3.1.3 设计确认循环` 附近补充：技术架构经用户确认后，先完成 spec 导入与修订，再进入下一阶段。
* Pros:
  * 与“已确认”这个措辞表面上接近。
* Cons:
  * 当前 `2.4` 更强调业务意图、验收证据、接口契约，提前塞入项目 `.trellis/spec/` 定制动作会打乱设计阶段边界。
  * 与 `3.5/3.6` 已存在的技术方案产出关系不够顺。

## Technical Approach

优先按 Approach A 处理：把新增动作定义为“技术架构经用户明确确认后的项目级门禁”，并同步检查：

* `docs/workflows/新项目开发工作流/工作流总纲.md` 的阶段衔接是否需要新增说明
* `docs/workflows/新项目开发工作流/commands/design.md` 的“下一步推荐”是否要体现该门禁
* `docs/workflows/新项目开发工作流/commands/plan.md` 或相关阶段说明是否需要补一条前置条件，明确 `task_plan.md` 生成前必须先完成这两个 spec 任务
* 如有必要，补充 `docs/workflows/新项目开发工作流/commands/start-patch-phase-router.md` 或相关说明，避免读者把两个门禁混为一谈

## Technical Notes

* 重点候选文件：
  * `docs/workflows/新项目开发工作流/工作流总纲.md`
  * `docs/workflows/新项目开发工作流/commands/start-patch-phase-router.md`
  * `docs/workflows/新项目开发工作流/commands/design.md`
  * `docs/workflows/新项目开发工作流/commands/plan.md`
  * `docs/workflows/自定义工作流制作规范.md`
* 已确认的现状边界：
  * 初始化门禁已存在，位置在 `1.4` 与 `start-patch-phase-router.md`
  * 技术架构产出已存在，位置在 `3.5` / `3.6`
  * `/trellis:plan` 当前只负责任务拆解，不承担 spec 接入与修订
  * 当前缺口在“架构确认后到 task_plan 之前”的项目 spec 定制过渡层
