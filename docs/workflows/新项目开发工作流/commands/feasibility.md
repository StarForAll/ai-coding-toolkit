---
name: feasibility
description: 新项目？先评估可行性 — 合规审查、风险评估、报价输出。触发词：帮我评估、能做吗、新项目想法、报价
---

# /trellis:feasibility — 项目可行性评估

> **Workflow Position**: §1 → 前: 无 → 后: `/trellis:brainstorm`
> **Cross-CLI**: ✅ Claude Code（项目命令：`/trellis:feasibility`） · ✅ Cursor（命令名: feasibility） · ✅ OpenCode（TUI: `/trellis:feasibility`；CLI: `trellis/feasibility`；见 `opencode/README.md`） · ⚠️ Codex（同项目会安装 `feasibility` skill；通过自然语言或显式 skill 触发，不提供项目级 `/trellis:feasibility` 命令；见 `codex/README.md`） · ⚠️ Gemini（兼容层；见 `gemini/README.md`）
>
> **Gate Rule**: 对于新项目 / 新客户需求，`/trellis:feasibility` 是进入 `/trellis:brainstorm` 前的默认前置门禁；只有 `assessment.md` 明确允许时，才继续进入需求发现。

---

## When to Use (自然触发)

用户说以下任何话时自动启动：
- "我有个新项目想法"
- "帮我评估一下这个需求能不能做"
- "有个客户找我做个项目"
- "这个项目的报价怎么算"
- "帮我看看有没有风险"

> 已有任务在进行中？跳过，直接 `/trellis:brainstorm` 或 `/trellis:start`。

### 前置条件与出口约束

- 本命令面向**新项目立项、外包接单、客户需求初聊**等“先判断值不值得接”的场景。
- 若已有有效 `assessment.md` 且本轮仅补充需求细节，可跳过本命令直接进入 `/trellis:brainstorm`。
- 若评估结论为 `暂停`，必须先补信息或完成谈判动作，再重新运行本命令。
- 若评估结论为 `拒绝`，应终止该项目链路，不进入 `/trellis:brainstorm`。

---

## 流程

### Step 1: 合规性审查

```bash
# 平台无关脚本
python3 docs/workflows/新项目开发工作流/commands/shell/feasibility-check.py --step compliance
```

检查清单：法律法规/数据隐私/强监管行业/知识产权

**不合规 → 立即终止并说明理由**

### Step 2: 需求粗估（一次一个问题）

1. 核心目标 → 2. 目标用户 → 3. 核心功能(≤3) → 4. 技术约束 → 5. 时间窗口

### Step 2.5: 风险分析（demand-risk-assessment skill 集成）

```bash
# 从文件读取需求文本
python3 docs/workflows/新项目开发工作流/commands/shell/feasibility-check.py --step risk-analysis --task-dir <任务目录> --requirement-file <需求文件路径>

# 从 stdin 读取需求文本
echo "需求文本" | python3 docs/workflows/新项目开发工作流/commands/shell/feasibility-check.py --step risk-analysis --task-dir <任务目录>
```

执行流程：

1. **生成风险分析指引**：脚本读取需求文本，生成 `risk-analysis-guide.md` 文件
2. **加载 skill**：AI 加载 `demand-risk-assessment` skill
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

### Step 3: 风险评估与报价

**Skill**: `demand-risk-assessment` — 按其框架判断接/谈判后接/暂停/拒绝。

```bash
python3 docs/workflows/新项目开发工作流/commands/shell/feasibility-check.py --step estimate
```

执行要求：

- 先产出 `assessment.md` 骨架，再使用 `demand-risk-assessment` 填充结论与证据。
- 不允许只给口头结论，必须把 go / no-go / pause 判断写回 `assessment.md`。
- `assessment.md` 必须明确写出“是否允许进入 brainstorm”，作为阶段二的前置判断。
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
- 是否允许进入 brainstorm：是 / 否
- `delivery_control_track`: `hosted_deployment` / `trial_authorization` / `undecided`
- `delivery_control_handover_trigger`: 例如 `final_payment_received`
- `delivery_control_retained_scope`: 尾款前仍由开发者保留的环境、账号、密钥、部署控制范围；若无则写 `none`
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

约束：

- `是否允许进入 brainstorm = 否` 时，不应直接进入 `/trellis:brainstorm`
- `总体决策 = 暂停` 时，下一步默认是“补信息后重跑 feasibility”
- `总体决策 = 拒绝` 时，下一步默认是“终止项目并保留 assessment 记录”
- 外部项目至少填完前三个 `delivery_control_*` 字段，不能只写中文描述不写机器字段
- 若 `delivery_control_track = trial_authorization`，`trial_authorization_terms.*` 不得留空
- 若当前只能做假设，必须在“关键字段快照”或“最小补充信息集”里写明证据缺口

## 下一步推荐

**当前状态**: 可行性评估完成，`assessment.md` 已生成。

根据评估结果和你的意图：

| 你的意图 | 推荐命令 | 说明 |
|---------|---------|------|
| 继续推进项目 | `/trellis:brainstorm` | **默认推荐**。评估通过，进入详细需求发现 |
| 信息不足，先补充再评估 | `/trellis:feasibility` | 默认用于 `暂停` 结论；补齐缺口、谈判后重跑 |
| 评估不通过，终止 | — | 记录原因，保留 `assessment.md` 作为拒绝依据 |
| 需求已经很明确，跳过 brainstorm | `/trellis:design` | 如果 PRD 内容已足够详细 |
| 需求简单，直接写代码 | `/trellis:start` | 跳过设计+拆解，适合小改动 |
| 不确定下一步 | `/trellis:start` | 用 Phase Router 自动检测 |
