---
name: review-gate
description: 质量检查完成了？进入任务级补充审查门禁 — 判断是否需要多 CLI 审查，生成 reviewer 指令包，汇总修复并重新验证。适用场景提示：补充审查、多 CLI 审查、多人审查、让其他 CLI 看一下、review-gate、审查门禁
---

# /trellis:review-gate — 任务级多 CLI 补充审查门禁

> **Workflow Position**: §5.1.x → 前: `/trellis:check`（条件触发） → 后: 回 `/trellis:continue` 修复；普通任务级闭环后进入 native `finish-work`；若当前 task 明确承担项目级收口，再继续 `delivery`
>
> **触发条件**：review-gate 不是所有 check 的必经步骤。默认只在明确高风险条件或用户显式要求时触发；普通 implementation 子任务在任务级闭环后直接进入 native `finish-work`。`review-gate` 仍以任务级补充审查为主；只有当前 task 明确承担项目级收口时，才继续进入 `delivery`。
> **Cross-CLI**: ✅ Claude Code（项目命令：`/trellis:review-gate`） · ✅ OpenCode（TUI: `/trellis:review-gate`；CLI: `trellis/review-gate`；见 `opencode/README.md`） · ⚠️ Codex（通过 AGENTS.md NL 路由触发，不提供项目级 `/trellis:review-gate` 命令；见 `codex/README.md`）

> **Strong Gate**: 本阶段受 [阶段状态机与强门禁协议](../阶段状态机与强门禁协议.md) 约束。review-gate 完成后，必须等待用户明确确认；它可以回 implementation 修复，或在任务级闭环后进入 native `finish-work`。若当前 task 还承担项目级收口，再进入 `delivery`；若 formal carrier 已声明且当前 task 不是它，则必须切回项目级 owner。

---

## When to Use (自然触发)

- "进入 review-gate"
- "让其他 CLI 看一下"
- "做个补充审查"
- "做个多 CLI 审查"
- 当前 CLI 已完成当前任务的质量检查，且需要判断是否进入多 CLI 审查

> 若补充审查识别到的是冻结后的需求讨论，按 [需求变更管理执行卡](../需求变更管理执行卡.md) 分流：纯澄清留在当前阶段；新增 / 修改 / 删除进入变更管理，不直接回实现吸收。

---

## 核心目标

`/trellis:review-gate` 不是简单重复 `check`，而是做三件事：

1. 判断当前任务是否需要进入**任务级多 CLI 补充审查层**
2. 若需要，生成给其他 CLI 直接执行的**标准化命令包**
3. 在其他 CLI 返回报告后，由当前 CLI 统一汇总、修复、回归验证

它的定位是：**高风险 / 高不确定任务的补充审查门禁**。普通任务多数应落在 `skip`，真正进入该层后也默认**轻量优先**，而不是一上来就走多 reviewer 重模式。

---

## 流程

### Step 1: 读取当前任务上下文

至少读取：

- `$TASK_DIR/check.md`
- `check.md` 中的 `## Review-Gate Decision` / `补充审查判定` 章节
- 当前任务的目标 / 验收标准 / 关联设计文档
- 当前任务改动范围、验证结果、风险点

### Step 2: 触发判定

**MCP 能力路由**

| 场景 | 调用能力 | 触发条件 | 说明 |
|------|---------|---------|------|
| 复杂影响面推理 | `sequential-thinking` | 当影响面涉及 ≥3 层或 ≥3 个高风险条件时 | blast radius 分析、多条件分支判定 |
| 依赖安全公告检查 | `exa_web_search_exa` | 当改动涉及依赖升级或外部组件风险时 | 若无法联网，标记 `[Evidence Gap]`，不要给出”无已知漏洞”的结论 |

---

#### 判定模型：硬条件 + 软条件分层门槛

**硬条件（命中任一即触发 `required`）**

以下任一条件成立时，必须进入 review-gate：

1. **认证、授权、权限边界、敏感信息处理**
2. **数据迁移、schema 变更、删除与回填**
3. **公共 API、跨层 contract、外部系统集成**
4. **支付、消息队列、缓存一致性、并发状态**
5. **核心共享模块且 blast radius 明显**（见下方判定标准）
6. **用户显式要求使用 `review-gate`**

---

#### 关键判定标准 1：blast radius 明显

**只有**至少满足以下任一条件时，才能判定为”blast radius 明显”：

