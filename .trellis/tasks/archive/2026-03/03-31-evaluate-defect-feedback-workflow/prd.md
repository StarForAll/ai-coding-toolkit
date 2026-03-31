# brainstorm: 评估新项目工作流去缺陷反馈机制

## Goal

从整个 `docs/workflows/新项目开发工作流/` 的执行闭环出发，评估“工作流补充工作流去缺陷反馈优化机制”是否已经足够合理、轻量且便于实际开发使用；若存在明显缺口，再提出最小化、可执行的完善建议。在用户未明确确认前，不进行文档修改。

## What I already know

* 核心机制定义位于 `docs/workflows/新项目开发工作流/工作流总纲.md §7.3.1`
* `§6.6.4` 已明确与 `§7.3.1` 建立衔接，避免 Bug 学习流程与工作流经验反馈机制重复定义
* `commands/start-patch-phase-router.md` 已加入自然触发词、隐式踩坑信号检测和路由规则
* `commands/delivery.md` 已加入 `tmp/` 待处理反馈文件检查、`retrospective.md` 与 `learn/` 分工说明
* `learn/README.md` 和 `learn/TEMPLATE.md` 已强调轻量化、真实开发口径，以及“AI 起草、人工决定是否回流”的边界
* 已存在一份示例记录 `learn/2026-03-31-learn-feedback-mechanism-sample.md`，说明该机制刚经历一轮实操优化

## Assumptions (temporary)

* 用户希望的是流程合理性评审与改进建议，不是立即实施改动
* 评估重点是“整体闭环是否顺手、会不会遗漏、会不会太重”，而不是追求制度完整性
* 若当前机制已满足实际开发需要，应明确说明“暂不建议修改”

## Open Questions

* 是否还存在跨文档表述不一致、责任边界不清或执行成本偏高的问题
* 是否需要进一步补强“谁来真正决策和回流”的收口动作

## Requirements (evolving)

* 基于真实文档现状做整体分析，不凭空假设
* 先判断合理性，再决定是否给出修改建议
* 建议必须是最小增量、方便实际开发执行
* 在用户未确认前，不直接改任何文档

## Acceptance Criteria (evolving)

* [ ] 明确说明该机制当前是否已经形成可执行闭环
* [ ] 若存在缺口，指出缺口发生在哪个环节，以及为什么会影响实际使用
* [ ] 若给出建议，建议应是轻量、可直接落地且不增加明显流程负担
* [ ] 不进行任何未获确认的文件修改

## Definition of Done (team quality bar)

* 结论建立在实际文档证据上
* 建议与当前工作流结构兼容
* 输出中明确区分：已合理部分 / 风险点 / 可选优化项

## Out of Scope (explicit)

* 不直接修改 `工作流总纲.md`、命令文档或 `learn/` 文档
* 不扩展成新的复杂命令体系或重型治理流程
* 不评估与“经验反馈机制”无关的整套新项目工作流质量

## Technical Notes

* 已检查：
  * `docs/workflows/新项目开发工作流/工作流总纲.md`
  * `docs/workflows/新项目开发工作流/commands/start-patch-phase-router.md`
  * `docs/workflows/新项目开发工作流/commands/delivery.md`
  * `docs/workflows/新项目开发工作流/learn/README.md`
  * `docs/workflows/新项目开发工作流/learn/TEMPLATE.md`
  * `docs/workflows/新项目开发工作流/learn/2026-03-31-learn-feedback-mechanism-sample.md`
* 评估重点：
  * 触发是否自然
  * 记录是否轻量
  * 回流是否有边界
  * 收尾是否防遗漏
  * 整体是否方便真实开发执行
