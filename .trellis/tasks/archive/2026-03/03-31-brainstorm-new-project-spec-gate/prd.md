# brainstorm: 校验新项目工作流 spec 对齐门禁

## Goal

确认 `docs/workflows/新项目开发工作流/` 中是否已经在“技术架构经用户明确确认后”定义了两个必须串行执行的项目级 spec 任务；若缺失，再继续澄清并补充。

## What I already know

* 用户要求在 `./docs/workflows/新项目开发工作流` 中，于技术架构被用户明确确认且后续不再变化后，增加两个串行任务：
  * 任务 1：根据技术架构从 `trellis-library` 获取合适 spec，添加到当前项目 `.trellis/spec`
  * 任务 2：结合项目作用、背景、技术架构等，对当前项目 `.trellis/spec` 做分析完善，删除错误内容并补充缺失内容
* 用户明确要求：如果工作流中已经存在上述任务，则忽略；如果不存在，再讨论清楚并在用户确认后添加。
* `docs/workflows/新项目开发工作流/工作流总纲.md` 已存在 `3.7 技术架构确认后的项目 Spec 对齐` 节点，并明确写出：
  * 触发条件是“技术架构已经被用户明确确认”
  * 必须按顺序先从 `trellis-library` 导入合适 spec，再对当前项目 `.trellis/spec/` 做项目化完善
* `docs/workflows/新项目开发工作流/commands/design.md` 已把这两个任务列为进入 `/trellis:plan` 前的前置任务。
* `docs/workflows/新项目开发工作流/commands/plan.md` 已把这两个任务写入 `/trellis:plan` 前置条件，并明确任务 1 必须先于任务 2。
* 仓库内已有归档任务 `.trellis/tasks/archive/2026-03/03-22-new-project-workflow-prd-spec/prd.md`，其需求描述与本次用户要求高度一致，说明这件事此前已经被规划并落地。

## Assumptions (temporary)

* 当前用户更关心“是否已存在并满足要求”，而不是要继续改写现有表述。
* 只要当前工作流中已有明确、顺序正确、与 `/trellis:plan` 衔接清晰的定义，本次就应按“忽略”处理，不再新增重复内容。

## Open Questions

* 若用户认为当前表述仍不够理想，是否希望进一步做“去重/收敛/措辞强化”，而不是重复新增同类步骤。

## Requirements (evolving)

* 验证“技术架构经用户确认后”的触发节点是否存在。
* 验证两个 spec 任务是否都已存在，并且顺序不可交换。
* 验证 `/trellis:plan` 是否把这两个任务作为前置条件。
* 若以上均已满足，则不新增重复内容。

## Acceptance Criteria (evolving)

* [ ] 能给出至少一处主文档证据，证明触发节点与两个顺序任务已存在。
* [ ] 能给出至少一处命令文档证据，证明 `/trellis:plan` 前置条件已接入。
* [ ] 结论明确区分“已存在，故忽略”和“缺失，需要补充”两种情况。

## Definition of Done (team quality bar)

* 结论有具体文件与行号支撑
* 不重复新增已存在的流程定义
* 若无代码/文档修改，明确说明未修改

## Out of Scope (explicit)

* 本轮不重写 `trellis-library` 中具体 spec 正文
* 本轮不主动做文档措辞优化或结构重排，除非用户进一步要求
* 本轮不进入实际工作流文档编辑

## Technical Notes

* 已检查文件：
  * `docs/workflows/新项目开发工作流/工作流总纲.md`
  * `docs/workflows/新项目开发工作流/commands/design.md`
  * `docs/workflows/新项目开发工作流/commands/plan.md`
  * `docs/workflows/新项目开发工作流/命令映射.md`
  * `docs/workflows/新项目开发工作流/完整流程演练.md`
  * `.trellis/tasks/archive/2026-03/03-22-new-project-workflow-prd-spec/prd.md`
* 关键证据：
  * `工作流总纲.md` 的 `3.7` 已定义主门禁
  * `design.md` 已在“下一步推荐”中承接
  * `plan.md` 已在前置条件中承接

## Research Notes

### 当前文档的主要问题

* **不是缺任务，而是跨文件定义分散**
  * `工作流总纲.md` 的 `3.7` 已是最完整定义
  * `design.md`、`plan.md`、`命令映射.md`、`完整流程演练.md` 都在重复承接这套门禁
* **阶段一与阶段三的 spec 导入边界仍容易误读**
  * 阶段一写的是“外部项目专用的交付控制 spec 预置”
  * 阶段三写的是“技术架构确认后的项目级 spec 对齐”
  * 两者都提到从 `trellis-library` 导入到 `.trellis/spec/`，但边界说明还不够集中
* **`design.md` 与 `工作流总纲.md` 的门禁粒度不完全一致**
  * `design.md` 把进入 `/trellis:plan` 前的任务压缩成 4 条
  * `工作流总纲.md` 的 `3.7` 已展开为 6 个动作，其中明确拆开了 `finish-work` 和 `record-session`
* **`plan.md` 的前置条件仍偏弱**
  * 已接入任务 1 / 2 / 3
  * 但尚未显式要求：`finish-work` 已完成首次项目化适配、`record-session` 已完成基线适配
* **“必选资产”表述仍有收敛空间**
  * `design.md` 使用了 `product-and-requirements.*`、`architecture.*`、`verification.*` 这样的族级写法
  * 这种写法便于表达范围，但容易被误读成“整个命名空间下所有 spec 都必选”

### Feasible approaches here

**Approach A: 最小一致性收敛** (Recommended)

* How it works:
  * 保留 `工作流总纲.md §3.7` 作为主定义
  * 调整 `design.md` / `plan.md` / `命令映射.md` / `完整流程演练.md`，让它们只承接或摘要，不再各自重新定义不同粒度版本
  * 补强“阶段一外部项目预置资产”与“阶段三项目级 spec 对齐”的边界说明
* Pros:
  * 改动小，风险低
  * 可以消除现在最主要的不一致
  * 不会重写整套工作流结构
* Cons:
  * 仍会保留一定跨文件重复，只是重复变得一致

**Approach B: 强主文档化重构**

* How it works:
  * 明确 `工作流总纲.md §3.7` 为唯一规范定义
  * 其余文件统一改成“引用 + 极短摘要 + 跳转”
  * 同时重排 `design.md` / `plan.md` 的前置条件结构
* Pros:
  * 长期维护成本最低
  * 源头最清楚
* Cons:
  * 改动面更大
  * 容易影响已有命令文档的独立可读性
