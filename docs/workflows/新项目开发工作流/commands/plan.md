---
name: plan
description: 设计好了？拆任务 — AI 驱动任务拆解、排期、DoR/DoD。触发词：拆任务、做计划、工作分解、排期
---

# /trellis:plan — AI 驱动任务拆解

> **Workflow Position**: §4 → 前: `/trellis:design` → 后: `/trellis:test-first` 或 `/trellis:start`
> **Cross-CLI**: ✅ Claude Code · ✅ Cursor (命令名: plan) · ⚠️ OpenCode · ⚠️ Codex/Gemini

---

## When to Use (自然触发)

- "拆一下任务"
- "做个工作计划"
- "把需求分解成小任务"
- "怎么排期"
- "需要制定实现步骤"

> 简单任务（1-2 文件）？跳过，直接 `/trellis:start`。

---

## 流程

### Step 1: 生成 Plan.md

**Skills**: `project-planner` `writing-plans`

```bash
# 读取输入
cat "$TASK_DIR/prd.md"
cat "$TASK_DIR/design/index.md" 2>/dev/null
```

AI 自动生成 `task_plan.md`：任务拆解 + 依赖分析 + 文件清单 + 验收标准

### Step 2: 排期

识别可并行任务，制定里程碑

### Step 3: DoR/DoD

每个任务定义 Ready 和 Done 标准

### Step 4: 验证拆分

```bash
python3 docs/workflows/新项目开发工作流/commands/shell/plan-validate.py
```

- [ ] 单任务独立可测试
- [ ] 单上下文可完整实现（Token 预算内）
- [ ] 依赖关系清晰

---

## 输出

```
$TASK_DIR/
├── task_plan.md   ← 任务拆解计划
└── ...
```

## 下一步推荐

**当前状态**: `task_plan.md` 已生成，任务拆解和依赖关系已明确。

根据你的意图：

| 你的意图 | 推荐命令 | 说明 |
|---------|---------|------|
| 测试先行 | `/trellis:test-first` | **默认推荐（复杂项目）**。先写测试再实现 |
| 直接写代码 | `/trellis:start` | 简单任务可跳过测试先行 |
| 拆解不合理，重新拆 | `/trellis:plan` | 重新执行拆解流程 |
| 设计有问题 | `/trellis:design` | 回退到设计阶段 |
| 需要并行开发多个任务 | `/trellis:parallel` | 使用 Git worktree 隔离开发 |
| 不确定下一步 | `/trellis:start` | 用 Phase Router 自动检测 |
