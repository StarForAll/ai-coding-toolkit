# Research: 工作流修复点审计

- **Query**: 深度分析 9 个修复点，判断当前工作流是否真正满足要求
- **Scope**: internal
- **Date**: 2026-05-09

## Findings

### 修复点 4: brainstorm 阶段确认完成并准备进入 design 前，需要在目标项目 docs/requirements/ 下补齐项目级需求文档结构；其中 customer-facing-prd.md 必须先可用并补齐 ## 项目级粗估摘要，developer-facing-prd.md 改为在 design 阶段技术架构确认后再正式生成

- **是否满足**: ✅ 已满足
- **证据**:

| 文件路径 | 行号/关键字 | 描述 |
|---|---|---|
| `commands/brainstorm.md` | Step 8 (L301-329) | 明确要求"在进入 design 前，必须先补齐 docs/requirements/customer-facing-prd.md"；"customer-facing-prd.md 必须已经补齐 ## 项目级粗估摘要"；"developer-facing-prd.md 不在此时强制生成；它等到 design 阶段技术架构确认后再正式落盘" |
| `commands/design.md` | Step 7 块 A (L253-270) | "正式生成 docs/requirements/developer-facing-prd.md"，仅在架构确认后的块 A 中执行 |
| `阶段状态机与强门禁协议.md` | Section 6 (L169-188) | "在技术架构确认前...customer-facing-prd.md 可以继续更新...若准备离开 brainstorm 进入 design，customer-facing-prd.md 必须已经补齐 ## 项目级粗估摘要...developer-facing-prd.md 不应正式生成"；"在技术架构确认后...才允许正式生成 developer-facing-prd.md" |
| `工作流总纲.md` | §2.2.0 (L453-476) | "customer-facing-prd.md 在进入 design 前必须存在"；"customer-facing-prd.md 在进入 design 前还必须补齐 ## 项目级粗估摘要"；"developer-facing-prd.md 在技术架构确认前不强制生成；它应在 design 阶段技术架构确认后再正式落盘" |
| `commands/brainstorm.md` | Step 9 路由表 (L385-387) | "需求已准确，但 customer-facing-prd.md 未生成或未同步 → 留在 brainstorm"；"需求已准确，但项目级粗估未生成或未同步 → 留在 brainstorm" |
| `阶段状态机与强门禁协议.md` | Section 5 补充约束 (L165) | "design 及后续阶段的入口还要通过 workflow-state.py validate 的文档门禁检查；其中包含 brainstorm 收口前必须落盘的项目级粗估要求" |

- **缺口描述**: 无
- **建议**: 无

---

### 修复点 5: 开启新的任务时需要判断对应的任务是否要求前一个任务必须完成，如果是则需要先进行校验，如果前一个任务完成了才真正开始当前任务

- **是否满足**: ⚠️ 部分满足
- **证据**:

| 文件路径 | 行号/关键字 | 描述 |
|---|---|---|
| `commands/plan.md` | Core Principle 3 (L98-100) | "同项目域内默认串行。单个项目域内，task 默认串行执行" |
| `commands/plan.md` | Core Principle 4 (L102-103) | "串行不等于自动续跑。即使前一个 task 已收口，也不会被解释成默认自动开始下一个" |
| `commands/plan.md` | Step 3 (L305-306) | "若 task 的输出会改变下一个 task 的实现前提，必须串行，不要伪装并行" |
| `工作流总纲.md` | §4.1.2 执行顺序规则 (L1885-1886) | "有前置依赖的 task，只有前置 task 收口后才允许作为下一个候选" |
| `commands/plan.md` | Step 4 门禁摘要 (L426-431) | "task 级门禁：不在本阶段预造；进入某个 task 实现前，由 /trellis:continue 自动执行 before-dev" |
| `工作流总纲.md` | §5.1 ① (L2071-2073) | "优先基于真实 Trellis task 图选择本轮唯一 task...串行不等于自动续跑" |
| `commands/continue.md` | 实施阶段额外约束 (L103) | "一次只推进一个具体叶子 task — 不能把多个 task 混在同一上下文里一起做" |
| `commands/continue.md` | 实施阶段额外约束 (L105) | "串行不等于自动续跑 — 前一 task 完成后仍需再次进入 /trellis:continue，不能自动开始下一个" |
| `commands/continue.md` | Phase Router action 表 (L88-97) | 路由 action 类型含 `awaiting_confirmation` 和 `blocked`，但 `blocked` 是指"执行阶段存在阻塞条件"，不特指"前置 task 未完成" |

