---
name: multi-cli-review-action
description: Use when processing multiple reviewer reports from multi-cli-review, performing deduplication, conflict detection, and executing the unified fix plan as the primary CLI.
---

# Multi-CLI Review Action

## Overview

Multi-CLI Review Action 是多 CLI 协作流程中**当前 CLI（唯一修复者）**使用的 skill。它负责：

1. 读取多个 reviewer 的缺陷报告
2. 聚合、去重、检测冲突
3. 做出统一决策（采纳/忽略/人工裁决）
4. 执行修复操作
5. 输出执行记录

**角色分工**：
- **其他 CLI（Reviewer）**：只审查不修改代码，使用 `multi-cli-review` 输出报告
- **当前 CLI（修复者）**：唯一修复者，负责汇总所有建议并执行修复

## When to Use

- 其他 CLI 已完成多份 `multi-cli-review` 报告
- 需要汇总多个 reviewer 的缺陷报告
- 需要去重、检测冲突、统一执行修复
- 需要输出聚合报告和执行记录

## When Not to Use

- 只需要处理单份报告 → 使用 `multi-cli-review-action` 的兼容模式
- 只需要生成问题报告，不需要执行优化 → 使用 `multi-cli-review`
- 只需要普通代码修改，不需要多 CLI 分工 → 直接执行实现流程

## Protocol Versions

### 协议版本

| 版本 | 描述 | 状态 |
|------|------|------|
| `action-v1` | 单报告处理器（兼容旧协议） | 兼容 |
| `action-v2` | 多报告聚合器（新协议） | **当前** |

> ⚠️ **重要**：`action-v2` 是默认协议版本。仅在传入单份报告或使用 `--legacy` 参数时启用兼容模式。

## Trigger Conditions

以下任一情况都应触发本 skill：

- 显式调用：`/multi-cli-review-action --task-dir <任务目录> [--round <N>]`
- 多报告调用：`/multi-cli-review-action <报告1.md> <报告2.md> ...`
- 单报告兼容：`/multi-cli-review-action <报告路径>`（旧协议）
- 自然语言请求：
  - "汇总这些审查报告并执行修复"
  - "处理 multi-cli-review 输出"
  - "执行多 CLI 审查的汇总"

## Input Parameters

### 新协议参数（action-v2）

| 参数 | 必需 | 说明 |
|------|------|------|
| `--task-dir` | 是 | 任务总目录，如 `tmp/multi-cli-review/<task-id>` |
| `--round` | 否 | 指定轮次；默认处理最新轮次 |
| `--force` | 否 | 强制重新处理已处理的报告 |
| `--dry-run` | 否 | 仅生成 summary，不执行修改 |

### 旧协议参数（兼容）

| 参数 | 必需 | 说明 |
|------|------|------|
| `<md-a-路径>` | 是 | 问题分析报告路径 |
| `<md-b-路径>` | 否 | 优化方案路径 |

## Path Resolution

### 新协议路径解析

1. **扫描 reviewer 报告**：
   - 扫描 `{task-dir}/review-round-{N}/` 下的所有 `.md` 文件
   - 排除 `summary-*.md` 和 `action.md`
   - 按 `reviewer-id` 识别来源
   - **数量边界**：默认 1 个 reviewer，最多 4 个 reviewer
   - **扫描时校验**：
     - 若扫描到 0 个报告 → 报错：无可处理报告
     - 若扫描到 > 4 个报告 → 报错并拒绝处理，提示超出规模上限
     - 若扫描到 1 个报告 → 作为默认单 reviewer 模式继续处理

2. **读取已处理记录**（可选）：
   - 检查 `{task-dir}/.processed.json` 是否存在
   - 已处理的报告默认跳过（除非使用 `--force`）

3. **确定输出文件**：
   - Summary：`{task-dir}/summary-round-{N}.md`
   - Action：`{task-dir}/action.md`

### 旧协议路径解析（兼容）

1. 显式传入 `md-a` / `md-b` → 直接使用
2. 未传路径 → 扫描最新 run-id

## Workflow

### 新协议：多 Reviewer 聚合模式（action-v2）

