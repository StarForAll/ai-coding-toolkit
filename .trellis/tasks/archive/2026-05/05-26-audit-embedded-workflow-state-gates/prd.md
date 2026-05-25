# Audit and patch embedded workflow state gates

## Goal

核实用户列出的 6 个 `docs/workflows/新项目开发工作流/` 嵌入后工作流状态机问题是否在 `/tmp/trellis-$(trellis -v)-2` 中真实存在；若真实存在，在用户确认修正方案后只修改 `docs/workflows/新项目开发工作流/` 与当前任务目录，避免影响本仓库当前运行中的 Trellis。

## What I Already Know

- 审计对象是 workflow source：`docs/workflows/新项目开发工作流/`。
- 行为对照对象是已执行 `trellis init` 并嵌入该工作流的目标项目：`/tmp/trellis-$(trellis -v)-2`。
- 用户要求先分析判断并给出修正方案，获得用户同意后再执行源工作流修复。
- 修复范围限定为 `docs/workflows/新项目开发工作流/`；当前任务目录允许记录审计材料。
- 候选问题涉及 `project-audit` 出口门禁、`project-audit -> implementation` 回退闭环、plan leaf task 与 implementation 入口字段契约、leaf task state 初始化、formal PROJECT-AUDIT carrier 与 delivery gate 对齐、`--awaiting-user-confirmation` 状态契约。

## Requirements

- 逐项验证 6 个候选问题，不能把假设当结论。
- 对照 source repo 与 generated target project 的实际文件，必要时查看运行命令输出。
- 主动搜索同类结构性问题；真实存在且同范围可修的，需要纳入同一修正方案。
- 在用户确认前，不修改 `docs/workflows/新项目开发工作流/`。
- 修复阶段需要补充或更新测试，证明不会引入新的 gate 绕过或阻塞。

## Acceptance Criteria

- [ ] 每个候选问题都有明确结论：confirmed / false alarm / evidence gap。
- [ ] confirmed issue 包含证据、影响、修复方向和验证方式。
- [ ] 修正方案得到用户确认后再改源工作流。
- [ ] 修改仅发生在 `docs/workflows/新项目开发工作流/` 与当前任务目录。
- [ ] 最终运行相关测试或说明未运行原因。

## Out of Scope

- 修改本仓库当前生效的 `.trellis/` 运行时。
- 直接修补 `/tmp/trellis-$(trellis -v)-2` 作为最终交付。
- 删除本轮任务目录。

## Technical Notes

- 使用 `workflow-audit` 作为本轮审计流程。
- Codex 当前为 inline 模式，不使用子代理。