- **缺口描述**:
  1. **规则层面已有约束**：plan.md 和工作流总纲明确规定"有前置依赖的 task，只有前置 task 收口后才允许作为下一个候选"，且"串行不等于自动续跑"。continue.md 的实施阶段额外约束也明确"一次只推进一个具体叶子 task"和"串行不等于自动续跑"。
  2. **缺少自动化校验机制**：当前工作流依赖人工判断和 before-dev 注入来间接约束，但 **没有脚本化的前置任务完成校验**。`workflow-state.py validate` 检查的是阶段状态和文档门禁，不检查"当前 task 的前置 task 是否已 archive/complete"。`plan-validate.py` 检查的是 plan 产物结构完整性，也不检查前置 task 完成状态。
  3. **continue 路由不检查前置 task 完成状态**：已完整读取 `continue.md`，Phase Router 的路由逻辑（`workflow-state.py route`）输出的 action 类型中，`blocked` 是通用阻断状态，不特指"前置 task 未完成"。路由逻辑中没有"查询 task_plan.md 中的依赖关系 → 校验前置 task 状态"的步骤。continue.md 只强调"一次只推进一个叶子 task"和"不能自动续跑"，但未要求在进入新 task 前校验其前置 task 的完成状态。

- **建议**: 在 `/trellis:continue` 或 before-dev 步骤中增加对前置 task 完成状态的校验；或在 `workflow-state.py validate` 中增加依赖任务完成状态检查项；或在 `workflow-state.py route` 中增加"依赖 task 状态检查"分支，当前置 task 未完成时返回 `blocked` 并列出未完成的前置 task。

---

### 修复点 7: 任务信息分配给具体的任务不能挤压到 task_plan.md 文件中而是使用 trellis 的任务机制且每一个具体的任务需要在执行前补充其任务相关的测试门禁

- **是否满足**: ✅ 已满足
- **证据**:

| 文件路径 | 行号/关键字 | 描述 |
|---|---|---|
| `commands/plan.md` | Core Principle 1 (L92-93) | "Trellis task 才是主执行单元...task_plan.md 只保留摘要；真实执行状态依赖 .trellis/tasks/<task>/task.json、.current-task、before-dev.md、check.md 等任务产物" |
| `commands/plan.md` | Step 3 (L257-275) | 创建真实 Trellis task（task.py create / add-subtask），而非只在 task_plan.md 中记录 |
| `commands/plan.md` | Core Principle 5 (L105-106) | "task 级门禁不在 plan 阶段虚构...每个 task 的具体测试门禁，在进入该 task 实现前由 /trellis:continue 自动触发 before-dev 后生成或刷新 $TASK_DIR/before-dev.md" |
| `工作流总纲.md` | §4.1.1 修正方案 (L1697-1699) | "plan 阶段优先拆成真实 Trellis task，task_plan.md 只保留任务图与门禁摘要" |
| `工作流总纲.md` | §5.1 ②③ (L2076-2086) | "自动执行 before-dev...生成或刷新 $TASK_DIR/before-dev.md...记录：当前 task 适用的 spec / guides / 项目级全局测试基线中当前 task 必须继承的项 / 当前 task 新补充的测试门禁" |
| `commands/test-first.md` | 前置条件 (L60-64) | "当前 task 的 before-dev.md 已存在，或能明确当前 task 的实现边界与门禁" |
| `commands/plan.md` | Step 4 门禁摘要 (L426-431) | "task 级门禁：不在本阶段预造；进入某个 task 实现前，由 /trellis:continue 自动执行 before-dev...自动生成或刷新 $TASK_DIR/before-dev.md，补该 task 的当前测试门禁与实现前约束" |

