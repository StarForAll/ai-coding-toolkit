# brainstorm: 审查新项目工作流多 CLI 补充审查层

## Goal

从 `./docs/workflows/新项目开发工作流/` 的整体流程出发，评估“任务级后置多 CLI 补充审查层”是否完整、可执行、低摩擦，并基于仓库内现有命令与 skill 设计给出贴近实际开发的修复完善建议。

## What I already know

* 工作流总纲已定义“任务级多 CLI 补充审查门禁”，位置在 `/trellis:self-review` 之后、`/trellis:finish-work` 之前。
* `/trellis:check` 被定义为该门禁的统一入口，负责触发判定、生成 reviewer 指令包、在报告返回后驱动 `multi-cli-review-action` 聚合修复。
* `skills/multi-cli-review/SKILL.md` 与 `skills/multi-cli-review-action/SKILL.md` 已存在，且都声明支持任务级多 reviewer 新协议。
* 现有设计已经定义 reviewer 数量上限、轮次上限、提前关闭与人工介入规则。

## Assumptions (temporary)

* 当前用户优先要的是机制分析与修复建议，而不是立即改文档。
* 评估重点应放在“整体流程是否顺滑、能否稳定落地、是否增加过多实际开发负担”。
* 若文档层、skill 层、脚本层之间存在冲突，应视为机制尚未完善。

## Open Questions

* 是否需要后续把分析结论直接落实为文档修订稿或命令/skill 修改方案。

## Requirements (evolving)

* 从整体工作流视角评估该补充审查层的定位是否合理。
* 检查文档设计、skill 协议、执行边界是否一致。
* 结合现实开发实践，判断该机制是否过重、是否容易中断开发节奏。
* 输出具体、低复杂度、便于落地的修复完善建议。
* 保留当前“硬条件 + 软条件分层门槛”判定模型，不另行简化为新打分规则。
* 不新增 shell/Python 辅助脚本，仍由当前 CLI 提示用户在其他 CLI 中调用对应 skill。
* 明确 reviewer 永远不负责创建目录，目录只能由当前 CLI/协调者创建。
* 将“高风险任务优先触发补充审查”作为机制定位，但不推翻现有 `required / recommended / skip` 结构。
* 对于缺少该机制的 CLI，不降级为其他协议；而是明确提示用户先补充对应 skill，再进入多 CLI 审查。

## Acceptance Criteria (evolving)

* [ ] 说明该机制当前已具备的闭环能力与其价值。
* [ ] 指出至少数个关键缺口、冲突或高摩擦点。
* [ ] 建议能落到工作流整体，而不是只局部点评某一段文案。
* [ ] 建议以“方便实际开发”为优先，而非引入更复杂的新层。
* [ ] 建议与用户确认的约束一致：不新增脚本、不重写门槛模型。

## Definition of Done (team quality bar)

* 分析基于仓库内现有文档与 skill 证据，而不是空泛经验判断。
* 明确区分：已具备、未闭环、建议优化。
* 如后续进入实施，应能直接转化为文档或 skill 修改项。

## Out of Scope (explicit)

* 立即改写整套新项目开发工作流文档。
* 立即实现自动化多 CLI 编排器。
* 讨论与本机制无关的工作流阶段。

## Technical Notes

* 关键文档：`docs/workflows/新项目开发工作流/工作流总纲.md`
* 关键命令：`docs/workflows/新项目开发工作流/commands/check.md`
* 上游命令：`docs/workflows/新项目开发工作流/commands/self-review.md`
* 关键 skill：`skills/multi-cli-review/SKILL.md`
* 关键 skill：`skills/multi-cli-review-action/SKILL.md`

## Research Notes

### What similar execution patterns inside this repo imply

* `self-review` 已经具备实际 shell 辅助脚本 `commands/shell/self-review-check.py`，说明“先有轻量验证脚本，再叠加 AI 判断”是当前工作流里更容易落地的模式。
* `check` 目前主要是文档协议，没有对应 shell helper；这意味着进入补充审查层后，更多依赖人工复制命令与 skill 协作。
* `codex-gemini/README.md` 明确写了 Codex/Gemini 不支持 slash command、hook、skills，这会降低该机制在跨 CLI 场景中的可执行性。

### Repo constraints

