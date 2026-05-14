# 修订新项目开发工作流审计后续文档

## Goal

根据本轮 `workflow-audit` 结论，直接修订 `docs/workflows/新项目开发工作流/`
中的 workflow 源文档，收紧冻结后变更收费处理、`review-gate` 轻量化、
`delivery` 的缺陷反馈机制，以及 `humanizer-zh` 在用户向文档中的执行边界，
让规则更贴近实际开发和交付过程。

## What I already know

* 本轮需求边界已经由用户明确，不需要再继续口头收敛。
* 需求冻结后的变更处理不需要写死价格表，但要明确：
  * 是否收费
  * 用户是否接受
  * 是否并入当前轮次
* 用户接受时并入当前轮次；不接受时忽略，不并入当前交付。
* `review-gate` 默认应走 `lite`：
  * `lite` 默认 1 个 reviewer
  * 若 reviewer 发现新问题，再使用 `multi-cli-review-action` 做汇总和修复
* `project-audit` 不复用 `lite`，保持 `full`。
* `review-gate` 的“3 轮”是建议值，不是硬上限；用户明确要求时允许继续。
* `review-gate` 的问题不是拖慢进度，而是默认层级应更贴近日常使用。
* `delivery` 中的 `Step 9a` / `Step 9b` 都不需要保留为默认主链要求。
* `humanizer-zh` 默认覆盖目标项目 `docs/` 目录下的非技术性文档。
* `humanizer-zh` 暂不默认覆盖：
  * `developer-facing-prd.md`
  * `transfer-checklist.md`
  * `retrospective.md`
* 如果用户明确要求某个文件做 `humanizer-zh` 优化，即使不在默认范围内也应执行。
* `humanizer-zh` 的执行时机已定：
  * 初稿完成后一次
  * 交付前一次
  * 项目整体完成后再一次

## Assumptions (temporary)

* 本次改动主要集中在 workflow 产品文档，不涉及安装器、upgrade-compat 或
  `/tmp` runtime validation。
* 改动会跨多个 command 文档、执行卡和总纲类文档，需要同步检查规则传播。
* 现有 `delivery` 中关于 `learn/` 的维护者回流说明可以被删除或降级，不再作为默认主链。

## Open Questions

* 需要在修改命令文档后同步更新哪些 walkthrough / 总纲 / 映射文档，取决于实际搜索到的传播面。

## Requirements (evolving)

* 修订 `需求变更管理执行卡`，补齐冻结后变更的商业处理闭环，但保持轻量化。
* 修订 `review-gate`：
  * 默认走 `lite`
  * 明确 `lite` / `full` 分层
  * 保留 `full` 的多 reviewer 路径
  * 明确“3 轮”为建议值，不是硬上限
* 修订 `project-audit`，明确其多 CLI 审查仍保持 `full`，不复用 `lite`
  口径。
* 修订 `delivery`，移除 `Step 9a` / `Step 9b` 及与默认 workflow 缺陷反馈机制
  相关的主链表述。
* 修订与 PRD / 交付文档相关的 workflow 文档，明确 `humanizer-zh`：
  * 默认适用范围
  * 默认排除范围
  * 用户显式指定时的例外规则
  * 三个执行时机
* 同步更新所有受这些规则影响的相关文档，避免命令正文、总纲、映射、walkthrough
  之间发生语义漂移。

## Acceptance Criteria (evolving)

* [ ] `需求变更管理执行卡` 明确写出冻结后变更的收费判断、用户接受状态和并入当前轮次规则。
* [ ] `review-gate` 明确区分 `lite` / `full`，且 `lite` 规则与用户本轮确认一致。
* [ ] `project-audit` 没有被错误改成可复用 `lite` 的模式。
* [ ] `delivery` 不再把 `Step 9a` / `Step 9b` 作为默认主链动作。
* [ ] workflow 文档中对 `humanizer-zh` 的默认范围、排除项、显式指定例外和执行时机表述一致。
* [ ] 受影响的总纲 / 映射 / walkthrough / 命令文档之间没有明显传播漂移。

## Definition of Done (team quality bar)

* 文档改动与本轮已确认需求一致
* 相关传播链已检查
* 运行至少一条与本次文档改动直接相关的验证命令并如实记录结果

## Out of Scope (explicit)

* 不修改 `workflow-capability-audit`
* 不修改安装器、upgrade-compat、hooks 或 CLI carrier 行为
* 不扩展 `humanizer-zh` 到所有技术文档
* 不重新设计完整的收费体系、法务模板或合同条款

## Technical Notes

* 预期高影响文件：
  * `docs/workflows/新项目开发工作流/需求变更管理执行卡.md`
  * `docs/workflows/新项目开发工作流/commands/review-gate.md`
  * `docs/workflows/新项目开发工作流/commands/project-audit.md`
  * `docs/workflows/新项目开发工作流/commands/delivery.md`
  * `docs/workflows/新项目开发工作流/commands/brainstorm.md`
  * `docs/workflows/新项目开发工作流/工作流总纲.md`
  * `docs/workflows/新项目开发工作流/命令映射.md`
* 需要遵守的 authoring/spec 约束：
  * `.trellis/spec/docs/index.md`
  * `.trellis/spec/scripts/workflow-command-doc-contracts.md`
  * `.trellis/spec/guides/cross-layer-thinking-guide.md`
  * `.trellis/spec/guides/code-reuse-thinking-guide.md`
