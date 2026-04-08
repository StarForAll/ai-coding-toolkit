---
name: check
description: 代码写完了？检查一下 — 基于真实改动范围和项目 spec 执行质量检查，运行项目化验证命令，输出偏差清单与下一步建议。触发词：检查一下、质量检查、对照 spec、对照规范、自检、有没有偏差
---

# /trellis:check — 实现后质量检查

> **Workflow Position**: §5.1.x → 前: `/trellis:start` 实施完成 → 后: `/trellis:review-gate` → `/trellis:finish-work`
> **Cross-CLI**: ✅ Claude Code（项目命令：`/trellis:check`） · ✅ OpenCode（TUI: `/trellis:check`；CLI: `trellis/check`；见 `opencode/README.md`） · ⚠️ Codex（通过 AGENTS.md NL 路由触发，不提供项目级 `/trellis:check` 命令；见 `codex/README.md`）

---

## When to Use (自然触发)

- "检查一下这次改动"
- "对照 spec 看看有没有问题"
- "做一轮质量检查"
- "实现写完了，先 check 一下"
- 当前任务代码已完成，需要在进入 `review-gate` 或 `finish-work` 之前先做一次任务级质量检查

> 以下场景不要误路由到本命令：
>
> - 需要跨层影响排查 → `/trellis:check-cross-layer`
> - 需要多 CLI 补充审查门禁 → `/trellis:review-gate`
> - 需要提交前完整收尾检查 → `/trellis:finish-work`

---

## 核心目标

`/trellis:check` 的目标不是重复实现阶段，也不是替代 `review-gate`，而是完成四件事：

1. 基于真实改动范围定位适用的 spec / guideline
2. 执行项目确认过的验证命令并记录证据
3. 检查实现偏差、边界风险、安全与性能问题
4. 输出结构化 `check.md`，供 `review-gate` / `finish-work` 消费

---

## 流程

### Step 1: 识别改动范围

先识别这次实际变更了哪些文件：

```bash
git diff --name-only HEAD
```

必要时补做影响面分析：

**MCP 能力路由**

| 场景 | 调用能力 | 触发条件 | 说明 |
|------|---------|---------|------|
| 代码影响面分析 | `ace.search_context` | 默认优先 | 查找相似代码、调用关系、潜在遗漏点。若不可用，改用 `rg` / 上下文阅读，并标记 `[Evidence Gap]` |
| 复杂验证链路推理 | `sequential-thinking` | 当验证链路涉及 ≥3 个条件组合、异常分支或交叉影响时 | 用于梳理验证优先级和风险路径 |

### Step 2: 定位并读取适用 spec / guideline

根据改动路径判断适用模块：

```bash
python3 ./.trellis/scripts/get_context.py --mode packages
```

然后执行：

1. 读取对应 `.trellis/spec/<package>/<layer>/index.md`
2. 跟随 `Quality Check` section 找到实际 guideline 文件
3. 阅读具体 guideline，而不是只停留在 index

最低要求：

- 不能只凭记忆判断“应该没问题”
- 不能跳过与当前改动直接相关的质量规则
- 若 spec / guideline 缺失，必须标记 `[Evidence Gap]`

### Step 3: 执行项目化验证

**调用 Skill**：`verification-before-completion` — 坚持“证据先于断言”完成验证。降级：明确列出验证命令、关键输出和 `pass / fail / not run` 结论。

```bash
python3 <WORKFLOW_DIR>/commands/shell/check-quality.py \
  <task_dir> \
  --test-cmd "<user-confirmed test command>" \
  --lint-cmd "<user-confirmed lint command>" \
  --typecheck-cmd "<user-confirmed type-check command>"
```

约束：

- test / lint / typecheck 命令必须来自技术架构确认后的项目化输入
- 若当前项目没有某一项检查，则省略对应参数，并在结果中标记 `not run`
- 不猜默认命令，不把其他项目习惯硬套到当前项目

### Step 4: 扩展质量检查清单

在原生 `check` 的基础上，继续补做以下检查：

- Spec 对照：实现是否满足需求 / 设计 / contract
- 验证证据：测试 / lint / typecheck 是否覆盖当前改动
- 边界场景：空值、极值、异常值、失败分支
- 安全风险：注入、越权、泄露、fail-open、危险配置
- 性能影响：复杂度、资源占用、慢路径
- 上下文健康：是否出现重复修错、方向漂移、明显遗漏

**调用 Skill**：`sharp-edges` — 检查危险 API 和配置。降级：手动检查 fail-open 默认值、危险配置和易误用接口。

### Step 5: 生成检查结果

写入：

```text
$TASK_DIR/check.md
```

最少包含：

- 改动范围
- 适用 spec / guideline
- 验证命令与 `pass / fail / not run`
- 偏差清单
- 未覆盖风险
- 建议人工关注模块
- 推荐下一步

建议结构：

```markdown
# Check Report

## Changed Scope

## Applied Specs

## Verification Results

## Deviations

## Uncovered Risks

## Suggested Next Step
```

### Step 6: 上下文污染检测

- 重复已修复的错误？→ 停止，开新会话
- 输出方向偏离？→ 导出决策摘要
- 若风险仍不明确，不直接进入 `finish-work`，先走 `review-gate`

---

## 输出

```text
$TASK_DIR/check.md
```

---

## 下一步推荐

**当前状态**: 质量检查完成，`check.md` 已生成。

> 本节定义的是阶段完成后的推荐输出口径，用于帮助当前 CLI 或协作者说明下一步；它不是框架层自动跳转保证。

根据检查结果：

| 检查结果 | Claude / OpenCode 推荐入口 | Codex 推荐入口 | 说明 |
|---------|---------------------------|----------------|------|
| 基本合规，需判断是否进入补充审查 | `/trellis:review-gate` | 进入补充审查判断，或显式触发 `review-gate` skill | **默认推荐**。由 `review-gate` 决定 `required / recommended / skip` |
| 存在实现偏差，需先修复 | `/trellis:start` | 回到实施阶段，或显式触发 `start` skill | 先修复偏差项，再重新执行 `check` |
| 测试或验证证据不足 | `/trellis:test-first` | 回到测试驱动，或显式触发 `test-first` skill | 先补验证证据，再重新执行 `check` |
| 风险较高但事实已整理完成 | `/trellis:review-gate` | 进入补充审查判断，或显式触发 `review-gate` skill | 让 gate 基于 `check.md` 做门禁判定 |
| 发现上下文污染 | `/trellis:start` | 开新会话并重新描述当前意图，或显式触发 `start` skill | 停止当前会话，开新会话并注入决策摘要 |
| 偏差来自冻结后新增 / 修改 / 删除需求 | `§2.5 需求变更管理` | 同上 | 先完成评估与确认；获批后再回到受影响的最早阶段 |
| 偏差仅是纯澄清 | 留在当前阶段 | 留在当前阶段 | 仅限不改变范围、接口契约、验收标准、成本、工期 |
| 不确定下一步 | `/trellis:review-gate` | 描述当前审查意图，或显式触发 `review-gate` skill | 先做任务级补充审查门禁判断 |
