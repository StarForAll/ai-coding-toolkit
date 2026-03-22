---
name: multi-cli-review
description: Use when analyzing a skill, command, workflow, document, or code artifact for problems and outputting a structured defect report, either standalone (legacy protocol) or as part of a multi-reviewer task workflow (new protocol).
---

# Multi-CLI Review

## Overview

Multi-CLI Review 是一个多 CLI 协作的问题分析流程，支持两种协议：

1. **旧协议（Legacy）**：单 run-id、单报告，适合单 reviewer 场景
2. **新协议（Task-Level Multi-Reviewer）**：任务级多 reviewer，适合并行独立审查

**角色分工**：
- 其他 CLI：reviewer，只审查不修改代码
- 当前 CLI：统一修复者，负责汇总建议、执行修复

## When to Use

- 需要分析 skill、command、workflow、文档、配置或代码中的问题
- 需要输出结构化的问题报告（供当前 CLI 后续处理）
- 需要在多 reviewer 场景下输出独立的审查报告
- 需要在优化操作后重新分析问题

## When Not to Use

- 只需要澄清需求，不需要结构化问题报告 → 使用 `brainstorm`
- 只需要对当前 git diff 做代码审查 → 使用 `code-review-router` 或 `requesting-code-review`
- 只需要直接修改文件，不需要 CLI 分工 → 直接执行实现流程

## Protocol Selection

### 协议优先级

| 优先级 | 条件 | 使用的协议 |
|--------|------|-----------|
| 1 | 显式传入 `--task-dir` | **新协议（Task-Level）** |
| 2 | 显式传入 `--output` 或 `--md-a` | 兼容旧协议（显式路径优先） |
| 3 | 无显式参数 | **新协议（推荐）** / 旧协议兜底 |

> ⚠️ **重要**：多 reviewer 场景下，必须显式传入 `--task-dir`，禁止依赖"最新 run-id 自动兜底"。

### 新协议（Task-Level Multi-Reviewer）

```
tmp/multi-cli-review/<task-id>/
  review-round-1/
    reviewer-a.md    # Reviewer A 的报告
    reviewer-b.md    # Reviewer B 的报告
  review-round-2/
    reviewer-a.md
    reviewer-c.md
```

**特点**：
- 以任务（task-id）为维度组织目录
- 每个 reviewer 输出独立的 `<reviewer-id>.md`
- 支持多轮审查（review-round-N）
- 当前 CLI 负责汇总和修复

### 旧协议（Legacy Single-Reviewer）

```
tmp/multi-cli-review/<run-id>/
  cur_defect.md      # 问题分析报告
  optimize.md        # 优化方案（由 multi-cli-review-action 生成）
```

**特点**：
- 以 run-id 为维度组织目录
- 输出固定文件名 `cur_defect.md`
- 仅适合单 reviewer 场景
- **仅作兼容，新场景优先使用新协议**

## Trigger Conditions

以下任一情况都应触发本 skill：

- 显式单独调用：`/multi-cli-review <问题描述> [目标路径] [参数...]`
- 多 reviewer 模式：`/multi-cli-review <问题描述> [目标路径] --task-dir <任务目录> [--reviewer-id <ID>] [--round <N>]`
- 组合调用：`$start /multi-cli-review ...`、`/trellis:brainstorm /multi-cli-review ...`
- 自然语言请求：
  - "分析这个 skill 在实际使用场景里的问题"
  - "输出一个结构化问题报告"
  - "用多 CLI 审查模式分析这个文档"

## Input Parameters

### 通用参数

| 参数 | 必需 | 说明 |
|------|------|------|
| `<问题描述>` | 是（首次分析） | 用户提出的问题，贯穿始终 |
| `[目标路径]` | 否 | 需要分析的目标文件或目录 |

### 新协议参数

| 参数 | 必需 | 说明 |
|------|------|------|
| `--task-dir` | 是（多 reviewer 模式） | 任务总目录路径，如 `tmp/multi-cli-review/<task-id>` |
| `--reviewer-id` | 否 | 审查者 ID；默认使用当前 CLI 名称 |
| `--round` | 否 | 轮次编号；默认自动递增（首次为 1） |
| `--output` | 否 | 直接指定输出文件路径（覆盖默认） |
| `--review-focus` | 否 | 本次审查重点描述 |

### 旧协议参数（兼容）

| 参数 | 必需 | 说明 |
|------|------|------|
| `--md-a` | 否 | 问题分析报告路径 |
| `--md-b` | 否 | 优化方案路径 |

## Path Resolution

### 新协议路径解析

1. **显式 `--task-dir` + `--reviewer-id`**：
   - 输出路径：`{task-dir}/review-round-{N}/{reviewer-id}.md`
   - 轮次 N：若未指定，默认取最大轮次 + 1

2. **显式 `--output`**：
   - 直接使用指定路径，不做解析

