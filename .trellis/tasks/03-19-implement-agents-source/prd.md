# 实现 agents/ 源资产层，完善 spec/agents 规范

> **Blocked**: 此任务依赖 `agents/<id>/` 下已有至少 1 个真实的 agent 源资产。
> 在此之前，无法从实际经验中提炼规范，任务无法启动。

---

## 前置条件（需先完成）

在开始本任务前，必须先在 `agents/` 目录下创建至少 1 个 agent 源资产：

```
agents/
  <agent-id>/
    README.md        # 用途、场景、调用方式
    SYSTEM.md        # 工具无关的系统提示词
    TOOLS.md         # 抽象权限需求（可选）
```

建议从简单场景入手（如 `research`、`debug`），创建完成后更新本任务状态。

---

## Goal

在 `agents/<id>/` 下已有真实 agent 资产的基础上，
将其部署到 `.claude/agents/`、`.opencode/agents/`、`.iflow/agents/`，
然后反填并完善 `.trellis/spec/agents/index.md`，将状态从 ⚠️ Design → ✅ Implemented。

---

## Requirements

### 阶段一：Agent 部署验证

- [ ] `agents/<id>/` 下的源资产已存在（前置完成）
- [ ] 将 agent 部署到三个工具目录，生成对应 frontmatter 的实例文件
- [ ] 验证 agent 在各工具中可正常调用

### 阶段二：规范完善

- [ ] 基于实际部署过程，更新 `spec/agents/index.md`：
  - 移除"⚠️ Design"标记和 Current State 小节
  - 修正 Field Mapping（按实际使用的 frontmatter 字段）
  - 修正 Sync Strategy（如有与实际不符之处）
  - 补充本项目特有的实现细节
- [ ] 更新 `spec/index.md` 中 agents 层 Status：⚠️ Design → ✅ Implemented
