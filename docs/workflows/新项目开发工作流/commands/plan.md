---
name: plan
description: 设计好了？拆任务 — 以 Trellis task 为主执行单元做任务图规划，`task_plan.md` 只保留摘要。触发词：拆任务、做计划、工作分解、排期、任务分解、里程碑、工作计划
---

# /trellis:plan — 基于 Trellis task 的任务拆解

> **Workflow Position**: §4 → 前: `/trellis:design` → 后: `/trellis:start`
> **Cross-CLI**: ✅ Claude Code（项目命令：`/trellis:plan`） · ✅ OpenCode（TUI: `/trellis:plan`；CLI: `trellis/plan`；见 `opencode/README.md`） · ⚠️ Codex（通过 AGENTS.md NL 路由触发，不提供项目级 `/trellis:plan` 命令；见 `codex/README.md`）

---

## When to Use (自然触发)

- "拆一下任务"
- "做个工作计划"
- "把需求分解成小任务"
- "怎么排期"
- "需要制定实现步骤"

> 简单任务（`L0`、单上下文可闭环）？跳过，直接 `/trellis:start`。

> 若 `PRD` 已冻结后命中需求讨论，按 [需求变更管理执行卡](../需求变更管理执行卡.md) 分流：纯澄清留在当前阶段；新增 / 修改 / 删除进入变更管理，不直接顺手改当前 `task_plan.md` 或 task 图。

## 前置条件

进入 `/trellis:plan` 前，应满足以下条件：

- 技术架构已经过用户明确确认
- 已根据技术架构，从 `trellis-library` 选择并导入合适 spec 到当前项目 `.trellis/spec/`（任务 1，必须先于任务 2 完成）
- 已结合当前项目作用、背景、技术架构，对当前项目 `.trellis/spec/` 完成分析完善（任务 2，仅在任务 1 完成后执行）
- 已基于当前项目实际技术栈，明确自动化检查矩阵（任务 3，仅在任务 1、任务 2 完成后执行；不得只写默认 `Lint`，必须有明确质量平台门禁；采用 Sonar 的项目必须写真实命令，未采用时必须写替代门禁和原因）
- 已基于任务 3 中写清的自动化检查矩阵，完成当前项目 `/trellis:finish-work` 的首次项目化适配（任务 4）
- 已完成当前项目 `/trellis:record-session` 的基线适配，至少明确记录入口、archive 前置条件、元数据边界与阻断条件（任务 5）
- 若项目包含前端视觉落地链路，已在 `design` 阶段明确：
  - `customer-facing-prd.md` 承担 BRD 主文档职责
  - `DDD.md` / `IDD.md` / `AID.md` / `STITCH-PROMPT.md` 是否需要创建
  - 后续需要单独拆出 `UI -> 首版代码界面` 的前端基线 task
- 若属于外包、定制开发或新客户项目（外部项目），已在 `assessment.md` 中明确 `delivery_control_track`（默认 `hosted_deployment`，必要时使用 `trial_authorization`），**并且已按轨道导入交付控制相关 spec**
- 当前 task 的 `workflow-state.json` 已明确切换到 `stage = plan`
- 当前阶段切换已经过用户明确确认，而不是由 `/trellis:start` 或“下一步推荐”自动推进

## 强门禁规则

- 当前阶段受 [阶段状态机与强门禁协议](../阶段状态机与强门禁协议.md) 约束
- `/trellis:plan` 只允许重入当前已确认的 plan 阶段，不允许顺手自动进入实现
- `plan` 完成后，必须先输出已完成/未完成/缺失项，再等待用户确认
- 只有用户确认后，才允许把执行态切到具体叶子 task 的 implementation / test-first 分支

`/trellis:plan` 的职责是：

1. 把已确认需求拆成真实 Trellis task
2. 规划依赖与任务图
3. 产出摘要型 `task_plan.md`

它**不负责**替代 spec 导入、spec 修订、自动化检查矩阵定义，以及 `finish-work` / `record-session` 的首次项目化适配动作。

## 历史数据防漂移要求

- 本命令默认只为本轮确认后的 `L1/L2` 任务生成或更新 `task_plan.md`
- 不为了匹配新规则而回写旧版 `task_plan.md`、旧任务执行矩阵或历史任务状态
- 若历史任务需要重拆、改边界或改验收标准，先走 [需求变更管理执行卡](../需求变更管理执行卡.md)

---

## 核心原则

1. **Trellis task 才是主执行单元**
   `task_plan.md` 只保留摘要；真实执行状态依赖 `.trellis/tasks/<task>/task.json`、`.current-task`、`before-dev.md`、`check.md` 等任务产物。

