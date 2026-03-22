---
name: self-review
description: 代码写完了？自审一下 — 对照 spec 逐项核对，输出偏差清单。触发词：自检、审查一下、有没有偏差、对照 spec
---

# /trellis:self-review — AI 广义自审

> **Workflow Position**: §5.1.x → 前: `/trellis:start` 实施完成 → 后: `/trellis:check` → `/trellis:finish-work`
> **Cross-CLI**: ✅ Claude Code · ✅ Cursor (命令名: self-review) · ⚠️ OpenCode · ⚠️ Codex/Gemini

---

## When to Use (自然触发)

- "自检一下"
- "对照 spec 看看有没有问题"
- "有没有偏差"
- "做一下自审"
- Implement Agent 完成后自动触发

---

## 流程

### Step 1: 验证

**Skill**: `verification-before-completion` — 证据先于断言

```bash
python3 docs/workflows/新项目开发工作流/commands/shell/self-review-check.py
```

### Step 2: 自审清单

逐项检查：Spec 对照 / 测试验证 / 边界场景 / 安全自检 / 性能影响

**安全检查**: **Skill**: `sharp-edges` — 识别危险 API 和配置

### Step 3: 偏差清单

写入 `$TASK_DIR/self-review.md`：不一致项 + 未覆盖风险 + 建议人工关注模块

### Step 4: 上下文污染检测

- 重复已修复的错误？→ 停止，开新会话
- 输出方向偏离？→ 导出决策摘要

---

## 风险分级

| L0 低风险 | L1 中风险 | L2 高风险 |
|----------|----------|----------|
| 快速自审 → `/trellis:check` 判定是否跳过补充审查 | 完整自审 → `/trellis:check` 补充审查门禁 | 完整自审 → `/trellis:check` + 人工裁决 |

## 下一步推荐

**当前状态**: 自审完成，`self-review.md`（偏差清单）已生成。

根据偏差清单结论：

| 偏差清单结论 | 推荐命令 | 说明 |
|------------|---------|------|
| 需要判断是否进入补充审查 | `/trellis:check` | **默认推荐**。由 `/trellis:check` 决定 `required / recommended / skip` |
| 合规度低，需先修复 | `/trellis:start` | 回到实施阶段修复偏差项 |
| L2 高风险，需人工裁决 | `/trellis:check` | 先进入补充审查门禁，必要时停在人工决策点 |
| 发现上下文污染 | `/trellis:start` | 停止当前会话，开新会话并注入决策摘要 |
| 测试未覆盖 | `/trellis:test-first` | 补充测试用例后再自审 |
| 偏差来自需求理解 | `/trellis:brainstorm` | 回到需求层澄清 |
| 不确定下一步 | `/trellis:check` | 先做任务级补充审查门禁判断 |
