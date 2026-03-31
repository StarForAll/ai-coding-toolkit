# brainstorm: 新项目开发工作流经验反馈优化机制

## Goal

为 `docs/workflows/新项目开发工作流/` 补齐一套可执行的“经验反馈优化机制”，把实际使用过程中的问题、经验、优化建议沉淀为 `learn/` 目录下的 Markdown 文档，并定义何时读取、如何判断“是否值得学习优化”、以及在人工介入确认后如何回流到工作流文档与命令体系。

## What I already know

* `docs/workflows/新项目开发工作流/learn/` 目录已存在，但目前为空，尚未形成入口文档、记录模板或筛选规则。
* `docs/workflows/新项目开发工作流/工作流总纲.md` 已有分散内容：
* `§5.2 人工介入机制` 定义了若干需要人工接管的触发条件与“介入结论记录”。
* `§6.6.4 反馈学习流程` 与 `§6.6.5 定期复盘会议` 主要围绕 Bug 修复后的学习闭环。
* `§7.3 经验沉淀` 只给出高层要求，未定义目录、文档契约、筛选标准与回流动作。
* `docs/workflows/新项目开发工作流/commands/delivery.md` 的 Step 9 已提到“经验沉淀”，但当前仍是抽象描述，未绑定 `learn/` 目录或具体执行步骤。
* 仓库中已有可借鉴模式：
* `.trellis/tasks/archive/2026-03/03-30-dual-track-e2e-simulation/delivery/retrospective.md` 展示了复盘文档的基本结构。
* `.agents/skills/break-loop/SKILL.md` 定义了“修完 Bug 后要把经验沉淀回规范”的思想，但它更偏调试/规范层，不直接覆盖工作流目录下的 learn 机制。

## Assumptions (temporary)

* 本次优先补“文档机制 + 最低模板 + 主流程挂点”，不默认新增新的 slash command 或自动评分脚本。
* “是否值得学习优化”应采用人工主导、AI 辅助判断，而不是全自动修改工作流。
* 经验反馈源既包括 Bug，也包括流程摩擦、命令误用、文档歧义、人工介入触发、交付阶段暴露的问题。

## Open Questions

* MVP 是否只做文档机制闭环，还是要同时补一个辅助模板/清单供 `delivery` 或后续维护时直接使用？

## Requirements (evolving)

* 明确说明为什么需要补充该机制，以及它与现有 `经验沉淀` / `反馈学习流程` 的关系。
* 在 `新项目开发工作流` 目录下定义 `learn/` 的职责、文档放置规则与最低字段契约。
* 定义“值得学习优化”的判断标准，至少覆盖重复性、影响面、可复用性、改造成本、人工确认门槛。
* 定义人工介入点：哪些情况下只能记录、不应直接改流程；哪些情况下可进入人工确认后的工作流优化。
* 将机制接入现有主流程文档，至少让使用者知道在何时记录、何时筛选、何时优化。
* 如有必要，更新 `命令映射.md` 或相关工作流说明，避免总纲与命令文档脱节。

## Acceptance Criteria (evolving)

* [ ] `工作流总纲.md` 明确新增或完善“经验反馈优化机制”章节，包含记录、筛选、人工介入、回流优化四步闭环。
* [ ] `learn/` 目录下至少有一份说明性文档或模板，能指导如何记录问题与经验。
* [ ] `delivery.md` 或其他合适入口明确指出经验反馈应沉淀到 `learn/`，而不是停留在抽象“复盘”表述。
* [ ] 文档中清楚区分“记录问题”与“批准修改工作流”是两个阶段，后一阶段必须人工介入。
* [ ] 相关文档之间不存在明显冲突，读者能从主流程找到 learn 机制入口。

## Definition of Done (team quality bar)

* Docs updated and internally consistent
* Relevant validation/read-through completed
* Scope boundary and manual-intervention boundary made explicit

## Out of Scope (explicit)

* 自动读取 `learn/` 并自动改写工作流的脚本化实现
* 新增复杂数据库、索引或知识库系统
* 为所有工作流统一引入 learn 机制的全仓库重构

## Technical Notes

* Primary target directory: `docs/workflows/新项目开发工作流/`
* Likely files to change:
* `docs/workflows/新项目开发工作流/工作流总纲.md`
* `docs/workflows/新项目开发工作流/commands/delivery.md`
* `docs/workflows/新项目开发工作流/命令映射.md`（视挂点是否需要）
* `docs/workflows/新项目开发工作流/learn/*`
* Research notes:
* 现有总纲已经覆盖 Bug 反馈学习、人工介入、经验沉淀，但缺少统一的 learn 目录契约和“值得学习优化”的筛选门槛。
* 已存在 `learn/` 空目录，说明结构预留已做，但机制尚未成型。
