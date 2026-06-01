---
name: check
description: 代码写完了？检查一下 — 基于真实改动范围和项目 spec 执行质量检查，运行项目化验证命令，输出偏差清单与下一步建议。适用场景提示：检查一下、质量检查、对照 spec、对照规范、自检、有没有偏差
---

# /trellis:check — 实现后质量检查

> **Workflow Position**: §5.1.x → 前: `/trellis:continue` 实施完成 → 后: native `/trellis:finish-work`（普通任务级收尾）/ `/trellis:review-gate`（条件触发）/ 回 `/trellis:continue` 修复；若当前 task 明确承担项目级收口，再继续 `project-audit` / `delivery`
> **Cross-CLI**: ✅ Claude Code（项目命令：`/trellis:check`） · ✅ OpenCode（TUI: `/trellis:check`；CLI: `trellis/check`；见 `opencode/README.md`） · ⚠️ Codex（通过 AGENTS.md NL 路由触发，不提供项目级 `/trellis:check` 命令；见 `codex/README.md`）

> **Strong Gate**: 本阶段受 [阶段状态机与强门禁协议](../阶段状态机与强门禁协议.md) 约束。`check` 完成后不能自动进入 `review-gate`、`delivery` 或 native `finish-work`，必须先等待用户确认。

---

## When to Use (自然触发)

- "检查一下这次改动"
- "对照 spec 看看有没有问题"
- "做一轮质量检查"
- "实现写完了，先 check 一下"
- 当前任务代码已完成，需要在进入 `review-gate`，或把当前 task 的检查证据交给项目级 owner 消费之前，先做一次任务级质量检查

> 以下场景不要误路由到本命令：
>
> - 需要跨层影响排查 → `/trellis:check`（跨层范围手动指定）
> - 需要多 CLI 补充审查门禁 → `/trellis:review-gate`
> - 需要项目级交付 / 收尾前检查 → `/trellis:delivery`
>
> 这里的“跨层范围手动指定”是指：继续使用当前 `check` 入口，但在执行 `check-quality.py` 时显式补充 `--scope frontend,backend,api` 这类范围声明，并在 `check.md` 的 `Changed Scope` 中同步写出受影响层。

---

## 核心目标

`/trellis:check` 的目标不是重复实现阶段，也不是替代 `review-gate`，而是完成四件事：

1. 基于真实改动范围定位适用的 spec / guideline
2. 执行项目确认过的验证命令并记录证据
3. 检查实现偏差、边界风险、安全与性能问题
4. 输出结构化 `check.md`，供 `review-gate` / `delivery` / native `finish-work` 消费

补充边界：

- 当前嵌入 workflow 显式禁用 `trellis-research` / `trellis-implement` / `trellis-check` 这类 agent/subagent 执行路径；implementation 内的 research / implement / 自检必须由主会话直接完成
- 这里提到的 research / implement / checking 只是 implementation 内部能力分工，不代表允许派发对应 agent
- `/trellis:check` 只在 implementation 主会话工作完成并经用户确认后进入
- `check.md` 记录的是**当前 active task / 当前实施轮**的任务级质量结论，不替代 `project-audit` 的项目级总复核
- 只有当 `task_plan.md` 已声明 formal `PROJECT-AUDIT` 且当前 task 不是对应 carrier 时，当前 stage 才只允许继续任务级动作：回 `implementation` 或进入 `review-gate`
- 普通 implementation 子任务在当前阶段闭环后，默认进入 native `finish-work` 做单任务收尾
- 只有当前 task 明确承担项目级收口时，才继续 `project-audit` / `delivery`

---

## 流程

### Step 1: 识别改动范围

先识别这次实际变更了哪些文件：

```bash
git diff --name-only HEAD
```

必要时补做影响面分析：

**MCP 能力路由**

