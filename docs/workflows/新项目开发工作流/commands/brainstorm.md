---
name: brainstorm
description: 需求还不够稳？先按 Trellis 原生需求发现主链收集上下文、研究方案并收敛，再判断需求准确性、复杂度、是否拆 sub task 与下一步路由。触发词：梳理需求、讨论方案、判断要不要拆任务、需求分析、PRD、需求文档、明确需求
---

# /trellis:brainstorm — 需求发现与任务生成前置路由

> **Workflow Position**: §2 → 前: `/trellis:feasibility` → 后: `/trellis:design` / `/trellis:plan` / `/trellis:start`
> **Cross-CLI**: ✅ Claude Code（项目命令：`/trellis:brainstorm`） · ✅ OpenCode（TUI: `/trellis:brainstorm`；CLI: `trellis/brainstorm`；见 `opencode/README.md`） · ⚠️ Codex（通过 AGENTS.md NL 路由触发，不提供项目级 `/trellis:brainstorm` 命令；见 `codex/README.md`）
>
> **Merge Rule**: 本命令保留 Trellis 原生 `brainstorm` 的需求发现主链（Task-first / Action-before-asking / Research-first / Diverge → Converge），并叠加当前 workflow 的 `assessment.md` 前置、需求准确性校验、`L0/L1/L2` 分类、`sub task` 拆分、以及项目级双需求文档门禁。

---

## When to Use (自然触发)

- "帮我梳理一下需求"
- "这个需求到底该怎么做"
- "先判断要不要拆任务"
- "这个任务复杂吗"
- "要不要分成几个子任务"
- "这件事能不能一个上下文做完"
- "这个方案先别急着写代码，先想清楚"

> 若 `assessment.md` 不允许进入 `brainstorm`，先回 `/trellis:feasibility`；若需求已冻结后出现新增 / 修改 / 删除，先走 `§2.5 需求变更管理`，不直接在当前阶段吸收。

---

## 前置条件与边界

- 进入本命令前，新项目默认已完成 `assessment.md` 驱动的可行性评估，且明确允许进入需求发现。
- 本命令负责**需求发现 + 任务生成前置路由**，不直接替代后续设计、计划、实现和审查阶段。
- 若当前已经存在有效 `prd.md`、`task_plan.md` 或任务执行矩阵，先检查是否已覆盖本轮要讨论的事项；已存在等价任务或子任务时，不重复生成。
- `task_dir/prd.md` 仅是当前任务的工作底稿，不等同于目标项目里的正式需求文档；项目级正式需求文档统一落在目标项目的 `docs/requirements/`。
- 本命令新增的规则默认只约束**后续新生成或重新确认的任务**，不追溯重写历史 `prd.md`、历史 `task_plan.md`、历史任务状态或既有审查记录。

### 历史数据防漂移规则

- 不为了套用新规则而回填旧任务的状态枚举、执行矩阵或已归档记录。
- 已冻结并进入执行的历史任务，如确需调整范围、拆分方式或验收标准，按 `§2.5 需求变更管理` 处理，而不是静默改写历史文档。
- 新规则下新增的字段、判定结论、拆分结果，应只写入本轮确认后的 `prd.md`、`task_plan.md` 或新建子任务中。

---

## Core Principles (Non-negotiable)

1. **Task-first**
   先确保当前讨论有可落点的任务目录和工作底稿，不让需求只停留在对话里。

2. **Action-before-asking**
   能从仓库、文档、已有任务、配置或快速调研得到的信息，先自己查，不先把低价值问题抛给用户。

3. **One question per message**
   只问阻塞或偏好型问题，而且一次只问一个，避免把 brainstorm 变成问卷。

4. **Prefer concrete options**
   需要用户决策时，优先给 2-3 个可执行选项和取舍，而不是泛泛追问。

5. **Research-first for technical choices**
   只要涉及方案选型、约定差异、行业实践或实现路径选择，先调研再收敛。

6. **Diverge → Converge**
   先扩展思路，把未来演进、异常路径、边界条件想清楚；再收敛到本轮 MVP 和明确的 out-of-scope。

7. **No meta questions**
   不问“要不要先搜一下”“要不要把代码贴给我”，直接搜、直接读；只有真正阻塞时才问最小必要问题。

---

## 流程

### Step 0: Ensure Task Exists (ALWAYS)

在任何澄清、调研或提问前，先确保当前讨论有任务目录可承载：

- 若当前已有 `$TASK_DIR`，直接复用并更新其中的 `prd.md`
- 若当前还没有任务目录，立即创建一个临时任务并种下工作底稿

```bash
TASK_DIR=$(python3 ./.trellis/scripts/task.py create "brainstorm: <short goal>" --slug <auto>)
```

