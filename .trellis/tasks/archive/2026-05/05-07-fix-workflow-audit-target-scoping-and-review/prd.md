# fix workflow-audit target scoping and review

## Goal

收紧 repo-local `workflow-audit` skill 的目标边界，明确其默认且唯一支持的审计对象是
`docs/workflows/新项目开发工作流/`，消除“当前项目根”与“workflow source root”之间的
目标漂移；同时同步检查 `.agents/skills/` 与 `.claude/skills/` 两个 repo-local surface
是否一致，并在修订前后做一轮更深入的缺陷审查，确认是否还存在其他高风险歧义、跨层
漂移或测试覆盖缺口。

## What I already know

* 现有 `workflow-audit` 在 `.agents/skills/workflow-audit/` 与
  `.trellis/spec/skills/workflow-audit.md` 中都把 `workflow_path` 的默认值写成了
  `docs/workflows/新项目开发工作流/`。
* 现有问题不在默认值本身，而在自然语言触发和步骤定义中没有把“目标 workflow root”
  绑定成硬约束，导致执行者可能把 repo root / current project 当成主要审计对象。
* `.trellis/spec/skills/index.md` 已将 `workflow-audit` 明确声明为
  `.agents/skills/workflow-audit/` 与 `.claude/skills/workflow-audit/` 的共享行为规范，
  因此这两个 surface 必须同步审查。
* `.trellis/spec/docs/index.md` 要求修改 workflow/product assets 时，必须区分 source
  repo、task runtime、target project 三个边界，不能混淆 repo-local 当前状态与目标项目
  或 workflow source root。

## Assumptions (temporary)

* 本次修订应把 `workflow-audit` 从“泛化支持 `docs/workflows/*`”收紧为“只支持当前仓库下
  的 `docs/workflows/新项目开发工作流/`”。
* `.agents/skills/workflow-audit/` 与 `.claude/skills/workflow-audit/` 都应与
  `.trellis/spec/skills/workflow-audit.md` 保持一致，不允许出现平台私有漂移，除非有
  明确的 repo-local reason。
* 现有测试目录下尚未覆盖“省略 workflow_path 但仍必须解析到固定 workflow root”的场景，
  需要补足。

## Open Questions

* 深审后是否需要把“单一 workflow scope”进一步上升为 `.trellis/spec/skills/workflow-audit.md`
  的显式约束，并新增对应回归测试。

## Requirements (evolving)

* 明确 `workflow-audit` 的唯一支持目标是 `docs/workflows/新项目开发工作流/`。
* 删除或改写会暗示泛化 `docs/workflows/*` / “任意 workflow target” 的表述。
* 在 `.agents/skills/workflow-audit/` 与 `.claude/skills/workflow-audit/` 审查并修复同类问题。
* 深审并记录除目标漂移外的其他问题：
  * source-of-truth 歧义
  * repo root / workflow root / target project 边界混淆
  * 与 spec 的行为漂移
  * 测试覆盖缺口
  * 示例、模板、引用文档中的残余泛化描述
* 保持 repo-local spec 与 skill surface 一致；必要时更新 `.trellis/spec/skills/workflow-audit.md`。
* 更新或新增测试场景，覆盖默认目标解析、固定目标约束及其他本次发现的重要边界。

## Acceptance Criteria (evolving)

* [ ] `workflow-audit` 不再把自己描述为对 `docs/workflows/*` 的泛化审计器，而是明确为只审计
      `docs/workflows/新项目开发工作流/`。
* [ ] `.agents/skills/workflow-audit/` 与 `.claude/skills/workflow-audit/` 的 SKILL、
      references、tests 在本次问题域内保持一致。
* [ ] `.trellis/spec/skills/workflow-audit.md` 与 repo-local skill surface 没有语义漂移。
* [ ] 新增或修复的测试能覆盖“省略目标时仍绑定固定 workflow root”的关键场景。
* [ ] 输出一份基于证据的深审结论，说明除了当前问题外还发现了哪些其他问题，哪些没有发现。

## Definition of Done (team quality bar)

* 相关 skill/spec/tests 已更新
* 运行相关验证命令并记录 pass/fail/not run
* 结论明确区分：已修复、未修复、剩余风险

## Out of Scope (explicit)

* 不修改 `workflow-capability-audit`
* 不修改 `docs/workflows/新项目开发工作流/` 产品 workflow 逻辑本身，除非深审证明 skill
  文本必须引用更新后的 source contract
* 不做与本次问题无关的风格性重写

## Technical Notes

* 主要目标文件：
  * `.agents/skills/workflow-audit/SKILL.md`
  * `.agents/skills/workflow-audit/references/*`
  * `.agents/skills/workflow-audit/tests/*`
  * `.claude/skills/workflow-audit/*`
  * `.trellis/spec/skills/workflow-audit.md`
* 主要约束来源：
  * `.trellis/spec/skills/index.md`
  * `.trellis/spec/docs/index.md`
  * `.trellis/spec/guides/code-reuse-thinking-guide.md`
  * `.trellis/spec/guides/cross-layer-thinking-guide.md`
