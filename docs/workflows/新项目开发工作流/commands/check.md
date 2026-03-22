---
name: check
description: 自审完了？做任务级补充审查门禁 — 判断是否需要多 CLI 审查，生成 reviewer 指令包，汇总修复并重新验证。触发词：补充审查、多人审查、让其他 CLI 看一下、check 一下
---

# /trellis:check — 任务级多 CLI 补充审查门禁

> **Workflow Position**: §5.1.x → 前: `/trellis:self-review` → 后: `/trellis:finish-work`
> **Cross-CLI**: ✅ Claude Code · ✅ Cursor (命令名: check) · ⚠️ OpenCode · ⚠️ Codex/Gemini

---

## When to Use (自然触发)

- "check 一下这个任务"
- "让其他 CLI 看一下"
- "做个补充审查"
- "多人审查一下"
- 当前 CLI 已完成任务原本 review，且需要判断是否进入多 CLI 审查

---

## 核心目标

`/trellis:check` 不是简单重复 `self-review`，而是做三件事：

1. 判断当前任务是否需要进入**任务级多 CLI 补充审查层**
2. 若需要，生成给其他 CLI 直接执行的**标准化命令包**
3. 在其他 CLI 返回报告后，由当前 CLI 统一汇总、修复、回归验证

---

## 流程

### Step 1: 读取当前任务上下文

至少读取：

- `$TASK_DIR/self-review.md`
- 当前任务的目标 / 验收标准 / 关联设计文档
- 当前任务改动范围、验证结果、风险点

### Step 2: 触发判定

判定模型：**硬条件 + 软条件分层门槛**

**硬条件（命中即触发）**
- 认证、授权、权限边界、敏感信息处理
- 数据迁移、schema 变更、删除与回填
- 公共 API、跨层 contract、外部系统集成
- 支付、队列、缓存一致性、并发状态
- 核心共享模块且 blast radius 明显
- 用户显式要求执行任务级多 CLI 审查

**软条件门槛**
- 复杂度层：改动文件数、改动行数、涉及模块/层数、异常路径数量
- 影响面层：公共模块、跨层边界、外部集成、blast radius
- 可信度层：测试覆盖不足、当前 CLI 不确定性高、AI 生成比例高、历史缺陷密度高

**判定结果**
- `required`：必须执行多 CLI 审查
- `recommended`：默认推荐执行；若用户坚持可跳过
- `skip`：无需执行，直接进入 `/trellis:finish-work`

将判定写入：

```text
$TASK_DIR/check/review-gate-round-<N>.md
```

### Step 3: 生成 reviewer 指令包

若结果为 `required` 或用户接受 `recommended`：

1. 当前 CLI 创建：

```text
tmp/multi-cli-review/<task-id>/review-round-<N>/
```

2. 当前 CLI 生成：

```text
$TASK_DIR/check/reviewer-commands-round-<N>.md
```

内容至少包括：

- 任务摘要
- 审查重点
- 目标路径 / 关键文件
- 实际轮次 `N`
- `task-dir`
- reviewer-id 分配
- 供其他 CLI 直接复制执行的完整 `multi-cli-review` 命令

约束：

- 默认 reviewer 数：2
- 最大 reviewer 数：4
- reviewer 只允许使用 `multi-cli-review`
- reviewer 不得直接修改代码
- 不转交当前完整对话上下文，只给标准化命令包

### Step 4: 其他 CLI 执行独立审查

用户在其他 CLI 中手动执行标准命令，例如：

```text
/multi-cli-review "<任务级审查描述>" <目标路径> --task-dir tmp/multi-cli-review/<task-id> --reviewer-id claude --round <N> --review-focus "边界条件与风险"
```

每个 reviewer 产出：

```text
tmp/multi-cli-review/<task-id>/review-round-<N>/<reviewer-id>.md
```

### Step 5: 当前 CLI 汇总并修复

其他 CLI 报告就绪后，当前 CLI 执行：

```text
/multi-cli-review-action --task-dir tmp/multi-cli-review/<task-id> --round <N>
```

`multi-cli-review-action` 负责：

- 聚合多个 reviewer 报告
- 去重
- 冲突标记
- 采纳 / 忽略 / 需人工裁决
- 执行统一修复
- 输出 `summary-round-<N>.md` 与 `action.md`

### Step 6: 重新验证与关闭

当前 CLI 根据修复结果重新跑该任务原本的 review / 验证：

- 必要的 lint / typecheck / tests
- 当前任务的关键回归检查
- 如有必要，重写或更新 `$TASK_DIR/self-review.md`

只有在以下任一条件成立时，当前任务才允许关闭：

- 本轮判定为 `skip`
- 多 CLI 审查已完成，且修复后重新验证通过
- 当前轮没有新的有效修复建议，且剩余问题均已明确忽略或关闭

---

## 提前关闭与人工介入

### 可提前关闭

- 当前轮所有 reviewer 都没有新的有效修复建议
- 当前 CLI 判断新增问题均为重复、低价值或不成立
- 修复后验证通过，且无剩余高优先级问题

### 必须人工介入

- reviewer 建议互斥
- 高优先级问题 2+ 轮未收敛
- 建议超出当前任务边界
- 建议可能违反项目规范或带来安全风险
- 当前 CLI 无法判断建议是否应采纳
- 达到 **3 轮上限** 且仍有未解决问题

---

## 输出

```text
$TASK_DIR/check/
├── review-gate-round-<N>.md
└── reviewer-commands-round-<N>.md

tmp/multi-cli-review/<task-id>/
├── review-round-<N>/<reviewer-id>.md
├── summary-round-<N>.md
└── action.md
```

---

## 下一步推荐

**当前状态**: `/trellis:check` 已完成当前任务的补充审查判定。

根据判定结果：

| 判定结果 | 推荐命令 | 说明 |
|---------|---------|------|
| `skip`，可直接提交前检查 | `/trellis:finish-work` | **默认推荐**。无需进入多 CLI 审查 |
| `required` 或接受 `recommended` | 在其他 CLI 中运行 `multi-cli-review` | 先生成 reviewer 报告，再回到当前 CLI 执行 `multi-cli-review-action` |
| 报告已就绪，准备汇总修复 | Skill: `multi-cli-review-action` | 当前 CLI 聚合报告、执行修复、重新验证 |
| 审查发现需回到实现阶段 | `/trellis:start` | 回到当前任务修复问题 |
| 出现冲突或超阈值 | 用户人工决策 | 停止自动推进，先做人工裁决 |
