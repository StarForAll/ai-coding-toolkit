# brainstorm: 修正新项目开发工作流 PRD 产物

## Goal

澄清并确认 `docs/workflows/新项目开发工作流` 在 Brainstorm 阶段完成后，是否应在当前项目的 `docs` 范围内生成两份可直接使用的 PRD 文档，以及这项改动应如何在 Claude Code、OpenCode、Codex 三种原生适配口径下保持一致。

## What I already know

* 用户明确要求：所有修改仅限 `docs/workflows/新项目开发工作流` 目录范围内。
* 用户明确要求：对该 workflow 的修改需要按 Claude Code / Codex / OpenCode 官方使用格式原生适配。
* 用户明确要求：在具体修改前，需要先和用户确认并说明如何修正。
* 用户已明确补充：这里讨论的是**项目级别的正式 PRD**，不是 `task_dir/prd.md`。
* 用户已明确补充：这两份文档本质上是**项目级需求文档**，覆盖项目中的所有需求功能点说明，后续需求变更也必须持续同步更新到对应文档中。
* 用户已明确补充：这条规则针对的是“新项目开发工作流”作用到的目标项目，不是当前仓库自身需要永久生成该类项目级文档。
* 当前 `docs/workflows/新项目开发工作流/commands/brainstorm.md` 的输出仍是任务目录下的 `prd.md`，并未要求在 `docs/` 内生成面向客户与面向开发人员的双 PRD。
* 当前 `docs/workflows/新项目开发工作流/工作流总纲.md` 已明确：安装后的需求发现基础资产至少包含需求发现核心规范，以及面向客户与面向开发人员的 PRD 规范、模板、检查清单。
* 当前仓库已经存在以下现成资产：
  * `.trellis/spec/universal-domains/product-and-requirements/prd-documentation-customer-facing/*`
  * `.trellis/spec/universal-domains/product-and-requirements/prd-documentation-developer-facing/*`
  * `.trellis/spec/templates/universal-domains/product-and-requirements/customer-facing-prd-template.md`
  * `.trellis/spec/templates/universal-domains/product-and-requirements/developer-facing-prd-template.md`
* 现有 PRD 规范显示：
  * 客户向 PRD 应以业务结果、用户体验、范围边界、非技术语言为主。
  * 开发向 PRD 应保留相同业务意图，但展开为实现可执行的技术规格、接口、异常、测试和风险。
* `docs/workflows/新项目开发工作流/命令映射.md` 与各 CLI README 已明确三种入口协议不同：
  * Claude Code：`/trellis:<phase>`
  * OpenCode：TUI `/trellis:<phase>`，CLI `trellis/<phase>`
  * Codex：自然语言 + 对应 skill，不提供项目级 `/trellis:xxx`

## Assumptions (temporary)

* 这次变更的重点是修正 workflow 文档与阶段命令说明，而不是新增 repo 根级新规范目录。
* `task_dir/prd.md` 与项目级正式 PRD 属于两类不同产物：
  * `task_dir/prd.md`：workflow 内部任务工作底稿 / 阶段上下文锚点
  * 项目级 PRD：目标项目 `docs/` 内的正式需求文档
* 项目级双文档是持续维护的需求基线，而不是 Brainstorm 阶段的一次性快照。
* 若最终要求在 Brainstorm 完成时生成双 PRD，更可能表现为“阶段门禁与项目文档产物升级”，并同步更新总纲、命令映射、`brainstorm` 阶段文档及三套 CLI 适配说明。
* “内容含义一致”应被落实为：客户向 PRD 与开发向 PRD 共享同一套目标、范围、验收与边界，只是表达深度和术语层次不同。

## Open Questions

* 是否将项目级双文档的目录语义正式定义为 `docs/requirements/`，而不是 `docs/prd/`？

## Requirements (evolving)

