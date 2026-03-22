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

## 前置条件

进入 `/trellis:plan` 前，应满足以下条件：

- 技术架构已经过用户明确确认
- 已根据技术架构，从 `trellis-library` 导入合适 spec 到当前项目 `.trellis/spec/`（任务 1，必须先于任务 2 完成）
- 已结合当前项目作用、背景、技术架构，对当前项目 `.trellis/spec/` 完成分析完善（任务 2，仅在任务 1 完成后执行）

`/trellis:plan` 的职责是任务拆解与生成 `task_plan.md`，不负责替代上述 spec 导入与 spec 修订动作。

---

## 流程

### Step 1: 生成 Plan.md

**Skills**: `project-planner` `writing-plans`

```bash
# 读取输入
cat "$TASK_DIR/prd.md"
cat "$TASK_DIR/design/index.md" 2>/dev/null
# 当前项目 `.trellis/spec/` 应已完成对齐，作为任务拆解约束输入
```

AI 自动生成 `task_plan.md`：任务拆解 + 依赖分析 + 文件清单 + 验收标准。

输入侧重点：

- 已确认的需求与设计文档
- 当前项目 `.trellis/spec/` 中已经落地的项目约束
- 基于项目 spec 提炼出的实现边界、验证要求和依赖关系

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
