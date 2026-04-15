# brainstorm: 修复新项目开发工作流设计阶段与技术架构联动

## Goal

修复 `docs/workflows/新项目开发工作流/` 中与 design 阶段、阶段切换、技术架构确认后联动动作相关的工作流定义，使其符合 Trellis 核心机制，并同时对 Claude Code / Codex / OpenCode 采用各自原生入口表达。

## What I already know

* 分析范围限定在 `docs/workflows/新项目开发工作流/` 目录。
* 当前阶段只需要分析问题并给出修改方案，不能直接实施，实施前需再次获得用户确认。
* 用户要求：若涉及和 Trellis 联动的判断，必须先在 `/tmp` 创建临时项目并执行 `trellis init`，基于真实初始化结果理解工作机制后再分析。
* 用户进一步澄清：问题不只是 `design` 退出规则不够严，而是该 workflow 的**每一个阶段**都需要严格遵循执行流程，不能随意跳步、泛化执行或擅自推进。
* 用户已确认采用 **强门禁模式**：每个阶段结束后，必须“阶段退出清单完成 + 用户明确确认”，才能进入下一阶段；AI 只能推荐下一步，不能自行切换阶段。
* 用户已确认文档边界：
* 项目级正式文档中，可提前同步的是“客户说明的产品信息和功能需求”。
* 除此之外，技术架构、设计决策、spec 对齐、检查矩阵、`finish-work` / `record-session` 适配等内容，在用户确认前都按“严格草稿隔离”处理，只允许停留在 task 工作底稿，不进入目标项目正式文档。
* 用户已确认：在技术架构确认之前，只维护 `customer-facing-prd.md` 作为项目级正式需求文档；`developer-facing-prd.md` 等到架构确认后再正式生成。
* 用户已确认：技术架构确认后，design 后半段也不能一次性顺序跑完，而应在 design 阶段内部按多个子块分段执行；每完成一个子块，都需要停下来给用户确认后再继续下一块。
* 用户已确认：design 后半段中的“项目级文档同步（块 C）”和“工程化联动（块 D）”允许按项目情况二选一先做，但二者都必须留在 design 阶段内完成，且每个子块完成后仍需用户确认。
* 用户已确认：在强门禁模式下，`/trellis:start` 可以直接重入“当前已确认阶段”的内部流程，但不能自动跨到下一个阶段。
* 用户已确认：阶段状态需要采用显式状态文件方案，而不是纯文档标记推断。
* 用户已确认：`.trellis/.current-task` 不能为空，必须明确指向当前正在执行的任务；为空时不允许做阶段识别或自动重入。
* 用户已确认：父任务和子任务并存时，只有当前执行中的叶子任务才允许拥有独立 `workflow-state`；父任务只做汇总，不参与当前阶段判定。
* 用户指出的核心问题包括：
* A1. UI 原型复制到当前项目并提示 AI 记住 UI 目录后，工作流会错误自动进入 `plan`，但 `design` 尚未完成。
* A2. 阶段切换必须由用户确认，且需要判断当前阶段事项是否全部完成，不能自动切换。
* A3. 错误进入下一阶段后重新回到 `design`，当前工作流会在未充分讨论和验证的情况下自动生成内容。
* B1. `design` 阶段 step 5 应是“技术选型”，不是直接把实现技术写进文档。
* B2. 技术框架候选应基于最新有效信息，提供多个可行选项，而非单一或少量固定选项。
* B3. 技术架构确定后，需要同步更新目标项目 `docs/` 下全部关联文档，例如 PRD、技术文档。
* B4. 技术架构确认后，当前应触发但未触发的动作需要先做判断分析，例如 spec 完善。
* B5. 技术架构确定后，`finish-work` 需要自适应补充 `sonar-scanner` 命令。
* B6. 技术架构确定后，需要补充目标项目根 `README.md` 与 `docs/` 目录所需文档。
* 当前代码库已有相关定义：`commands/design.md`、`commands/start-patch-phase-router.md`、`commands/plan.md`、`commands/finish-work-patch-projectization.md`、`commands/shell/design-export.py`。

