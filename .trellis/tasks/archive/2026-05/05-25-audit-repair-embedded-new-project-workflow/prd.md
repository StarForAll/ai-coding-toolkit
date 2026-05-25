# Audit And Repair Embedded New-Project Workflow

## Goal

基于 `/tmp/trellis-0.5.17-2` 这个已经执行 `trellis init` 并嵌入 `docs/workflows/新项目开发工作流/` 的临时目标项目，审计 `docs/workflows/新项目开发工作流/` 是否存在真实缺陷、遗漏文档、安装后不一致、补丁缺失、同类问题未一并修复等问题。先形成证据化结论与修复方案，待用户确认后，再只在 `docs/workflows/新项目开发工作流/` 内实施修复。

## What I Already Know

- 用户明确要求分析对象是 `/tmp/trellis-0.5.17-2` 的实际嵌入结果，而不是当前仓库自身运行中的工作流。
- 修复范围只允许在 `docs/workflows/新项目开发工作流/` 内，其他目录不能修改；当前任务目录例外，可用于记录审计产物。
- 如果问题属于 Trellis 原生能力缺口，需要在该工作流内部用补丁或安装器机制兜住，而不是直接修改仓库外层其他目录。
- 用户给出的若干问题点只是候选假设，必须先验证真伪，再决定是否修复。
- 用户要求尽量扩大同类问题排查，不只修单点。
- 用户要求在给出修正方案后先征求同意，再继续操作。

## Assumptions

- 当前仓库中的 `docs/workflows/新项目开发工作流/` 是生成 `/tmp/trellis-0.5.17-2` 的来源工作流版本。
- 当前 Trellis 版本与该工作流兼容版本满足 `workflow-audit` 的同版本维护前提，或只存在允许分析的补丁级差异。
- `/tmp/trellis-0.5.17-2` 仍保留足够的嵌入产物与运行态文件，可用于静态和有限运行态核查。

## Open Questions

- 当前工作流与 `/tmp/trellis-0.5.17-2` 的版本锚点是否一致，是否满足 `workflow-audit` 的版本门禁。
- 候选问题中哪些是真缺陷，哪些只是表述误读或历史残影。
- 是否存在与候选问题同根因的其他路径、脚本、文档、补丁缺口。
- 最小且稳妥的修复面应该落在哪些源文件与补丁文件上。

## Requirements

- 必须先完成证据收集，再下结论。
- 必须区分 source repo、generated target project、runtime command output 三类证据层。
- 必须以 `/tmp/trellis-0.5.17-2` 为主要验证对象，必要时可参考同类临时项目作对照，但不能把对照项目当作结论主体。
- 必须先给出问题判断与修复方案，用户同意后才能改 `docs/workflows/新项目开发工作流/`。
- 修复时必须考虑不能引入新问题，并尽可能顺带修复同类缺陷。

## Acceptance Criteria

- [ ] 输出候选问题的真伪判断与证据。
- [ ] 输出同类问题补充发现与归因分组。
- [ ] 输出仅涉及 `docs/workflows/新项目开发工作流/` 的修复方案与风险控制点。
- [ ] 在用户确认前，不修改 `docs/workflows/新项目开发工作流/`。
- [ ] 用户确认后，实施修复并完成相关验证。

## Out Of Scope

- 不直接修改当前仓库根级 `.trellis/`、`.codex/`、`.agents/` 等当前项目运行面文件。
- 不把当前仓库自身 Trellis 运行时问题当作本任务修复目标，除非它们必须通过目标工作流补丁在安装后修复。

## Technical Notes

- 审计对象根：`docs/workflows/新项目开发工作流/`
- 目标项目：`/tmp/trellis-0.5.17-2`
- 参考技能：`trellis-start`、`workflow-audit`
