# 生成新项目工作流全局流转说明

## Goal

为 `docs/workflows/新项目开发工作流/` 补一份可视化、通俗、面向使用者的大局说明，帮助读者快速理解整套 workflow 的阶段流转、CLI 入口差异、关键门禁和常见分支。

## Requirements

- 说明整套 workflow 为什么存在
- 用一张主链图讲清楚从 `feasibility` 到 `record-session` 的流转
- 明确 Claude Code / OpenCode / Codex 三种原生适配的入口差异
- 用通俗语言说明每个阶段解决什么问题、产出什么、下一步去哪
- 补充常见分支判断：什么时候回退、什么时候变更管理、什么时候直接 `start`
- 尽量视觉化，方便第一次接触的人快速建立全局认知

## Acceptance Criteria

- [ ] 新文档位于 `docs/workflows/新项目开发工作流/`
- [ ] 文档包含可视化主链图
- [ ] 文档说明三 CLI 入口差异
- [ ] 文档说明常见阶段分流
- [ ] 至少有一个可视化产物（mind map）

## Out of Scope

- 不重写 `工作流总纲.md`
- 不替代 `命令映射.md` 或各阶段命令正文
- 不新增新的流程规则