* 明确 Brainstorm 阶段完成后的**项目级正式文档产物**定义。
* 明确 `task_dir/prd.md` 与项目级 PRD 的职责边界，避免两者混淆。
* 若项目级产物升级为双 PRD，必须定义客户向与开发向文档的关系、内容一致性约束与表达差异。
* Brainstorm 确认完成后，必须先生成项目级双 PRD，才能进入下一阶段。
* 项目级双文档必须被定义为后续需求变更的持续同步目标，而不是只在初次 Brainstorm 时生成一次。
* 任何 workflow 修正都只能落在 `docs/workflows/新项目开发工作流` 范围内。
* 对 Claude Code、OpenCode、Codex 的说明必须保持阶段语义一致，但遵循各自原生入口协议。
* 在真正修改文档前，需要先向用户给出修正思路并获得确认。

## Acceptance Criteria (evolving)

* [x] 明确 Brainstorm 阶段完成后的项目级目标产物为双 PRD，且这是进入下一阶段的强制门禁。
* [ ] 若为双 PRD，明确客户向与开发向 PRD 的最小内容边界与一致性规则。
* [ ] 明确项目级双文档在目标项目 `docs/` 下的目录与命名规则。
* [ ] 明确项目后续需求变更必须同步回写双文档。
* [ ] 明确需要更新的 workflow 文档范围与 CLI 适配文档范围。
* [ ] 在实施前形成一份可供用户确认的修正方案摘要。

## Research Notes

### Current workflow behavior

* `docs/workflows/新项目开发工作流/commands/brainstorm.md` 目前将阶段输出定义为任务目录下的 `prd.md`，并据此决定后续去 `design` / `plan` / `start`。
* `.codex/hooks/session-start.py`、`.iflow/hooks/inject-subagent-context.py` 等运行时逻辑仍把 `task_dir/prd.md` 视为当前任务的 requirements 主文档。
* `docs/workflows/新项目开发工作流/多CLI通用新项目完整流程演练.md` 已把 Brainstorm 的退出门禁定义为“需求已准确 + 完成 L0/L1/L2 分类 + 决定下阶段”，但尚未把“产出正式双 PRD”列为门禁。

### Existing repo constraints

* 仓库已经具备客户向 / 开发向 PRD 的规范、模板、检查清单和示例，可直接作为 workflow 目标产物约束来源。
* 目前 `docs/workflows/新项目开发工作流` 内没有现成的目标项目双 PRD 路径约定，因此如果本次修正引入双 PRD，必须顺便补齐命名与落位规则。
* 由于本次用户限制修改范围仅在 `docs/workflows/新项目开发工作流`，更适合修正文档规则、阶段门禁和 CLI 说明，而不适合顺手改 repo 其他运行时代码。
* 因此，本次修正如果引入项目级 PRD，只能在 workflow 文档里明确：
  * 它是目标项目 `docs/` 下的正式产物
  * 它与 `task_dir/prd.md` 的关系
  * 它构成 Brainstorm 的退出门禁
  * 它也是后续需求变更的持续同步基线

### Feasible approaches here

**Approach A: 保留任务 `prd.md` 作为内部底稿，同时在 Brainstorm 确认后要求生成目标项目 `docs/requirements/` 内双需求文档**（Recommended）

* How it works:
  * `task_dir/prd.md` 继续承担阶段内工作底稿与运行时上下文锚点。
  * Brainstorm 确认完成后，要求额外生成目标项目 `docs/requirements/` 下两份正式需求文档：客户向 + 开发向。
  * 两份正式文档共享同一语义基线，分别按客户模板和开发模板展开。
  * 后续任何正式需求变更，都必须同步更新这两份文档。
* Pros:
  * 不与现有 `prd.md` 依赖链冲突。
  * 能满足“对外可读”和“对内可实施”的双文档诉求。
  * 目录语义更符合“持续维护的需求文档集合”，而不仅是一次性 PRD。
  * 只需要修正文档流程和阶段门禁，符合本次修改范围限制。