`$TASK_DIR/prd.md` 至少保留这些区块：

```markdown
# brainstorm: <short goal>

## Goal

## What I Already Know

## Assumptions (Temporary)

## Open Questions

## Requirements (Evolving)

## Acceptance Criteria (Evolving)

## Out of Scope

## Technical Notes

## Workflow Decisions
- Accuracy Status:
- Complexity:
- Need More Divergence:
- Need Sub Tasks:
- Next Step:
```

说明：

- `task_dir/prd.md` 是阶段内工作底稿，用于承接澄清、调研和路由判断
- 它不能替代目标项目中的 `docs/requirements/customer-facing-prd.md` 与 `docs/requirements/developer-facing-prd.md`

### Step 1: Auto-Context (Do This Before Asking Questions)

至少读取：

- `assessment.md`
- `prd.md`
- `task_plan.md`（若存在）
- 当前任务执行矩阵或已存在的子任务列表（若存在）
- `docs/requirements/customer-facing-prd.md`（若存在）
- `docs/requirements/developer-facing-prd.md`（若存在）
- 与当前需求直接相关的 repo 代码 / 文档 / 设计说明

先完成这些动作，再决定要不要问用户：

- 检查当前工作流中是否已存在等价任务或子任务
- 检查这次讨论是纯澄清，还是会触发范围 / 契约 / 验收变化
- 找出现有模式、相邻流程、历史兼容约束和关键依赖
- 把已确认事实写回 `prd.md` 的 `What I Already Know` / `Technical Notes`

### Step 2: Question Gate (Ask Only High-Value Questions)

在问任何问题前，先做三层判断：

1. **能否直接推导**
   - 能从仓库、文档、已有任务、快速调研得到答案 → 不问，直接补到 `prd.md`

2. **是不是 meta / lazy question**
   - 类似“要不要先搜一下”“你能把代码贴给我吗” → 不问，直接执行动作

3. **问题类型是不是值得问**
   - 只问 `Blocking` 或 `Preference`
   - `Derivable` 问题不问

### Step 3: Research-first Mode

命中以下任一情况，先调研、后收敛：

- 存在多种可行方案，需要比较取舍
- 用户问“怎么做更合适”“行业里一般怎么做”
- 需求涉及协议、框架、插件机制、CLI 交互约定或模板选型
- 需求虽然明确，但实现路径会明显影响任务拆分方式

**MCP 能力路由**

| 场景 | 调用能力 | 触发条件 | 说明 |
|------|---------|---------|------|
| 需求模糊、需增强 | `ace.enhance_prompt` | 当需求描述不够清晰需要增强时 | 回退：`sequential-thinking`。无 `ace.enhance_prompt` 时，手动补齐目标/范围/验收/边界四项后再分类 |
| 复杂任务发散推理 | `sequential-thinking` | 当需求拆解涉及 ≥3 个决策分支或依赖链 >3 层时 | 复杂任务场景 |
| 可视化需求关系 | `markmap` | 当需要生成需求层级图时 | 需求 → 功能 → 验收标准 |

**调用 Skill**：`prd`

- 当需要从零生成或大幅重写 PRD 时调用
- 降级：手动按目标 / 范围 / 验收标准 / 技术约束 / 边界条件结构生成

### Step 4: 需求描述准确性校验

在生成具体任务前，先判断当前需求描述是否满足以下条件：

- 目标是否清晰
- 范围是否明确
- 验收标准是否可测试
- 关键边界 / 依赖 / 约束是否已知

判定结果：

- `未准确`：继续澄清，不进入任务生成
- `已准确`：进入复杂度分类

若未准确，优先补以下内容：

- 缺失信息
- 隐含假设
- 歧义点
- 关键边界条件

### Step 5: 复杂度统一分类（`L0/L1/L2`）

统一复用当前 workflow 的复杂度口径：

- `L0 简单任务`
  - 需求已准确
  - 单个上下文可闭环
  - 通常只涉及 1-2 个文件或一个明确变更点
  - 不强制先生成 `task_plan.md`

- `L1 标准任务`
  - 需求已准确
  - 涉及多文件、多步骤或明确依赖
  - 需要进入 `/trellis:plan` 生成显式任务拆解

- `L2 复杂任务`
  - 跨模块、跨层、架构级、高风险或高不确定
  - 在正式拆任务前，必须先做发散补充
  - 最终应拆成多个可闭环子任务

### Step 6: 判断是否需要先发散补信息

以下任一命中，先补信息，再决定如何拆任务：

