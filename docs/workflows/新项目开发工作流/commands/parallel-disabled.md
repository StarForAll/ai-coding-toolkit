<!-- workflow-parallel-disabled -->
---
name: parallel
description: 当前 workflow 明确禁用基于 parallel/worktree 的后台 dispatch 与 PR 完成路径。若需要重新安排优先级或阶段顺序，请回到 `/trellis:plan` 或 `/trellis:start`。
---

# /trellis:parallel — Disabled In This Workflow

当前 `docs/workflows/新项目开发工作流` 不使用基于 `parallel/worktree` 的后台 dispatch 流水线。

禁用原因：

- 不允许在后台默默执行完整任务
- 不允许通过 `create-pr` / `gh pr create` / `git pr` 作为任务完成方式
- 当前 workflow 的默认执行模型是：**在目标项目当前工作区直接完成任务**

如果你的真实意图是：

- 重新安排任务顺序 → 回到 `/trellis:plan`
- 继续当前阶段或让系统判断下一步 → 回到 `/trellis:start`
- 进入项目级全局审查 → 使用 `/trellis:project-audit`

不要在当前 workflow 中继续使用：

- 后台 worktree agent
- dispatch + create-pr 流水线
- 任何 PR 驱动的任务收尾方式