| 场景 | 调用能力 | 触发条件 | 说明 |
|------|---------|---------|------|
| 代码影响面分析 | `ace.search_context` | 默认优先 | 查找相似代码、调用关系、潜在遗漏点。若不可用，改用 `rg` / 上下文阅读，并标记 `[Evidence Gap]` |
| 复杂验证链路推理 | `sequential-thinking` | 当验证链路涉及 ≥3 个条件组合、异常分支或交叉影响时 | 用于梳理验证优先级和风险路径 |

### Step 2: 定位并读取适用 spec / guideline

根据改动路径判断适用模块：

```bash
python3 ./.trellis/scripts/get_context.py --mode packages
```

然后执行：

1. 读取对应 `.trellis/spec/<package>/<layer>/index.md`
2. 优先从 index 中定位当前层已经项目化的 guideline；若 index 仍是通用模板，则继续读取该层的 `quality-guidelines.md`
3. 结合 design 阶段 `§3.7` 已沉淀的项目化证据继续定位：
   - `$TASK_DIR/design/context7-review.md`
   - 当前 task 或上游 task 中记录自动化检查矩阵的位置
   - `finish-work-checklist.md` 中已经冻结的验证矩阵（若当前任务已进入 close-out 准备态）
4. 阅读具体 guideline 和项目化矩阵，而不是只停留在 index

最低要求：

- 不能只凭记忆判断“应该没问题”
- 不能跳过与当前改动直接相关的质量规则
- 若 index 仍停留在通用模板、`quality-guidelines.md` 也只剩占位说明，且当前 task / 设计产物中仍找不到真实项目化规则来源，必须标记 `[Evidence Gap]`

### Step 3: 执行项目化验证

**调用 Skill**：`verification-before-completion` — 坚持“证据先于断言”完成验证。降级：明确列出验证命令、关键输出和 `pass / fail / not run` 结论。

```bash
python3 <WORKFLOW_DIR>/commands/shell/check-quality.py \
  <task_dir> \
  --test-cmd "<user-confirmed test command>" \
  --lint-cmd "<user-confirmed lint command>" \
  --typecheck-cmd "<user-confirmed type-check command>" \
  --scope "frontend,backend,api" \
  --extra-check "Build=<user-confirmed build command>" \
  --extra-check "E2E=<user-confirmed e2e command>" \
  --extra-check "Migration=<user-confirmed migration validation command>"
```

约束：

- test / lint / typecheck 命令必须来自技术架构确认后的项目化输入
- 若当前项目还需要 build / e2e / migration / 平台质量门禁，使用 `--extra-check "标签=命令"` 追加，不要把它们口头带过
- 若需要手动指定跨层检查范围，使用 `--scope frontend,backend,api` 这类显式声明；它用于提示当前轮 check 应重点覆盖哪些层，不替代 `check.md` 中 `Changed Scope` 的事实记录
- 若当前项目没有某一项检查，则省略对应参数，并在结果中标记 `not run`
- 不猜默认命令，不把其他项目习惯硬套到当前项目
- 失败输出必须保留关键 stdout / stderr 证据，不能只给一句“没过”

### Step 4: 扩展质量检查清单

在原生 `check` 的基础上，继续补做以下检查：

- Spec 对照：实现是否满足需求 / 设计 / contract
- 验证证据：测试 / lint / typecheck 是否覆盖当前改动
- 边界场景：空值、极值、异常值、失败分支
- 安全风险：注入、越权、泄露、fail-open、危险配置
- 性能影响：复杂度、资源占用、慢路径
- 上下文健康：是否出现重复修错、方向漂移、明显遗漏

若当前任务涉及 `ownership_proof_required = yes` 且改动命中了受保护水印文件，还必须追加：

```bash
python3 <WORKFLOW_DIR>/commands/shell/source-watermark-guard.py --task-dir <task-dir> --mode check
```

若只发现已在 `source-watermark-plan.md` 中声明为可自动恢复的低风险片段漂移，可先执行：

```bash
python3 <WORKFLOW_DIR>/commands/shell/source-watermark-guard.py --task-dir <task-dir> --mode repair
```

