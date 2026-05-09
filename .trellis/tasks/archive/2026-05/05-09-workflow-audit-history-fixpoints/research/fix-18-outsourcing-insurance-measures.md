# Research: 修复点 #18 外包项目全款收取的保险措施

- **Query**: 审计修复点 #18，检查工作流是否为外包项目全款收取提供保险措施，特别关注上次审计标记的缺口：渐进里程碑付款、客户拒付尾款救济、验收争议升级机制
- **Scope**: internal
- **Date**: 2026-05-09

## Findings

### 安装后产物

| File Path | Description |
|---|---|
| `/tmp/trellis-0.5.9-2/.claude/commands/trellis/feasibility.md` | 可行性评估命令，含外包控制分支 |
| `/tmp/trellis-0.5.9-2/.trellis/scripts/workflow/feasibility-check.py` | 可行性验证脚本，含外包字段验证 |
| `/tmp/trellis-0.5.9-2/.trellis/scripts/workflow/delivery-control-validate.py` | 双轨交付控制验证脚本 |
| `/tmp/trellis-0.5.9-2/.trellis/workflow.md` | 工作流总纲，含 §1.4.1 交付控制原则 |

### 源码文件

| File Path | Description |
|---|---|
| `docs/workflows/新项目开发工作流/commands/feasibility.md` | 源码版可行性评估命令 |
| `docs/workflows/新项目开发工作流/工作流总纲.md` | 源码版工作流总纲 |

### 上次审计缺口逐项复查

#### 缺口 1: 渐进里程碑付款字段

**当前状态**: ❌ 未满足

搜索全部安装后产物和源码，未找到以下任一概念：
- `里程碑付款` / `milestone_payment` / `progress_payment` / `progressive_payment` / `分期付款`
- 渐进式付款进度表
- 里程碑与付款绑定的触发机制

**已有内容**:
- `kickoff_payment_ratio`（启动款比例，最低 30%）-- 这是开工前门禁，不是里程碑付款
- `delivery_control_handover_trigger`（最终移交触发条件，通常为 `final_payment_received`）-- 这是尾款到账后的移交条件
- feasibility-check.py 行 214: 必须谈判条件中有"尾款比例、触发条件、逾期处理" -- 但这只是谈判条件列表项，不是结构化里程碑付款字段
- 工作流总纲.md 行 841: 需求冻结后的变更判定标准中提及"工期或里程碑发生变化" -- 但这指的是里程碑时点变化，不是里程碑付款

**分析**: 当前工作流的付款结构是**首尾两段式**（启动款 + 尾款），不支持渐进式里程碑付款。assessment.md 模板（feasibility-check.py 行 105-225）只有 `kickoff_payment_ratio` 和 `delivery_control_handover_trigger` 两个付款相关字段，没有中间里程碑付款进度。

#### 缺口 2: 客户拒付尾款救济路径

**当前状态**: ⚠️ 部分满足

**已有内容**:
- feasibility.md 行 143-145: "首选轨：托管部署，尾款前只提供开发者控制的试运行环境" -- 通过控制源码和部署环境来防止尾款拒付风险
- feasibility.md 行 146: "备选轨：试运行授权，仅在双方明确接受授权方案时使用" -- 试运行版到期可限制功能
- feasibility.md 行 295-309: 必须谈判条件中覆盖"尾款比例、触发条件、逾期处理" -- 提及了逾期处理
- delivery-control-validate.py 行 119-128: 验证 `delivery_control_handover_trigger` 字段 -- 确保移交触发条件明确

**缺口**:
- `逾期处理` 在必须谈判条件中提及，但没有结构化的机器字段（如 `overdue_handling_policy`）
- 没有具体的救济路径步骤（如：催告期限 -> 限制功能 -> 暂停服务 -> 终止授权），只有"逾期处理"这个笼统概念
- 托管部署/试运行授权是预防措施，不是事后的救济路径

#### 缺口 3: 验收争议升级机制

**当前状态**: ❌ 未满足

搜索全部安装后产物和源码，未找到以下任一概念：
- `验收争议` / `acceptance_dispute` / `争议升级` / `dispute_escalation` / `验收仲裁`
- 验收不通过时的处理流程（如：整改周期 -> 复验 -> 第三方仲裁 -> 解约）
- 验收争议的判定标准