3. **无显式参数（首次）**：
   - 自动生成 task-id：`task-{时间戳}`
   - 输出路径：`tmp/multi-cli-review/{task-id}/review-round-1/{reviewer-id}.md`

### 旧协议路径解析（兼容）

1. 显式 `--md-a`：直接使用指定路径
2. 只传 `--md-b`：根据同级目录推导 `cur_defect.md`
3. 两者都未传：扫描 `tmp/multi-cli-review/` 下已有数字目录，取最大 + 1

## Reviewer ID Rules

> 本章节集中定义 reviewer-id 的所有规则。

### 显式优先

- 多 reviewer 场景下，**必须显式传入 `--reviewer-id`**
- 显式传入的 ID 具有最高优先级，不可被覆盖

### 默认值

- 若未传入 `--reviewer-id`，默认使用**当前 CLI 名称**
- CLI 名称仅作为默认值，不得在显式指定时被忽略

### 文件命名

- 输出文件名固定为 `{reviewer-id}.md`
- 不得使用其他文件名（如 `cur_defect.md`）

### 轮次一致性

- 同一 reviewer 在多轮审查中应使用**相同的 reviewer-id**
- 不允许同一 reviewer 使用不同 ID（如第一轮用 `codex`，第二轮用 `claude`）

### 冲突处理

- 若输出文件 `{reviewer-id}.md` 已存在，**必须报错**，要求确认：
  ```
  ❌ 文件已存在：{path}

  请选择：
  1. 使用 --overwrite 覆盖
  2. 使用不同的 --reviewer-id
  ```
- 禁止静默覆盖已有报告

### 来源标识

- 报告元数据中的 `reviewer-id` 必须与文件名一致
- 用于后续 `multi-cli-review-action` 按 reviewer-id 识别来源

## Output Files

### 新协议输出格式

**文件名**：`{reviewer-id}.md`

```markdown
---
task-id: <任务标识>
round: <轮次>
reviewer-id: <审查者 ID>
source-cli: <CLI 名称>
review-time: <ISO 8601 时间>
review-focus: <本次审查重点>
protocol: task-level
---

# 缺陷分析报告

## 审查概要

- **审查者**：[reviewer-id]
- **审查时间**：[review-time]
- **审查重点**：[review-focus]
- **目标**：[目标路径]

## 分析结果

### 问题 1：[问题标题]

- **位置**：文件路径 + 行号范围
- **问题描述**：具体是什么问题
- **严重程度**：🔴 高 / 🟡 中 / 🟢 低
- **影响范围**：[具体影响什么]
- **必须解决原因**：说明为什么必须解决
- **建议修复方向**：具体的修复建议

### 问题 2：...

## 审查状态

- **审查者**：[reviewer-id]
- **审查时间**：[review-time]
- **协议版本**：task-level-v1
```

### 旧协议输出格式（兼容）

```markdown
# 问题分析报告

## 问题描述
<用户输入的问题描述，贯穿始终>

## 分析结果
### 问题 1：[问题标题]
- **位置**：文件路径 + 行号范围
- **问题描述**：具体是什么问题
- **严重程度**：高/中/低
- **影响范围**：[具体影响什么]
- **必须解决原因**：（仅对未解决的问题）说明为什么 CLI 2 必须解决

## 迭代状态
- 当前迭代次数：1
- 上次分析时间：2026-03-20
- 当前运行目录：tmp/multi-cli-review/<run-id>/
- 协议版本：legacy
```

## Workflow

### 新协议：任务级多 Reviewer 模式

**推荐触发方式**：`/multi-cli-review <问题描述> --task-dir tmp/multi-cli-review/{task-id} --reviewer-id {reviewer-id} [--round <N>]`

**执行流程**：

1. **解析参数**：
   - 确认 `--task-dir` 和 `--reviewer-id`
   - 确定轮次（显式优先，自动递增兜底）

2. **创建目录结构**：
   - 确保 `{task-dir}/review-round-{N}/` 存在

3. **分析问题**：
   - 分析目标文件或目标目录
   - 识别问题，按格式输出

4. **写入报告**：
   - 写入 `{task-dir}/review-round-{N}/{reviewer-id}.md`
   - 包含完整的元数据

5. **回显执行结果**：
   ```
   ✅ 多 CLI 审查报告已生成

   📁 task-dir: tmp/multi-cli-review/{task-id}
   🔄 round: {N}
   👤 reviewer-id: {reviewer-id}
   📄 输出文件: tmp/multi-cli-review/{task-id}/review-round-{N}/{reviewer-id}.md
   ```

### 旧协议：单 Reviewer 模式（兼容）

**推荐触发方式**：`/multi-cli-review <问题描述> [目标路径] [--md-a <路径>]`

**执行流程**：

1. **确定输出路径**
2. **分析问题**
3. **输出问题报告**
4. **回显实际路径**

## Echo Requirements

**每次执行结束时，必须回显以下信息**：