✅ **成立条件**：
- 改动落在多个 feature / module / package 共用的核心模块，且当前代码搜索已知下游消费者不少于 3 处
- 改动改变多个层之间共享的数据 contract / serialization / validation 语义
- 改动影响全局启动 / 构建 / runtime 初始化 / 全局状态一致性
- 一旦出错，影响不是局部功能退化，而是跨功能、跨任务或跨模块系统性失效

❌ **不成立**：
- 若以上证据无法从代码、配置、调用关系或任务上下文中成立，不得仅凭”感觉重要”命中该硬条件

---

#### 关键判定标准 2：测试或验证证据明显不足

**只有**至少满足以下任一条件时，才能判定为”测试或验证证据明显不足”：

✅ **成立条件**：
- 改变了行为或修复了 bug，但没有对应自动化测试，也没有明确的手工验证记录
- 改变了失败路径 / 异常分支 / 回退逻辑，但没有负向验证证据
- 改变了跨层 contract / serialization / integration 行为，但没有对应集成或边界验证
- 跳过了当前任务本应执行的关键验证命令，且没有等价替代证据

❌ **不成立**（以下情况默认不构成”证据不足”）：
- 一般性的覆盖率不够理想，但当前改动路径已有合理自动化或手工验证
- 纯文档改动
- 纯重构且未改变性能特征、序列化格式、缓存策略或其他非功能性行为
- 无行为变化改动
- 仅因为”理论上还能补更多测试”

---

#### ⚠️ Anti-Pattern：不得单独作为触发理由

以下情况**单独出现时**，不得作为进入 `review-gate` 的理由：

❌ “看起来复杂”
❌ “改动文件稍多”
❌ “CLI 想更稳一点”

---

#### 软条件门槛

当未命中硬条件时，综合评估以下维度：

- **复杂度层**：改动文件数、改动行数、涉及模块/层数、异常路径数量
- **影响面层**：公共模块、跨层边界、外部集成、blast radius
- **可信度层**：测试或验证证据明显不足、当前 CLI 不确定性高、AI 生成比例高、历史缺陷密度高

---

#### 判定结果与门槛

| 判定结果 | 触发条件 | 说明 |
|---------|---------|------|
| `required` | 命中任一硬条件 | 必须执行多 CLI 审查 |
| `recommended` | 未命中硬条件，但可信度层因”测试或验证证据明显不足”单独达到中门槛 | 建议执行；若现有验证已足够且用户接受风险，可跳过并写明原因 |
| `recommended` | 未命中硬条件，但多个软条件叠加达到现有中门槛 | 同上 |
| `skip` | 否则 | 无需继续多 CLI 审查；普通 implementation 子任务在当前任务级闭环后进入 native `finish-work`；只有当前 task 明确承担项目级收口时，才继续 `delivery` |

将判定写入：

```text
$TASK_DIR/review-gate/review-gate-round-<N>.md
```

### Step 3: 执行模式判定

当本轮不为 `skip` 时，继续判定执行模式：

- `lite`：默认模式。适用于 `recommended`，或用户只是希望先让其他 CLI 补一轮视角时。
- `full`：重模式。默认用于 `required`，或用户明确要求按多 reviewer 审查处理时。

约束：

- `lite` 默认只使用 **1 个 reviewer**
- `full` 默认使用 **2 个 reviewer**
- `full` 最多允许扩展到 **4 个 reviewer**
- `project-audit` 内部使用 `multi-cli-review` 时不复用这里的 `lite`，仍按其自身的 full 口径处理
- 若 `Decision = required`，`Mode` 必须是 `full`；不得用 `required + lite` 规避正式聚合审查

### Step 4: 确认能力前置并生成 reviewer 指令包

若结果为 `required` 或用户接受 `recommended`：

先确认：

- 当前 CLI 已具备 `multi-cli-review-action` 能力
- 目标 reviewer CLI 已具备 `multi-cli-review` 能力

若任一能力缺失：

- 先提示用户在对应 CLI 中补齐对应 skill
- **不要**降级为临时上下文注入或其他兼容协议继续该审查层
- 仅当本轮判定为 `recommended + lite`，且用户明确接受残余风险时，才允许以 `not_run` 结束本轮 review-gate
- 若允许以 `not_run` 结束，必须在 `review-gate-round-<N>.md` 中同时写明：
  - `review_gate_closure_status: not_run`
  - `review_gate_capability_gap: yes`
  - `review_gate_capability_gap_acknowledged_by_user: yes`
  - `review_gate_capability_gap_reason`
- `required` 不允许因能力缺口降级为 `not_run`

用户触发边界：

