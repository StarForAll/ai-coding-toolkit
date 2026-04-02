---
name: self-review
description: 代码写完了？自审一下 — 对照 spec 逐项核对，输出偏差清单。触发词：自检、审查一下、有没有偏差、对照 spec、自查、对照规范、检查偏差
---

# /trellis:self-review — AI 广义自审

> **Workflow Position**: §5.1.x → 前: `/trellis:start` 实施完成 → 后: `/trellis:check` → `/trellis:finish-work`
> **Cross-CLI**: ✅ Claude Code（项目命令：`/trellis:self-review`） · ✅ OpenCode（TUI: `/trellis:self-review`；CLI: `trellis/self-review`；见 `opencode/README.md`） · ⚠️ Codex（通过 AGENTS.md NL 路由触发，不提供项目级 `/trellis:self-review` 命令；见 `codex/README.md`）

---

## When to Use (自然触发)

- "自检一下"
- "对照 spec 看看有没有问题"
- "有没有偏差"
- "做一下自审"
- Implement Agent 完成后自动触发

> 若自审发现的是冻结后的需求讨论，按 `§2.5` 分流：纯澄清留在当前阶段；新增 / 修改 / 删除进入需求变更管理，不直接回实现吸收变更。

---

## 流程

### Step 1: 验证

**MCP 能力路由**

| 场景 | 调用能力 | 触发条件 | 说明 |
|------|---------|---------|------|
| 代码影响面分析 | `ace.search_context` | 默认 | 查找相似代码、调用关系。若不可用，改用 `rg`/上下文阅读手动完成，并标记 `[Evidence Gap]` |
| 复杂验证逻辑推理 | `sequential-thinking` | 当验证链路涉及 ≥3 个条件组合、异常分支或交叉影响时 | 复杂验证场景 |

**调用 Skill**：`verification-before-completion` — 坚持“证据先于断言”完成验证。降级：明确列出验证命令、关键输出和 `pass / fail / not run` 结论。

```bash
python3 <WORKFLOW_DIR>/commands/shell/self-review-check.py
```

### Step 2: 自审清单

逐项检查：Spec 对照 / 测试验证 / 边界场景 / 安全自检 / 性能影响

**调用 Skill**：`sharp-edges` — 检查危险 API 和配置。降级：手动检查 fail-open 默认值、危险配置和易误用接口。

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

> 本节定义的是阶段完成后的推荐输出口径，用于帮助当前 CLI 或协作者说明下一步；它不是框架层自动跳转保证。

根据偏差清单结论：

| 偏差清单结论 | Claude / OpenCode 推荐入口 | Codex 推荐入口 | 说明 |
|------------|---------------------------|----------------|------|
| 需要判断是否进入补充审查 | `/trellis:check` | 进入补充审查判断，或显式触发 `check` skill | **默认推荐**。由 `/trellis:check` 决定 `required / recommended / skip` |
| 合规度低，需先修复 | `/trellis:start` | 回到实施阶段，或显式触发 `start` skill | 回到实施阶段修复偏差项 |
| L2 高风险，需人工裁决 | `/trellis:check` | 进入补充审查判断，或显式触发 `check` skill | 先进入补充审查门禁，必要时停在人工决策点 |
| 发现上下文污染 | `/trellis:start` | 开新会话并重新描述当前意图，或显式触发 `start` skill | 停止当前会话，开新会话并注入决策摘要 |
| 测试未覆盖 | `/trellis:test-first` | 回到测试驱动，或显式触发 `test-first` skill | 补充测试用例后再自审 |
| 偏差来自冻结后新增 / 修改 / 删除需求 | `§2.5 需求变更管理` | 同上 | 先完成评估与确认；获批后再回到受影响的最早阶段 |
| 偏差仅是纯澄清 | 留在当前阶段 | 留在当前阶段 | 仅限不改变范围、接口契约、验收标准、成本、工期 |
| 不确定下一步 | `/trellis:check` | 描述当前审查意图，或显式触发 `check` skill | 先做任务级补充审查门禁判断 |