**推荐触发方式**：`/multi-cli-review-action --task-dir tmp/multi-cli-review/{task-id} [--round <N>]`

**执行流程**：

#### 阶段 1：读取报告

1. **解析参数**：确认 `--task-dir` 和 `--round`
2. **扫描报告**：读取 `{task-dir}/review-round-{N}/` 下所有 reviewer 报告
3. **校验 reviewer 数量**：
   - 默认 1 个 reviewer，最多 4 个
   - 超过 4 个 → 报错拒绝处理
   - 1 个 reviewer 即为默认模式，可继续
4. **检查已处理**：跳过已处理的报告（除非 `--force`）
5. **解析内容**：提取每个报告中的问题清单

**回显**：
```
📊 读取报告列表：
- reviewer-a.md (reviewer-id: reviewer-a)
- reviewer-b.md (reviewer-id: reviewer-b)
共 2 份报告待处理
```

#### 阶段 2：聚合与去重

5. **合并问题清单**：将所有报告中的问题合并
6. **去重判断**：
   - 判断问题是否重复（基于位置、描述相似度）
   - 重复问题合并，保留所有来源的"建议修复方向"
   - 记录去重原因

7. **冲突检测**：
   - 判断同一问题的多个建议是否互斥
   - 互斥建议标记为**冲突**
   - 冲突问题不得自动决定

**回显**：
```
📊 聚合结果：
- 去重前问题总数：7
- 去重后问题数：5
- 冲突问题数：1
```

#### 阶段 3：决策

8. **逐项决策**：
   - **采纳**：建议明确、可执行、在任务边界内
   - **忽略**：问题不成立、重复、低价值
   - **需人工裁决**：冲突、边界不清、高风险

9. **记录决策原因**：
   - 每项决策必须记录原因
   - 忽略项必须记录忽略原因（避免下一轮重复触发）

#### 阶段 4：执行

10. **生成 summary 文件**：
    - 写入 `{task-dir}/summary-round-{N}.md`
    - 包含聚合结果、去重说明、冲突标记

11. **执行修复操作**（需用户确认）：
    - 按"采纳"项执行修改
    - 标记忽略项及原因
    - 冲突项标记为"待人工裁决"

12. **生成 action 文件**：
    - 写入 `{task-dir}/action.md`
    - 记录决策与执行详情

13. **更新已处理记录**：
    - 更新 `{task-dir}/.processed.json`

**回显**：
```
✅ 执行完成

📄 summary: tmp/multi-cli-review/{task-id}/summary-round-{N}.md
📄 action: tmp/multi-cli-review/{task-id}/action.md

📊 统计：
- 已采纳：3
- 已忽略：1
- 需人工裁决：1
```

#### 阶段 5：验证与收尾

14. **验证修复**：
    - 执行 lint/typecheck（如果有）
    - 运行相关测试

15. **提示后续**：
    - 告知用户修复已完成
    - 建议重新执行 review 验证

## Output Files

### Summary 文件

**文件名**：`summary-round-{N}.md`