* Cons:
  * 需要明确三者关系：底稿、客户 PRD、开发 PRD。
  * 会增加一层同步要求，需要在 workflow 中写清“谁是事实来源”。

**Approach B: 直接把 Brainstorm 阶段主产物改成项目级双 PRD，弱化或不再强调任务 `prd.md`**

* How it works:
  * Brainstorm 结束时直接以双 PRD 作为唯一正式产物。
  * 文档里不再把任务 `prd.md` 作为主要门禁依据。
* Pros:
  * 表达上更直接，阶段目标更统一。
* Cons:
  * 与现有 hooks / task workflow 依赖 `task_dir/prd.md` 的事实不一致。
  * 若只改 workflow 文档，不改其他运行时代码，容易形成文档与实际行为漂移。

**Approach C: Brainstorm 只冻结单 PRD，双 PRD 延后到 Design 阶段再生成**

* How it works:
  * Brainstorm 仍只完成单 PRD 和分类。
  * 进入 Design 后再基于冻结需求展开双 PRD。
* Pros:
  * 变更最小，和现状最接近。
* Cons:
  * 已不满足用户刚确认的强制门禁要求。
  * 客户沟通与开发对齐会继续滞后一阶段。

## Decision (ADR-lite)

**Context**: 需要明确 Brainstorm 阶段完成后是否必须生成项目级正式 PRD，以及它与任务工作底稿的关系。

**Decision**: 用户已确认，Brainstorm 完成后必须先生成项目级双文档（客户向 + 开发向），并将其作为进入下一阶段的强制门禁；`task_dir/prd.md` 不等同于项目级需求文档；项目后续需求变更也必须同步更新这两份正式文档。

**Consequences**:

* Workflow 文档必须明确区分“任务工作底稿”与“项目正式需求文档”。
* Brainstorm 的退出门禁、下一步推荐、各 CLI 适配说明都需要同步更新。
* 仍需继续确认目标项目下双 PRD 的目录与命名规则。

## Definition of Done (team quality bar)

* Docs/notes updated if behavior changes
* Validation commands or document consistency checks identified
* Cross-CLI wording remains semantically aligned
* Scope stays within `docs/workflows/新项目开发工作流`

## Out of Scope (explicit)

* 直接修改 `docs/workflows/新项目开发工作流` 之外的仓库目录
* 直接修改 `.trellis/spec/` 或 `trellis-library/` 的 PRD 规范资产
* 在未确认方案前直接改动现有 workflow 文档

## Technical Notes

* Inspected:
  * `docs/workflows/新项目开发工作流/工作流总纲.md`
  * `docs/workflows/新项目开发工作流/命令映射.md`
  * `docs/workflows/新项目开发工作流/多CLI通用新项目完整流程演练.md`
  * `docs/workflows/新项目开发工作流/commands/brainstorm.md`
  * `docs/workflows/新项目开发工作流/commands/claude/README.md`
  * `docs/workflows/新项目开发工作流/commands/opencode/README.md`
  * `docs/workflows/新项目开发工作流/commands/codex/README.md`
  * `.claude/commands/trellis/brainstorm.md`
  * `.opencode/commands/trellis/brainstorm.md`
  * `.trellis/spec/universal-domains/product-and-requirements/prd-documentation-customer-facing/*`
  * `.trellis/spec/universal-domains/product-and-requirements/prd-documentation-developer-facing/*`
  * `.trellis/spec/templates/universal-domains/product-and-requirements/customer-facing-prd-template.md`
  * `.trellis/spec/templates/universal-domains/product-and-requirements/developer-facing-prd-template.md`
  * `trellis-library/examples/assembled-packs/requirements-discovery-foundation.md`
* Existing evidence indicates the repo already treats customer-facing and developer-facing PRD as paired but distinct documentation assets, while the current Brainstorm command still stops at a single task-local `prd.md`.
