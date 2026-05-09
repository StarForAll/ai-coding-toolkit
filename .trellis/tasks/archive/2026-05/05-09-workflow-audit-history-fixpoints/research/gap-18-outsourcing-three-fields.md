# Research: Gap #18 外包项目全款保险三项缺漏

- **Query**: milestone_payment_schedule / non_payment_remedy_path / dispute_escalation_path 三项字段在安装后的 delivery-control-validate.py、delivery.md、feasibility-check.py、workflow-state.py 中是否存在
- **Scope**: internal
- **Date**: 2026-05-09

## Findings

### Files Found

| File Path | Description |
|---|---|
| `/tmp/trellis-0.5.9-2/.trellis/scripts/workflow/delivery-control-validate.py` | 安装后的交付控制验证脚本 |
| `/tmp/trellis-0.5.9-2/.claude/commands/trellis/delivery.md` | 安装后的 delivery 命令 |
| `/tmp/trellis-0.5.9-2/.trellis/scripts/workflow/feasibility-check.py` | 安装后的 feasibility-check 脚本 |
| `/tmp/trellis-0.5.9-2/.trellis/scripts/workflow/workflow-state.py` | 安装后的 workflow-state 脚本 |
| `/ops/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/commands/shell/delivery-control-validate.py` | 源码交付控制验证 |
| `/ops/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/commands/delivery.md` | 源码 delivery 命令 |

### 三项字段覆盖状态

#### 1. `milestone_payment_schedule` (渐进里程碑付款字段)

| 位置 | 存在 | 行号/证据 |
|---|---|---|
| feasibility-check.py ASSESSMENT_TEMPLATE | ✅ | line 121: `- \`milestone_payment_schedule\`: 例如 \`M1:40%,M2:30%,Final:30%\`` |
| feasibility-check.py step_validate | ✅ | line 376-382: 校验 milestone_payment_schedule 字段 |
| delivery-control-validate.py validate_assessment | ✅ | line 141-146: 校验 milestone_payment_schedule |
| delivery-control-validate.py validate_task_plan | ✅ | line 280-284: 检查 task_plan 中 milestone_payment_schedule |
| delivery-control-validate.py validate_delivery (transfer-checklist) | ✅ | line 350-354: 检查 transfer-checklist 中 milestone_payment_schedule |
| delivery.md | ✅ | line 149, 153, 164, 173-175: 多处提及 milestone_payment_schedule |
| workflow-state.py validate_external_project_controls | ❌ | 不校验此字段 |

#### 2. `non_payment_remedy_path` (客户拒付尾款救济路径)

| 位置 | 存在 | 行号/证据 |
|---|---|---|
| feasibility-check.py ASSESSMENT_TEMPLATE | ✅ | line 122: `- \`non_payment_remedy_path\`: 例如 \`written_notice -> retained_control_delivery_only -> suspend_final_handover\`` |
| feasibility-check.py step_validate | ✅ | line 384-390: 校验 non_payment_remedy_path 字段 |
| delivery-control-validate.py validate_assessment | ✅ | line 148-153: 校验 non_payment_remedy_path |
| delivery-control-validate.py validate_task_plan | ✅ | line 286-290: 检查 task_plan 中 non_payment_remedy_path |
| delivery-control-validate.py validate_delivery (transfer-checklist) | ✅ | line 356-360: 检查 transfer-checklist 中 non_payment_remedy_path |
| delivery.md | ✅ | line 149, 153, 165, 173-175: 多处提及 non_payment_remedy_path |
| workflow-state.py validate_external_project_controls | ❌ | 不校验此字段 |

#### 3. `dispute_escalation_path` (验收争议升级机制)

| 位置 | 存在 | 行号/证据 |
|---|---|---|
| feasibility-check.py ASSESSMENT_TEMPLATE | ✅ | line 123: `- \`dispute_escalation_path\`: 例如 \`technical_review -> project_negotiation -> third_party_arbitration\`` |
| feasibility-check.py step_validate | ✅ | line 392-398: 校验 dispute_escalation_path 字段 |
| delivery-control-validate.py validate_assessment | ✅ | line 155-160: 校验 dispute_escalation_path |
| delivery-control-validate.py validate_task_plan | ✅ | line 292-296: 检查 task_plan 中 dispute_escalation_path |
| delivery-control-validate.py validate_delivery (transfer-checklist) ✅ | line 362-366: 检查 transfer-checklist 中 dispute_escalation_path |
| delivery.md | ✅ | line 149, 153, 166, 173-175: 多处提及 dispute_escalation_path |
| workflow-state.py validate_external_project_controls | ❌ | 不校验此字段 |

### 源码对比

安装后的 delivery-control-validate.py 与源码 **完全一致**。
安装后的 delivery.md 与源码 **完全一致**。

### delivery.md 新增内容

安装后的 delivery.md 对比上次审计时：
- Step 6 (line 152-184): 完整的"交付事件 checklist"章节，包含交付事件判定速查表、每次交付事件核对项（milestone_payment_schedule / non_payment_remedy_path / dispute_escalation_path）、交付事件执行门禁表
- Step 5 transfer-checklist 最小内容契约 (line 149): 显式要求 milestone_payment_schedule / non_payment_remedy_path / dispute_escalation_path 是否与 assessment.md、task_plan.md 对齐

## 判定: ✅ 已修复

### 修复证据

1. feasibility-check.py 的 ASSESSMENT_TEMPLATE 和 step_validate 均已包含三项字段
2. delivery-control-validate.py 在 assessment / task_plan / delivery 三个阶段均校验三项字段
3. delivery.md 在 Step 5 / Step 6 中多处显式要求三项字段的核对和对齐
4. plan.md (源码) Step 4 task_plan.md 摘要结构中要求外部项目交付控制包含三项字段

### 残留缺口

- workflow-state.py 的 `validate_external_project_controls` 函数 **不校验** milestone_payment_schedule / non_payment_remedy_path / dispute_escalation_path。这意味着如果只依赖 workflow-state.py validate 来做外包项目门禁，三项字段可能漏检。不过实际流程中 feasibility-check.py 和 delivery-control-validate.py 覆盖了这些字段，且 brainstorm.md Gate 0 只要求 workflow-state.py validate 通过。对于 feasibility 阶段，需要额外调用 feasibility-check.py --step validate 才能完整覆盖。

## Caveats / Not Found

- 无新增发现