```markdown
---
task-id: <任务标识>
round: <轮次>
generated-at: <ISO 8601 时间>
protocol: action-v2
---

# 缺陷汇总报告

## 审查概要

- **任务目录**：[task-dir]
- **轮次**：round-{N}
- **审查者**：reviewer-a, reviewer-b
- **汇总时间**：[generated-at]

## 报告来源

| Reviewer | 来源文件 | 问题数 |
|----------|----------|--------|
| reviewer-a | review-round-1/reviewer-a.md | 3 |
| reviewer-b | review-round-1/reviewer-b.md | 4 |

## 聚合结果

### 问题汇总表

| # | 位置 | 问题描述 | 严重程度 | 来源 | 去重说明 | 冲突 | 决策 |
|---|------|----------|----------|------|----------|------|------|
| 1 | src/a.py:10 | 缺少错误处理 | 🔴 高 | reviewer-a, reviewer-b | 去重（同一位置） | 否 | 采纳 |
| 2 | src/b.py:20 | 命名不规范 | 🟡 中 | reviewer-a | - | 否 | 采纳 |
| 3 | src/c.py:30 | 逻辑冲突 | 🔴 高 | reviewer-a, reviewer-b | - | 是 | 需人工裁决 |

### 去重详情

- **问题 1**（src/a.py:10）：
  - 来源：reviewer-a, reviewer-b
  - 去重原因：同一位置、同一问题
  - 保留的修复建议：
    - reviewer-a：添加 try-catch
    - reviewer-b：使用装饰器统一处理

### 冲突详情

- **问题 3**（src/c.py:30）：
  - reviewer-a 建议：重构整个函数
  - reviewer-b 建议：仅修改返回值
  - 建议互斥，无法自动决定

## 决策摘要

| 决策 | 数量 |
|------|------|
| 采纳 | 3 |
| 忽略 | 1 |
| 需人工裁决 | 1 |

## 忽略项

### 问题 X（src/d.py:40）
- **忽略原因**：该问题已在之前轮次解决
- **来源**：reviewer-a

## 冲突项（需人工裁决）

### 问题 3（src/c.py:30）
- **问题描述**：[...]
- **reviewer-a 建议**：重构整个函数
- **reviewer-b 建议**：仅修改返回值
- **冲突原因**：建议方向互斥

---

## 后续行动

- [ ] 请人工裁决冲突项
- [ ] 确认采纳项后，执行修复
- [ ] 修复后重新执行 review 验证
```

### Action 文件

**文件名**：`action.md`

```markdown
---
task-id: <任务标识>
round: <轮次>
executed-at: <ISO 8601 时间>
protocol: action-v2
---

# 执行记录

## 执行概要

- **任务目录**：[task-dir]
- **轮次**：round-{N}
- **执行时间**：[executed-at]
- **执行模式**：normal（/ dry-run）

## 决策记录

### 采纳项

| # | 位置 | 操作 | 状态 |
|---|------|------|------|
| 1 | src/a.py:10 | 添加 try-catch 错误处理 | ✅ 已执行 |
| 2 | src/b.py:20 | 重命名 variableX → meaningful_name | ✅ 已执行 |

### 忽略项

| # | 位置 | 忽略原因 |
|---|------|----------|
| 4 | src/d.py:40 | 该问题已在之前轮次解决 |

### 需人工裁决项

| # | 位置 | 冲突描述 | 状态 |
|---|------|----------|------|
| 3 | src/c.py:30 | 建议互斥 | ⏳ 待裁决 |

## 执行详情

### 操作 1：src/a.py:10
- **修改前**：
```python
def func():
    process()
```
- **修改后**：
```python
def func():
    try:
        process()
    except Exception as e:
        logger.error(f"Error: {e}")
        raise
```

### 操作 2：src/b.py:20
- **修改前**：`variableX = value`
- **修改后**：`meaningful_name = value`

## 验证结果

- [✅] lint 通过
- [✅] typecheck 通过
- [ ] 测试通过（待执行）

## 后续行动

- [ ] 请人工裁决冲突项
- [ ] 确认所有问题解决后，重新执行 review
```

### 已处理记录

**文件名**：`.processed.json`

```json
{
  "task-id": "<任务标识>",
  "processed": [
    {
      "reviewer-id": "reviewer-a",
      "file": "review-round-1/reviewer-a.md",
      "processed-at": "<ISO 时间>",
      "action": "consumed"
    },
    {
      "reviewer-id": "reviewer-b",
      "file": "review-round-1/reviewer-b.md",
      "processed-at": "<ISO 时间>",
      "action": "consumed"
    }
  ]
}
```

## Conflict Detection

### 冲突定义

当同一问题满足以下任一条件时，标记为冲突：

1. **方向冲突**：一个建议添加/删除，另一个建议保留
2. **方案冲突**：两个建议使用完全不同的实现方式
3. **优先级冲突**：一个标记为高优先级，另一个标记为低优先级且理由矛盾

### 冲突处理原则

- **不得自动决定**：冲突必须由人工裁决
- **保留所有建议**：不删除任何 reviewer 的建议
- **明确标记冲突点**：清晰说明冲突的具体内容

## Early Stop Conditions

> 以下情况下，当前 CLI 可主动决定提前关闭多 CLI 审查机制。
> 与"必须暂停"不同，这些是可选择提前结束的条件。

