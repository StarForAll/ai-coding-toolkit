# brainstorm: 新项目开发工作流补充 PRD 规范接入

## Goal

在 `docs/workflows/新项目开发工作流/` 的具体工作流实现中，补充一条明确可执行的要求：当项目嵌入对应自定义工作流后，必须立即在 `trellis-library` 中补充与该工作流匹配的“面向客户”和“面向开发人员”的 PRD 规范资产，并让相关步骤、产物和后续验证路径保持一致。

## What I already know

* `docs/workflows/新项目开发工作流/commands/start-patch-phase-router.md` 当前只描述了 `/trellis:start` 的阶段路由，没有提到自定义工作流嵌入后的 PRD 规范补充动作。
* `docs/workflows/自定义工作流制作规范.md` 已定义“通过工作流子目录分发并注入 start patch”的制作方式。
* `trellis-library/specs/universal-domains/product-and-requirements/` 下已存在 `prd-documentation`、`prd-documentation-customer-facing`、`prd-documentation-developer-facing` 等规范。
* `trellis-library/checklists/universal-domains/product-and-requirements/` 下也已存在 customer-facing 和 developer-facing PRD checklist，可作为工作流中引用的验证资产。

## Assumptions (temporary)

* 本次主要是补充工作流文档与相关说明，不需要新建全新的 PRD 规范内容。
* 如需补充 `trellis-library` 侧引用或说明，更可能是补充索引/映射/工作流说明，而不是重写现有 normative rules。

## Open Questions

* 应该把该动作落在 `新项目开发工作流` 的哪一个具体步骤中，才能既符合现有阶段划分，又不和现有 PRD/设计/计划阶段冲突？

## Requirements (evolving)

* 明确自定义工作流嵌入完成后，必须立即补充或登记对应的 PRD 规范资产。
* 说明该 PRD 规范至少覆盖 customer-facing 与 developer-facing 两个面向。
* 让工作流读者知道应该引用 `trellis-library` 中哪一组规范/检查清单。

## Acceptance Criteria (evolving)

* [ ] `docs/workflows/新项目开发工作流/` 中有明确步骤描述该补充动作及其时机。
* [ ] 文档能指向 `trellis-library` 中相关 PRD 规范或检查清单。
* [ ] 变更后的说明与现有阶段定义不冲突，读者能看出后续如何继续执行。

## Definition of Done (team quality bar)

* Tests added/updated (unit/integration where appropriate)
* Lint / typecheck / CI green
* Docs/notes updated if behavior changes
* Rollout/rollback considered if risky

## Out of Scope (explicit)

* 不改写整套 AI Workflow 方法论。
* 不重新设计 customer-facing / developer-facing PRD 的内容结构。
* 不新增与本次需求无关的 workflow 命令。

## Technical Notes

* 重点候选文件：
  * `docs/workflows/新项目开发工作流/工作流总纲.md`
  * `docs/workflows/新项目开发工作流/commands/start-patch-phase-router.md`
  * `docs/workflows/自定义工作流制作规范.md`
* 已发现相关 library 资产：
  * `trellis-library/specs/universal-domains/product-and-requirements/prd-documentation/normative-rules.md`
  * `trellis-library/specs/universal-domains/product-and-requirements/prd-documentation-customer-facing/normative-rules.md`
  * `trellis-library/specs/universal-domains/product-and-requirements/prd-documentation-developer-facing/normative-rules.md`
  * `trellis-library/checklists/universal-domains/product-and-requirements/customer-facing-prd-checklist.md`
  * `trellis-library/checklists/universal-domains/product-and-requirements/developer-facing-prd-checklist.md`
