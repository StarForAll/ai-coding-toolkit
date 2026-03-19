# 实现 commands/ 源资产层，完善 spec/commands 规范

> **Blocked**: 此任务依赖 `commands/claude/<id>/`、`commands/shell/<id>/` 等目录下已有至少 1 个真实的命令脚本。
> 在此之前，无法从实际经验中提炼规范，任务无法启动。

---

## 前置条件（需先完成）

在开始本任务前，必须先在 `commands/` 相关目录下创建至少 1 个命令：

```
commands/
  shell/
    <command-id>.sh       # 含 shebang、error handling、--help
    README.md
```

建议从通用场景入手（如 `validate-skills`、`deploy-helper`），创建完成后更新本任务状态。

---

## Goal

在 `commands/<tool>/<id>/` 下已有真实命令资产的基础上，
将其部署到对应工具的 commands 目录，然后反填并完善 `.trellis/spec/commands/index.md`，
将状态从 ⚠️ Design → ✅ Implemented。

---

## Requirements

### 阶段一：Command 部署验证

- [ ] `commands/<tool>/<id>/` 下的源资产已存在（前置完成）
- [ ] 将命令部署到对应工具目录（`.claude/commands/`、`.opencode/commands/`、`.iflow/commands/`）
- [ ] 验证命令在目标工具中可正常运行

### 阶段二：规范完善

- [ ] 基于实际部署过程，更新 `spec/commands/index.md`：
  - 移除"⚠️ Design"标记和 Current State 小节
  - 修正 deployment mapping（按实际部署路径）
  - 补充本项目特有的实现细节（如 slash command frontmatter 格式）
- [ ] 更新 `spec/index.md` 中 commands 层 Status：⚠️ Design → ✅ Implemented
