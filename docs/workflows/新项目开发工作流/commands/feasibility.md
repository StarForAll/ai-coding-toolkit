---
name: feasibility
description: 新项目？先评估可行性 — 合规审查、风险评估、报价输出。触发词：帮我评估、能做吗、新项目想法、报价
---

# /trellis:feasibility — 项目可行性评估

> **Workflow Position**: §1 → 前: 无 → 后: `/trellis:brainstorm`
> **Cross-CLI**: ✅ Claude Code · ✅ Cursor (命令名: feasibility) · ⚠️ OpenCode (通过 instructions) · ⚠️ Codex/Gemini (通过 shell 脚本)

---

## When to Use (自然触发)

用户说以下任何话时自动启动：
- "我有个新项目想法"
- "帮我评估一下这个需求能不能做"
- "有个客户找我做个项目"
- "这个项目的报价怎么算"
- "帮我看看有没有风险"

> 已有任务在进行中？跳过，直接 `/trellis:brainstorm` 或 `/trellis:start`。

---

## 流程

### Step 1: 合规性审查

```bash
# 平台无关脚本
python3 docs/workflows/新项目开发工作流/commands/shell/feasibility-check.py --step compliance
```

检查清单：法律法规/数据隐私/强监管行业/知识产权

**不合规 → 立即终止并说明理由**

### Step 2: 需求粗估（一次一个问题）

1. 核心目标 → 2. 目标用户 → 3. 核心功能(≤3) → 4. 技术约束 → 5. 时间窗口

### Step 3: 风险评估与报价

**Skill**: `demand-risk-assessment` — 按其框架判断接/谈判后接/暂停/拒绝。

```bash
python3 docs/workflows/新项目开发工作流/commands/shell/feasibility-check.py --step estimate
```

### Step 4: 确认与初始化

```bash
TASK_DIR=$(python3 ./.trellis/scripts/task.py create "<项目名>" --slug <name>)
```

---

## 输出

```
$TASK_DIR/
├── assessment.md   # 评估报告
├── prd.md          # 初始 PRD
└── task.json
```

## 下一步推荐

**当前状态**: 可行性评估完成，`assessment.md` 已生成。

根据评估结果和你的意图：

| 你的意图 | 推荐命令 | 说明 |
|---------|---------|------|
| 继续推进项目 | `/trellis:brainstorm` | **默认推荐**。评估通过，进入详细需求发现 |
| 评估不通过，终止 | — | 记录原因，归档 assessment.md |
| 需求已经很明确，跳过 brainstorm | `/trellis:design` | 如果 PRD 内容已足够详细 |
| 需求简单，直接写代码 | `/trellis:start` | 跳过设计+拆解，适合小改动 |
| 不确定下一步 | `/trellis:start` | 用 Phase Router 自动检测 |