| 字段 | 说明 |
|------|------|
| `task-dir` | 任务总目录路径（新协议）或 run 目录（旧协议） |
| `round` | 当前轮次编号 |
| `reviewer-id` | 实际使用的审查者 ID |
| `output-path` | 实际输出文件路径 |

**格式示例**：
```
✅ 审查报告已生成

📁 task-dir: tmp/multi-cli-review/my-task
🔄 round: 2
👤 reviewer-id: claude-code
📄 输出文件: tmp/multi-cli-review/my-task/review-round-2/claude-code.md
```

## Iteration Rules

### 新协议多轮审查

- **最大轮次**：3 轮
- **轮次自动递增**：未指定 `--round` 时，默认取最大轮次 + 1
- **提前关闭**：当前轮所有 reviewer 均未产出新的可执行修复建议时，可提前结束

### 旧协议迭代

- **最大迭代次数**：5 次
- **状态标记**：
  - `pending`：等待用户确认
  - `completed`：已完成本轮操作
  - `blocked`：被阻塞
  - `abandoned`：用户选择终止

## Error Handling

### 目录不存在

- 自动创建所需目录结构

### 旧协议兜底警告

- 旧协议仅作兼容，新场景应使用新协议
- 显式提示建议迁移到新协议

## Common Mistakes

### ❌ 省略元数据

- 问题：输出报告缺少 `task-id`、`round`、`reviewer-id` 等字段
- 后果：汇总阶段无法识别来源
- 正确做法：新协议必须包含完整元数据

### ❌ 不回显执行信息

- 问题：生成文件后没有说明实际写入位置
- 后果：当前 CLI 无法定位报告
- 正确做法：每次执行末尾都回显 task-dir、round、reviewer-id、output-path

### ❌ 承担聚合职责

- 问题：在 review 阶段做去重、汇总
- 后果：与 multi-cli-review-action 职责重叠
- 正确做法：只负责产出当前 reviewer 的独立报告

## Tips

1. **新协议优先**：多 reviewer 场景默认使用 `--task-dir` 模式
2. **review-focus 要明确**：帮助其他 reviewer 理解本次审查侧重点
3. **保留"必须解决原因"**：这是后续聚合和决策的重要依据
4. **保留"建议修复方向"**：包含具体的修复建议，不只是问题描述

## Examples

### 示例 1：新协议单 Reviewer

```text
用户：/multi-cli-review 分析 skills/multi-cli-review 存在的问题 --task-dir tmp/multi-cli-review/skill-review --reviewer-id codex

CLI Reviewer：
1. 解析参数：task-dir=tmp/multi-cli-review/skill-review, reviewer-id=codex, round=1
2. 创建目录结构
3. 分析问题
4. 写入报告
5. 回显执行结果

✅ 审查报告已生成

📁 task-dir: tmp/multi-cli-review/skill-review
🔄 round: 1
👤 reviewer-id: codex
📄 输出文件: tmp/multi-cli-review/skill-review/review-round-1/codex.md
```

### 示例 2：新协议多 Reviewer

```text
用户（CLI 1）：/multi-cli-review 分析 skills/multi-cli-review 存在的问题 --task-dir tmp/multi-cli-review/skill-review --reviewer-id gemini

CLI Reviewer（Gemini）：
分析完成，写入 tmp/multi-cli-review/skill-review/review-round-1/gemini.md

用户（CLI 1）：/multi-cli-review 分析 skills/multi-cli-review 存在的问题 --task-dir tmp/multi-cli-review/skill-review --reviewer-id claude

CLI Reviewer（Claude）：
分析完成，写入 tmp/multi-cli-review/skill-review/review-round-1/claude.md

当前 CLI（CLI 1）使用 multi-cli-review-action 汇总两份报告，执行修复
```

### 示例 3：旧协议兼容

```text
用户：/multi-cli-review 分析 ./docs/api.md

CLI：
1. 扫描 tmp/multi-cli-review/，发现已有 run-id=3
2. 使用 run-id=4
3. 输出到 tmp/multi-cli-review/4/cur_defect.md
4. 回显路径
```

## Related Skills

- `multi-cli-review-action`：当前 CLI，负责汇总多个 reviewer 报告并执行修复
- `brainstorm`：澄清问题边界
- `requesting-code-review`：轻量级代码审查

## Protocol Migration Guide

### 从旧协议迁移到新协议

| 旧协议 | 新协议 |
|--------|--------|
| `tmp/multi-cli-review/{run-id}/cur_defect.md` | `{task-dir}/review-round-{N}/{reviewer-id}.md` |
| run-id 自动递增 | task-id + round 组合 |
| 固定 `cur_defect.md` | `{reviewer-id}.md` |
| CLI 2 生成 `optimize.md` | 当前 CLI 生成 `summary-round-{N}.md` + `action.md` |

### 兼容性说明

- 旧协议参数（`--md-a`、`--md-b`）仍然支持
- 旧协议输出文件格式（无元数据）仍然支持
- 新场景**强烈建议使用新协议**
