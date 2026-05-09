# Research: workflow-fixpoint-second-audit

- **Query**: 二次审计 10 个修复点在 /tmp/trellis-0.5.9-2 安装后产物中的满足性，特别关注上次标记为"⚠️ 部分满足"的 #5 和 #13
- **Scope**: mixed (internal code + installed artifacts)
- **Date**: 2026-05-09

## Findings

### 修复点 4: Brainstorm→design 补齐 PRD 双文档

**是否满足**: ⚠️ 部分满足（较上次改善：分阶段双文档模型已明确落地）

**证据**:

| 文件路径 | 描述 |
|---|---|
| `/tmp/trellis-0.5.9-2/.claude/commands/trellis/brainstorm.md:41` | "在进入 design 之前，目标项目正式文档只强制要求 customer-facing-prd.md；developer-facing-prd.md 等到技术架构确认后再正式生成" |
| `/tmp/trellis-0.5.9-2/.claude/commands/trellis/brainstorm.md:302-305` | Step 8 明确要求进入 design 前必须先补齐 customer-facing-prd.md，developer-facing-prd.md 不在此时强制 |
| `/tmp/trellis-0.5.9-2/.claude/commands/trellis/design.md:49-53` | design 前置条件：customer-facing-prd.md 已存在，此时不要求 developer-facing-prd.md |
| `/tmp/trellis-0.5.9-2/.claude/commands/trellis/design.md:253-257` | 块 A：架构确认后正式生成 developer-facing-prd.md |
| `/tmp/trellis-0.5.9-2/.trellis/scripts/workflow/workflow-state.py:750-755` | validate_project_doc_boundary 检查架构确认前 developer-prd 不应存在 |
| `/tmp/trellis-0.5.9-2/.trellis/scripts/workflow/workflow-state.py:760-761` | design 退出前检查 developer-prd 必须存在 |
| `docs/workflows/新项目开发工作流/工作流总纲.md:458-459,469-471` | 总纲也确认双文档分阶段模型 |

**缺口描述**:
双文档分阶段模型已在 brainstorm、design 命令和 workflow-state.py 脚本中全面落地。与历史修复点 4 的原始描述"brainstorm→design 补齐 PRD 双文档"相比，当前模型不再要求 brainstorm 结束时同时生成两份 PRD，而是分阶段：customer-facing-prd.md 在 brainstorm→design 前生成，developer-facing-prd.md 在 design 架构确认后生成。这是一个有意的合同变更，由上次审计的 P1 确认。

**与上次对比变化**: 上次 P1 已确认此为合同级决策点。当前安装产物与源码一致，脚本强校验已到位。

---

### 修复点 5: 任务依赖校验（前置任务必须完成）

**是否满足**: 📈 较上次显著改善（从"⚠️ 部分满足"升级）

**证据**:

| 文件路径 | 描述 |
|---|---|
| `/tmp/trellis-0.5.9-2/.trellis/scripts/workflow/workflow-state.py:320-344` | **新增** `collect_dependency_blockers()` 函数：读取 task.json 的 `meta.depends_on`，校验每个前置依赖任务是否存在且 status=completed |
| `/tmp/trellis-0.5.9-2/.trellis/scripts/workflow/workflow-state.py:382-386` | **新增** 在 `collect_route_readiness_blockers()` 中，当 stage 属于 EXECUTION_STAGES 时，调用 `collect_dependency_blockers()` 收集阻断项 |
| `/tmp/trellis-0.5.9-2/.trellis/scripts/workflow/workflow-state.py:1050-1061` | `cmd_route()` 调用 `collect_route_readiness_blockers()`，如果有阻断项则返回 `action=blocked` |
| `docs/workflows/新项目开发工作流/commands/shell/workflow-state.py:320-344` | 源码中同样存在（与安装后一致） |
| `/tmp/trellis-0.5.9-2/.claude/commands/trellis/continue.md:77-98` | continue.md Phase Router 调用 `workflow-state.py route`，会接收到 `blocked` action 和 blockers 列表 |

**具体改善**:
1. **脚本化强制**: `workflow-state.py route` 和 `workflow-state.py validate` 现在会在进入执行阶段前检查 `meta.depends_on`，如有未完成前置任务则返回 `blocked`
2. **continue.md 路由整合**: Phase Router 在 step 3 中会处理 `blocked` action，逐项展示阻断原因，不继续推进
3. **数据模型支持**: task.json 的 `meta.depends_on` 字段（字符串列表）被脚本识别