然后重新执行 `--mode check`，确认修复后的水印保持状态重新通过。未声明为可恢复的漂移不得自动修复，必须人工处理。

**调用 Skill**：`sharp-edges` — 检查危险 API 和配置。降级：手动检查 fail-open 默认值、危险配置和易误用接口。

### Step 5: 生成检查结果

写入：

```text
$TASK_DIR/check.md
```

最少包含：

- 改动范围
- 适用 spec / guideline
- 验证命令与 `pass / fail / not run`
- 偏差清单
- 未覆盖风险
- `Review-Gate Decision` / `补充审查判定`
  - `review_gate_decision`: `skip` / `recommended` / `required`
  - `review_gate_reason`: 当前为什么判成该结果
  - 若 `review_gate_decision = recommended` 且准备在本 task 上直接进入 `delivery`（当前轮未声明 formal `PROJECT-AUDIT`，或当前 task 本身就是 formal carrier），必须额外写：
    - `recommended_review_skip_accepted_by_user`: `yes`
    - `recommended_review_skip_acceptance_note`: 用户为何接受跳过本轮补充审查
  - 6 个任务级硬条件的 `yes` / `no` 留痕
- 建议人工关注模块
- 推荐下一步

建议结构：

```markdown
# Check Report

## Changed Scope

## Applied Specs

## Verification Results

## Deviations

## Uncovered Risks

## Review-Gate Decision

- `review_gate_decision`: `skip`
- `review_gate_reason`: `未命中 review-gate 硬条件，现有验证证据足够`
- `check_gate_status`: `pass` / `fail`
- `recommended_review_skip_accepted_by_user`: `yes` / `no`（仅当 `review_gate_decision = recommended` 且准备在本 task 上直接进入 `delivery`）
- `recommended_review_skip_acceptance_note`: `<仅当上一字段为 yes 时填写>`
- `auth_or_sensitive`: `no`
- `data_migration_or_schema_change`: `no`
- `public_api_or_cross_layer_contract_or_external_integration`: `no`
- `payment_queue_cache_concurrency`: `no`
- `shared_core_with_blast_radius`: `no`
- `explicit_user_review_gate_request`: `no`

## Suggested Next Step
```

### Step 5.5: 写入等待确认状态

当 `check.md` 已完成并且当前轮任务级验证结论已经落盘后，必须显式写入等待确认状态：

```bash
python3 <WORKFLOW_DIR>/commands/shell/workflow-state.py set <task-dir> \
  --stage-status awaiting_user_confirmation \
  --awaiting-user-confirmation true
```

只在用户明确确认后，才允许切到 `review-gate` / `implementation`；若当前 task 只需要任务级收口，则在当前阶段闭环后进入 native `finish-work`；只有当前 task 明确承担项目级收口时，才继续 `project-audit` / `delivery`。

### Step 6: 上下文污染检测

- 重复已修复的错误？→ 停止，开新会话
- 输出方向偏离？→ 导出决策摘要
- 若风险仍不明确，先进入 `/trellis:review-gate` 做正式判定（可能判定为 `skip`），不直接跳到 native `finish-work`

---

## 输出

```text
$TASK_DIR/check.md
```

---

## 下一步推荐

**当前状态**: 质量检查完成，`check.md` 已生成；在用户明确确认前，仍停留在 check 阶段。

> 本节定义的是阶段完成后的推荐输出口径，用于帮助当前 CLI 或协作者说明下一步；它不是框架层自动跳转保证。

根据检查结果：

