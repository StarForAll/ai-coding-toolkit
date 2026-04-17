---
name: feasibility
description: 新项目？先评估可行性 — 合规审查、风险评估、报价输出。触发词：帮我评估、能做吗、新项目想法、报价、看看这个项目、能不能接、估个价、接私活、外包项目、客户需求
---

# /trellis:feasibility — 项目可行性评估

> **Workflow Position**: §1 → 前: 无 → 后: `/trellis:brainstorm`
> **Cross-CLI**: ✅ Claude Code（项目命令：`/trellis:feasibility`） · ✅ OpenCode（TUI: `/trellis:feasibility`；CLI: `trellis/feasibility`；见 `opencode/README.md`） · ⚠️ Codex（通过 AGENTS.md NL 路由触发，不提供项目级 `/trellis:feasibility` 命令；见 `codex/README.md`）
>
> **Gate Rule**: 对于新项目 / 新客户需求 / 首次立项，`/trellis:feasibility` 是进入 `/trellis:brainstorm` 前的强制前置门禁；只有在已形成仍有效的 `assessment.md` 且评估前提未变化时，才允许复用既有评估结果而不重跑本阶段。

> **Strong Gate**: 本阶段受 [阶段状态机与强门禁协议](../阶段状态机与强门禁协议.md) 约束。可行性评估完成后，仍需等待用户明确确认，不能自动切到 `brainstorm` / `design` / `start`。

---

## When to Use (自然触发)

用户说以下任何话时，通常可优先视为进入本阶段的候选入口：
- "我有个新项目想法"
- "帮我评估一下这个需求能不能做"
- "有个客户找我做个项目"
- "这个项目的报价怎么算"
- "帮我看看有没有风险"

> 若项目已存在仍有效的 `assessment.md`，且当前只是继续同一轮需求推进，可直接复用该评估结果进入后续阶段；否则仍应先完成本命令。

### 前置条件与出口约束

- 本命令面向**新项目立项、外包接单、客户需求初聊**等“先判断值不值得接”的场景。
- 若当前项目还没有有效 `assessment.md`，或客户主体、需求范围、法律/合规前提发生足以推翻结论的变化，必须先执行本命令，不允许直接进入 `/trellis:brainstorm`。
- 若本命令是**当前项目第一次进入 workflow 的入口**，且目标项目为新建仓库，则应先确认本地主分支和初始分支为 `main`；若当前仓库尚无本地提交历史且分支不是 `main`，先修正分支，再继续 workflow。
- 若目标项目已经存在本地提交历史或已有存量开发内容，则不强制切换成 `main`，但应把当前分支策略作为初始化边界记录清楚。
- 若已存在有效 `assessment.md`，且本轮只是继续同一项目的后续阶段，可复用该评估结果，不需要重复执行本命令。
- 判断 `assessment.md` 是否仍有效时，至少确认：`总体决策` 不是 `暂停/拒绝`、`是否允许进入 brainstorm = 是`、`法律/合规风险结论` 已明确，且当前前提未发生足以推翻评估结论的变化。
- 若评估结论为 `暂停`，必须先补信息或完成谈判动作，再重新运行本命令。
- 若评估结论为 `拒绝`，应终止该项目链路，不进入 `/trellis:brainstorm`。

---

## 流程

### Step 0: 仓库基线检查（仅当本命令是首次入口时）

- 新建目标项目：本地主分支和初始分支必须使用 `main`
- 已有本地提交历史或已有存量开发内容的项目：允许保留现有分支，不强制改名
- 当前 workflow 安装器会执行同口径校验；若后续会话要直接继续 `brainstorm`，也必须先确认当前 `assessment.md` 仍有效

### Step 1: 法律与合规风险初筛（必须先做）

```bash
# 平台无关脚本
python3 <WORKFLOW_DIR>/commands/shell/feasibility-check.py --step compliance
```

检查清单：法律法规/数据隐私/强监管行业/知识产权

**不合规 → 立即终止并说明理由**

> Step 1 完成后，必须立刻进入法律风险结构化分析；在该分析完成前，不得继续需求粗估、报价、交付控制判断或正式 task 初始化。

