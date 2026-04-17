# Reviewer Commands - Round 2

## Task Summary

- task-id: `04-17-workflow-fix-new-project`
- target path: `docs/workflows/新项目开发工作流`
- review round: `2`
- task-dir: `tmp/multi-cli-review/04-17-workflow-fix-new-project`
- reviewer count: `2`
- protocol: `task-level`

## Review Focus

- 项目级粗估硬门禁是否仍有误伤正常路径
- round 1 修复后的跨文档一致性是否仍有遗漏
- 阶段路由、L0 直进 `start`、`brainstorm -> design` 门禁是否仍存在回归风险

## Round 1 Context

执行 round 2 前，reviewer 应同时读取：

- `tmp/multi-cli-review/04-17-workflow-fix-new-project/summary-round-1.md`
- `tmp/multi-cli-review/04-17-workflow-fix-new-project/action.md`

要求：

- 只报告修复后**仍然成立**的高价值问题
- 不重复 round 1 已关闭项
- 不输出低价值风格建议
- reviewer 只审查，不修改代码

## Reviewer Commands

### Claude

```text
/multi-cli-review "复核当前针对“项目级粗估必须在 brainstorm 收口前落盘且不能跳过”的 workflow 修改，在 round-1 修复后是否仍存在未覆盖的高价值问题。重点检查：1) workflow-state.py 现有门禁是否仍误伤 brainstorm、L0 直进 start/implementation、design/plan 等正常路径；2) brainstorm、design、总纲、命令映射、walkthrough、平台 README、阶段状态机、思维导图之间是否仍有矛盾或遗漏；3) 只报告当前仍成立的新问题，不重复 round-1 已关闭项。" docs/workflows/新项目开发工作流 --task-dir tmp/multi-cli-review/04-17-workflow-fix-new-project --reviewer-id claude --round 2 --review-focus "项目级粗估硬门禁、跨文档一致性、阶段路由与回归风险；同时读取 summary-round-1.md 与 action.md 作为 round-1 决策上下文"
```

### OpenCode

```text
/multi-cli-review "复核当前针对“项目级粗估必须在 brainstorm 收口前落盘且不能跳过”的 workflow 修改，在 round-1 修复后是否仍存在未覆盖的高价值问题。重点检查：1) workflow-state.py 现有门禁是否仍误伤 brainstorm、L0 直进 start/implementation、design/plan 等正常路径；2) brainstorm、design、总纲、命令映射、walkthrough、平台 README、阶段状态机、思维导图之间是否仍有矛盾或遗漏；3) 只报告当前仍成立的新问题，不重复 round-1 已关闭项。" docs/workflows/新项目开发工作流 --task-dir tmp/multi-cli-review/04-17-workflow-fix-new-project --reviewer-id opencode --round 2 --review-focus "项目级粗估硬门禁、跨文档一致性、阶段路由与回归风险；同时读取 summary-round-1.md 与 action.md 作为 round-1 决策上下文"
```

## Output Contract

- reviewer output path:
  - `tmp/multi-cli-review/04-17-workflow-fix-new-project/review-round-2/claude.md`
  - `tmp/multi-cli-review/04-17-workflow-fix-new-project/review-round-2/opencode.md`
- aggregator command after both reports are ready:

```text
/multi-cli-review-action --task-dir tmp/multi-cli-review/04-17-workflow-fix-new-project --round 2
```
