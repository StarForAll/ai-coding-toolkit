---
name: project-audit
description: 所有代码任务都完成了？进入项目级全局代码审查与查缺补漏，先分析讨论，再确认方案，最后统一修改。触发词：项目全局审查、全局代码审查、代码查缺补漏、项目审计、project-audit
---

# /trellis:project-audit — 项目级全局代码审查

> **Workflow Position**: §5.1 → 前: 全部 `任务域=代码相关` 的任务完成 → 后: `/trellis:check` → （默认）`/trellis:finish-work`；任务级条件触发时：`/trellis:review-gate` → `/trellis:finish-work` → `/trellis:delivery`
> **Cross-CLI**: ✅ Claude Code（项目命令：`/trellis:project-audit`） · ✅ OpenCode（TUI: `/trellis:project-audit`；CLI: `trellis/project-audit`；见 `opencode/README.md`） · ⚠️ Codex（通过 AGENTS.md NL 路由触发，不提供项目级 `/trellis:project-audit` 命令；见 `codex/README.md`）

> **Strong Gate**: 本阶段受 [阶段状态机与强门禁协议](../阶段状态机与强门禁协议.md) 约束。project-audit 完成后，必须等待用户明确确认，不能自动切到 `check` / `finish-work` / `delivery`。

---

## When to Use (自然触发)

- "做项目全局审查"
- "全局看一下代码有没有缺漏"
- "做代码查缺补漏"
- "进入 project-audit"
- 所有 `任务域=代码相关` 的任务均已完成，需要在进入最终质量门禁前做一次项目级统一回看

> 手动触发也允许，但默认属于**预审模式**：可以完整执行分析、方案与修改，不替代最终正式 `project-audit`。

---

## 核心目标

`/trellis:project-audit` 不是单任务 `check` 的重复版，它负责：

1. 站在项目全局视角回看所有代码相关产物，而不是只盯着单个任务 diff
2. 识别跨任务累积形成的缺口、遗漏、不一致与错误实现
3. 先和用户讨论发现，再确认修正方案，最后统一修改
4. 作为进入最终质量门禁前的项目级总复核

补充约束：

- `project-audit` 新发现的问题留在当前阶段内处理，不回挂到具体任务
- 若需要多 CLI 审查能力，它在本阶段内作为辅助分析或修复手段使用，不转入任务级 `review-gate`

---

## 自动触发与手动触发

### 自动触发（正式模式）

满足以下**任一**条件时，优先进入本命令：

- `task_plan.md` 存在，且其中定义的全部代码相关 Trellis task 均已完成，且 `PROJECT-AUDIT` 尚未完成
- 多任务 / 跨模块 / 发版前 / 高 blast radius 场景
- 外包 / 新客户项目在交付前

**不强制触发的情况**（Lite 链路）：

- L0 单任务闭环，无跨模块影响
- 内部小任务，影响面明确可控

正式模式下，本命令执行完成后，可以将 `PROJECT-AUDIT` 标记为 `已完成`。

### 手动触发（预审模式）

用户在任意时点都可以手动进入本命令。

预审模式下：

- 允许完整执行下面三步
- 允许实际修改代码
- 但**不**将项目级 `PROJECT-AUDIT` 任务标记为最终完成
- 后续当全部 `代码相关` 任务都完成后，仍需再执行一次正式 `project-audit`

---

## 前置输入

至少读取：

- `$TASK_DIR/prd.md`
- `$TASK_DIR/task_plan.md`
- `docs/requirements/customer-facing-prd.md`（若存在）
- `docs/requirements/developer-facing-prd.md`（若存在）
- 当前项目 `.trellis/spec/` 中与已完成代码任务直接相关的规范
- 与本项目代码相关的核心目录、配置、脚本、测试和关键入口文件

如果 `task_plan.md` 存在，先识别：

- 哪些 Trellis task 属于 `代码相关`
- 哪些 Trellis task 属于 `非代码相关`
- `PROJECT-AUDIT` 当前处于正式模式还是预审模式

---

## 流程

### Step 1: 代码分析阶段

从项目全局角度分析所有代码相关内容，重点看：

- 跨任务之间是否出现实现不一致
- 是否存在遗漏的更新点、漏改点、残留兼容分支
- 是否存在重复实现、错误抽象、接口/字段不一致
- 是否存在“单任务都看起来正确，但放到项目整体就有问题”的情况

必要时优先使用：

- `ace.search_context`：做项目级代码定位与相似实现排查
- `sequential-thinking`：当问题涉及多层依赖、多个模块或多条异常路径时

默认由当前 CLI 先完成首轮分析，至少写出：

- 初始发现
- 初始影响范围
- 本轮审查重点（review focus）

只有在以下任一条件命中时，才允许在分析 / 方案阶段提前引入 `multi-cli-review` 作为辅助证据：

- 当前问题存在高不确定性
- 当前问题存在强争议
- 当前问题涉及跨模块因果链，当前 CLI 难以单独判断
- 用户显式要求使用 `multi-cli-review`

注意：这些是 `project-audit` 内部引入 `multi-cli-review` 的条件，与 `check` 后触发 `review-gate` 的硬条件（安全 / 跨层 / 高 blast radius / 外包 / L2）不同。

即使命中以上条件，也必须先由当前 CLI 形成聚焦后的问题包，再交给 reviewer；不要把宽泛的“整个项目看一下”直接丢给其他 CLI。

若在本阶段提前引入 `multi-cli-review`：

- reviewer 临时证据目录使用：

```text
tmp/multi-cli-review/<task-id>-project-audit/review-round-<N>/
```

其中：