## Assumptions (temporary)

* 当前问题主要是 workflow 文档与辅助脚本的阶段门禁定义不够严格，而不是 Trellis 核心脚本本身已经实现了自动强制阶段跳转。
* 需要同时修正“阶段完成判定”“用户确认门禁”“设计阶段步骤定义”“技术架构确认后的派生动作清单”四类内容。
* 可能需要修改的不止 `commands/design.md`，还包括总纲、命令映射、演练文档、phase router、辅助校验脚本与测试。
* 需要把“阶段纪律”提升为整个 workflow 的统一约束，而不是只在 design 阶段局部补丁。
* design 阶段需要进一步细分“项目级需求同步”和“技术设计正式落盘”两类动作的边界。

## Open Questions

* 通过真实 `trellis init` 初始化后的最小项目结构里，哪些文件/机制能作为“阶段完成判定”和“阶段切换确认”的可靠锚点？
* 现有 workflow 中哪些文档已经定义了设计阶段退出门禁，但还不够严格或彼此不一致？

## Requirements (evolving)

* 输出基于仓库证据和真实 Trellis 初始化结果的分析结论。
* 给出可执行的修改方案，覆盖 A/B 两组问题。
* 修改方案必须覆盖全阶段严格执行流程，而不是只修 `design` 阶段。
* 在未获确认前不直接修改 workflow 文件。

## Acceptance Criteria (evolving)

* [ ] 识别当前 workflow 中导致 `design` 阶段误切换或误自动推进的定义位置。
* [ ] 识别当前 workflow 中各阶段存在的“自动跳步 / 未确认推进 / 缺少退出门禁”定义位置。
* [ ] 识别 `design` 阶段 step 5 与技术架构确认后联动动作的现状和缺口。
* [ ] 基于真实 Trellis 初始化结果说明哪些机制可作为设计修正依据。
* [ ] 输出一个用户可确认的修正方案，明确建议修改点与预期行为。

## Definition of Done (team quality bar)

* 分析基于真实仓库内容与可复现初始化结果
* 不虚构 CLI 原生适配能力
* 若涉及时效性技术选型建议，基于最新有效信息给出候选方向
* 修改前先明确影响范围与验证方式

## Out of Scope (explicit)

* 本轮不直接修改 `docs/workflows/新项目开发工作流/` 中任何文件
* 本轮不直接实施目标项目文档生成、spec 导入或 finish-work 改造

## Technical Notes

* 初步相关文件：
* `docs/workflows/新项目开发工作流/commands/design.md`
* `docs/workflows/新项目开发工作流/commands/start-patch-phase-router.md`
* `docs/workflows/新项目开发工作流/commands/plan.md`
* `docs/workflows/新项目开发工作流/commands/finish-work-patch-projectization.md`
* `docs/workflows/新项目开发工作流/commands/shell/design-export.py`
* `docs/workflows/新项目开发工作流/工作流总纲.md`
* `docs/workflows/新项目开发工作流/命令映射.md`

## Research Notes

### 当前 workflow 已确认的现状