- 需求虽然大体明确，但边界仍可能影响拆分方式
- 需要对齐相邻流程、兼容历史行为或跨层契约
- 失败 / 异常场景会改变实现路径
- 不补信息就无法判断是否应拆成多个子任务

默认规则：

- `L0`：通常不需要发散，直接收敛为单任务
- `L1`：按需做轻量发散
- `L2`：必须先发散补充，再做任务拆解

### Step 7: 判断是否拆 `sub task`

在进入具体任务生成前，必须明确：

- 当前事项是否能在**单个上下文**中完整完成
- 是否可以形成**单任务闭环**
- 若不能，应该拆成几个**可独立验证、可独立收尾**的子任务

拆分原则：

- 单个上下文只负责一个任务
- 单个任务必须独立可测试、可验证、可修复
- 若任务超出单上下文预算，不允许硬塞进一个上下文继续做

### Step 8: 项目级双需求文档门禁（强制）

当需求已达到“可确认”状态后，在进入 `design` / `plan` / `start` 前，必须先补齐目标项目中的两份正式需求文档：

- `docs/requirements/customer-facing-prd.md`
- `docs/requirements/developer-facing-prd.md`

要求：

- 两份文档描述的是同一组项目需求功能点，目标、范围、验收、边界含义必须一致
- 客户向文档尽量用非技术化语言表达业务结果与用户价值
- 开发向文档要展开为实现、测试、接口、约束、风险等开发可执行信息
- `task_dir/prd.md` 继续保留为阶段内工作底稿，但不能替代这两份项目级正式文档
- 后续若命中 `§2.5 需求变更管理` 且变更获批，必须同步更新这两份文档

### Step 9: 生成下一步路由

| 判定结果 | 下一步 | 说明 |
|---------|------|------|
| 需求未准确 | 留在 `/trellis:brainstorm` | 继续澄清，不生成具体任务 |
| 需求已准确，但项目级双需求文档未生成或未同步 | 留在 `/trellis:brainstorm` | 先补齐 `docs/requirements/customer-facing-prd.md` 与 `docs/requirements/developer-facing-prd.md` |
| `L0` | `/trellis:start` | 仅限已补齐项目级双需求文档，且单任务闭环成立 |
| `L1` | `/trellis:plan` | 仅限已补齐项目级双需求文档后，进入显式任务拆解与执行安排 |
| `L2` | 继续 `/trellis:brainstorm` 发散补充，然后 `/trellis:plan` | 先补信息，再拆成多个子任务 |

---

## 单任务上下文闭环要求

无论是 `L0` 直接进入 `/trellis:start`，还是 `L1/L2` 经过 `/trellis:plan` 后再执行，单个任务上下文都必须覆盖完整闭环：

- 代码实现
- 代码检测
- 质量检测
- 代码修复

禁止将“一个上下文里同时推进多个任务”伪装成单任务执行。

---

## 输出

```text
$TASK_DIR/
├── prd.md                                   # 当前任务的工作底稿：需求发现、调研、复杂度判定、是否拆分的依据
└── task_plan.md                             # 仅当进入 `/trellis:plan` 时生成

docs/requirements/
├── customer-facing-prd.md                   # 项目级正式需求文档（客户向）
└── developer-facing-prd.md                  # 项目级正式需求文档（开发向）
```

建议至少记录以下判定结果：

- 需求描述是否已准确
- 当前复杂度等级：`L0` / `L1` / `L2`
- 是否需要先发散补信息
- 是否需要拆 `sub task`
- 项目级双需求文档是否已生成并完成同步
- 推荐下一步命令

---

## 下一步推荐

**当前状态**: 已完成需求发现与任务生成前置路由判断。

> 本节定义的是阶段完成后的推荐输出口径，用于帮助当前 CLI 或协作者说明下一步；它不是框架层自动跳转保证。

根据判定结果：

| 你的意图 | Claude / OpenCode 推荐入口 | Codex 推荐入口 | 说明 |
|---------|---------------------------|----------------|------|
| 继续澄清需求 | `/trellis:brainstorm` | 继续需求澄清，或显式触发 `brainstorm` skill | 信息不足或需求仍有歧义 |
| 做设计 | `/trellis:design` | 进入设计阶段，或显式触发 `design` skill | 前提：项目级双需求文档已生成并同步 |
| 拆任务 | `/trellis:plan` | 进入任务拆解，或显式触发 `plan` skill | `L1/L2` 默认走这里，前提同上 |
| 直接做单任务 | `/trellis:start` | 直接进入实施，或显式触发 `start` skill | 仅限 `L0`、单上下文可闭环，且已补齐项目级双需求文档 |
| 冻结后出现正式变更 | `§2.5 需求变更管理` | 同上 | 不直接改现有任务基线 |
