# brainstorm: 新项目开发工作流补充多 AI CLI review

## Goal

在 `docs/workflows/新项目开发工作流/` 中补强“具体任务实现完成后的 review 阶段”，把现有偏单一的自审 / 提交前检查链路，扩展为支持多 AI CLI 协作 review 的明确机制。先确认 review 机制、阶段位置、参与角色与交接方式，再进入具体文档和命令实现补充。

## What I already know

* 用户当前目标不是立即改文件，而是先确认多 AI CLI review 的工作方式，再实施补充。
* 当前主工作流在阶段五完成后，文字总纲默认收尾链路是 `/trellis:self-review` → `/trellis:finish-work` → `/trellis:delivery`。
* `docs/workflows/新项目开发工作流/命令映射.md` 中存在 `/trellis:check` 节点，位置在 `self-review` 之后、`finish-work` 之前。
* 目标目录当前没有 `docs/workflows/新项目开发工作流/commands/check.md`，说明 review 阶段的命令层实现缺失。
* `commands/self-review.md` 当前主要描述 AI 广义自审，输出偏差清单 `self-review.md`，并把下一步推荐到 `/trellis:check` 或回到 `/trellis:start`。
* `commands/delivery.md` 当前仅在交付阶段提到 `requesting-code-review`，更偏 PR 前外部审查，不是“实现完成后立即进入的多 AI CLI review”。
* 仓库里已有 `skills/multi-cli-review/SKILL.md` 与 `skills/multi-cli-review-action/SKILL.md`，定义了 CLI 1 产出缺陷报告、CLI 2 审查并执行优化、再回到 CLI 1 复核的双 CLI 循环。
* `skills/collaborating-with-claude/SKILL.md` 说明了“主 CLI 持续实现，次级 CLI 给第二意见或 diff review”的轻量协作模式。
* 该仓库是多层协作仓库，工作流变更会同时影响总纲、命令映射、命令文档、可能的安装/兼容说明，因此属于跨层变更。

## Assumptions (temporary)

* 多 AI CLI review 的补充优先面向“所有需求实现完成后、当前 CLI 已完成项目级 review 之后”的追加 review 层，而不是改写现有主工作流链路。
* 本次补充至少会涉及 `工作流总纲.md`、`命令映射.md`，并大概率需要新增或补全 review/check 阶段命令文档。
* “多 AI CLI” 不一定要求所有 CLI 都能原生执行命令；对 Codex/Gemini 这类可先接受 markdown 注入、脚本调用或 skill 驱动的适配方式。

## Open Questions

* 其他多个 CLI 在项目级 review 中是只做审查输出，还是允许直接修复？
* 多个外部 CLI 的结果是串行汇总还是并行汇总？
* 这层追加的“多 CLI 项目级 review”应落在 `/trellis:finish-work` 之前，还是作为 `delivery` 前的独立门禁？

## Requirements (evolving)

* 明确当前工作流中“实现完成后的 review 阶段”应如何接入多 AI CLI。
* 给出至少 2 到 3 种可行机制，并说明顺序执行、职责划分、上下文交接与优缺点。
* 在用户确认机制后，再把选定机制补充进目标工作流文档和相关命令文档。
* 新机制应与已有 `multi-cli-review` / `multi-cli-review-action` 能力保持一致或明确说明为何不用。
* 新机制要明确与 `self-review`、`finish-work`、`delivery` 的关系，避免重复和阶段冲突。
* 不改变现有主工作流的实现链路；多 AI CLI review 应作为“当前 CLI 项目级 review 完成后”的追加层，而不是替换当前链路。
* 当前更偏向任务级追加机制：在具体任务中，当前 CLI 完成原本 review 后，再决定是否追加多其他 CLI 的补充审查层。
* 多其他 CLI 只做审查，不直接修改代码；当前 CLI 是唯一修复者与唯一收口者。
* 多 reviewer 采用“先批量独立审查，再统一修复”的子模式，不采用边审边修的串行模式。
* 是否触发任务级多 CLI 审查，由当前 AI 基于“硬条件 + 软条件评分”综合判断；若用户强制要求，则必须执行。
* 当前 CLI 触发该机制时，应给出供其他 CLI 直接使用的完整命令/输入协议，而不是把当前对话上下文整体转交给其他 CLI。
* 其他 CLI 使用 `multi-cli-review` 产出各自的 `cur_defect.md` 或等价审查建议文件。
* 当前 CLI 使用增强后的 `multi-cli-review-action` 统一处理多个 reviewer 产物，避免重复触发、重复修复与建议冲突失控。
* 默认由用户手动调用其他 2 个 CLI；允许扩展，但单任务最多使用 4 个其他 CLI。
* 单任务最多触发 3 轮补充审查；若其他 CLI 在当前轮未给出可执行修复建议，可提前关闭该机制。
* 当建议冲突、重复轮次过多、或达到人工介入阈值时，必须提示用户手动决策，不继续自动推进。
* 软条件评分采用“分层门槛制”，不采用简单加权总分制。

