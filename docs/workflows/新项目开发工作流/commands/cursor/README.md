# Cursor 适配

Cursor 使用 `.cursor/commands/` 目录，无 `trellis:` 前缀。

## 部署方式

```bash
# 将工作流命令部署到 Cursor
for cmd in feasibility brainstorm design plan test-first check review-gate delivery; do
  # 提取 markdown 内容（去掉 YAML frontmatter）
  sed '1,/^---$/d' "docs/workflows/新项目开发工作流/commands/${cmd}.md" | \
  sed '1,/^---$/d' > ".cursor/commands/${cmd}.md"
done
```

## 命令调用

| Trellis (Claude Code) | Cursor |
|----------------------|--------|
| `/trellis:feasibility` | `/feasibility` |
| `/trellis:brainstorm` | `/brainstorm` |
| `/trellis:design` | `/design` |
| `/trellis:plan` | `/plan` |
| `/trellis:test-first` | `/test-first` |
| `/trellis:check` | `/check` |
| `/trellis:review-gate` | `/review-gate` |
| `/trellis:delivery` | `/delivery` |

## 注意事项

- Cursor 无 Hook 系统，不会自动注入 spec context
- 需要在命令中手动读取 spec 文件
- Shell 脚本可直接使用（平台无关）
- Skills 加载需要通过 @file 手动引用
