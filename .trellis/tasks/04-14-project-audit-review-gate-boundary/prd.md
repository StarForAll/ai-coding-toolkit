# 收敛 project-audit 与 review-gate 阶段边界

## Goal

只修改 `docs/workflows/新项目开发工作流/` 下相关文档，收敛 `project-audit` 与 `review-gate` 的阶段边界、主链关系，以及多 CLI 审查能力在项目级审查中的使用规则。

## Requirements

- `review-gate` 仅保留为任务级后置门禁
- `project-audit` 发现的新高风险问题留在当前阶段内讨论、确认、修复，不回挂具体任务
- `project-audit` 默认由当前 CLI 先完成发现与方案讨论
- 命中高不确定、强争议、跨模块因果难判断或用户显式要求时，分析/方案阶段允许提前引入 `multi-cli-review`
- 修复执行阶段允许使用 `multi-cli-review` 与 `multi-cli-review-action`
- `project-audit.md` 拆分 `Confirmed Findings` 与 `Candidate Findings / Reviewer Evidence`
- 被否定的候选项从主文档删除；延期项按实际需要决定是否保留
- `project-audit` 过程记录与 `review-gate` 目录隔离
- 仅修改 `docs/workflows/新项目开发工作流/` 对应工作流内容，不修改其他工作流

## Acceptance Criteria

- [ ] `commands/project-audit.md` 反映新的阶段规则、触发条件、记录结构和目录约定
- [ ] `commands/review-gate.md` 更新默认 reviewer 数和轮次规则
- [ ] 总纲、命令映射、walkthrough、通俗版中不再出现 `project-audit` 后默认进入 `review-gate` 的冲突表述
- [ ] 相关文档均限定在 `docs/workflows/新项目开发工作流/`

## Technical Notes

- 本轮为文档修订，不调整其他工作流
- reviewer 临时证据继续复用 `tmp/multi-cli-review/...`，但项目级审查使用 `<task-id>-project-audit` 隔离目录
