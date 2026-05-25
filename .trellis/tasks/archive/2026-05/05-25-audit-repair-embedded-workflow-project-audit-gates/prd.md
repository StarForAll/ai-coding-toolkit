# workflow-audit: 审计并修复嵌入式工作流的 project-audit / delivery / gate 合同缺口

## Goal

以 `/tmp/trellis-0.5.17-2` 这个已执行 `trellis init` 并嵌入 `docs/workflows/新项目开发工作流/` 的目标项目为验收样本，验证用户列出的 project-audit / delivery / workflow-state / embed-integrity 相关问题是否真实存在；若确认为工作流源缺陷，则仅在 `docs/workflows/新项目开发工作流/` 内修复，并顺带修复同类问题，确保后续目标项目嵌入后行为一致且不再复发。

## What I Already Know

- 审计对象是 `docs/workflows/新项目开发工作流/` 这套源工作流，但真实性判断必须基于 `/tmp/trellis-0.5.17-2` 这个已嵌入目标项目样本。
- 修改范围只允许落在 `docs/workflows/新项目开发工作流/` 与当前任务目录；其他目录不能修改。
- 用户给出的 10 个问题点是候选假设，不应直接当作既成缺陷；需要逐条做证据化判断，并排查相邻合同缺口。
- 用户要求在分析出具体问题和修正方案后，先征得同意，再继续改动工作流源文件。
- 当前仓库为工作流作者仓库，不是被嵌入目标项目；若发现是 Trellis 原生缺陷，需要在该工作流内以补丁/安装器方式修复，而不是修改仓库根层 Trellis 运行时。

## Assumptions (temporary)

- `/tmp/trellis-0.5.17-2` 的嵌入状态足以复现当前源工作流安装后的真实行为。
- 历史归档任务中已有相近审计痕迹，但仍需按当前源文件与目标项目状态重新验证，不能直接复用旧结论。
- 若某个问题只存在于文档描述而未影响状态机/验证器/安装器行为，需要区分为“文档合同缺陷”而非“运行时缺陷”。

## Open Questions

- 哪些候选问题在当前版本仍真实存在，哪些已经被此前修复消除？
- 若问题真实存在，最小且不引入新回归的修复落点应在文档、验证器、状态机、安装器脚本中的哪一层？
- 是否还存在与这 10 个点同源的相邻问题，需要在同一轮补齐？

## Requirements (evolving)

- 逐条核验用户列出的 10 个候选问题，输出真实缺陷 / 非缺陷 / 证据不足分类。
- 分析目标是 `/tmp/trellis-0.5.17-2` 中已嵌入工作流的实际内容与行为，不是当前仓库根层运行时。
- 若发现 Trellis 原生缺口影响该工作流，需在 `docs/workflows/新项目开发工作流/` 内通过补丁、安装器、文档或验证器修复。
- 在修改前先给出证据、问题列表、修正方案和风险控制点，并等待用户确认。
- 修复时需要同时覆盖同类问题，但不得修改 `docs/workflows/新项目开发工作流/` 以外的目录。

## Acceptance Criteria (evolving)

- [ ] 给出基于源工作流与 `/tmp/trellis-0.5.17-2` 的证据化问题判断，不靠记忆或假设下结论。
- [ ] 至少覆盖 project-audit、delivery、check gate、workflow-state transition/audit 字段、embed_integrity CLI 合同这几类问题。
- [ ] 若给出修复建议，说明落点、原因、风险和需要同步修复的类似问题。
- [ ] 在用户明确同意前，不修改 `docs/workflows/新项目开发工作流/` 下的源文件。

## Definition of Done

- 形成可执行的问题分析与修正方案，等待用户确认。
- 用户确认后，仅修改允许范围内文件并完成相关验证。
- 真实验证结果以 pass / fail / not run 诚实记录。

## Out of Scope

- 不修改仓库根层 `.trellis/`、`.codex/`、`.claude/`、`.opencode/` 等当前作者仓库运行时层。
- 不处理与 `docs/workflows/新项目开发工作流/` 无关的其他 workflow 产品。

## Technical Notes

- 重点源文件预计包括：
  - `docs/workflows/新项目开发工作流/commands/project-audit.md`
  - `docs/workflows/新项目开发工作流/commands/delivery.md`
  - `docs/workflows/新项目开发工作流/commands/shell/workflow-state.py`
  - `docs/workflows/新项目开发工作流/commands/shell/validators_gates.py`
  - `docs/workflows/新项目开发工作流/commands/shell/embed_integrity.py`
- 重点样本目录为 `/tmp/trellis-0.5.17-2`，需要比对 clean `trellis init` 基线之外的 workflow 安装后状态。