### Step 1.5: 法律风险结构化分析（阶段起始硬门禁）

```bash
# 从文件读取需求文本
python3 <WORKFLOW_DIR>/commands/shell/feasibility-check.py --step risk-analysis --task-dir <任务目录> --requirement-file <需求文件路径>

# 从 stdin 读取需求文本
echo "需求文本" | python3 <WORKFLOW_DIR>/commands/shell/feasibility-check.py --step risk-analysis --task-dir <任务目录>
```

执行流程：

1. **生成风险分析指引**：脚本读取需求文本，生成 `risk-analysis-guide.md` 文件
2. **调用 Skill**：`demand-risk-assessment` — 按框架执行风险分析
3. **执行风险分析**：按 skill 框架执行完整风险评估流程
   - 阶段0：结构化抽取（关键字段快照 + 信息充分性 X/8）
   - 阶段0.25：踩坑信号扫描
   - 阶段0.5：冲突检测
   - 阶段1：红线检查（先决条件）
   - 阶段2：结构化评分（仅当红线未命中时）
   - 阶段3-5：Pre-mortem → 风险登记表 → 决策/谈判条件
4. **写入评估结果**：将分析结果写入 `assessment.md`

输出文件：
- `$TASK_DIR/risk-analysis-guide.md` — 风险分析指引（含需求文本 + 执行步骤）
- `$TASK_DIR/assessment.md` — 评估报告（由 AI 填充）

> 在 Step 1.5 完成前，不得继续需求粗估、报价、交付控制轨道判断或正式 task 初始化。

> ⚠️ 硬门禁：Step 1.5 未完成前，Step 2 / Step 3 / Step 4 一律视为未开放，不允许提前执行。

### Step 2: 需求初聊补充（一次一个问题）

1. 核心目标 → 2. 目标用户 → 3. 核心功能(≤3) → 4. 技术约束 → 5. 时间窗口

### Step 2.5: MCP 能力路由

| 场景 | 调用能力 | 触发条件 | 说明 |
|------|---------|---------|------|
| 竞品分析、技术方案深度调研 | `exa_create_research` | 当需要进行竞品分析或技术调研时 | 回退：`grok-search`。无法联网时不输出行业最新情况结论，改为本地已知风险清单，标记 `[Evidence Gap]` |
| 风险评估复杂推理 | `sequential-thinking` | 当风险评估涉及 ≥3 个决策分支或推理步骤 >3 步时 | 复杂风险场景 |
| 参考 GitHub 开源项目 | `deepwiki` | 当需要参考外部开源项目时 | 回退：`exa_search` |

### Step 3: 风险评估与商务预判

**调用 Skill**：`demand-risk-assessment` — 按框架执行风险评估，输出决策建议。降级：手动五维度评估。

```bash
python3 <WORKFLOW_DIR>/commands/shell/feasibility-check.py --step estimate
```

执行要求：

- 先产出 `assessment.md` 骨架，再使用 `demand-risk-assessment` 填充结论与证据。
- 不允许只给口头结论，必须把 go / no-go / pause 判断写回 `assessment.md`。
- `assessment.md` 必须明确写出“是否允许进入 brainstorm”，作为阶段二的前置判断。
- 本阶段允许输出**商务预判**、预算区间策略和是否值得继续推进，但**不承担需求澄清后的正式项目级工期承诺**。
- 需求与客户讨论清楚后的正式项目级粗估，必须在 `brainstorm` 收口前写入 `task_dir/prd.md` 与 `docs/requirements/customer-facing-prd.md`，不能在这里跳过后移。
- 若属于外包、定制开发或新客户项目，必须同步明确交付控制轨道：
  - **首选轨：托管部署**，尾款前只提供开发者控制的试运行环境
  - **备选轨：试运行授权**，仅在双方明确接受授权方案时使用
- 不允许把“隐藏后门”“未披露的失效逻辑”“不可恢复的锁定机制”当作风险控制手段写入方案。

