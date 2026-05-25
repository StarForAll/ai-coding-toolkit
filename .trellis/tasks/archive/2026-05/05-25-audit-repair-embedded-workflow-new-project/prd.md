# Audit And Repair Embedded Workflow New-Project Workflow

## Goal

审计 `docs/workflows/新项目开发工作流/` 在目标项目 `trellis init` 后嵌入到 `/tmp/trellis-0.5.17-2` 的真实行为，验证用户列出的候选问题和同类问题是否真实存在；若问题成立，则只在 `docs/workflows/新项目开发工作流/` 范围内设计并实施修复，避免引入新的阶段流转、安装、校验或 CLI 适配回归。

## What I Already Know

- 修复范围被限制在 `docs/workflows/新项目开发工作流/`，其他目录不能修改。
- 判断对象不是当前仓库运行态，而是 `/tmp/trellis-0.5.17-2` 中已经 `trellis init` 且嵌入该工作流后的真实内容。
- 当前 workflow 兼容锚点版本为 `0.5.17`，本机 `trellis -v` 也是 `0.5.17`，版本门禁通过。
- 用户给出了 10 个候选问题与参考定位，但这些点都必须先验证，不能直接假定成立。
- 该 workflow 的强门禁、阶段状态机、安装器补丁和技能/脚本分布在 `docs/workflows/新项目开发工作流/commands/`、`commands/shell/` 以及相关文档中。

## Assumptions

- `/tmp/trellis-0.5.17-2` 是可信的工作流嵌入样本，可用于静态和必要的轻量运行时验证。
- 嵌入后的 `.trellis/scripts/workflow/*.py`、`.agents/skills/*/SKILL.md` 与源工作流产物存在一一对应关系，可反推源工作流缺陷。
- 在给出修复方案并取得用户同意之前，不修改 `docs/workflows/新项目开发工作流/` 源文件。

## Open Questions

- 无阻塞性问题；先用静态分析和必要的轻量运行时验证完成候选问题定性。

## Requirements

- 逐项验证用户列出的候选问题是否真实存在。
- 对每个成立问题给出证据链，区分 source repo、generated target project、runtime command output。
- 主动搜索并纳入同类问题，避免只修单点。
- 修复时只能修改 `docs/workflows/新项目开发工作流/`。
- 若问题属于 Trellis 原生能力缺口，只能在该 workflow 合适位置通过补丁或安装期注入方式修复。
- 在给出修正方案后等待用户同意，再执行源码修改。
- 完成修改后执行与工作流相关的验证命令，真实报告 pass / fail / not run。

## Acceptance Criteria

- [ ] 已完成 `/tmp/trellis-0.5.17-2` 的静态证据收集与必要运行时验证。
- [ ] 已明确列出真实存在的问题、非问题、证据不足项和同类问题。
- [ ] 已向用户提交修复方案并等待确认。
- [ ] 用户确认后，仅修改 `docs/workflows/新项目开发工作流/` 内的必要文件。
- [ ] 修改后完成相关验证并真实汇报结果。

## Definition Of Done

- 审计结论有证据，不靠记忆或推测。
- 修复覆盖已确认的问题及明显同类问题。
- 不修改工作流目录外的源码。
- 验证命令已执行并记录真实结果。

## Out Of Scope

- 修改当前仓库正在使用的 `.trellis/`、`.claude/`、`.opencode/`、`.codex/` 运行态文件。
- 直接修改 `/tmp/trellis-0.5.17-2` 作为最终交付修复。
- 做与本次候选问题无关的样式优化或大范围重写。

## Technical Notes

- 判断对象：`/tmp/trellis-0.5.17-2`
- 修复源：`docs/workflows/新项目开发工作流/`
- 关键证据面：阶段状态机、skill 文档、gate validator、plan validator、安装器/补丁脚本、CLI 路由与文档引用