- 若用户明确要求进入 `review-gate`，则必须进入本阶段；AI 不得以“当前风险不高”为由拒绝。
- 但进入阶段后，当前轮判定结果仍可为 `skip` / `recommended` / `required`。
- 若用户明确要求“多 CLI 审查 / 让其他 CLI 再看一轮 / multi-cli-review”，则外部 reviewer 执行视为必需动作；若能力不可用，必须显式阻塞并说明依赖缺失，不得静默降级。

1. 当前 CLI 创建：

```text
tmp/multi-cli-review/<task-id>/review-round-<N>/
```

2. 当前 CLI 生成：

```text
$TASK_DIR/review-gate/reviewer-commands-round-<N>.md
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

- `lite` 默认 reviewer 数：1（其他 CLI）
- `full` 默认 reviewer 数：2（其他 CLI）
- `full` 最大 reviewer 数：4
- 建议轮次：3；若超过建议轮次，需用户显式要求继续
- task-level reviewer-id 默认使用协调者分配的字母槽位：`a` / `b` / `c` / `d`
- 实际执行审查的 CLI 身份由 reviewer 报告 metadata 中的 `source-cli` 记录，不写入 `reviewer-id`
- `lite` 默认只生成一条 reviewer 命令
- `full` 默认生成两条**审查描述相同、`review-focus` 相同、仅 `reviewer-id` 不同**的命令
- 只有在明确需要角色分工时，才允许为不同 reviewer 编写不同的审查描述或不同的审查重点
- task-level 标准命令必须显式包含 `--task-dir`、`--reviewer-id`、`--round`
- reviewer 只允许使用 `multi-cli-review`
- reviewer 不得直接修改代码
- reviewer 不得创建目录；目录只能由当前 CLI/协调者创建
- reviewer 不得追加 `--output`、`--md-a`、`--md-b` 等参数绕开标准报告路径
- 不转交当前完整对话上下文，只给标准化命令包

### Step 5: 其他 CLI 执行独立审查

用户在其他 CLI 中手动执行标准命令，例如：

```text
/multi-cli-review "<任务级审查描述>" <目标路径> --task-dir tmp/multi-cli-review/<task-id> --reviewer-id a --round <N> --review-focus "边界条件与风险"
```

每个 reviewer 产出：

```text
tmp/multi-cli-review/<task-id>/review-round-<N>/<reviewer-id>.md
```

补充约束：

- reviewer 只写入一个 `{reviewer-id}.md`
- reviewer 报告必须使用标准 metadata，并与目录 / 文件名一致
- reviewer 不得写入 `summary-round-<N>.md`、`action.md`、`.processed.json`

### Step 6: 当前 CLI 汇总、确认并修复

若是 `full` 模式，或 `lite` 模式下 reviewer 提出了新的有效问题，当前 CLI 执行：

```text
/multi-cli-review-action --task-dir tmp/multi-cli-review/<task-id> --round <N>
```

`multi-cli-review-action` 负责：

- 校验 reviewer 报告是否符合标准路径与 metadata 契约
- 结合本地代码、当前任务边界和项目规范重新确认候选问题
- 聚合多个 reviewer 报告、去重并标记冲突
- 先输出 `summary-round-<N>.md`
- 等待用户确认后，只对 `adopted` 且不会明显引入新问题/回归的项执行修复
- 输出 `action.md` 与 `.processed.json`

若 `lite` 模式下 reviewer 没有提出新的有效问题，则可直接记录“无新增有效问题”，不必强制进入 `multi-cli-review-action`。

### Step 6.5: 写入等待确认状态

当本轮判定、聚合结论和必要修复都已落盘后，必须显式写入等待确认状态：

```bash
python3 <WORKFLOW_DIR>/commands/shell/workflow-state.py set <task-dir> \
  --stage-status awaiting_user_confirmation \
  --awaiting-user-confirmation true
```

只有在用户明确确认后，才允许回到 `implementation` 修复；若当前轮未声明 formal `PROJECT-AUDIT`，或当前 task 本身就是 formal carrier，则也允许在当前 task 上继续进入 `delivery`。仅当 formal carrier 已声明且当前 task 不是它时，才必须切回项目级 owner。

### Step 7: 重新验证与关闭

当前 CLI 根据修复结果重新跑该任务的质量检查 / 验证：

- 必要的 lint / typecheck / tests
- 当前任务的关键回归检查
- 如有必要，重写或更新 `$TASK_DIR/check.md`

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
- 建议的修复路径本身可能引入新的问题或回归，当前 CLI 不能给出低回归理由
- 当前 CLI 无法判断建议是否应采纳
- 已超过建议轮次（3 轮）且用户未明确要求继续

---

## 输出

```text
$TASK_DIR/review-gate/
├── review-gate-round-<N>.md
└── reviewer-commands-round-<N>.md