> **📋 双轨交付控制基线输出**
>
> 本步骤确定的交付控制轨道将作为贯穿后续阶段的决策基线：
> - `delivery_control_track` → `/trellis:design` 阶段选择必选 spec
> - `delivery_control_track` + `trial_authorization_terms.*` → `/trellis:plan` 阶段拆分双轨任务
> - `delivery_control_handover_trigger` → `/trellis:delivery` 阶段判断是否允许最终移交
>
> 详见工作流总纲 §1.4.1、§4、§7.2.1

### Step 4: 确认与初始化

```bash
TASK_DIR=$(python3 ./.trellis/scripts/task.py create "<项目名>" --slug <name>)
```

仅当 `assessment.md` 结论允许继续推进时，才创建/初始化正式任务目录；否则保留评估记录，等待补信息、谈判或终止。

创建任务后，应立即初始化当前叶子任务的阶段状态：

```bash
python3 .trellis/scripts/workflow/workflow-state.py init "$TASK_DIR" --stage feasibility
```

若在当前源仓库维护 workflow 内容时，可直接使用：

```bash
python3 docs/workflows/新项目开发工作流/commands/shell/workflow-state.py init "$TASK_DIR" --stage feasibility
```

---

## 输出

```
$TASK_DIR/
├── assessment.md   # 评估报告
├── prd.md          # 初始 PRD
└── task.json
```

### `assessment.md` 最低字段契约

`assessment.md` 至少应包含以下内容，供后续 `/trellis:brainstorm` 或人工决策直接复用：

```markdown
# 项目可行性评估

## 概览
- 总体决策：接 / 谈判后接 / 暂停 / 拒绝
- 是否可做：
- 是否值得做：
- 如何做更稳：
- 法律/合规风险结论：通过 / 不通过 / 待补充
- 是否允许进入 brainstorm：是 / 否
- `delivery_control_track`: `hosted_deployment` / `trial_authorization` / `undecided`
- `delivery_control_handover_trigger`: 例如 `final_payment_received`
- `delivery_control_retained_scope`: 尾款前仍由开发者保留的环境、账号、密钥、部署控制范围；若无则写 `none`
- `source_watermark_level`: `none` / `basic` / `hybrid` / `forensic`
- `source_watermark_channels`: 例如 `visible,zero-width,subtle-markers,zero-watermark`
- `zero_width_watermark_enabled`: `yes` / `no`
- `subtle_code_marker_enabled`: `yes` / `no`
- `ownership_proof_required`: `yes` / `no`
- 交付控制轨道：托管部署 / 试运行授权 / 未确定
- 当前结论的前提：
- 场景标签：
- 总体置信度：高/中/低
- 信息充分性：X/8
- 承诺门：G0/G1/G2/G3

## 关键字段快照
| 关键字段 | 状态(明确/暗示/缺失/冲突) | 证据锚点 | 关键假设/缺口备注 |
|----------|---------------------------|----------|------------------|
| 范围边界 | ... | ... | ... |
| 交付物清单 | ... | ... | ... |
| 验收口径 | ... | ... | ... |
| 付款结构 | ... | ... | ... |
| 工期/里程碑 | ... | ... | ... |
| 源码移交时点 | ... | ... | ... |
| 管理员权限/密钥移交时点 | ... | ... | ... |
| 托管部署或试运行授权方案 | ... | ... | ... |
| 授权到期行为/永久授权触发条件 | ... | ... | ... |
| 源码水印策略 | ... | ... | ... |
| 关键依赖 | ... | ... | ... |
| 数据合规要点 | ... | ... | ... |
| 决策/验收负责人 | ... | ... | ... |

## Trial Authorization Terms（仅当 `delivery_control_track = trial_authorization`）
- `trial_authorization_terms.validity`: ...
- `trial_authorization_terms.clock_source_or_usage_basis`: ...
- `trial_authorization_terms.expiration_behavior`: ...
- `trial_authorization_terms.renewal_policy`: ...
- `trial_authorization_terms.permanent_authorization_trigger`: ...

## 红线检查
✅ 通过 / ❌ 不通过 / ⚠️ 信息不足需补充
- [检查项]: 通过/不通过/不足 - 证据锚点或缺口

## 踩坑信号扫描
- 命中: [话术/信号] - 证据锚点 - 影响

## 冲突检测
- 命中项: ...（证据锚点）
- 影响: ...

## 评分总览（如适用）
总分(base): XX/100 | 区间(best~worst): AA~BB/100

| 维度(权重) | 维度得分(0-5) | 贡献分(/100) | 置信度 | 证据/缺口/冲突 |
|------------|---------------|--------------|--------|----------------|
| 合规风险(30) | x | yy.y | ... | ... |
| 可交付性(20) | x | yy.y | ... | ... |
| 工期可行性(20) | x | yy.y | ... | ... |
| 价格与收益匹配(20) | x | yy.y | ... | ... |
| 协作与沟通风险(10) | x | yy.y | ... | ... |

## Pre-mortem：最可能的失败链路
1. ...
2. ...
3. ...

## 风险登记表
| 风险 | 影响类型 | 概率(1-5) | 影响(1-5) | 优先级(P*I) | 缓解动作 | Kill Criteria |
|------|----------|-----------|-----------|--------------|----------|--------------|
| ... | ... | ... | ... | ... | ... | ... |

## 必须谈判条件
- [ ] 条件 1（映射：失败链路/风险项）
- [ ] 条件 2

若项目采用双轨交付控制，上述条件至少应覆盖：

- [ ] 选择哪条交付控制轨道：托管部署 / 试运行授权
- [ ] 尾款比例、触发条件、逾期处理
- [ ] 源码仓库、源码包、管理员账号、密钥、生产权限的移交时点
- [ ] 若采用试运行授权：有效期、续期方式、到期行为、永久授权交付条件
- [ ] 若采用托管部署：演示/试运行环境的访问范围、SLO、数据责任边界

若项目需要作者归属保护或希望降低被冒名顶替风险，上述条件还应至少覆盖：

- [ ] 是否要求源码水印与归属证明门禁（`ownership_proof_required`）
- [ ] 源码水印档位（`source_watermark_level`）
- [ ] 是否启用零宽字符水印（仅允许注释 / 文档字符串 / Markdown）
- [ ] 是否启用不起眼代码标识
- [ ] 是否要求交付时提供 `ownership-proof.md` 与 `source-watermark-verification.md`

## 最小补充信息集
1. ...（关联维度/为什么会改结论）

## 下一步建议
- 若允许进入 brainstorm：带着哪些边界与假设继续
- 若不允许：补信息 / 谈判 / 终止
```