**已有内容**:
- 工作流总纲.md 行 530-531: "模糊点澄清记录" -- 这是需求阶段的歧义澄清，不是验收争议
- 工作流总纲.md §6.4-6.5: 验收测试和 Bug 修复流程 -- 这是技术层面的缺陷修复，不是客户与开发方之间的验收争议解决
- brainstorm.md: 需求变更管理流程 -- 这是需求变更，不是验收争议

**分析**: 当前工作流假设验收是一个客观过程（有验收标准、有缺陷修复流程），但没有覆盖客户主观拒绝验收或双方对验收标准理解分歧的场景。

### 保险措施总览

| 措施 | 是否存在 | 实现方式 | 强制执行 |
|---|---|---|---|
| 启动款门禁 (>=30%) | ✅ | `kickoff_payment_ratio` + `kickoff_payment_received` | feasibility-check.py + delivery-control-validate.py |
| 托管部署轨 | ✅ | `delivery_control_track = hosted_deployment` | delivery-control-validate.py |
| 试运行授权轨 | ✅ | `delivery_control_track = trial_authorization` + 5 个条款字段 | delivery-control-validate.py |
| 尾款前控制权保留 | ✅ | `delivery_control_retained_scope` | delivery-control-validate.py |
| 最终移交触发条件 | ✅ | `delivery_control_handover_trigger` | delivery-control-validate.py |
| 源码水印/归属证明 | ✅ | `source_watermark_*` + `ownership_proof_required` | ownership-proof-validate.py |
| 渐进里程碑付款 | ❌ | 不存在 | -- |
| 客户拒付尾款救济路径 | ⚠️ | 仅有预防措施（托管/试运行），无事后救济步骤 | -- |
| 验收争议升级机制 | ❌ | 不存在 | -- |

### delivery-control-validate.py 验证覆盖情况

- feasibility 阶段: 7 项检查（project_engagement_type, kickoff_payment_ratio, kickoff_payment_received, delivery_control_track, delivery_control_handover_trigger, delivery_control_retained_scope, trial_authorization_terms.*）
- plan 阶段: 5 项检查（交付控制章节, 任务拆分, task 图摘要, 开工款触发, 最终移交触发）
- delivery 阶段: 3 项检查 + 条件子检查（transfer-checklist, deliverables, acceptance）

## 审计判定

- **是否满足**: ⚠️ 部分满足（📈 较上次改善）
- **证据**: feasibility.md 行 138-145, 295-309; feasibility-check.py 行 19-24, 79-106, 214; delivery-control-validate.py 全文; 工作流总纲.md 行 271-347
- **缺口描述**:
  1. **渐进里程碑付款字段**: 缺失。当前只有首尾两段式付款（启动款 + 尾款），没有中间里程碑付款进度。assessment.md 模板中没有 `milestone_payments` / `payment_schedule` 等字段
  2. **客户拒付尾款救济路径**: 部分缺失。有预防措施（托管部署/试运行授权），但"逾期处理"只在必须谈判条件中作为列表项提及，没有结构化救济步骤和机器字段
  3. **验收争议升级机制**: 缺失。工作流有技术层验收（§6.4-6.5）和需求变更管理（§2.5），但无客户与开发方之间验收争议的升级路径
- **与上次对比变化**: 
  - 改善点：启动款门禁从 30% 强化到最低 30% 且默认建议 30% 或 40%；delivery-control-validate.py 脚本新增了完整的双轨交付控制验证；托管部署和试运行授权的条款字段更完整（trial_authorization_terms 有 5 个子字段）
  - 未改善：渐进里程碑付款、客户拒付救济路径、验收争议升级机制三个缺口仍然存在

## Caveats / Not Found

- `逾期处理` 出现在必须谈判条件中（feasibility-check.py 行 214），但只是作为谈判清单项，不是结构化字段，也没有下游校验
- 工作流总纲.md §7.2.1-7.2.2 描述了尾款前后的交付控制逻辑，但假设的是"尾款到账/未到账"的二元状态，没有覆盖"逾期未付"的中间状态
- 托管部署和试运行授权本身构成了一种"事实上的救济"（客户不付尾款则无法获得源码/永久授权），但这更接近预防而非事后救济