2. **复杂任务继续拆**
   若某个 task 过大、跨越太多上下文、无法单上下文闭环，就必须继续拆成多个串行 task，不允许长期把复杂子阶段堆在单个 `task_plan.md` 里。

3. **同项目域内默认串行**
   单个项目域内，task 默认串行执行。
   若目标项目包含多个相对独立的项目域 / 端（如前台、后台、管理端），允许按项目域分 lane；但每个 lane 内仍默认串行。

4. **串行不等于自动续跑**
   即使前一个 task 已收口，也不会被解释成“默认自动开始下一个”。下一 task 仍需显式进入 `/trellis:start` 并重新选定实施对象。

5. **task 级门禁不在 plan 阶段虚构**
   `plan` 只记录全局门禁摘要。每个 task 的具体测试门禁，在进入该 task 实现前由 `/trellis:start` 自动触发 `before-dev` 后补到 `$TASK_DIR/before-dev.md`。

---

## 流程

### Step 1: 读取输入并识别执行域

**调用 Skill**：`project-planner` + `writing-plans`

```bash
cat "$TASK_DIR/prd.md"
cat "$TASK_DIR/design/index.md" 2>/dev/null
```

输入侧重点：

- 已确认的需求与设计文档
- 当前项目 `.trellis/spec/` 中已经落地的项目约束
- 当前项目的自动化检查矩阵
- 若为外部项目，`assessment.md` 中约定的交付控制轨道、源码移交时点、权限移交时点

先判断任务是否属于：

- 单项目域单链路
- 多项目域 / 多端并行 lane

若属于后者，先划清项目域边界，再在每个项目域内部做串行 task 链。

### Step 2: 创建或补齐真实 Trellis task

真实执行单元必须优先落成 Trellis task，而不是只写在 `task_plan.md` 里。

最少动作：

```bash
python3 ./.trellis/scripts/task.py create "<title>" --slug <name>
python3 ./.trellis/scripts/task.py create "<child-title>" --slug <child-name> --parent "$TASK_DIR"
python3 ./.trellis/scripts/task.py add-subtask "$TASK_DIR" "$CHILD_DIR"
```

拆分规则：

- 一个 task 只承载一个可闭环实现目标
- 若 task 超出单上下文预算，继续拆子 task
- 若 task 的输出会改变下一个 task 的实现前提，必须串行，不要伪装并行
- 若多个项目域彼此独立，可分别建立 lane，但 lane 内不自动续跑
- 若项目包含前端视觉落地链路，必须额外拆出一个独立 task：`UI -> 首版代码界面`
  - 该 task 只负责把已确认 UI 原型落成第一版代码界面
  - 该 task **禁止**使用 Codex 作为主执行器，必须改用 Claude Code / OpenCode
  - 该 task 的完成定义必须包含 `design/frontend-ui-spec.md`
  - 后续所有前端视觉相关 task 默认依赖这份 `frontend-ui-spec.md`

### Step 3: 生成摘要型 `task_plan.md`

`task_plan.md` 只保留摘要，不再承载实时执行矩阵。

建议结构：

```markdown
## 概述
## 项目域执行策略
## Trellis Task 清单
## 依赖关系
## 门禁摘要
## 任务图摘要
## 外部项目交付控制（如适用）
```

说明：

- `Trellis Task 清单`：列出现实存在的 task / child task / project-audit task
- `依赖关系`：只描述依赖和顺序，不写实时状态
- `门禁摘要`：只写项目级全局门禁；task 级具体门禁在执行前写入 `$TASK_DIR/before-dev.md`
- `任务图摘要`：用于人类快速理解 lane、主链、project-audit 触发条件
- 若存在前端视觉落地链路，必须在 `门禁摘要` 或 `任务图摘要` 中明确：
  - `UI -> 首版代码界面` task 的专属边界
  - `design/frontend-ui-spec.md` 是后续前端任务的统一约束来源

推荐最小模板：