### 双轨字段映射表

| 字段 | 填写位置 | 作用 | 下游消费点 |
|---|---|---|---|
| `delivery_control_track` | `## 概览` | 决定交付轨道 | `/trellis:design` 选择必选 spec；`/trellis:plan` 决定是否拆试运行授权任务 |
| `delivery_control_handover_trigger` | `## 概览` | 定义最终控制权移交触发条件 | `/trellis:plan` 设置前置依赖；`/trellis:delivery` 判断是否允许最终移交 |
| `delivery_control_retained_scope` | `## 概览` | 明确尾款前仍由开发者保留的控制范围 | `/trellis:plan` 拆 retained-control 任务；`/trellis:delivery` 校验未提前移交 |
| `trial_authorization_terms.*` | `## Trial Authorization Terms` | 冻结试运行授权条款 | `/trellis:design` 导入 `authorization-management`；`/trellis:delivery` 校验到期行为与永久授权触发条件 |
| 源码/密钥/管理员权限移交时点 | `## 关键字段快照` | 补足正式移交边界 | `/trellis:design` 判断是否导入 `secrets-and-config`；`/trellis:plan` 拆移交任务 |
| 尾款比例、付款结构、逾期处理 | `## 关键字段快照` + `## 必须谈判条件` | 冻结付款与移交关系 | `/trellis:plan` 标记触发依赖；`/trellis:delivery` 作为最终移交门禁依据 |
| `source_watermark_level` | `## 概览` | 冻结源码水印档位 | `/trellis:design` 生成 `source-watermark-plan.md`；`/trellis:plan` 拆水印任务 |
| `source_watermark_channels` | `## 概览` | 冻结采用的源码水印通道 | `/trellis:design` 约束零宽字符与隐蔽标识边界；`/trellis:delivery` 校验交付证明 |
| `zero_width_watermark_enabled` / `subtle_code_marker_enabled` | `## 概览` | 明确是否启用零宽字符水印与不起眼代码标识 | `/trellis:plan` 拆对应 task；`ownership-proof-validate.py` 校验一致性 |
| `ownership_proof_required` | `## 概览` | 冻结是否启用归属证明门禁 | `/trellis:delivery` 决定是否必须产出归属证明包 |