| 提前关闭条件 | 说明 |
|-------------|------|
| 本轮无新建议 | 当前轮所有 reviewer 均未产出新的可执行修复建议 |
| 全部可忽略 | 当前 CLI 判断所有问题均为重复、低价值或不成立 |
| 验证已通过 | 任务已重新验证通过，且无剩余高优先级问题 |

**关闭流程**：
1. 汇总当前轮次的审查结果
2. 在 `summary-round-{N}.md` 中标记 `status: closed-early`
3. 在 `action.md` 中记录提前关闭原因
4. 明确告知用户：多 CLI 审查已提前关闭，不再进入下一轮

## Manual Intervention Triggers

> 以下情况**必须暂停**，不得自动推进，必须要求人工介入。

| 触发条件 | 说明 |
|----------|------|
| 冲突存在 | 存在未解决的建议冲突（互斥建议） |
| 高优先级问题未收敛 | 同一高优先级问题在 2+ 轮仍未解决 |
| 超出任务边界 | 建议涉及不属于本任务的文件或功能 |
| 违反项目规范 | 建议可能导致安全问题或规范冲突 |
| 当前 CLI 无法判断 | 建议的归属或有效性超出当前 CLI 的判断能力 |
| **轮次达到上限（3 轮）且仍有未解决问题** | 达到轮次上限时，若仍存在未采纳/未忽略的问题，必须触发人工裁决 |

> ⚠️ **3 轮上限不是提前关闭条件，而是强制停机条件。**
> 达到轮次上限时，无论是否存在冲突，都必须输出当前汇总结果并要求人工决策：
> - 若所有问题均已解决（采纳/忽略），方可视为提前关闭
> - 若仍有未解决问题（采纳/忽略/冲突），必须进入人工介入流程，不得自动推进

### 人工介入提示

```
⚠️ 需要人工介入

检测到以下需要人工决策的问题：

🔴 冲突问题（建议互斥）：
  - 问题 3（src/c.py:30）：
    - reviewer-a 建议：重构整个函数
    - reviewer-b 建议：仅修改返回值

请选择：
1. 采纳 reviewer-a 的建议
2. 采纳 reviewer-b 的建议
3. 自定义修复方案
4. 忽略此问题
```

## Echo Requirements

**每次执行结束时，必须回显以下信息**：

| 字段 | 说明 |
|------|------|
| `reviewer-files` | 本次读取的 reviewer 文件列表 |
| `total-before-dedup` | 去重前问题数 |
| `total-after-dedup` | 去重后问题数 |
| `conflict-count` | 冲突问题数 |
| `adopted-count` | 已采纳数量 |
| `ignored-count` | 已忽略数量 |
| `manual-decision-count` | 需人工决策数量 |
| `summary-path` | summary 文件实际路径 |
| `action-path` | action 文件实际路径 |

**格式示例**：
```
✅ 多 CLI 审查汇总完成

📁 task-dir: tmp/multi-cli-review/my-task
🔄 round: 1

📊 报告统计：
- 读取的 reviewer 文件：2
  - review-round-1/reviewer-a.md
  - review-round-1/reviewer-b.md
- 去重前问题数：7
- 去重后问题数：5
- 冲突问题数：1

📋 决策统计：
- 已采纳：3
- 已忽略：1
- 需人工裁决：1

📄 输出文件：
- summary: tmp/multi-cli-review/my-task/summary-round-1.md
- action: tmp/multi-cli-review/my-task/action.md
```

## Error Handling

### 目录不存在

- 报错：`❌ 任务目录不存在：{task-dir}`
- 建议：请确认路径是否正确，或先执行 multi-cli-review 生成报告

### 无可处理报告

- 报错：`⚠️ 目录中无可处理的报告：{task-dir}/review-round-{N}/`
- 建议：请确认 review-round-{N} 目录存在且包含 .md 文件

### 所有报告已处理

- 提示：`ℹ️ 所有报告已处理，使用 --force 强制重新处理`
- 不执行任何操作

### 执行失败

- 标记受影响的操作为 `blocked`
- 记录阻塞原因
- 提示用户确认是否继续

## Common Mistakes

