# audit 新项目开发工作流嵌入与阶段门修复

## Goal

基于 `/tmp/trellis-0.5.17-2` 这个已经执行过 `trellis init` 且嵌入了 `docs/workflows/新项目开发工作流/` 的目标项目样本，核实用户给出的阶段门禁/交付链路候选问题是否真实存在；若确认存在，则仅在 `docs/workflows/新项目开发工作流/` 范围内给出最小且成体系的修复方案，并在用户确认后实施，确保后续工作流嵌入目标项目时行为正确。

## What I already know

- 用户限定审计与修复对象是 `docs/workflows/新项目开发工作流/`，不能修改其他目录；当前任务目录除外。
- 审计基线目标项目是 `/tmp/trellis-$(trellis -v)-2`，当前解析为 `/tmp/trellis-0.5.17-2`。
- `docs/workflows/新项目开发工作流/commands/workflow_assets.py` 中 `COMPATIBLE_TRELLIS_VERSION = "0.5.17"`，当前 `trellis -v` 也是 `0.5.17`，版本门禁通过。
- 用户给了 6 个候选问题，但它们只是待验证假设，不可直接当作已确认缺陷。
- `workflow-audit` 需要结合源码、文档、测试与 `/tmp` 目标项目的实际嵌入结果一起判断问题是否存在。

## Assumptions (temporary)

- 目标项目 `/tmp/trellis-0.5.17-2` 的嵌入状态可用于判断当前工作流源码的真实装后行为。
- 若候选问题已经在当前工作流源码中被修复，则应记录为 false alarm / non-defect，而不是重复修改。
- 若发现同类问题，允许在同一修复中一并处理，但仍需保持改动只落在工作流源目录内。

## Open Questions

- 这 6 个候选问题里，哪些在当前源码与目标项目中仍可复现？
- 若存在“文档口径错误但代码正确”或“测试已覆盖但文档仍错”的情况，应按哪一层修？
- 是否存在未列出的同类阶段门禁/证据绑定问题，需要顺带纳入修复？

## Requirements (evolving)

- 必须先验证候选问题真假，再决定是否修改。
- 结论必须区分：confirmed issue / false alarm / blocked / similar issue。
- 分析对象是目标项目样本和工作流源资产，不是本仓库当前运行中的 `.trellis/` 工作流。
- 修复范围只能是 `docs/workflows/新项目开发工作流/`。
- 在给出修正方案后，必须等待用户同意，才能继续实际修改。
- 若需要修 Trellis 原生问题，只能通过该工作流中的补丁/安装器路径解决。

## Acceptance Criteria (evolving)

- [ ] 6 个候选问题都给出有证据支撑的判定结果。
- [ ] 若问题真实存在，给出具体修复面、受影响文件和同类问题扫描结果。
- [ ] 若问题不成立，明确指出现有源码/测试/装后行为为何已覆盖该风险。
- [ ] 在用户确认前，不修改 `docs/workflows/新项目开发工作流/` 下任何源文件。
- [ ] 用户确认后实施的修改仅落在允许范围内，并补齐必要验证。

## Definition of Done (team quality bar)

- 证据来自源码、文档、测试或 `/tmp` 目标项目运行结果，而不是记忆。
- 若进入修改阶段，相关单测或回归验证命令要实际运行并记录 pass / fail / not run。
- 最终结论要说明已完成、未完成、风险和下一步。

## Out of Scope (explicit)

- 修改 `docs/workflows/新项目开发工作流/` 之外的仓库资产。
- 直接把 `/tmp/trellis-0.5.17-2` 当成最终修复对象。
- 未经用户确认就开始修改工作流源文件。

## Technical Notes

- 相关源文件大概率包括：
  - `docs/workflows/新项目开发工作流/commands/shell/workflow-state.py`
  - `docs/workflows/新项目开发工作流/commands/shell/validators_gates.py`
  - `docs/workflows/新项目开发工作流/commands/shell/test_workflow_state.py`
  - `docs/workflows/新项目开发工作流/commands/project-audit.md`
  - `docs/workflows/新项目开发工作流/commands/delivery.md`
  - `docs/workflows/新项目开发工作流/commands/review-gate.md`
  - `docs/workflows/新项目开发工作流/commands/workflow-patch-projectization.md`
- 当前先保持任务状态在 `planning`，等完成分析并获得用户确认后再进入实施阶段。
