# brainstorm: 新项目工作流补充 todo.txt 初始化约定

## Goal

在 `./docs/workflows/新项目开发工作流/` 中补充一条初始化约定：在对应项目根目录初始化时生成 `todo.txt`，内容为当前项目的常规定时任务与协作提醒，例如任务完成后或上下文更新后同步更新文档、保持代码与文档同步。该约定需要在工作流文档与 README 中说明，但不引入额外流程步骤干预当前工作流。

## What I already know

* 用户明确要求补充的是 `./docs/workflows/新项目开发工作流/` 下的新项目开发工作流文档
* 新增内容聚焦于项目根目录的 `todo.txt`
* `todo.txt` 的定位是“当前项目常规定时任务”说明文件，而不是新的流程节点或自动化脚本
* 用户明确要求：初始化阶段生成该文档，并在 `README.md` 中说明
* 用户明确要求：不需要做额外的事情，不需要干预当前工作流
* 当前工作流目录下没有顶层 `README.md`，仅有 `learn/README.md`
* 现有初始化相关落点主要在 `工作流总纲.md §1.4 项目确认与初始化`、`commands/start-patch-phase-router.md` 与 `commands/install-workflow.py`
* `commands/install-workflow.py` 当前只会在目标项目根目录写入 `.trellis/workflow-installed.json`，不会生成 `todo.txt` 或修改根 `README.md`
* 用户已明确：这里的 `README.md` 指目标项目根目录的 `README.md`
* 用户已明确：初始化时生成的 `todo.txt` 默认只包含一条内容：`文档内容需要和实际当前的代码同步`

## Assumptions (temporary)

* 需要修改的主要文件位于 `docs/workflows/新项目开发工作流/` 目录下
* `todo.txt` 应在目标项目初始化时真实生成，而不是只作为文档约定示例
* 对目标项目根 `README.md` 的要求，应以工作流说明的方式提出，不需要在本仓库额外生成 README 模板

## Open Questions

* 无阻塞问题

## Requirements (evolving)

* 在新项目开发工作流文档中增加 `todo.txt` 初始化约定
* 说明 `todo.txt` 的用途与典型内容
* 说明 `todo.txt` 在初始化阶段生成
* 明确这里的 `README.md` 指目标项目根 `README.md`
* 要求目标项目根 `README.md` 说明 `todo.txt` 的存在与用途
* 初始化生成的 `todo.txt` 默认仅包含一条内容：`文档内容需要和实际当前的代码同步`
* 不新增会改变当前工作流执行方式的额外步骤或额外人工门禁

## Acceptance Criteria (evolving)

* [ ] `docs/workflows/新项目开发工作流/` 下相关文档明确说明初始化阶段需要生成 `todo.txt`
* [ ] 文档明确说明初始化生成的 `todo.txt` 默认内容为 `文档内容需要和实际当前的代码同步`
* [ ] 文档明确说明目标项目根 `README.md` 需要提到 `todo.txt` 的存在与用途
* [ ] 如涉及安装/初始化实现，目标项目初始化时会真实创建 `todo.txt`
* [ ] 文档与实现都不会引入新的强制人工干预步骤

## Definition of Done (team quality bar)

* Tests added/updated (unit/integration where appropriate)
* Lint / typecheck / CI green
* Docs/notes updated if behavior changes
* Rollout/rollback considered if risky

## Out of Scope (explicit)

* 修改当前工作流主线以增加新的人工审批或额外操作
* 扩展到其他工作流目录
* 在 `todo.txt` 初始化时写入多条默认任务
* 把 `todo.txt` 升级成新的检查门禁或状态机

## Technical Notes

* 已检查 `docs/workflows/新项目开发工作流/` 目录结构：无顶层 `README.md`，有 `工作流总纲.md`、`完整流程演练.md`、`命令映射.md`、`commands/`、`learn/`
* `工作流总纲.md §1.4` 已承载“项目确认与初始化”说明，适合补 `todo.txt` 初始化约定
* `commands/start-patch-phase-router.md` 已定义首次嵌入后的初始化门禁，若需要把 `todo.txt` 变成显式初始化检查，可落在这里；但这会比“只补文档说明”更强
* `commands/install-workflow.py` 当前真实安装产物不含 `todo.txt` 与根 `README.md` 修改，因此若要“初始化阶段生成”变成真实行为，需要改该脚本或补辅助脚本

## Research Notes

### What similar workflow points already do

* `工作流总纲.md §1.4` 负责项目确认后的初始化要求
* `commands/start-patch-phase-router.md` 负责首次嵌入后的初始化门禁与补齐要求
* `commands/install-workflow.py` 负责把工作流命令和辅助脚本安装到目标项目

### Constraints from our repo/project

* 当前工作流目录没有可直接同步说明该事项的顶层 `README.md`
* 用户要求“不需要干预当前工作流”，意味着不宜把 `todo.txt` 做成新的强制门禁或额外步骤
* 用户已确认“初始化阶段生成”是字面上的真实生成，因此仅改文档无法满足要求，必须改安装/初始化脚本或等价初始化实现
* 用户已确认目标项目根 `README.md` 需要说明该文件，而不是本工作流目录新增 README

### Feasible approaches here

**Approach A: 只补工作流文档约定**

* How it works:
  * 在 `工作流总纲.md` 的初始化部分说明：目标项目根目录应建立 `todo.txt`
  * 在相关说明文档中补充 README 需要声明 `todo.txt` 的存在与用途
* Pros:
  * 不改变当前工作流执行链路
  * 符合“不要额外干预当前工作流”
* Cons:
  * 无法满足“初始化时真实生成 `todo.txt`”

**Approach B: 在安装/初始化脚本中真实生成 `todo.txt`** (Recommended)

* How it works:
  * 修改 `commands/install-workflow.py`，在目标项目根目录写入 `todo.txt` 模板
  * 同时补充工作流文档，说明目标项目根 `README.md` 应记录该文件用途
* Pros:
  * 能真正满足“初始化阶段就生成该文档”
  * 用户不用手动补文件
* Cons:
  * 需要新增很小的初始化实现，但不改变主流程和阶段路由

## Technical Approach

在不改动阶段路由和门禁的前提下：

* 在 `工作流总纲.md` 的 `§1.4 项目确认与初始化` 中补充 `todo.txt` 初始化要求
* 在适合描述初始化产物/安装结果的位置补充：目标项目根 `README.md` 需要说明 `todo.txt` 的存在与用途
* 修改 `commands/install-workflow.py`，使目标项目初始化时真实创建 `todo.txt`，默认内容仅一条：`文档内容需要和实际当前的代码同步`
* 若需要，补充安装脚本测试，验证 `todo.txt` 被创建且内容正确

## Decision (ADR-lite)

**Context**: 用户要求在新项目初始化阶段就生成项目根目录 `todo.txt`，并要求目标项目根 `README.md` 对该文件作说明，同时又不希望增加新的工作流干预步骤。

**Decision**: 采用 Approach B。通过最小化修改初始化安装脚本来真实生成 `todo.txt`，并仅在工作流文档中补充说明，不把该文件纳入新的门禁或阶段路由。

**Consequences**:

* 初始化行为会多一个轻量产物 `todo.txt`
* 当前工作流主链与命令路由保持不变
* 目标项目根 `README.md` 的说明要求将通过工作流文档传播，而不是在本仓库额外维护一个 README 模板