## Acceptance Criteria (evolving)

* [ ] 已识别当前 review 阶段的实际缺口与现有相关资产。
* [ ] 已给出多 AI CLI review 的可行机制选项与推荐方案。
* [ ] 用户已明确选定默认机制和边界。
* [ ] 选定机制能映射到具体工作流文档和命令层补充点。

## Definition of Done (team quality bar)

* Tests added/updated (unit/integration where appropriate)
* Lint / typecheck / CI green
* Docs/notes updated if behavior changes
* Rollout/rollback considered if risky

## Out of Scope (explicit)

* 立即实现所有 AI CLI 的真实命令执行桥接脚本
* 重新设计需求、设计、拆解等非 review 阶段流程
* 未经确认就直接改动全部工作流命令

## Technical Notes

* 关键现状文件：
  * `docs/workflows/新项目开发工作流/工作流总纲.md`
  * `docs/workflows/新项目开发工作流/命令映射.md`
  * `docs/workflows/新项目开发工作流/commands/self-review.md`
  * `docs/workflows/新项目开发工作流/commands/delivery.md`
  * `docs/workflows/新项目开发工作流/commands/start-patch-phase-router.md`
* 关键参考资产：
  * `skills/multi-cli-review/SKILL.md`
  * `skills/multi-cli-review-action/SKILL.md`
  * `skills/collaborating-with-claude/SKILL.md`
* 当前发现：
  * `命令映射.md` 使用了 `/trellis:check`，但 `commands/check.md` 缺失。
  * 当前“多 AI review”更像散落在 skill 层，还没被正式编排进新项目开发工作流。

## Research Notes

### What similar tools/patterns do

* **模式 A：单主 CLI + 顺序二次 review**
  * 主 CLI 完成实现和自审。
  * 第二个 AI CLI 只做问题发现或 patch review。
  * 主 CLI 统一修复、验证并推进后续阶段。
* **模式 B：双 CLI 闭环**
  * CLI 1 先输出结构化问题报告。
  * CLI 2 基于报告讨论并执行优化。
  * CLI 1 再次复核是否真正解决。
  * 本仓库现有 `multi-cli-review` / `multi-cli-review-action` 就是这种模式。
* **模式 C：并列多 reviewer 汇总**
  * 多个 AI CLI 对同一实现并行审查。
  * 主 CLI 或人工汇总冲突意见，再统一修复。
  * 信息更全，但协调和去重成本最高。

### Constraints from our repo/project

* 工作流当前已经有 `self-review` 与映射中的 `check` 分层，适合把“多 AI CLI review”收敛到 `check`，避免污染 `self-review` 的“自审”语义。
* 仓库已有双 CLI review skill，可复用现成的职责划分、路径协议和迭代机制。
* 对 Codex/Gemini/OpenCode 的命令扩展能力不一致，机制应强调“协议和交接物”优先，而不是要求所有工具都能同构运行。
* 现有总纲已经强调风险分级审查，因此多 AI CLI review 最适合作为 L1/L2 风险任务的增强审查路径。
* 如果扩展到“多个其他 CLI”，现有 `multi-cli-review` / `multi-cli-review-action` 需要被看作单 reviewer 协议的复用单元；多 reviewer 场景需要额外定义聚合与去重规则。

### Feasible approaches here