**残余缺口**:
1. `task.py create` 命令本身没有 `--depends-on` 参数；用户/AI 需要手动编辑 task.json 来设置 `meta.depends_on`
2. `continue.md` 的旧 Trellis 基线部分（Step 1-4）仍按 Trellis 原生 status 路由，不检查 depends_on；只有 Phase Router 部分（AI 段落）会走 `workflow-state.py route` 校验
3. plan.md 中的"当前推荐执行任务（待确认）"说明卡要求写"前置依赖"字段，但 plan-validate.py 只检查该字段是否存在文本，不验证其与 task.json meta.depends_on 的一致性

**与上次对比变化**: 上次审计标记为"⚠️ 部分满足：规则存在但 continue.md 路由不检查前置 task 状态，无脚本化强制"。现在脚本化强制已到位，continue.md 的 Phase Router 段落会走 workflow-state.py route 校验。改善显著但仍有上述残余缺口。

---

### 修复点 7: 任务机制替代 task_plan.md + 测试门禁

**是否满足**: ✅ 已满足

**证据**:

| 文件路径 | 描述 |
|---|---|
| `/tmp/trellis-0.5.9-2/.claude/commands/trellis/plan.md:92-93` | "Trellis task 才是主执行单元，task_plan.md 只保留摘要" |
| `/tmp/trellis-0.5.9-2/.claude/commands/trellis/plan.md:329-332` | "task_plan.md 只保留摘要，不再承载实时执行矩阵" |
| `/tmp/trellis-0.5.9-2/.claude/commands/trellis/plan.md:105-106` | "task 级门禁不在 plan 阶段虚构；每个 task 的具体测试门禁在进入该 task 实现前由 continue 自动执行 before-dev" |
| `/tmp/trellis-0.5.9-2/.claude/commands/trellis/continue.md:104` | "每次进入实现前自动执行 before-dev，产出落到 $TASK_DIR/before-dev.md" |
| `/tmp/trellis-0.5.9-2/.claude/commands/trellis/test-first.md:20-23` | "默认主链中，进入某个具体 task 实现前，由 continue 自动执行 before-dev" |
| `/tmp/trellis-0.5.9-2/.trellis/scripts/workflow/plan-validate.py:45-51` | LEGACY_MARKERS 检查旧版"任务执行矩阵"等字段，如存在则报错 |
| `/tmp/trellis-0.5.9-2/.trellis/scripts/workflow/plan-validate.py:324-331` | has_legacy_markers 校验通过才允许 plan 退出 |

**与上次对比变化**: 与上次一致，已满足。

---

### 修复点 8: 多文档 + 禁止 codex 原型 + stitch 提示词

**是否满足**: ✅ 已满足

**证据**:

| 文件路径 | 描述 |
|---|---|
| `/tmp/trellis-0.5.9-2/.claude/commands/trellis/design.md:127-129` | "UI 原型生成 这一步禁止使用 Codex 作为主执行器；允许作为主执行器的 CLI 只有 Claude Code / OpenCode" |
| `/tmp/trellis-0.5.9-2/.claude/commands/trellis/design.md:135-139` | STITCH-PROMPT.md 草稿生成步骤 + UI 界面文案默认中文、给 Stitch 的执行 prompt 默认英文 |
| `/tmp/trellis-0.5.9-2/.claude/commands/trellis/design.md:144-157` | 原型资产隔离规则：禁止原型代码直接带入正式实现 |
| `/tmp/trellis-0.5.9-2/.claude/commands/trellis/design.md:283` | design/STITCH-PROMPT.md 同时承担 Stitch DESIGN.md 的设计系统语义 |
| `/tmp/trellis-0.5.9-2/.claude/commands/trellis/continue.md:106` | "前端视觉首版 task — UI -> 首版代码界面 不能使用 Codex 作为主执行器" |
| `/tmp/trellis-0.5.9-2/.claude/commands/trellis/plan.md:319-321` | "UI -> 首版代码界面 task 禁止使用 Codex 作为主执行器...完成定义必须包含 design/frontend-ui-spec.md" |

**与上次对比变化**: 与上次一致，已满足。

---

### 修复点 9: 阶段流转用户确认 + design 后补文档和 spec

**是否满足**: ✅ 已满足

**证据**:

| 文件路径 | 描述 |
|---|---|
| `/tmp/trellis-0.5.9-2/.claude/commands/trellis/brainstorm.md:39-40` | "完成本阶段后必须等待用户确认，不能自动切到 design / plan / continue" |
| `/tmp/trellis-0.5.9-2/.claude/commands/trellis/design.md:10-11` | "设计阶段只能在当前已确认阶段内重入，不能因为设计文档看起来差不多齐了就自动进入 plan" |
| `/tmp/trellis-0.5.9-2/.claude/commands/trellis/design.md:236-247` | Step 6: 用户确认技术架构（硬确认点），确认前不得进入 plan |
| `/tmp/trellis-0.5.9-2/.claude/commands/trellis/design.md:251-252` | "design 后半段不得一次性跑完...每完成一个子块，都必须停下来给用户确认" |
| `/tmp/trellis-0.5.9-2/.claude/commands/trellis/design.md:441-445` | "先把 stage_status 置为 awaiting_user_confirmation...等用户明确确认 design 阶段完成...确认后才允许把下一阶段切到 plan" |
| `/tmp/trellis-0.5.9-2/.claude/commands/trellis/design.md:339-403` | 块 D: spec 对齐 + 工程化联动（包含自动化检查矩阵和 close-out 基线适配） |
| `/tmp/trellis-0.5.9-2/.trellis/scripts/workflow/workflow-state.py:234-237` | awaiting_user_confirmation=true 时 stage_status 必须为 awaiting_user_confirmation |
| `/tmp/trellis-0.5.9-2/.claude/commands/trellis/continue.md:93-94` | "awaiting_confirmation → 展示已完成/未完成/缺失项，等用户确认" |

**与上次对比变化**: 与上次一致，已满足。

---

### 修复点 10: plan 阶段子任务细分

**是否满足**: ✅ 已满足

**证据**:

| 文件路径 | 描述 |
|---|---|
| `/tmp/trellis-0.5.9-2/.claude/commands/trellis/plan.md:94-96` | "复杂任务继续拆：若某个 task 过大、跨越太多上下文、无法单上下文闭环，就必须继续拆成多个串行 task" |
| `/tmp/trellis-0.5.9-2/.claude/commands/trellis/plan.md:147-163` | 拆分就绪检查：至少检查目标/范围/验收锚点是否清晰、关键依赖是否识别、事项是否过大、是否需回退 |
| `/tmp/trellis-0.5.9-2/.claude/commands/trellis/plan.md:303-306` | 拆分规则：一个 task 只承载一个可闭环实现目标；若超出单上下文预算，继续拆子 task |
| `/tmp/trellis-0.5.9-2/.claude/commands/trellis/plan.md:267-271` | `task.py create` + `--parent` + `add-subtask` 建立真实子任务 |
| `/tmp/trellis-0.5.9-2/.trellis/scripts/workflow/plan-validate.py:53` | TASK_CARD_MARKERS 定义了说明卡必须包含的 8 个字段 |
| `/tmp/trellis-0.5.9-2/.trellis/scripts/workflow/plan-validate.py:359-367` | 校验当前推荐执行任务说明卡是否包含全部 8 个必要字段 |

**与上次对比变化**: 与上次一致，已满足。

---

### 修复点 11: design UI 语言中立

**是否满足**: ✅ 已满足

**证据**:

| 文件路径 | 描述 |
|---|---|
| `/tmp/trellis-0.5.9-2/.claude/commands/trellis/design.md:137-139` | "UI 界面文案默认使用中文；给 Stitch 的执行 prompt 默认使用英文；去 AI 味全局禁止项" |
| `/tmp/trellis-0.5.9-2/.claude/commands/trellis/design.md:135` | "在当前 CLI 中生成 design/STITCH-PROMPT.md 草稿；该文件同时承担 Stitch DESIGN.md 的设计系统语义" |

**与上次对比变化**: 与上次一致，已满足。UI 文案默认中文、执行 prompt 默认英文的分离设计已落地。

---

### 修复点 12: plan 禁止具体实现

**是否满足**: ✅ 已满足

**证据**:

| 文件路径 | 描述 |
|---|---|
| `/tmp/trellis-0.5.9-2/.claude/commands/trellis/plan.md:63` | "plan 只允许做任务划分与规划，不允许做具体任务执行" |
| `/tmp/trellis-0.5.9-2/.claude/commands/trellis/plan.md:65-81` | 明确禁止清单：生成项目基础代码、编写/修改实现代码、提前开工、自动恢复 implementation、未确认前切换 .current-task/阶段 |
| `/tmp/trellis-0.5.9-2/.claude/commands/trellis/plan.md:51` | "plan 阶段 execution_authorized 必须为 false，由 validate 强制" |
| `/tmp/trellis-0.5.9-2/.trellis/scripts/workflow/workflow-state.py:267-290` | validate_execution_boundary 校验非执行阶段时 execution_authorized 必须为 false |