tmp/multi-cli-review/<task-id>/
├── review-round-<N>/<reviewer-id>.md
├── summary-round-<N>.md   # 当前 CLI / multi-cli-review-action 输出
├── action.md              # 当前 CLI / multi-cli-review-action 输出
└── .processed.json        # 当前 CLI / multi-cli-review-action 维护
```

最小契约补充：

- `review-gate-round-<N>.md`
  - `## Decision` 中必须以结构化单值写入 `review_gate_decision`，只能是 `skip` / `recommended` / `required`
  - `## Mode` 中必须以结构化单值写入 `review_gate_mode`，只能是 `lite` / `full`
  - `review_gate_closure_status` 必须是 `pass` / `fail` / `not_run`
- 当 `review_gate_closure_status = not_run` 时，仅允许用于 `recommended + lite`，且必须额外写入：
  - `review_gate_capability_gap: yes`
  - `review_gate_capability_gap_acknowledged_by_user: yes`
  - `review_gate_capability_gap_reason`
- 当 `Decision` 为 `recommended` 或 `required` 时，必须生成 `reviewer-commands-round-<N>.md`
- `recommended + lite` 至少需要 1 份真实 reviewer 报告；不能只生成指令包。唯一例外是上面的 capability-gap `not_run` 闭环
- 当 `Mode = full` 时，必须补齐 `summary-round-<N>.md`
- `required + full` 至少需要 2 份真实 reviewer 报告，且 reviewer 报告路径必须落在 `tmp/multi-cli-review/<task-id>/review-round-<N>/`
- 当 `Decision = required` 时，`Mode` 必须是 `full`
- 若已生成 reviewer 报告，需有 `tmp/multi-cli-review/<task-id>/action.md` 或 `$TASK_DIR/review-gate/action-round-<N>.md` 记录当前 CLI 的采纳/拒绝决策与复验结果

---

## 下一步推荐

**当前状态**: `/trellis:review-gate` 已完成当前任务的补充审查判定；在用户明确确认前，仍停留在 review-gate 阶段。

> 本节定义的是阶段完成后的推荐输出口径，用于帮助当前 CLI 或协作者说明下一步；它不是框架层自动跳转保证。

根据判定结果：

| 判定结果 | Claude / OpenCode 推荐入口 | Codex 推荐入口 | 说明 |
|---------|---------------------------|----------------|------|
| `skip`，当前任务级补充审查已闭环 | 若未声明 formal `PROJECT-AUDIT`，或当前 task 本身就是 formal carrier，则进入 `/trellis:delivery`；否则切回项目级 owner 再进入 `/trellis:project-audit` 或 `/trellis:delivery` | 同左 | **默认推荐**。只有在 formal carrier 已声明且当前 task 不是它时，才需要 owner handoff |
| 接受 `recommended` | 在已具备 `multi-cli-review` 能力的其他 CLI 中运行 `multi-cli-review`（`lite`） | 在目标 CLI 中发起 lite 审查，或显式触发 `multi-cli-review` skill | **默认 1 个 reviewer**。若发现新问题，再进入 `multi-cli-review-action` |
| `required` | 在已具备 `multi-cli-review` 能力的其他 CLI 中运行 `multi-cli-review`（`full`） | 在目标 CLI 中发起 full 审查，或显式触发 `multi-cli-review` skill | **默认 2 个 reviewer**；若目标 CLI 尚未具备该 skill，先补齐能力再执行 |
| 报告已就绪，准备汇总修复 | `multi-cli-review-action` 能力 | `multi-cli-review-action` skill | 当前 CLI 先汇总报告、输出 `summary`、等待用户确认后仅执行低回归的 `adopted` 修复，再重新验证 |
| 审查发现需回到实现阶段 | `/trellis:continue` | 回到实施阶段，或显式触发 `trellis-continue` skill | 回到当前任务修复问题 |
| 审查发现冻结后新增 / 修改 / 删除需求 | [需求变更管理执行卡](../../需求变更管理执行卡.md) | 同上 | 先处理评估与基线更新，再回到受影响的最早阶段 |
| 出现冲突或超过建议轮次仍未收敛 | 用户人工决策 | 用户人工决策 | 若用户未明确要求继续下一轮，先做人工裁决 |