**Approach A: 顺序式第二意见 Review** (轻量)

* How it works:
  * 主 CLI 实现完成后先执行 `self-review`
  * 再调用第二个 AI CLI 做审查，输出问题列表或 patch 建议
  * 主 CLI 统一修复并进入 `finish-work`
* Pros:
  * 最接近用户提出的“第一个 review 结束之后第二个进行”
  * 实现成本低，文档容易写清楚
  * 不强依赖新的 run 目录协议
* Cons:
  * 第二个 CLI 只提供建议时，闭环验证偏弱
  * 不足以支撑多轮 review / fix / re-review

**Approach B: `/trellis:check` 承载双 CLI 闭环** (Recommended)

* How it works:
  * `/trellis:self-review` 只负责本 CLI 自审和生成偏差清单
  * `/trellis:check` 作为正式 review 阶段，默认调用多 CLI 协作协议
  * CLI 1 生成结构化缺陷报告，CLI 2 审查并执行优化或给出阻塞说明，CLI 1 再复核
  * 通过后再进入 `/trellis:finish-work`
* Pros:
  * 和当前映射图最一致，能顺手补上缺失的 `check.md`
  * 复用现有 `multi-cli-review` / `multi-cli-review-action`
  * 阶段边界清晰：自审、外部 review、提交前检查各司其职
* Cons:
  * 文档改动面更大
  * 需要定义 CLI 1 / CLI 2 / 人工的职责与退出条件

**Approach C: 风险分级多 Reviewer 编排**

* How it works:
  * L0 仍走 `self-review -> finish-work`
  * L1 走单个第二 AI CLI 顺序 review
  * L2 才进入双 CLI 或多 reviewer 汇总
* Pros:
  * 最符合风险分级原则，成本控制更好
  * 可以在文档层逐步引入多 AI review，而不是一刀切
* Cons:
  * 规则更复杂
  * 需要额外定义每级别的默认机制与回退路径

**Approach D: 现有工作流不变 + 追加多 CLI 项目级 Review 层**

* How it works:
  * 当前 CLI 按现有工作流完成项目实现、自审、项目级 review
  * 在当前 CLI 给出项目级 review 结论后，再交给其他 CLI【多个】做项目级 review
  * 其他 CLI 只基于统一输入包做独立审查，输出各自问题清单
  * 最后由当前 CLI 汇总问题、去重、判断是否修复，并给出最终收口
* Pros:
  * 不破坏现有工作流主体，侵入性最低
  * 更符合“主实现 CLI 负责到底，其他 CLI 提供补充审查”的角色分工
  * 适合项目级 review，因为多个 CLI 看的是整体而不是单个实现细节
* Cons:
  * 发现问题较晚，返工成本高于实现中途插入 review
  * 多 CLI 输出容易重复、冲突，必须设计统一汇总协议
  * 如果允许其他 CLI 直接修复，会和“不改变现有工作流”目标产生边界冲突

**Approach E: 任务级后置补充审查层 + AI 风险判定触发** (Current Direction)

* How it works:
  * 当前 CLI 按原本任务流程完成实现与原有 review
  * 当前 CLI 基于风险、复杂度、影响面判断该任务是否需要进入多其他 CLI 补充审查
  * 若命中触发条件，先冻结同一份任务审查输入包，再交给多个其他 CLI 独立执行 `multi-cli-review`
  * 多个其他 CLI 只输出缺陷报告，不直接改代码
  * 当前 CLI 逐份吸收或汇总这些报告，使用 `multi-cli-review-action` 执行统一修复
  * 修复后，当前 CLI 重新跑该任务原本的 review/验证，再判定任务完成
* Pros:
  * 比项目级追加更早发现问题，返工成本更低
  * 不需要把多 CLI 审查强塞给所有任务，可按风险动态触发
  * 保持“一个 CLI 负责修改与收口”，避免多头写代码冲突
* Cons:
  * 需要定义 AI 触发标准，否则容易过度触发或漏触发
  * 需要定义多 reviewer 的去重、冲突裁决、报告汇总机制
  * 修复后必须重跑原本 review，否则流程证据链断裂

## Decision (ADR-lite)