```markdown
## 概述

- 来源：<prd / design / requirements>
- 目标：<一句话目标>

## 项目域执行策略

- <项目域 A>：TASK-A → TASK-B → TASK-C（域内串行，不自动续跑）
- <项目域 B>：TASK-D → TASK-E（域内串行，不自动续跑）

## Trellis Task 清单

| 任务路径 | 类型 | 项目域 | 说明 |
|---------|------|--------|------|
| .trellis/tasks/04-14-task-a | implementation | 项目域 A | ... |
| .trellis/tasks/04-14-task-b | implementation | 项目域 A | ... |
| .trellis/tasks/04-14-project-audit | project-audit | 全局 | 全部代码相关 task 完成后才允许开始 |

## 依赖关系

- TASK-B 依赖 TASK-A
- TASK-C 依赖 TASK-B
- PROJECT-AUDIT 依赖全部代码相关 task 完成

## 门禁摘要

- 项目级全局门禁：
  - <lint / typecheck / test / build / quality gate / delivery gate>
- task 级门禁：
  - 不在本阶段预造；进入某个 task 实现前，由 `/trellis:start` 自动执行 `before-dev`
  - 自动生成 `$TASK_DIR/before-dev.md`，补该 task 的当前测试门禁与实现前约束

## 任务图摘要

- 主链：TASK-A → TASK-B → TASK-C
- 全局终局任务：PROJECT-AUDIT（条件触发）

## 外部项目交付控制（如适用）

- <试运行版交付任务 / 托管部署任务 / 永久授权切换任务 / 源码移交任务 / 控制权移交任务>
```

### Step 4: 项目级终局任务与外部交付任务

满足以下任一条件时，生成 `PROJECT-AUDIT`：

- 多任务 / 跨模块项目
- 发版前或交付前
- 高 blast radius
- 外包 / 新客户项目

外部项目若采用“托管部署 / 试运行授权”的双轨交付控制，仍需在 `task_plan.md` 摘要中显式列出：

- `试运行版交付任务`
- `托管部署任务`
- `永久授权切换任务`
- `源码移交任务`
- `控制权移交任务`

但这些任务也应优先落成真实 Trellis task，而不是只留在摘要里。

### Step 5: 验证拆分结果

```bash
python3 <WORKFLOW_DIR>/commands/shell/plan-validate.py <task-dir>
```

校验重点：

- `task_plan.md` 结构是否完整
- `task_plan.md` 中列出的关键 task 是否已真实存在
- 是否写清项目域执行策略、依赖关系、门禁摘要、任务图摘要
- 是否仍残留旧版执行矩阵字段

不负责判断：

- 依赖设计是否最优
- 任务图是否绝对最省工时
- lane 划分是否唯一正确

---

## 输出

```text
$TASK_DIR/
├── task_plan.md     ← 摘要型计划，不是执行真源
└── ...              ← 对应的真实 Trellis tasks / child tasks / project-audit task
```

补充状态约束：

- 如果当前 root task 在 plan 阶段拆出了 children，则继续实施前应把 `.current-task` 切到实际要执行的叶子任务
- 父任务只保留汇总意义，不应继续作为执行态叶子任务持有 `workflow-state.json`

## 下一步推荐

**当前状态**: 真实 Trellis task 已拆出，`task_plan.md` 仅保留任务图与门禁摘要；在用户明确确认前，仍停留在 plan 阶段。

> 本节定义的是阶段完成后的推荐输出口径，用于帮助当前 CLI 或协作者说明下一步；它不是框架层自动跳转保证。

根据你的意图：

| 你的意图 | Claude / OpenCode 推荐入口 | Codex 推荐入口 | 说明 |
|---------|---------------------------|----------------|------|
| 开始做某个具体 task | `/trellis:start` | 直接进入实施，或显式触发 `start` skill | **默认推荐**。仅在用户明确确认 plan 已完成后才允许；先切换到目标叶子 task，再由 start 自动执行 before-dev 并补 task 门禁 |
| 显式先测某个 task | `/trellis:test-first` | 进入测试驱动，或显式触发 `test-first` skill | 非默认主链；仅在明确要 TDD / 补验证证据时使用 |
| 拆解不合理，重新拆 | `/trellis:plan` | 继续任务拆解，或显式触发 `plan` skill | 重新执行拆解流程 |
| 设计有问题 | `/trellis:design` | 回退设计阶段，或显式触发 `design` skill | 回退到设计阶段 |
| 冻结后出现新增 / 修改 / 删除需求 | [需求变更管理执行卡](../../需求变更管理执行卡.md) | 同上 | 先冻结当前计划；获批后再回到受影响的最早阶段更新计划 |
| 需要项目级全局代码审查 | `/trellis:project-audit` | 进入项目级审查，或显式触发 `project-audit` skill | 仅在全部代码相关 task 完成且用户明确确认后进入；中途也可手动预审 |
| 不确定下一步 | `/trellis:start` | 描述当前意图，或显式触发 `start` skill | 用 Phase Router / skill 路由做阶段检测 |