| 检查结果 | Claude / OpenCode 推荐入口 | Codex 推荐入口 | 说明 |
|---------|---------------------------|----------------|------|
| 当前 task 只是普通 implementation 子任务，且基本合规 | `/trellis:finish-work` | 描述当前活动任务的最终收尾 / 归档 / 会话记录意图，或显式触发 `trellis-finish-work` skill | **默认推荐**。任务级质量闭环后直接做单任务收尾，不进入项目级 `project-audit` / `delivery` |
| 当前 task 明确承担项目级收口，且基本合规 | `/trellis:delivery` | 进入交付收口，或显式触发 `delivery` skill | 仅项目级 owner / formal carrier 使用。进入 delivery 前仍需满足对应项目级门禁 |
| 当前轮已声明 formal `PROJECT-AUDIT`，但当前 task 不是 carrier | `/trellis:continue` 或 `/trellis:review-gate` | 回到实施阶段，或显式触发 `review-gate` skill | 当前 task 只承载任务级 `check`；不得在这个 stage 上直接进入 `project-audit` / `delivery` |
| 当前 task 是 formal `PROJECT-AUDIT` carrier，且基本合规 | `/trellis:delivery` | 进入交付收口，或显式触发 `delivery` skill | 仅在 carrier task 上允许；进入 delivery 前仍需满足并列双门禁 |
| 命中 review-gate 硬条件，或用户显式要求进入补充审查 | `/trellis:review-gate` | 进入补充审查判断，或显式触发 `review-gate` skill | **条件触发**。仅在用户明确确认后才允许切换到 review-gate |
| 存在实现偏差，需先修复 | `/trellis:continue` | 回到实施阶段，或显式触发 `trellis-continue` skill | 回到 implementation 内部链修复偏差项，再重新执行正式 `check` |
| 测试或验证证据不足 | `/trellis:continue` | 回到 implementation 并说明测试先行意图，或显式触发 `trellis-continue` skill | 先补验证证据，再重新执行 `check` |
| 发现上下文污染 | `/trellis:continue` | 开新会话并重新描述当前意图，或显式触发 `trellis-continue` skill | 停止当前会话，开新会话并注入决策摘要 |
| 偏差来自冻结后新增 / 修改 / 删除需求 | [需求变更管理执行卡](../../需求变更管理执行卡.md) | 同上 | 先完成评估与确认；用户接受并入当前轮次后再回到受影响的最早阶段 |
| 偏差仅是纯澄清 | 留在当前阶段 | 留在当前阶段 | 仅限不改变范围、接口契约、验收标准、成本、工期 |
| 不确定下一步 | `/trellis:review-gate` | 描述当前检查结果，或显式触发 `review-gate` skill | 若当前轮已声明 formal `PROJECT-AUDIT` 且当前 task 不是 carrier，不要在本阶段默认建议项目级 `delivery` / `project-audit` |

**review-gate 触发条件**（不是所有 check 都必须走 review-gate）：

- 命中以下任一硬条件：
  - 认证 / 授权 / 权限边界 / 敏感信息处理
  - 数据迁移 / schema 变化 / 删除 / 回填
  - 公共 API / 跨层 contract / 外部系统集成
  - 支付 / 消息队列 / 缓存一致性 / 并发状态
  - 共享核心模块且 blast radius 明显
  - 用户显式要求进入 `review-gate`
- 或根据当前改动的软条件预判，进入 `review-gate` 后大概率会被判定为 `recommended`

`check.md` 必须把这组判定结果结构化写入 `## Review-Gate Decision`。若其中任一硬条件为 `yes`，则 `review_gate_decision` 只能写 `required`；不得再从 `check` 直接切到 `delivery`。若当前轮已声明 formal `PROJECT-AUDIT` 且当前 task 不是对应 carrier，则也不得从 `check` 直接切到 `project-audit` / `delivery`。若 `review_gate_decision = recommended` 且准备在本 task 上直接进入 `delivery`，则必须额外记录 `recommended_review_skip_accepted_by_user = yes` 与 `recommended_review_skip_acceptance_note`。

不满足以上条件时，若当前轮未声明 formal `PROJECT-AUDIT`，或当前 task 本身就是 formal carrier，check 可直接进入 delivery，无需经过 review-gate；否则当前 task 仍只停留在任务级闭环，项目级 `project-audit` / `delivery` 需切回项目级 owner 再进入。