- **缺口描述**: 无
- **建议**: 无

---

### 修复点 8: 项目包含多种文档以及禁止 codex 使用原型实现前端界面, design 阶段需要尽可能完善在 stitch 生成原型所需要的提示词

- **是否满足**: ✅ 已满足
- **证据**:

**禁止 Codex 使用原型实现前端界面**:

| 文件路径 | 行号/关键字 | 描述 |
|---|---|---|
| `commands/design.md` | Step 2 执行边界 (L127-129) | "UI 原型生成 这一步禁止使用 Codex 作为主执行器...允许作为主执行器的 CLI 只有 Claude Code / OpenCode" |
| `commands/design.md` | Step 7 块 B (L289-294) | "UI -> 首版代码界面 task 禁止使用 Codex 作为主执行器" |
| `工作流总纲.md` | §3.1.1 执行边界 (L1162-1164) | "UI 原型生成 这一步禁止使用 Codex 作为主执行器" |
| `工作流总纲.md` | §3.1.4 (L1287-1293) | "UI -> 首版代码界面...也禁止使用 Codex 作为主执行器...必须改由 Claude Code / OpenCode 承担主执行入口" |
| `阶段状态机与强门禁协议.md` | Section 6 (L191-211) | "design 参考资产隔离规则...UI 原型只属于参考资产，不属于正式实现输入" |

**design 阶段完善 Stitch 提示词**:

| 文件路径 | 行号/关键字 | 描述 |
|---|---|---|
| `commands/design.md` | Step 2 最小执行步骤 (L131-142) | 7 步完整流程：从 PRD 提取 → uiprompt.site 风格选择 → 生成 STITCH-PROMPT.md 草稿 → 固定中文文案/英文 prompt/去 AI 味 → 按页面提取英文 Prompt → Stitch 生成 → Figma 校正 |
| `工作流总纲.md` | §3.1.2 (L1206-1244) | 完整的"外部工具精细化设计与 Stitch Prompt 固定模板"流程，包括 5 步执行流程 + 固定骨架 Prompt 生成 + STITCH-PROMPT.md 固定规则 |
| `工作流总纲.md` | §3.1.2 STITCH-PROMPT.md 固定规则 (L1252-1274) | "默认按单页面/单流程给 Stitch 执行...必须带去 AI 味全局禁止项...建议默认基线禁止项至少包括：不要通用 SaaS 模板感、不要廉价渐变、不要过度圆角/玻璃拟态/悬浮阴影"等 6 项 |
| `commands/design.md` | Step 7 块 B (L283) | "design/STITCH-PROMPT.md（同时承担 Stitch DESIGN.md 的设计系统语义）" |

**项目包含多种文档**:

| 文件路径 | 行号/关键字 | 描述 |
|---|---|---|
| `工作流总纲.md` | §2.2.1 (L553-629) | 完整的技术文档体系结构：BRD/TAD/DDD/IDD/AID/ODD-dev/ODD-user/STITCH-PROMPT/frontend-ui-spec |
| `commands/design.md` | Step 7 块 B (L272-295) | 列出所有条件文档与按需文档 |

- **缺口描述**: 无
- **建议**: 无

---

### 修复点 9: 工作流每一阶段进入下一阶段必须严格遵循要求, 需要用户确认才能进入下一阶段; design 阶段技术架构明确之后补充文档和 spec

- **是否满足**: ✅ 已满足
- **证据**:

**每一阶段进入下一阶段需要用户确认**:

| 文件路径 | 行号/关键字 | 描述 |
|---|---|---|
| `阶段状态机与强门禁协议.md` | Section 1 (L9-13) | "每个阶段结束后，必须先完成退出清单，再由用户明确确认，才允许切换到下一阶段...AI 只能推荐下一步，不能把下一步推荐解释成已经获批的阶段切换" |
| `阶段状态机与强门禁协议.md` | Section 5 (L138-167) | 完整的"阶段切换协议"：7 步流程，强调"未确认前：不能进入下个阶段...不能因为看起来差不多而自动推进" |
| `commands/brainstorm.md` | 前置条件 (L38-42) | "当前阶段只允许重入 brainstorm...完成本阶段后必须等待用户确认，不能自动切到 design / plan / continue" |
| `commands/design.md` | Step 6 (L234-247) | "只有用户明确确认技术架构后，才允许进入 design 后半段" |
| `commands/design.md` | Step 7 (L250-251) | "design 后半段不得一次性跑完，而要按多个子块分段执行。每完成一个子块，都必须停下来给用户确认" |
| `commands/plan.md` | 强门禁规则 (L47-51) | "plan 完成后，必须先输出已完成/未完成/缺失项，再等待用户确认...只有用户确认后，才允许把执行态切到具体叶子 task" |
| `commands/test-first.md` | L11-12 | "测试先行完成后，必须等待用户确认，不能自动推进到实现或 check" |
| `commands/check.md` | L11 | "check 完成后不能自动进入 review-gate 或 finish-work，必须先等待用户确认" |
| `commands/review-gate.md` | L13 | "review-gate 完成后，必须等待用户明确确认，不能自动进入 finish-work" |
| `commands/delivery.md` | L11 | "delivery 完成后，必须等待用户明确确认，不能自动进入 close-out" |
| `commands/continue.md` | Phase Router 核心定位 (L63-64) | "只做当前已确认阶段的识别与重入，不做跨阶段自动推进" |

**design 阶段技术架构明确之后补充文档和 spec**:

| 文件路径 | 行号/关键字 | 描述 |
|---|---|---|
| `commands/design.md` | Step 6 (L234-247) | 架构确认硬确认点：确认前 architecture_confirmed = false，确认后才能进入后半段 |
| `commands/design.md` | Step 7 块 A (L253-270) | "正式生成 developer-facing-prd.md" |
| `commands/design.md` | Step 7 块 B (L272-328) | "正式生成 design/TAD.md, ODD-dev.md, ODD-user.md" 及条件文档 |
| `commands/design.md` | Step 7 块 C (L331-337) | "项目级文档同步"：README.md, README.en.md, docs/ |
| `commands/design.md` | Step 7 块 D (L339-403) | "工程化联动"：spec 导入、spec 完善、自动化检查矩阵、finish-work 适配、close-out 基线适配 |
| `阶段状态机与强门禁协议.md` | Section 6 (L169-227) | "在技术架构确认前...developer-facing-prd.md 不应正式生成...在技术架构确认后...才允许正式生成 developer-facing-prd.md...才允许正式落盘设计文档、项目级文档同步和工程化联动" |

- **缺口描述**: 无
- **建议**: 无

---

### 修复点 10: plan 阶段如果任务足够复杂则需要细分成多个子任务

- **是否满足**: ✅ 已满足
- **证据**:

| 文件路径 | 行号/关键字 | 描述 |
|---|---|---|
| `commands/plan.md` | Core Principle 2 (L95-97) | "复杂任务继续拆：若某个 task 过大、跨越太多上下文、无法单上下文闭环，就必须继续拆成多个串行 task，不允许长期把复杂子阶段堆在单个 task_plan.md 里" |
| `commands/plan.md` | Step 1 拆分就绪检查 (L156-157) | "当前事项是否过大，是否应该继续拆小" |
| `commands/plan.md` | Step 3 (L304-306) | "若 task 超出单上下文预算，继续拆子 task"；"一个 task 只承载一个可闭环实现目标" |
| `commands/brainstorm.md` | Step 7 (L287-299) | "判断是否拆 sub task...若不能，应该拆成几个可独立验证、可独立收尾的子任务...拆分原则：单个上下文只负责一个任务...若任务超出单上下文预算，不允许硬塞进一个上下文继续做" |
| `commands/brainstorm.md` | Step 5 L2 (L258-259) | "L2 复杂任务...最终应拆成多个可闭环子任务" |
| `工作流总纲.md` | §4.1.2 (L1878) | "若某个 task 过大、跨越太多上下文，必须继续拆成多个串行 task" |

