# OpenCode 适配

OpenCode 使用 `opencode.json` 的 `instructions` 字段加载指令。

## 部署方式

在项目根目录的 `opencode.json` 中添加：

```json
{
  "instructions": [
    "docs/workflows/新项目开发工作流/工作流总纲.md",
    "docs/workflows/新项目开发工作流/commands/feasibility.md",
    "docs/workflows/新项目开发工作流/commands/brainstorm.md",
    "docs/workflows/新项目开发工作流/commands/design.md",
    "docs/workflows/新项目开发工作流/commands/plan.md",
    "docs/workflows/新项目开发工作流/commands/test-first.md",
    "docs/workflows/新项目开发工作流/commands/self-review.md",
    "docs/workflows/新项目开发工作流/commands/check.md",
    "docs/workflows/新项目开发工作流/commands/delivery.md"
  ]
}
```

## 注意事项

- OpenCode 的命令系统尚在开发中（TBD）
- 目前通过 `instructions` 加载 markdown 作为上下文
- Shell 脚本可直接使用（平台无关）
- 命令通过自然语言触发词被 AI 识别和调用
- Skills 通过 `~/.agents/skills/` 自动发现（如支持）