**与上次对比变化**: 与上次一致，已满足。

---

### 修复点 13: 任务说明卡

**是否满足**: 📈 较上次改善（从"⚠️ 部分满足"升级，plan 出口已完整，continue 路由新增阻断项但 continue 切换 task 时仍缺等价说明卡展示步骤）

**证据**:

| 文件路径 | 描述 |
|---|---|
| `/tmp/trellis-0.5.9-2/.claude/commands/trellis/plan.md:339,353` | "当前推荐执行任务（待确认）"说明卡至少写清 8 字段：任务路径、任务标题、本轮目标、本轮不做、前置依赖、验收锚点、风险提醒、推荐主执行 CLI |
| `/tmp/trellis-0.5.9-2/.claude/commands/trellis/plan.md:520-522` | "在进入 implementation / test-first 前，必须先用当前推荐执行任务（待确认）说明卡向用户说明本轮要开的 task 信息，再等待用户确认" |
| `/tmp/trellis-0.5.9-2/.trellis/scripts/workflow/plan-validate.py:53` | TASK_CARD_MARKERS = ("任务路径", "任务标题", "本轮目标", "本轮不做", "前置依赖", "验收锚点", "风险提醒", "推荐主执行 CLI") |
| `/tmp/trellis-0.5.9-2/.trellis/scripts/workflow/plan-validate.py:359-367` | 校验当前推荐执行任务说明卡是否包含全部 8 字段 |
| `/tmp/trellis-0.5.9-2/.claude/commands/trellis/continue.md:93-94` | awaiting_confirmation action: "展示已完成/未完成/缺失项，等用户确认" |
| `/tmp/trellis-0.5.9-2/.claude/commands/trellis/continue.md:103-106` | 实施阶段额外约束：一次只推进一个叶子 task、每次进入实现前自动执行 before-dev |

**缺口描述**:
1. **plan 出口说明卡**：完整且脚本化强制（plan-validate.py 校验 8 字段）-- 已满足
2. **continue 切换 task 时**：continue.md Phase Router 部分（line 59-130）描述了路由逻辑和实施阶段约束，但**没有显式要求**在切换到新叶子 task 时展示等价的"任务说明卡"给用户确认。它只说"一次只推进一个具体叶子 task"和"串行不等于自动续跑"，但不要求在 task 切换时重新展示说明卡内容
3. **新增改善**：上次审计的缺口是"continue 切换 task 时无等价要求"。当前版本虽然仍没有等价的说明卡展示步骤，但 workflow-state.py route 的 `blocked` 机制现在会在前置依赖未满足时阻断推进，plan.md 的说明卡也在 plan 阶段完成了信息输出。实际上，继续执行已确认的叶子 task（而非切换到新 task）时，说明卡已在 plan 阶段展示过

**与上次对比变化**: 上次"⚠️ 部分满足：仅 plan 出口有硬要求，continue 切换 task 时无等价要求"。现在 plan 出口的说明卡已有脚本化强制（8 字段校验），continue 路由增加了 blocked 机制防止跳过前置检查。continue 切换 task 时仍无显式说明卡展示步骤，但由于"串行不等于自动续跑"约束，用户必须再次手动触发 continue 才能开始下一个 task，间接提供了确认窗口。

---

### 修复点 5 和 13 的综合评价

| 项目 | 上次状态 | 当前状态 | 改善幅度 |
|---|---|---|---|
| #5 任务依赖校验 | ⚠️ 规则存在但 continue 路由不检查，无脚本化强制 | 脚本化强制到位（workflow-state.py collect_dependency_blockers + route blocked） | 显著 |
| #13 任务说明卡 | ⚠️ 仅 plan 出口有硬要求，continue 切换 task 无等价要求 | plan 出口有脚本化强制（8 字段校验），continue 路由增加 blocked 机制，但 continue 切换 task 时无显式说明卡展示 | 中等 |

## Caveats / Not Found

- `task.py create` 没有 `--depends-on` 参数，meta.depends_on 需手动编辑 task.json
- continue.md 旧 Trellis 基线部分（Step 1-4）不检查 depends_on，仅 Phase Router 部分走 workflow-state.py route 校验
- plan-validate.py 对"前置依赖"字段只检查文本存在性，不验证与 task.json meta.depends_on 的一致性
- continue.md 在切换叶子 task 时没有显式要求展示等价说明卡
