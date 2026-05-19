# Audit And Fix Embedded Workflow Runtime Gates

## Goal

审计并修复 `docs/workflows/新项目开发工作流/` 在目标项目嵌入后暴露出的真实运行时问题。分析对象是 `/tmp/trellis-0.5.17-2` 这个已经过 `trellis init` 和工作流嵌入的目标项目；修改范围严格限制在本仓库的工作流源目录 `docs/workflows/新项目开发工作流/` 与当前任务目录。

## What I already know

- 用户已给出 6 组候选问题，重点集中在：
  - `workflow-state.py route` 对非执行阶段全局门禁仅 warning 不 blocked
  - Codex patched skill 完整性检查漏检 `trellis-continue` / `trellis-finish-work` 语义漂移
  - 工作流文档对 customization / parser-only 的维护边界描述失真
  - degraded active-task fallback 可能误选任务
  - 旧 phase/step 语言与 helper 残留
  - tasks 视图动态调用 route 带来可观测性与性能问题
- 该任务要求以 `/tmp/trellis-0.5.17-2` 的已安装实际行为作为证据，而不是只看当前仓库本身。
- 如果问题根因位于 Trellis 原生文件，需要在工作流源中通过 patch / installer 机制修复，而不是直接修改当前仓库根层 `.trellis/` 基线。
- 当前工作流兼容锚点版本为 `0.5.17`，本机 `trellis -v` 为 `0.5.17`，同版本，可继续按 `workflow-audit` 合同执行。

## Assumptions (temporary)

- `/tmp/trellis-0.5.17-2` 保留了足够的已安装工作流文件，可用于静态与必要的命令级验证。
- 当前仓库中已有若干先前修复，需重新核实哪些问题仍真实存在，哪些已修复，避免重复制造“优化型修复”。
- Codex 当前以 inline 模式运行，因此本次直接在主会话执行，不使用 agents。

## Open Questions

- 是否存在与上述 6 项同类、同根因的漏检或漏补丁点，需要一起修复。
- 已安装目标项目中的当前实际行为是否与源工作流模板完全一致，还是还存在安装器/补丁输出漂移。

## Requirements

- 逐项验证用户给出的候选问题是否真实存在，必须给出源文件和 `/tmp` 目标项目证据。
- 对真实存在的问题，在 `docs/workflows/新项目开发工作流/` 内实施修复；必要时补 installer、patch、文档、测试。
- 对同类问题做扩展扫描，一并修复，避免局部修补后遗留同根因缺口。
- 不修改工作流目录外的仓库文件；当前任务目录除外。
- 修复要尽量避免引入新问题，优先选择与现有工作流契约一致的最小成组改动。
- 最终需要给出哪些问题真实存在、哪些不成立、做了哪些修复、验证结果如何。

## Acceptance Criteria

- [ ] `audit-report.md` 记录版本门禁、证据边界、已确认问题、非问题项与修复方向。
- [ ] 对真实存在的问题已在 `docs/workflows/新项目开发工作流/` 中完成修复。
- [ ] 若存在同类缺口，已一并修复或在报告中明确说明为何不修。
- [ ] 相关验证命令已执行，并如实记录 pass / fail / not run。
- [ ] 未修改工作流目录外的业务/产品源文件。

## Definition of Done

- 相关脚本测试、静态检查、或最接近的可执行验证已运行
- 审计结论以证据为基础，不凭记忆下结论
- 修复后的源工作流能更可靠地服务后续嵌入目标项目

## Out Of Scope

- 直接修补 `/tmp/trellis-0.5.17-2` 下的已安装文件
- 修改当前仓库正在使用的 Trellis 根层运行时，除非通过工作流 patch 机制表达
- 跨版本兼容性审计（本次是同版本维护审计）

## Technical Notes

- 审计技能：`workflow-audit`
- 前置 spec：`.trellis/spec/docs/index.md`、`.trellis/spec/guides/index.md`
- 目标目录：`docs/workflows/新项目开发工作流/`
- 运行时样本：`/tmp/trellis-0.5.17-2`
