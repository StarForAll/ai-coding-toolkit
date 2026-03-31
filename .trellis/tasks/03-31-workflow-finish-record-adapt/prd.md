# brainstorm: 新项目工作流补充 finish-work 和 record-session 自适应修正

## Goal

让 `docs/workflows/新项目开发工作流/` 在“技术架构确认后补充项目 spec”的阶段，明确引导用户同步检查并轻量修正对应项目中的 `/trellis:finish-work` 和 `/trellis:record-session`，使其与当前项目的技术栈、校验命令、交付边界、会话记录约束保持一致；仅提供流程与文案引导，不引入复杂自动化机制。

## What I already know

* 现有 `docs/workflows/新项目开发工作流/commands/design.md` 已在“下一步推荐”中要求：技术架构确认后先导入合适 spec，并对项目 `.trellis/spec/` 做项目化完善，然后才进入 `/trellis:plan`。
* 现有 `docs/workflows/新项目开发工作流/工作流总纲.md` 的 `3.7 技术架构确认后的项目 Spec 对齐` 已要求完成 spec 导入、项目化完善、自动化检查矩阵定义，但没有把 `/trellis:finish-work` 与 `/trellis:record-session` 的项目自适应修正明确纳入这一阶段的输出。
* 当前通用 `.claude/commands/trellis/finish-work.md` 是偏通用/应用型清单；项目内 `.agents/skills/finish-work/SKILL.md` 已有一版元项目定制，但工作流文档没有在设计阶段提醒“新项目要按自身项目内容定制 finish-work”。
* 当前通用 `.claude/commands/trellis/record-session.md` 主要讲记录步骤；新项目工作流额外通过 `docs/workflows/新项目开发工作流/commands/shell/record-session-helper.py` 和工作流总纲/命令映射定义了元数据闭环门禁，但也没有在技术架构确认后的 spec 对齐阶段要求“对应项目应按自己的任务流、归档边界、helper 入口做适配说明”。
* 用户明确要求：目标是“引导对应的用户去进行自适应修改”，不需要做复杂机制实现。

## Assumptions (temporary)

* 本次优先改工作流文案与引导顺序，不新增新的 helper 脚本、自动检测器或安装补丁逻辑。
* 自适应修正主要体现为：在项目完成 spec 对齐后，用户需要同步检查并修正该项目里的 `/trellis:finish-work` 与 `/trellis:record-session` 文案/命令/门禁说明，而不是由本仓库自动生成这些内容。
* 为避免文档漂移，至少需要同步更新工作流主文档和对应命令文档；是否同时更新演练文档与命令映射，需要进一步确认范围。

## Open Questions

* 最终变更范围是只覆盖“主链路文档 + design 命令”，还是也要同步覆盖“命令映射 + 完整流程演练”？

## Requirements (evolving)

* 在技术架构确认后的 spec 对齐阶段，新增一条明确动作：检查并按当前项目情况修正 `/trellis:finish-work`。
* 在技术架构确认后的 spec 对齐阶段，新增一条明确动作：检查并按当前项目情况修正 `/trellis:record-session`。
* 引导内容必须强调“轻量人工适配”，不要引入自动化生成或复杂机制。
* 引导内容应说明修正依据至少包括：技术栈、真实检查命令、任务归档规则、会话记录入口、交付/元数据边界。
* 工作流链路中的相关文档表述应前后一致，避免一个地方要求适配、另一个地方仍按通用命令描述。
* 阶段策略采用“基线前置 + 后续校正”：
  * `/trellis:finish-work` 的主适配阶段放在 `§3.7 技术架构确认后的项目 Spec 对齐`
  * `/trellis:record-session` 的基线适配也放在 `§3.7`，但允许在 `§4 plan` 后按任务归档与交付边界再做一次轻量校正

## Acceptance Criteria (evolving)

* [ ] 设计阶段文档明确写出：补 spec 后，还要同步检查并修正项目内 `/trellis:finish-work` 与 `/trellis:record-session`
* [ ] 文档对这两个命令的修正范围给出具体但轻量的指导项
* [ ] 文档没有引入新的复杂机制、自动生成器或额外系统
* [ ] 至少主链路文档与命令文档之间不存在表述冲突

## Definition of Done (team quality bar)

* 相关工作流文档已更新
* 相关说明前后一致
* 验证命令已运行并说明结果

## Out of Scope (explicit)

* 不实现新的命令自动 patch / 自动生成机制
* 不改造 `record-session-helper.py` 或新增 finish-work helper
* 不为所有项目提供完整模板生成器

## Technical Notes

* 已检查文件：
  * `docs/workflows/新项目开发工作流/commands/design.md`
  * `docs/workflows/新项目开发工作流/工作流总纲.md`
  * `docs/workflows/新项目开发工作流/命令映射.md`
  * `docs/workflows/新项目开发工作流/commands/shell/record-session-helper.py`
  * `.claude/commands/trellis/finish-work.md`
  * `.claude/commands/trellis/record-session.md`
  * `.agents/skills/finish-work/SKILL.md`
* 关键约束：
  * `record-session` 在新项目工作流里已有 helper 闭环约束，设计阶段若要求项目自适应，就应提醒用户确认最终项目实际入口和前置门禁。
  * `finish-work` 的项目差异主要来自真实 lint/typecheck/test/build/security 检查命令，适合与 `3.7` 中的“自动化检查矩阵”一起定义。

## Decision (ADR-lite)

**Context**：需要决定 `/trellis:finish-work` 与 `/trellis:record-session` 应该在哪个阶段做项目自适应，既要足够早，避免后续沿用通用模板，又不能过早到连技术栈/任务边界都还没确定。

**Decision**：
- `/trellis:finish-work`：主适配阶段放在 `§3.7 技术架构确认后的项目 Spec 对齐`
- `/trellis:record-session`：基线适配同样放在 `§3.7`，并在 `§4 plan` 之后允许做一次轻量复核，补齐“什么任务算完成、何时 archive、最终通过什么入口记录 session”的项目化边界

**Consequences**：
- 好处：在进入 `/trellis:plan`、`/trellis:start` 前，就把收尾门禁和记录规则项目化，避免实现阶段继续沿用通用命令
- 好处：`finish-work` 可以直接绑定 `3.7` 的自动化检查矩阵，不会脱离真实项目命令
- 好处：`record-session` 不需要等到收尾时才第一次思考，但又保留在 plan 之后按任务结构做一次轻量修正的空间
- 代价：文档里需要明确区分“基线适配”和“后续轻量校正”，避免用户误以为要在多个阶段重复大改
