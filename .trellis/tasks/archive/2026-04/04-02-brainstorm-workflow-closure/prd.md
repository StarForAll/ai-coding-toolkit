# brainstorm: 补全新项目开发工作流执行闭环

## Goal

补全 `docs/workflows/新项目开发工作流/` 中“流程层面已经定义，但执行闭环仍未真正落地”的部分，确保讨论对象是这套新项目工作流本身，而不是当前仓库作为设计仓库的内部开发流程。

## What I already know

* 用户要求分析并补全的是 [docs/workflows/新项目开发工作流](/ops/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流)，不是当前仓库自己的日常开发流程。
* 这套 workflow 的安装前提是目标项目已经执行过 `trellis init`；目标项目里本来就存在 Trellis 原生命令/技能，workflow 做的是“嵌入”和“增强”，不是从零重建整套命令。
* 主链文档已经把新项目工作流定义为 `feasibility -> brainstorm -> design -> plan -> test-first -> start -> self-review -> check -> finish-work -> delivery -> record-session`。
* [命令映射.md](/ops/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/命令映射.md) 和 [多CLI通用新项目完整流程演练.md](/ops/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/多CLI通用新项目完整流程演练.md) 都把 `finish-work`、`record-session` 视为正式阶段。
* 当前仓库中实际存在 Trellis 原生的 [finish-work.md](/ops/projects/personal/ai-coding-toolkit/.claude/commands/trellis/finish-work.md)、[record-session.md](/ops/projects/personal/ai-coding-toolkit/.claude/commands/trellis/record-session.md) 以及对应 skills，因此这两个阶段并非“缺失”，而是复用基线资产。
* 当前存在 [record-session-patch-metadata-closure.md](/ops/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/commands/record-session-patch-metadata-closure.md)，说明 `record-session` 采用“保留目标项目原生命令 + 注入 workflow 补丁”的模型。
* [install-workflow.py](/ops/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/commands/install-workflow.py) / [upgrade-compat.py](/ops/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/commands/upgrade-compat.py) 的 `NEW_COMMANDS` 只覆盖到 `delivery`，说明 workflow 新增分发的是前半段阶段命令；`start.md` 和 `record-session.md` 走的是补丁/恢复链路。
* [test_workflow_installers.py](/ops/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/commands/test_workflow_installers.py) 已显式构造 Trellis 基线 `record-session.md`，并验证安装器会把元数据闭环说明注入进去。
* [docs/workflows/自定义工作流制作规范.md](/ops/projects/personal/ai-coding-toolkit/docs/workflows/自定义工作流制作规范.md) 仍写着“唯一冲突点是 `start.md`”，这与当前实际机制不一致，因为 `record-session.md` 也已经是补丁注入与升级恢复点。
* 平台适配 README 展示的 workflow 自定义命令树通常只列到 `delivery`，没有明确说清“`finish-work` / `record-session` 属于 Trellis 原生基线，其中 `record-session` 会被 workflow 增强”。
* [learn/README.md](/ops/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/learn/README.md) 里举了 `2026-03-31-record-session-closure-gap.md` 作为示例文件名，但 `learn/` 目录下实际并不存在该文件，说明“示例/索引层”与“真实资产层”也存在轻微脱节。

## Assumptions (temporary)

* 本轮目标不是评审整套 workflow 是否合理，而是补齐那些已经被主链承诺、但“嵌入机制、继承关系、补丁口径、升级校验”尚未讲清或收口不完整的地方。
* “补全”更可能需要修正文档层、嵌入规范和安装/升级脚本说明之间的对应关系，而不是简单新增缺失命令文件。
* 用户更关心最小可执行闭环，而不是继续增加新的阶段或复杂机制。

## Open Questions

* 本轮补全是否只聚焦“原生命令继承 + workflow 补丁增强”这条嵌入闭环，还是连同其它轻度一致性问题一并收口？

## Requirements (evolving)

* 分析对象必须限定为 `docs/workflows/新项目开发工作流/` 这套 workflow。
* 结论必须基于现有文档、Trellis 原生命令基线、安装器、升级脚本与测试的实际状态。
* 需要区分三类资产：Trellis 原生已有、workflow 新增分发、workflow 对原生命令做补丁增强。
* 需要明确指出哪些内容已经“流程有定义”，但在嵌入/继承/补丁/升级校验层仍未闭环。
* 补全方案应优先选择最小增量，避免引入新的重型流程。

## Acceptance Criteria (evolving)

* [ ] 明确列出当前 workflow 中至少一组“流程定义存在，但嵌入闭环未收完”的具体缺口。
* [ ] 每个缺口都能定位到对应文档、补丁文件、安装器或测试，而不是抽象判断。
* [ ] 输出的补全方向能说明需要改的是文档口径、嵌入规范、安装/升级逻辑还是多者联动。
* [ ] 不把 Trellis 原生命令误判为 workflow 缺失资产。
* [ ] 不把“当前仓库自己的开发流程”误当成目标 workflow 本身。

## Definition of Done (team quality bar)

* 需求范围和补全对象边界清楚。
* 已识别的缺口能够直接转成后续实施项。
* 输出中区分“主缺口”和“次要一致性问题”。

## Out of Scope (explicit)

* 不评审当前仓库所有 Trellis 技能或全局 AGENTS 设计质量。
* 不把“目标项目如何实际使用这套 workflow”扩展成新的业务案例设计。
* 不在本阶段直接修改文件，除非用户确认补全范围后进入实施。

## Technical Notes

* 已检查的核心文件：
  * [工作流总纲.md](/ops/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/工作流总纲.md)
  * [命令映射.md](/ops/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/命令映射.md)
  * [多CLI通用新项目完整流程演练.md](/ops/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/多CLI通用新项目完整流程演练.md)
  * [完整流程演练.md](/ops/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/完整流程演练.md)
  * [commands/design.md](/ops/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/commands/design.md)
  * [commands/plan.md](/ops/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/commands/plan.md)
  * [commands/test-first.md](/ops/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/commands/test-first.md)
  * [commands/self-review.md](/ops/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/commands/self-review.md)
  * [commands/check.md](/ops/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/commands/check.md)
  * [commands/delivery.md](/ops/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/commands/delivery.md)
  * [commands/install-workflow.py](/ops/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/commands/install-workflow.py)
  * [commands/upgrade-compat.py](/ops/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/commands/upgrade-compat.py)
  * [learn/README.md](/ops/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/learn/README.md)
* 修正后的主缺口候选：
  * workflow 文档对“哪些阶段来自 Trellis 原生、哪些阶段由 workflow 新增、哪些阶段靠补丁增强”讲得还不够明确。
  * `record-session` 的补丁增强和升级恢复机制已经存在，但上游嵌入规范仍保留“唯一冲突点是 `start.md`”的旧口径。
  * 平台适配层对收尾链末端的继承关系展示不足，容易让阅读者误以为 workflow 本身缺少 `finish-work` / `record-session`。
  * learn 目录示例与真实文件存在轻微脱节。