* `commands/start-patch-phase-router.md` 已写明“下一步推荐不等于自动跳阶段”，但路由树里仍使用未结构化定义的“设计完成”作为 `plan` 入口条件。
* `commands/design.md` 当前把 `Step 5` 定义成“可执行原型验证”，而 `工作流总纲.md §3.5` 对应的是“技术方案设计/技术选型”，两者存在编号与语义错位。
* `commands/design.md` 与 walkthrough 已要求技术架构确认后执行 spec 对齐、检查矩阵、`finish-work`/`record-session` 项目化适配，但目前没有统一的“已完成哪些动作、哪些仍待触发”的显式 checklist / 哨兵文件 / 用户确认门禁。
* `commands/shell/design-export.py` 只校验 `design/` 目录内部文档，不校验目标项目 `docs/requirements/`、项目根 `README.md`、技术架构确认后的 spec 对齐、检查矩阵或 `finish-work` 补丁是否已完成。
* 当前 workflow 还没有明确区分：
* 哪些内容属于“项目级需求文档，可在架构未确认前同步”
* 哪些内容属于“技术设计正式文档，必须在架构确认后才能写入目标项目”
* `developer-facing-prd.md` 的生成时机也需要从当前 workflow 中收紧到“技术架构确认后”。
* design 阶段需要支持内部子阶段门禁，而不是只有“进入 design”和“退出 design”两层门禁。
* design 阶段后半段的子块顺序不必完全固定，但必须受“已完成块 + 用户确认 + 仍在 design 阶段”的状态约束。
* 全 workflow 的路由器需要从“跨阶段推荐/推进”收紧为“识别当前阶段 + 重入当前阶段内部流程”；跨阶段切换只能由用户明确确认触发。
* 现有 Trellis `task.json` 的 `current_phase` / `next_action` 可作为任务基线字段保留，但不足以单独承载当前 workflow 需要的强门禁状态机；后续方案应考虑“task.json + workflow 专用状态文件”的组合。
* 多任务场景下，阶段识别链路应以 `.current-task -> 当前 task -> workflow-state.json` 为唯一判定口径，而不是在多个 active task 间自行猜测。
* 状态归属应采用“叶子任务持有执行态、父任务持有汇总态”的模型，避免项目级任务和执行中子任务之间出现双重阶段状态冲突。

### `/tmp` Trellis 初始化结果

* 在 `/tmp/trellis-workflow-fixture` 执行 `trellis init --claude --opencode --codex -y -u xzc` 后，得到的是 Trellis 基线资产，不包含当前 repo 维护的 `feasibility` / `design` / `plan` / `delivery` 等自定义阶段。
* Trellis 基线会生成：
* Claude 侧 `.claude/commands/trellis/*.md`
* OpenCode 侧 `.opencode/commands/trellis/*.md`
* Codex 侧 `.agents/skills/*/SKILL.md`、`.codex/config.toml`、`.codex/hooks.json`
* 这说明“设计阶段是否完成”“是否可进入 plan”“技术架构确认后需触发哪些动作”并不是 Trellis init 自带机制，而是当前 workflow 自己必须补齐的约束层。

### CLI 原生适配观察

* Claude Code 官方文档确认：项目命令可放在 `.claude/commands/`，且新推荐写法是 `.claude/commands/*.md` 或 `.claude/commands/<namespace>/*.md`，旧 `.md` 语法仍兼容。
* OpenCode 官方文档确认：项目命令来自 `.opencode/commands/*.md`，用户通过 `/command-name` 使用；当前 repo 的 `trellis/<phase>` 命名空间属于本 workflow 的额外约定，后续修改时需要避免写成 OpenCode 官方已经明确承诺的固定语法。
* OpenAI Codex 官方文档确认：长期项目规则以 `AGENTS.md` 形式工作，并按“当前目录向上查找、最近优先”的方式生效；官方 slash commands 页面未体现与 `.claude/commands/` / `.opencode/commands/` 对等的项目级 workflow 命令目录。

### 初步可归纳的问题类型

* 阶段门禁缺少“用户确认完成”与“完成证据清单”双重约束。
* 设计阶段步骤编号、名称、输出物与退出门禁之间存在错位。
* 技术架构确认后的派生动作虽散落在多个文档中，但没有统一触发清单和静态校验。
* 设计阶段的静态校验只覆盖 `design/` 子目录，未覆盖用户实际关心的目标项目级文档同步与收尾命令适配。
* 当前需要把上述问题从 design 扩展到所有阶段，形成统一的阶段状态机规则：进入条件、阶段内允许动作、退出清单、禁止自动推进、用户确认切换。