### ❌ 承担 Reviewer 职责

- 问题：生成 reviewer 报告而不是处理报告
- 后果：与 `multi-cli-review` 职责重叠
- 正确做法：只读取和处理 reviewer 报告，不生成新报告

### ❌ 自动决定冲突

- 问题：对互斥建议自动选择其一
- 后果：可能选择错误方案
- 正确做法：冲突必须由人工裁决

### ❌ 不记录忽略原因

- 问题：忽略问题时未记录原因
- 后果：下一轮重复触发同一问题
- 正确做法：忽略项必须记录详细原因

### ❌ 跳过验证

- 问题：执行修复后不验证
- 后果：修复引入新问题
- 正确做法：执行后必须运行 lint/测试验证

### ❌ 遗漏已处理检查

- 问题：重复处理同一报告
- 后果：重复执行相同的修改
- 正确做法：检查 `.processed.json`，避免重复消费

## Tips

1. **先汇总后决策**：先读取所有报告，再做去重和决策
2. **保留所有来源**：即使去重，也要保留所有 reviewer 的建议
3. **冲突必须上报**：不要试图自己决定冲突项
4. **记录决策原因**：每项决策都要有明确的理由
5. **修复后必须验证**：执行修改后立即验证，不要留到下一轮
6. **及时更新记录**：执行完成后更新 `.processed.json`

## Examples

### 示例 1：新协议多 Reviewer 汇总

```text
用户：/multi-cli-review-action --task-dir tmp/multi-cli-review/skill-review

CLI（当前 CLI）：
1. 扫描报告：reviewer-a.md, reviewer-b.md
2. 解析内容：共 7 个问题
3. 去重：合并为 5 个问题
4. 冲突检测：发现 1 个冲突
5. 决策：3 采纳、1 忽略、1 需人工裁决
6. 执行修复
7. 生成 summary 和 action 文件
8. 回显统计

✅ 多 CLI 审查汇总完成

📁 task-dir: tmp/multi-cli-review/skill-review
🔄 round: 1

📊 报告统计：
- 读取的 reviewer 文件：2
- 去重前问题数：7
- 去重后问题数：5
- 冲突问题数：1

📋 决策统计：
- 已采纳：3
- 已忽略：1
- 需人工裁决：1

📄 输出文件：
- summary: tmp/multi-cli-review/skill-review/summary-round-1.md
- action: tmp/multi-cli-review/skill-review/action.md
```

### 示例 2：指定轮次

```text
用户：/multi-cli-review-action --task-dir tmp/multi-cli-review/skill-review --round 2

CLI：
处理 round-2 的报告，跳过 round-1（已在 round-1 处理过）
```

### 示例 3：冲突检测

```text
CLI 检测到冲突：

⚠️ 发现 1 个冲突问题

🔴 问题 3（src/c.py:30）：
  问题描述：返回值类型与声明不符

  reviewer-a 建议：
    - 严重程度：🔴 高
    - 建议修复方向：修改函数签名，返回正确类型

  reviewer-b 建议：
    - 严重程度：🔴 高
    - 建议修复方向：添加类型转换器，保持函数签名

  冲突原因：修改点不同（函数签名 vs 返回值处理）

请选择：
1. 采纳 reviewer-a 的建议
2. 采纳 reviewer-b 的建议
3. 自定义修复方案
4. 忽略此问题
```

## Related Skills

- `multi-cli-review`：其他 CLI 使用，生成缺陷报告
- `brainstorm`：澄清问题边界
- `requesting-code-review`：轻量级代码审查

## Protocol Migration Guide

### 从 action-v1 迁移到 action-v2

| action-v1 | action-v2 |
|-----------|------------|
| 单份 cur_defect.md | 多份 reviewer-{id}.md |
| CLI 2 生成 optimize.md | 当前 CLI 生成 summary + action |
| CLI 1 复核 | 当前 CLI 执行修复后重新验证 |
| 手动决策 | 支持半自动决策 + 人工介入触发 |

### 兼容性说明

- 使用单份报告调用时，自动启用兼容模式（action-v1）
- 新场景**必须使用 action-v2**（`--task-dir` 参数）