### 源码水印档位速查

| 档位 | 含义 | 最低要求 |
|---|---|---|
| `none` | 不启用源码水印与归属证明门禁 | 不要求 |
| `basic` | 最低档：至少要求可见源码水印 | `source_watermark_channels` 至少包含 `visible` |
| `hybrid` | 默认推荐档：可见水印 + 若干隐蔽辅助层 | `source_watermark_channels` 至少包含 `visible`，其他通道按需组合 |
| `forensic` | 取证强化档：尽量保留多层水印与证明 | `source_watermark_channels` 至少包含 `visible`，建议启用全部已确认通道 |

说明：

- 是否真正启用后续 design / plan / delivery 的归属证明门禁，仍以 `ownership_proof_required` 为准
- 只要启用了归属证明门禁，当前 workflow 默认要求保留 `visible` 通道
- `basic` / `hybrid` / `forensic` 主要表达策略强度与默认期望；真正决定后续实际校验范围的，仍是 `source_watermark_channels`

约束：

- `是否允许进入 brainstorm = 否` 时，不应直接进入 `/trellis:brainstorm`
- `法律/合规风险结论 = 待补充` 时，不应把当前 `assessment.md` 视为可直接复用的有效评估结果
- `总体决策 = 暂停` 时，下一步默认是“补信息后重跑 feasibility”
- `总体决策 = 拒绝` 时，下一步默认是“终止项目并保留 assessment 记录”
- 外部项目至少填完前三个 `delivery_control_*` 字段，不能只写中文描述不写机器字段
- 若 `delivery_control_track = trial_authorization`，`trial_authorization_terms.*` 不得留空
- 需要作者归属保护的项目，不得只写“会做水印”这种自然语言描述；必须显式填写 `source_watermark_*` 与 `ownership_proof_required`
- 若启用零宽字符水印，后续 design 阶段必须遵守 [源码水印与归属证据链执行卡](../源码水印与归属证据链执行卡.md) 中的“只允许注释 / 文档字符串 / Markdown”边界
- 若当前只能做假设，必须在“关键字段快照”或“最小补充信息集”里写明证据缺口

## 下一步推荐

**当前状态**: 可行性评估完成，`assessment.md` 已生成；在用户明确确认前，仍停留在 feasibility 阶段。

> 本节定义的是阶段完成后的推荐输出口径，用于帮助当前 CLI 或协作者说明下一步；它不是框架层自动跳转保证。

根据评估结果和你的意图：

| 你的意图 | Claude / OpenCode 推荐入口 | Codex 推荐入口 | 说明 |
|---------|---------------------------|----------------|------|
| 继续推进项目 | `/trellis:brainstorm` | 继续需求发现，或显式触发 `brainstorm` skill | **默认推荐**。仅在用户明确确认，且当前 `assessment.md` 仍有效时才允许切换；后续会话也可直接复用这份评估结果 |
| 信息不足，先补充再评估 | `/trellis:feasibility` | 补信息后重跑评估，或显式触发 `feasibility` skill | 默认用于 `暂停` 结论；补齐缺口、谈判后重跑 |
| 评估不通过，终止 | — | — | 记录原因，保留 `assessment.md` 作为拒绝依据 |
| 不确定下一步 | `/trellis:start` | 描述当前意图，或显式触发 `start` skill | 用 Phase Router / skill 路由做阶段检测 |