- `<task-id>` 应复用当前任务目录名 / task slug，例如 `04-14-project-audit-review-gate-boundary`
- 同一任务在 `project-audit` 阶段多轮审查时，复用同一个 `tmp/multi-cli-review/<task-id>-project-audit/` 根目录，仅递增 `review-round-<N>`

- 当前 CLI 过程记录写入：

```text
$TASK_DIR/project-audit/reviewer-commands-round-<N>.md
```

- 默认 reviewer 数：2（其他 CLI）
- 最大 reviewer 数：4
- 建议优先在 3 轮内收敛；若超过建议轮次，需用户明确要求继续
- 若当前轮使用双 reviewer，默认生成两条**审查描述相同、`review-focus` 相同、仅 `reviewer-id` 不同**的命令
- 只有在当前 CLI 明确认定需要角色分工时，才允许为不同 reviewer 编写不同的审查描述或不同的审查重点

标准命令示例：

```text
/multi-cli-review "<project-audit 审查描述>" docs/workflows/新项目开发工作流 --task-dir tmp/multi-cli-review/<task-id>-project-audit --reviewer-id <reviewer-id> --round <N> --review-focus "<审查重点>"
```

然后输出：

- 发现列表
- 影响范围
- 哪些属于必须修复，哪些属于可记录风险

这一步必须先和用户讨论；只有在用户确认“讨论结束，可以进入方案阶段”后，才能继续下一步。

### Step 2: 方案确认阶段

根据步骤 1 的发现，给出合适的修正方案。

方案至少说明：

- 修正目标
- 影响文件或模块
- 为什么这样改
- 是否会影响既有任务边界或验收结果
- 是否需要补测试、补文档、补规范

若存在多个可行方案，应给出 2-3 个具体选项和取舍，不要只抛问题给用户。

记录规则：

- 当前 CLI 已复核、且用户认可纳入本轮处理范围的问题，写入 `Confirmed Findings`
- 来自 `multi-cli-review` 的辅助证据，或当前 CLI 尚未完全确认的问题，写入 `Candidate Findings / Reviewer Evidence`
- `Candidate Findings / Reviewer Evidence` 中的每条记录必须标注来源标签，例如 `[self]`、`[reviewer:claude-round-1]`
- 已被否定的候选项从主文档删除，但对应否定原因应保留在本轮过程记录（如 `action-round-<N>.md`）中
- 延期项是否继续保留在候选区，由当前 CLI 结合实际价值判断
- 只有进入 `Confirmed Findings` 的问题，才允许进入 `Confirmed Fix Plan`

这一步也必须等待用户确认。只有在用户明确确认方案后，才能继续下一步。

### Step 3: 具体修改阶段

按已确认方案执行实际修改。

约束：

- 修改必须只围绕 `project-audit` 已确认的全局缺口
- 不借此扩大范围做新的需求扩张
- 改完后不要直接进入交付；下一步必须回到 `/trellis:check`

执行阶段可按需要使用：

- `multi-cli-review`：补充执行中的新疑点、边界条件或争议点
- `multi-cli-review-action`：在用户已确认方案后聚合 reviewer 结论、统一执行修复动作

若执行阶段调用了 reviewer / action 能力，过程记录写入：

```text
$TASK_DIR/project-audit/action-round-<N>.md
```

若当前是正式模式：

- 可在当前任务矩阵中将 `PROJECT-AUDIT` 任务标记为 `已完成`

若当前是预审模式：

- 记录本次预审结论与已做修改
- 但不把 `PROJECT-AUDIT` 标记为最终完成

---

## 输出

```text
$TASK_DIR/project-audit.md

$TASK_DIR/project-audit/
├── reviewer-commands-round-<N>.md
└── action-round-<N>.md

tmp/multi-cli-review/<task-id>-project-audit/
└── review-round-<N>/<reviewer-id>.md
```

清理约定：

- 正式模式的 `project-audit` 完成后，可归档或清理对应 `tmp/multi-cli-review/<task-id>-project-audit/` 目录
- 预审模式可暂时保留该目录，供后续正式模式参考

建议最少包含：

```markdown
# Project Audit Report

## Mode
- formal / pre-audit

## Confirmed Findings

## Candidate Findings / Reviewer Evidence
<!-- 每条记录必须标注来源标签，如 [self] 或 [reviewer:claude-round-1] -->

## Confirmed Fix Plan

## Applied Changes

## Remaining Risks

## Suggested Next Step
```

---

## 下一步推荐

**当前状态**: 项目级全局审查已完成本轮分析/修正；在用户明确确认前，仍停留在 project-audit 阶段。

> 本节定义的是阶段完成后的推荐输出口径，用于帮助当前 CLI 或协作者说明下一步；它不是框架层自动跳转保证。

根据结果：

| 当前结果 | Claude / OpenCode 推荐入口 | Codex 推荐入口 | 说明 |
|---------|---------------------------|----------------|------|
| 已完成本轮审查与修复 | `/trellis:check` | 进入质量检查，或显式触发 `check` skill | **默认推荐**。仅在用户明确确认后才允许进入质量检查 |
| 只完成分析，仍需继续讨论 | `/trellis:project-audit` | 继续项目级审查，或显式触发 `project-audit` skill | 留在当前阶段继续收敛 |
| 方案未确认 | `/trellis:project-audit` | 继续项目级审查，或显式触发 `project-audit` skill | 先确认方案，不进入后续门禁 |
| 审查发现冻结后新增 / 修改 / 删除需求 | [需求变更管理执行卡](../../需求变更管理执行卡.md) | 同上 | 先完成变更评估，不直接混入本轮审查修改 |
| 不确定下一步 | `/trellis:project-audit` | 描述当前审查结果，或显式触发 `project-audit` skill | 先停留在当前阶段澄清，而不是自动跳到下一阶段 |