**Context**: 用户希望不打断当前 CLI 的原本实现与 review 流程，但希望在单个任务完成原本 review 后，根据风险自动判断是否追加多个其他 CLI 的补充审查；其他 CLI 只审查，不改代码；当前 CLI 统一吸收建议并完成修复与收口。

**Decision**:

* 采用“任务级后置补充审查层”而非项目级追加层。
* 采用“批量独立审查后统一修复”，不采用边审边修的串行 reviewer 模式。
* 触发条件采用“硬条件 + 软条件分层门槛制”。
* 其他 CLI 使用 `multi-cli-review` 输出审查结果。
* 当前 CLI 使用增强后的 `multi-cli-review-action` 统一读取并处理多个 reviewer 产物。
* 触发时由当前 CLI 生成给其他 CLI 的完整命令/输入模板，而不是迁移当前会话全文上下文。
* 默认由用户手动调用其他 2 个 CLI；单任务最多扩展到 4 个 reviewer CLI。
* 单任务最多 3 轮补充审查；若当前轮没有新增有效修复建议，可提前结束。
* 当达到人工介入阈值时，必须停止自动推进并要求用户决策。

**Consequences**:

* 需要新增一套任务级触发判定规则，至少包含硬触发项、软评分项、阈值与用户覆盖规则。
* `multi-cli-review-action` 不能再只面向单个 `cur_defect.md`，需要支持多报告聚合、去重、冲突裁决与统一执行。
* 其他 CLI 的输入必须标准化，否则多 reviewer 结果不可比。
* 当前 CLI 在根据审查结果完成修改后，必须重新跑该任务原本的 review/验证闭环。
* 需要定义 reviewer 数量上限、轮次上限、提前关闭条件、以及人工介入阈值。

## Technical Approach

### Trigger Model

采用两段式判断：

* **Hard Trigger**：命中即进入多 CLI 审查
* **Soft Gate**：未命中硬条件时，根据分层门槛判断 `required / recommended / skip`

### Hard Trigger Candidates

* 认证、授权、权限边界、敏感信息处理
* 数据迁移、schema 变更、删除与回填
* 公共 API / 跨层 contract / 外部系统集成
* 支付、队列、缓存一致性、并发状态
* 核心共享模块且 blast radius 明显
* 用户显式要求执行多 CLI 审查

### Soft Score Candidates

* 改动文件数
* 涉及层数 / 模块数
* 逻辑复杂度与异常路径数量
* 测试覆盖充分度
* 当前 CLI 的自我置信度或不确定性
* 历史缺陷密度高的模块
* 大规模 AI 生成代码或重构比例

### Soft Gate Shape

建议按层分门槛，而不是单一总分：

* **复杂度层**：改动文件数、改动行数、涉及模块/层数、异常路径数量
* **影响面层**：公共模块、跨层边界、外部集成、blast radius
* **可信度层**：测试覆盖不足、当前 CLI 不确定性高、AI 生成比例高、历史缺陷密度高

触发建议：

* 任一层达到高门槛 → `required`
* 两层达到中门槛 → `recommended`
* 均未达到门槛 → `skip`

### Reviewer Handoff

当前 CLI 触发该机制时，生成：

* 任务摘要
* 相关文件/路径
* 审查重点
* 输出路径协议
* 供其他 CLI 直接执行的完整 `multi-cli-review` 调用模板

不直接转交当前会话全文，避免污染、泄漏无关上下文与 reviewer 间输入不一致。

### Reviewer Limits

* 默认 reviewer 数：2
* 最大 reviewer 数：4
* 默认由用户手动在其他 CLI 中执行
* 单任务最大补充审查轮次：3

### Early Stop / Manual Intervention

可提前关闭的情况：

* 当前轮所有 reviewer 均未产出新的可执行修复建议
* 当前 CLI 判断新增问题均为重复、低价值或明显不成立
* 当前任务已重新验证通过，且无剩余高优先级问题

必须人工介入的情况：

* reviewer 之间对同一问题给出互斥建议
* 连续多轮仍出现高优先级未决问题
* 达到单任务最大轮次仍未稳定收敛
* 当前 CLI 无法判断某建议是否应纳入本任务边界
