# brainstorm: 完善新项目开发工作流任务生成规则

## Goal

在 `docs/workflows/新项目开发工作流/` 中补齐“生成具体任务之前”的前置判定规则，确保工作流在进入任务拆解与执行前，先判断当前需求描述是否准确，再判断任务是否复杂、是否需要拆分为多个子任务、是否需要先发散补齐更详细的信息；同时明确单个上下文只负责一个任务，并且该任务上下文内应覆盖代码实现、代码检测、质量检测、代码修复的完整闭环。

## What I already know

* `docs/workflows/新项目开发工作流/commands/brainstorm.md` 当前不存在，`brainstorm` 规则主要散落在 `工作流总纲.md`、`命令映射.md` 及上下游命令中。
* `docs/workflows/新项目开发工作流/工作流总纲.md` 的阶段二已经要求做详细需求分析、识别缺失信息、隐含假设与边界条件，但还没有把“需求描述准确性校验 -> 复杂度判断 -> 是否拆 sub task -> 是否先发散补信息 -> 再生成具体任务”串成一条显式前置流程。
* `docs/workflows/新项目开发工作流/工作流总纲.md` 的 `4.1.1` 和 `4.1.2` 已经覆盖“按上下文预算拆分任务”“单个上下文可完整实现（Token 预算内）”“人工审核任务拆解完整性”等规则。
* `docs/workflows/新项目开发工作流/commands/plan.md` 已要求 `task_plan.md` 写出任务拆解、依赖关系、执行安排、任务执行矩阵，并校验“单任务独立可测试”“单上下文可完整实现（Token 预算内）”。
* `docs/workflows/新项目开发工作流/工作流总纲.md` 的阶段五和 `commands/check.md` 已经覆盖任务执行后的实现、自审、多 CLI 补充审查、修复和重新验证闭环。
* `docs/workflows/新项目开发工作流/工作流总纲.md` 的 `5.6.2` 已明确“复杂任务需拆分为多个可闭环的子任务”，但这条规则出现在偏后面的执行/调试链路，不在 brainstorm 或 plan 入口。
* 目前已有规则更偏向“任务已经生成后怎么执行与验证”，而你要补的是“任务生成前如何判断是否该生成、该怎么生成、是否该先拆分或补信息”。

## Assumptions (temporary)

* 本次改动以补充工作流文档和命令说明为主，不默认新增脚本，除非现有结构无法清晰承载这些规则。
* “如果对应工作流中已经存在上述任务则忽略” 的含义是：已有等价规则则不重复新增，只补缺口与衔接位置，不重复造概念。
* 若现有 `brainstorm` 规则仍主要落在总纲中，则本次可能需要决定：是仅更新总纲/plan，还是新增独立 `commands/brainstorm.md` 来承载这些入口规则。

## Open Questions

* 当前无阻塞问题，等待用户确认规则草案后执行文档修改。

## Requirements (evolving)

* 在生成具体任务前，必须先判断当前需求描述是否准确、完整、无明显歧义。
* 只有在需求描述满足前置准确性要求后，才进入复杂度判断。
* 复杂度判断后，必须明确是否需要拆成多个子任务（sub task）执行。
* 若当前信息不足以高质量拆任务，必须先做发散补充，补齐背景、边界、技术细节或风险点，再进入具体任务生成。
* 单个上下文中只允许负责一个任务；若任务超出单上下文可闭环范围，必须拆分。
* 单个任务的执行上下文中，必须覆盖代码实现、代码检测、质量检测、代码修复的完整闭环。
* 若现有工作流已经存在等价规则，则不重复添加；若不存在或不足，则先与用户讨论并确认后再补入文档。
* 简单且需求已准确的任务，允许在 `brainstorm` 后直接收敛为“单任务执行”，不强制先输出显式 `task_plan.md`。
* `brainstorm` 阶段的复杂度判断统一复用现有 `L0/L1/L2` 口径，避免与 `plan`、`self-review`、`check` 的规则冲突。

## Acceptance Criteria (evolving)

* [ ] 能明确指出当前工作流里哪些规则已存在、哪些缺失、哪些只是部分覆盖。
* [ ] 工作流文档中出现“需求描述准确性校验 -> 复杂度判断 -> 是否拆 sub task -> 是否发散补信息 -> 再生成具体任务”的清晰顺序。
* [ ] 文档明确“单个上下文只完成单个任务”的适用位置与约束，不只是在后置执行阶段零散出现。
* [ ] 文档明确单任务上下文必须包含实现、检测、质量审查、修复闭环。
* [ ] 若新增规则落地，读者能看出它与现有 `plan`、`start`、`check`、阶段五执行链路的衔接关系。

## Definition of Done (team quality bar)

* Docs/notes updated if behavior changes
* Validation run for changed workflow files when applicable
* No duplicate rule text that conflicts with existing workflow stages

## Out of Scope (explicit)

* 不重写整套新项目开发工作流。
* 不在未确认范围前直接新增大段脚本逻辑或命令实现。
* 不重复添加已经完整存在且语义等价的规则。
* 不把“任务执行后的修复/审查流程”误当成“任务生成前的入口判定流程”。

## Technical Notes

* 已检查：
  * `docs/workflows/新项目开发工作流/工作流总纲.md`
  * `docs/workflows/新项目开发工作流/commands/plan.md`
  * `docs/workflows/新项目开发工作流/commands/design.md`
  * `docs/workflows/新项目开发工作流/commands/check.md`
* 关键现状：
  * `plan` 已有“按上下文预算拆分”“单上下文可完整实现”
  * 阶段五已有实现/检测/修复闭环
  * 缺少一个明确放在 brainstorm/任务生成前的前置分类层
  * `commands/brainstorm.md` 缺失，可能影响规则承载位置
* 已确认决策：
  * 本次采用“新增独立 `docs/workflows/新项目开发工作流/commands/brainstorm.md`”的方式承载 `brainstorm` 前置判定规则
  * 需要同时回链 `工作流总纲.md`、`命令映射.md`、上下游命令说明，避免只有入口文件而主链路不同步
  * 简单且需求已准确的任务允许在 `brainstorm` 后直接进入单任务实施闭环
  * 复杂度判断统一采用 `L0/L1/L2` 口径：`L0` 单任务闭环，`L1` 进入 `plan` 拆解，`L2` 先发散补信息再拆成多个子任务