- **缺口描述**: 无
- **建议**: 无

---

### 修复点 11: design 阶段产出的 UI 只是作为项目的参考，该 UI 所包含的源码编程语言不能作为实际实现的编程语言参考, 这个是根据实际技术架构决定的

- **是否满足**: ✅ 已满足
- **证据**:

**UI 只是作为项目的参考**:

| 文件路径 | 行号/关键字 | 描述 |
|---|---|---|
| `commands/design.md` | Step 2 原型资产隔离 (L144-157) | "下列内容禁止直接带入正式实现：原型工具导出的组件代码、页面源码、临时演示代码"；"即使原型提供了网页源码或可导出代码，也不能把该代码直接作为正式实现输入" |
| `阶段状态机与强门禁协议.md` | Section 6 (L189-211) | "design 参考资产隔离规则...UI 原型只属于参考资产，不属于正式实现输入...禁止直接带入正式实现的内容：Figma / Stitch / HTML / Storybook 等原型文件本体或分享链接...原型工具导出的组件代码、页面源码、切图占位代码" |
| `工作流总纲.md` | §3.3.0 (L1367-1389) | "原型只用于验证交互与视觉结论，不直接进入正式实现...禁止直接带入正式实现：原型工具导出的组件代码、页面源码、临时演示代码...允许保留的结论必须先转写为结构化设计输入" |

**UI 源码编程语言不能作为实际实现的编程语言参考，由实际技术架构决定**:

| 文件路径 | 行号/关键字 | 描述 |
|---|---|---|
| `阶段状态机与强门禁协议.md` | Section 6 (L209-211) | "若原型与最终技术架构使用的语言、框架、组件体系不一致，仍只保留交互/视觉结论，不继承其代码形态" |
| `commands/design.md` | Step 5 (L186-232) | 技术选型在 UI 设计之后独立进行，实际技术架构由用户在 Step 6 确认 |
| `commands/design.md` | Step 6 (L234-247) | "只有用户明确确认技术架构后，才允许进入 design 后半段"——技术架构独立于 UI 原型 |

- **缺口描述**: 无
- **建议**: 无

---

### 修复点 12: plan 阶段需要强制要求避免执行具体的任务, 不能进行具体的代码实现而是执行当前阶段的任务划分

- **是否满足**: ✅ 已满足
- **证据**:

| 文件路径 | 行号/关键字 | 描述 |
|---|---|---|
| `commands/plan.md` | 硬禁令 (L63-81) | "plan 只允许做任务划分与规划，不允许做具体任务执行"；"明确禁止：生成项目基础代码、脚手架代码、页面初版、接口实现、迁移脚本...编写或修改任何属于具体 task 执行范围的实现代码...借先补个基础文件先做一点为名提前开工" |
| `阶段状态机与强门禁协议.md` | Section 7 (L233-258) | "plan 阶段只允许做规划动作，不允许做执行动作...明确禁止：生成项目基础代码、脚手架代码、页面初版、接口实现、迁移脚本...编写或修改任何属于具体 task 执行范围的实现代码...借先做一点顺手补一个基础文件为名提前进入 implementation" |
| `commands/plan.md` | 强门禁规则 (L51) | "plan 阶段 execution_authorized 必须为 false，由 validate 强制" |
| `工作流总纲.md` | §4.1.1 (L1701-1703) | "硬禁令：plan 阶段必须强制避免执行具体任务...不允许生成项目基础代码、不允许编写实现代码、不允许直接进入 implementation" |
| `工作流总纲.md` | §4.1.1 状态机门禁 (L1703) | "plan 阶段 checkpoints.execution_authorized 必须保持 false" |

- **缺口描述**: 无
- **建议**: 无

---

### 修复点 13: 在具体任务开始前必须输出对应的任务说明

- **是否满足**: ⚠️ 部分满足
- **证据**:

