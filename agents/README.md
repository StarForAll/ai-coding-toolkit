# Agents

这里存放自定义 agent（或 agent 相关资产），用于复用固定的工作流、约束与提示词。

## 推荐目录结构（可按需调整）

```text
agents/
  <agent-id>/
    README.md        # 该 agent 的用途、适用场景、示例
    SYSTEM.md        # 系统提示词（System Prompt）
    TOOLS.md         # 工具/权限/边界约束（可选）
    EXAMPLES/        # 输入输出示例（可选）
```

## 命名建议

- `agent-id` 用短横线风格：`feature-planner`、`bug-fixer`、`release-helper`。
- 以“任务/角色”为中心命名，避免跟具体项目强绑定（否则建议放到 `docs/` 并标注项目背景）。