* 工作流总纲要求 `/trellis:check` 成为任务关闭前的门禁之一，但触发门槛目前只有概念描述，没有统一量化规则。
* `multi-cli-review` 与 `multi-cli-review-action` 已定义新协议，但 `multi-cli-review` 在“目录不存在”处理上前后矛盾：正文要求报错，错误处理段落又写自动创建目录。
* 当前设计把“标准命令包生成”“多 reviewer 报告收集”“汇总修复”“重跑验证”都串在一起，如果没有进一步轻量化，实际执行摩擦会偏高。

### Feasible directions here

**Approach A: 保留机制，明显轻量化**（Recommended）

* How it works:
  * 保留 `/trellis:check` 作为门禁，但默认只做快速判定。
  * 多 CLI 审查只在高风险或用户显式要求时进入，且默认 1 个额外 reviewer 即可。
  * 不增加脚本，仍通过标准命令包 + skill 调用完成协作。
* Pros:
  * 保留质量收益，同时更适合真实开发节奏。
* Cons:
  * 仍需维护一层任务级审查协议，且依赖用户在其他 CLI 手动执行。

**Approach B: 将其降级为可选增强层**

* How it works:
  * `/trellis:check` 不再默认嵌入收尾门禁，只在高风险任务或人工发起时使用。
* Pros:
  * 最省摩擦。
* Cons:
  * 流程一致性下降，容易再次退回“看心情要不要多人审查”。

**Approach C: 继续保持现状，仅补文案**

* How it works:
  * 不动机制，只修正文档冲突和说明。
* Pros:
  * 成本最低。
* Cons:
  * 无法解决实际执行负担和跨 CLI 落地问题。

## Decision (ADR-lite)

**Context**: 用户希望继续分析该机制，但要求方案保持简单、便于实际开发，不增加额外脚本，不重写当前门槛模型。

**Decision**:
* 采纳“保留机制但轻量化”的方向。
* 默认 reviewer 数从 2 收敛到 1，必要时再扩展。
* 不新增 helper 脚本，继续依赖 `/trellis:check` 生成标准命令包，并提示用户在其他 CLI 使用对应 skill。
* 明确 reviewer 永远不建目录，只消费当前 CLI 创建好的目录结构。
* 将该层定位为偏高风险任务的补充审查层，这是对现有门禁定位的强调，而不是新建一套规则。
* 对于尚无该机制的 CLI，把“补齐 skill 能力”视为进入补充审查层的前置准备动作。

**Consequences**:
* 流程仍保留多 CLI 协作收益，但成本会更贴近日常开发。
* 机制成败更依赖文档一致性和命令包可复制性。
* 需要修正文档与 skill 内部冲突，避免执行时职责不清。
* 需要把“reviewer CLI 必须已具备对应 skill”写成显式前提，避免命令包生成后无法执行。

## Design Principles

### 不可动摇的设计原则

* `check` 是补充审查门禁，不是对 `self-review` 的重复实现。
* 多 CLI 审查优先服务高风险、高不确定、高影响面任务，而不是常规任务默认流程。
* 当前 CLI 是唯一协调者与唯一修复者；reviewer 只产出报告，不改代码、不建目录。
* 进入多 CLI 审查的前提是 reviewer CLI 已具备对应 skill；若缺失，先补 skill，再进入流程。
* 补充审查层必须尽量降低默认成本，避免因流程过重而被日常开发绕开。
* 文档主链路必须先表达“为何触发”和“如何关闭”，再表达多轮、冲突、人工介入等扩展情况。

### 可调参数

* 默认 reviewer 数：默认 1，必要时可扩到 2-4。
* 轮次上限：保持 3 轮上限不变。
* 触发结果：保持 `required / recommended / skip` 三档不变。
* 前置准备动作：允许在进入补充审查层前，先执行 skill 安装/补齐动作。
* 提前关闭策略：保留“当前轮无新有效修复建议可提前关闭”。

### Risks

* 若 `recommended` 的文案仍过重，用户会把该层当作隐性强制评审。
* 若标准命令包不够具体，reviewer 会自行补上下文，破坏协议边界。
* 若能力前置条件未写清，流程会在跨 CLI 执行阶段才暴露阻塞。
* 若 `.processed.json` 等内部状态未被适度显性化，多轮审查时用户会难以理解当前状态。
