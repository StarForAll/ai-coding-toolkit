---
name: feasibility
description: 新项目？先评估可行性 — 合规审查、风险评估、报价输出。触发词：帮我评估、能做吗、新项目想法、报价
---

# /trellis:feasibility — 项目可行性评估

> **Workflow Position**: §1 → 前: 无 → 后: `/trellis:brainstorm`
> **Cross-CLI**: ✅ Claude Code · ✅ Cursor (命令名: feasibility) · ⚠️ OpenCode (通过 instructions) · ⚠️ Codex/Gemini (通过 shell 脚本)
>
> **Gate Rule**: 对于新项目 / 新客户需求，`/trellis:feasibility` 是进入 `/trellis:brainstorm` 前的默认前置门禁；只有 `assessment.md` 明确允许时，才继续进入需求发现。

---

## When to Use (自然触发)

用户说以下任何话时自动启动：
- "我有个新项目想法"
- "帮我评估一下这个需求能不能做"
- "有个客户找我做个项目"
- "这个项目的报价怎么算"
- "帮我看看有没有风险"

> 已有任务在进行中？跳过，直接 `/trellis:brainstorm` 或 `/trellis:start`。

### 前置条件与出口约束

- 本命令面向**新项目立项、外包接单、客户需求初聊**等“先判断值不值得接”的场景。
- 若已有有效 `assessment.md` 且本轮仅补充需求细节，可跳过本命令直接进入 `/trellis:brainstorm`。
- 若评估结论为 `暂停`，必须先补信息或完成谈判动作，再重新运行本命令。
- 若评估结论为 `拒绝`，应终止该项目链路，不进入 `/trellis:brainstorm`。

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

执行要求：

- 先产出 `assessment.md` 骨架，再使用 `demand-risk-assessment` 填充结论与证据。
- 不允许只给口头结论，必须把 go / no-go / pause 判断写回 `assessment.md`。
- `assessment.md` 必须明确写出“是否允许进入 brainstorm”，作为阶段二的前置判断。

### Step 4: 确认与初始化

```bash
TASK_DIR=$(python3 ./.trellis/scripts/task.py create "<项目名>" --slug <name>)
```

仅当 `assessment.md` 结论允许继续推进时，才创建/初始化正式任务目录；否则保留评估记录，等待补信息、谈判或终止。

---

## 输出

```
$TASK_DIR/
├── assessment.md   # 评估报告
├── prd.md          # 初始 PRD
└── task.json
```

### `assessment.md` 最低字段契约

`assessment.md` 至少应包含以下内容，供后续 `/trellis:brainstorm` 或人工决策直接复用：

```markdown
# 项目可行性评估

## 概览
- 总体决策：接 / 谈判后接 / 暂停 / 拒绝
- 是否可做：
- 是否值得做：
- 如何做更稳：
- 是否允许进入 brainstorm：是 / 否
- 当前结论的前提：

## 需求摘要
- 核心目标：
- 目标用户：
- 核心功能（≤3）：
- 技术约束：
- 时间窗口：

## 红线与关键信号
- 合规红线：
- 付款 / 验收 / 范围风险：
- AI / LLM 特有风险（如适用）：

## 关键风险 Top 5
| 风险 | 类型 | 级别 | 应对 |
|------|------|------|------|

## 必须谈判条件
- 条件 1：
- 条件 2：

## 最小补充信息集
- 缺口 1：
- 缺口 2：

## 下一步建议
- 若允许进入 brainstorm：带着哪些边界与假设继续
- 若不允许：补信息 / 谈判 / 终止
```

约束：

- `是否允许进入 brainstorm = 否` 时，不应直接进入 `/trellis:brainstorm`
- `总体决策 = 暂停` 时，下一步默认是“补信息后重跑 feasibility”
- `总体决策 = 拒绝` 时，下一步默认是“终止项目并保留 assessment 记录”

## 下一步推荐

**当前状态**: 可行性评估完成，`assessment.md` 已生成。

根据评估结果和你的意图：

| 你的意图 | 推荐命令 | 说明 |
|---------|---------|------|
| 继续推进项目 | `/trellis:brainstorm` | **默认推荐**。评估通过，进入详细需求发现 |
| 信息不足，先补充再评估 | `/trellis:feasibility` | 默认用于 `暂停` 结论；补齐缺口、谈判后重跑 |
| 评估不通过，终止 | — | 记录原因，保留 `assessment.md` 作为拒绝依据 |
| 需求已经很明确，跳过 brainstorm | `/trellis:design` | 如果 PRD 内容已足够详细 |
| 需求简单，直接写代码 | `/trellis:start` | 跳过设计+拆解，适合小改动 |
| 不确定下一步 | `/trellis:start` | 用 Phase Router 自动检测 |