| 文件路径 | 行号/关键字 | 描述 |
|---|---|---|
| `commands/plan.md` | Step 4 当前推荐执行任务 (L338-353) | 输出"当前推荐执行任务（待确认）"说明卡，包含任务路径、标题、本轮目标、本轮不做、前置依赖、验收锚点、风险提醒、推荐主执行 CLI |
| `commands/plan.md` | 补充状态约束 (L530-532) | "在进入 implementation / test-first 前，必须先用当前推荐执行任务（待确认）说明卡向用户说明本轮要开的 task 信息，再等待用户确认" |
| `commands/plan.md` | Step 3 (L273-275) | "当前推荐执行任务（待确认）对应的 leaf task 目录已经具备最小 prd.md"——包含 Goal、In Scope、Out of Scope、Acceptance Anchors、Preferred CLI |
| `commands/test-first.md` | 前置条件 (L60-64) | "当前要处理的具体 task 已明确...当前 task 的 before-dev.md 已存在，或能明确当前 task 的实现边界与门禁" |
| `工作流总纲.md` | §5.1 ②③ (L2076-2086) | before-dev 自动执行，生成/刷新 before-dev.md，包含 task 适用的 spec/guides、测试门禁等 |
| `commands/continue.md` | 实施阶段额外约束 (L104) | "每次进入实现前自动执行 before-dev — 不要求用户显式输入 /trellis:before-dev；产出落到 $TASK_DIR/before-dev.md" |
| `commands/continue.md` | Phase Router (L63-64) | "只做当前已确认阶段的识别与重入，不做跨阶段自动推进" |
| `commands/continue.md` | 下一步推荐输出格式 (L110-129) | 要求每个命令执行完毕后输出"下一步推荐"区块，但该区块是阶段路由推荐，不等同于任务说明卡 |

- **缺口描述**:
  1. **plan -> 首个 implementation 切换有说明卡**：plan.md Step 4 要求输出"当前推荐执行任务（待确认）"说明卡，这是明确的。
  2. **后续任务切换缺少明确的"必须先输出任务说明"硬要求**：当第一个 task 完成后，用户通过 `/trellis:continue` 进入下一个 task 时，continue.md 只要求 before-dev 自动注入上下文并生成 before-dev.md（L104），但**没有显式要求在进入新 task 前先输出该 task 的说明卡**。
  3. **before-dev.md 是技术上下文注入，不等同于"任务说明"**：before-dev.md 记录的是 spec/guides/测试门禁等技术信息，而"任务说明"更偏向于面向人类的目标/范围/不做/验收/风险提醒概览。两者互补但不可互相替代。
  4. **plan.md 的说明卡只约束 plan 出口**：plan.md 的"在进入 implementation / test-first 前，必须先用说明卡"仅约束 plan 阶段退出时的第一个 task，后续通过 continue 切换 task 时没有等价要求。
  5. **continue.md 的"下一步推荐"不满足说明卡要求**：continue.md L110-129 要求输出"下一步推荐"区块，但这是阶段路由推荐（类似"继续当前阶段"/"准备切到下一阶段"的选项表），不包含任务路径、本轮目标、本轮不做、验收锚点等说明卡必需字段。

- **建议**: 在 `/trellis:continue` 的实施阶段额外约束中增加一个硬要求：在进入新 task 实现前，必须先输出该 task 的说明卡（至少包含任务路径、标题、本轮目标、本轮不做、验收锚点），等待用户确认后才允许进入实现代码编写。

## Caveats / Not Found

- `/tmp/trellis-0.5.9-2/.claude/commands/trellis/` 下的命令文件与源工作流 `commands/` 下的命令文件内容基本一致，仅链接路径使用 `.trellis/workflow-docs/` 替代了源工作流的相对路径。审计结论基于两套文件交叉验证。
- 已完整读取 `continue.md`（源工作流路径 `commands/continue.md` 不存在独立文件，已安装版位于 `/tmp/trellis-0.5.9-2/.claude/commands/trellis/continue.md`）。确认 continue.md 中不存在前置任务完成校验和任务说明输出硬要求，修复点 5 和 13 的缺口判定维持不变。
