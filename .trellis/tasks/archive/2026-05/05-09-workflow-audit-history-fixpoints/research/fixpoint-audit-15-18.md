# Research: 工作流修复点审计 (15-18)

- **Query**: 深度分析修复点 15/16/17/18，判断当前工作流是否真正满足要求
- **Scope**: internal
- **Date**: 2026-05-09

## Findings

### 修复点 15: 项目初始化时必须强制分析法律风险

**判定**: ✅ 已满足

#### 证据链

| 证据来源 | 文件路径 | 行号/关键字 | 说明 |
|---|---|---|---|
| 工作流总纲 | `docs/workflows/新项目开发工作流/工作流总纲.md` | §1.1 合法性审查 | "法律合规性检查：确认项目在当地法律法规框架下是否合规"，"如果不符合法律法规，终止项目，不进行任何后续工作" |
| 工作流总纲 | 同上 | §1.3.1 门禁 | "可行性评估应至少产出 assessment.md" 包含"法律/合规风险结论：通过 / 不通过 / 待补充" |
| feasibility 命令 | `docs/workflows/新项目开发工作流/commands/feasibility.md` | Step 1 | "法律与合规风险初筛（必须先做）"，运行 `feasibility-check.py --step compliance`，检查清单：法律法规/数据隐私/强监管行业/知识产权，"不合规 → 立即终止并说明理由" |
| feasibility 命令 | 同上 | Step 1.5 | "法律风险结构化分析（阶段起始硬门禁）"，运行 `feasibility-check.py --step risk-analysis`，调用 `demand-risk-assessment` Skill，包含阶段0结构化抽取→踩坑信号扫描→冲突检测→红线检查→结构化评分→Pre-mortem→风险登记表→决策/谈判条件 |
| feasibility 命令 | 同上 | 硬门禁 | "Step 1.5 未完成前，Step 2 / Step 3 / Step 4 一律视为未开放，不允许提前执行" |
| brainstorm 命令 | `docs/workflows/新项目开发工作流/commands/brainstorm.md` | Gate 0 | "当前客户主体、需求范围、法律/合规前提未发生足以推翻评估结论的变化"，不满足则"先回 /trellis:feasibility 重新评估" |
| workflow_assets.py | `docs/workflows/新项目开发工作流/commands/workflow_assets.py` | HELPER_SCRIPTS | 包含 `feasibility-check.py`，安装时分发到目标项目 |
| 临时项目验证 | `/tmp/trellis-0.5.9-2/.trellis/scripts/workflow/feasibility-check.py` | 文件存在 | 脚本已安装 |
| 临时项目验证 | `/tmp/trellis-0.5.9-2/.claude/commands/trellis/feasibility.md` | Step 1 + Step 1.5 | 安装后的命令包含完整法律风险初筛与结构化分析 |
| 临时项目 workflow.md | `/tmp/trellis-0.5.9-2/.trellis/workflow.md` | 无直接法律关键词 | 基线 workflow.md 未嵌入法律风险相关内容（这是正确的：渐进性披露，法律风险分析在 feasibility 命令中展开） |

#### 机制完备性

1. **强制优先级**: Step 1 是 feasibility 流程的第一个实质步骤（Step 0/0.5 是仓库和目录准备），法律风险在所有商务讨论之前
2. **硬门禁**: Step 1.5 是"阶段起始硬门禁"，后续步骤全部锁定直到法律分析完成
3. **脚本化检查**: `feasibility-check.py --step compliance` 和 `--step risk-analysis` 提供自动化支持
4. **Skill 集成**: 调用 `demand-risk-assessment` Skill 完成结构化风险评估
5. **产物契约**: assessment.md 包含"法律/合规风险结论"字段和"红线检查"章节
6. **安装后完整性**: 临时项目已安装所有必需脚本和命令

### 修复点 16: 项目个人水印,防止项目被冒用或者个人水印

**判定**: ✅ 已满足

#### 证据链

| 证据来源 | 文件路径 | 行号/关键字 | 说明 |
|---|---|---|---|
| 源码水印执行卡 | `docs/workflows/新项目开发工作流/源码水印与归属证据链执行卡.md` | 全文 | 完整的水印分层模型：W0 可见源码水印 / W1 零宽字符水印 / W2 不起眼代码标识 / W3 零水印记录，含核心原则、阶段动作、产物契约、校验命令 |
| workflow_assets.py | `docs/workflows/新项目开发工作流/commands/workflow_assets.py` | EXECUTION_CARDS | `["需求变更管理执行卡.md", "源码水印与归属证据链执行卡.md"]` |
| workflow_assets.py | 同上 | HELPER_SCRIPTS | 包含 `ownership-proof-validate.py` |
| feasibility 命令 | `docs/workflows/新项目开发工作流/commands/feasibility.md` | Step 3 | "当前 workflow 默认启用作者归属保护；除非项目明确写 ownership_proof_required = no，否则 source_watermark_* 与 ownership_proof_required 都必须在本阶段显式冻结" |
| feasibility 命令 | 同上 | assessment.md 契约 | 包含 source_watermark_level / source_watermark_channels / zero_width_watermark_enabled / subtle_code_marker_enabled / ownership_proof_required 字段 |
| feasibility 命令 | 同上 | 离开前自检 | `ownership-proof-validate.py --phase feasibility --task-dir <task-dir>` |
| 工作流总纲 | `docs/workflows/新项目开发工作流/工作流总纲.md` | §1.4.1 | "当前 workflow 的常规默认值里，作者归属保护继续按启用处理" |
| 工作流总纲 | 同上 | §3.7 | "若 ownership_proof_required = yes，任务 5 还必须补齐 $TASK_DIR/design/source-watermark-plan.md" |
| brainstorm 命令 | `docs/workflows/新项目开发工作流/commands/brainstorm.md` | Gate 0 | "若 assessment.md 中 ownership_proof_required = yes，则后续需求路由与复杂度判断必须默认感知源码水印与归属证明链路" |
| 临时项目验证 | `/tmp/trellis-0.5.9-2/.trellis/workflow-docs/源码水印与归属证据链执行卡.md` | 文件存在 | 执行卡已安装 |
| 临时项目验证 | `/tmp/trellis-0.5.9-2/.trellis/scripts/workflow/ownership-proof-validate.py` | 文件存在 | 校验脚本已安装 |
| 临时项目验证 | `/tmp/trellis-0.5.9-2/.claude/commands/trellis/feasibility.md` | 水印字段 + 自检步骤 | 安装后命令包含完整水印字段映射表和校验步骤 |

#### 机制完备性

1. **分层模型**: 四层水印（可见/零宽/不起眼/零水印记录）提供不同强度的归属保护
2. **默认启用**: ownership_proof_required 常规默认值为 yes，除非项目明确写 no
3. **全阶段闭环**: feasibility 冻结字段 → design 设计水印方案 → plan 拆水印任务 → delivery 校验交付证明
4. **脚本化校验**: ownership-proof-validate.py 支持 feasibility/design/plan/delivery 四个阶段的校验
5. **独立执行卡**: 源码水印与归属证据链执行卡作为独立文档，安装时分发到 .trellis/workflow-docs/
6. **零宽字符边界**: 明确"只允许注释/文档字符串/Markdown"，禁止在标识符、路径、配置键等位置使用

### 修复点 17: 项目总工时估算

**判定**: ✅ 已满足

#### 证据链

| 证据来源 | 文件路径 | 行号/关键字 | 说明 |
|---|---|---|---|
| 工作流总纲 | `docs/workflows/新项目开发工作流/工作流总纲.md` | §1.3 项目评估与报价 | "工作量评估：功能开发工时 + 评审工时 + 测试工时 + 文档工时"，"时间成本分析：按里程碑拆分，给出最早/最晚交付窗口"，"报价输出：给出基础版范围、变更单价规则、交付SLO草案" |
| 工作流总纲 | 同上 | §1.3 | "本阶段的时间/报价输出默认是商务预判与区间策略，不替代需求澄清后的正式项目级粗估；正式粗估必须在阶段二 brainstorm 收口前落盘" |
| 工作流总纲 | 同上 | §2.1.1 第8点 | "在离开 brainstorm 之前，还必须先产出不可跳过的项目级粗估"，"若暂时无法给出单点值，也必须给出区间、置信度与适用前提；不得以'后续再估'为由跳过" |
| brainstorm 命令 | `docs/workflows/新项目开发工作流/commands/brainstorm.md` | Step 8 | "在进入 design、plan 或任何执行阶段前，必须先产出不可跳过的项目级粗估"，"由 workflow-state.py validate 强制检查项目级粗估门禁" |
| brainstorm 命令 | 同上 | Step 6 横切检查 | "当前项目级粗估相对 feasibility 是否已经刷新；若没有变化，也必须写清'为什么不变'" |
| feasibility 命令 | `docs/workflows/新项目开发工作流/commands/feasibility.md` | Step 3 | "本阶段允许输出商务预判、预算区间策略和是否值得继续推进，但不承担需求澄清后的正式项目级工期承诺" |
| 工作流总纲 | 同上 | task 规格 | "预估工时：X小时或X人天" |
| assessment.md 契约 | feasibility.md | 关键字段快照 | "工期/里程碑" 行 |
| brainstorm 命令 | 同上 | prd.md 区块 | `## 项目级粗估` 是必须补齐的区块 |
| 临时项目验证 | `/tmp/trellis-0.5.9-2/.claude/commands/trellis/brainstorm.md` | Step 8 | 安装后命令包含完整的项目级粗估硬门禁 |

#### 机制完备性

1. **三级估算体系**:
   - feasibility 阶段：商务预判（区间策略，不承担正式工期承诺）
   - brainstorm 阶段：项目级粗估（硬门禁，不可跳过，由 workflow-state.py 强制校验）
   - plan 阶段：单任务级"预估工时"（每个 Trellis task 都有独立估算）
2. **硬门禁强制**: workflow-state.py validate 在 design/plan 入口强制检查项目级粗估是否已落盘
3. **区间容差**: 若无法给单点值，必须给区间+置信度+适用前提，"后面再说""先不估"不算通过
4. **刷新要求**: brainstorm 阶段要求检查粗估是否相对 feasibility 已刷新
5. **成本维度完整**: 功能开发工时 + 评审工时 + 测试工时 + 文档工时 + AI 相关成本

### 修复点 18: 外包项目全款收取的保险措施

**判定**: ⚠️ 部分满足

#### 证据链

| 证据来源 | 文件路径 | 行号/关键字 | 说明 |
|---|---|---|---|
| 工作流总纲 | `docs/workflows/新项目开发工作流/工作流总纲.md` | §1.4.1 | 开工前置门禁：kickoff_payment_ratio 至少 30%；kickoff_payment_received = yes 前不得进入 implementation/test-first |
| 工作流总纲 | 同上 | §1.4.1 | 首选轨：托管部署 — "尾款前只提供由开发者控制的演示/试运行环境"，"尾款前不移交源码仓库、生产环境密钥、管理员账号、最终部署权限" |
| 工作流总纲 | 同上 | §1.4.1 | 备选轨：试运行授权 — "到期行为必须可预期，优先限制为'演示模式'或'只读模式'，不得破坏已有数据"，"尾款到账后，交付永久授权、源码及最终控制权" |
| 工作流总纲 | 同上 | §1.4.1 禁止项 | "不得植入未披露的后门、隐藏开关、远程锁定或暗门控制逻辑"，"不得使用会破坏数据、阻断导出、导致客户无法恢复业务的失效机制" |
| 工作流总纲 | 同上 | §7.2.1 | 外部项目双轨交付门禁：尾款未到账时的交付范围限定 |
| 工作流总纲 | 同上 | §7.2.2 | 尾款到账后的最终移交清单 |
| 工作流总纲 | 同上 | §7.2 | `delivery-control-validate.py --phase delivery --task-dir <task-dir>` 和 `ownership-proof-validate.py --phase delivery` 双校验 |
| feasibility 命令 | `docs/workflows/新项目开发工作流/commands/feasibility.md` | Step 3 | 外包项目必须同步执行启动款门禁、开工状态、交付控制轨道判断 |
| feasibility 命令 | 同上 | assessment.md 契约 | kickoff_payment_ratio / kickoff_payment_received / delivery_control_track / delivery_control_handover_trigger / delivery_control_retained_scope / trial_authorization_terms.* |
| feasibility 命令 | 同上 | 约束 | "外包项目在 kickoff_payment_received != yes 时，不得进入 implementation / test-first"；"workflow-state.py validate 在后续阶段强制校验" |
| workflow_assets.py | `docs/workflows/新项目开发工作流/commands/workflow_assets.py` | OUTSOURCING_ONLY_SCRIPTS | `["delivery-control-validate.py"]` |
| 临时项目验证 | `/tmp/trellis-0.5.9-2/.trellis/scripts/workflow/delivery-control-validate.py` | 文件存在 | 交付控制校验脚本已安装 |
| 临时项目验证 | `/tmp/trellis-0.5.9-2/.claude/commands/trellis/feasibility.md` | 外包控制字段 | 安装后命令包含完整的外包项目控制字段映射和约束 |

#### 已满足部分

1. **启动款门禁**: 至少 30% 预付款，未到账前不得开工
2. **托管部署轨**: 尾款前开发者保留源码、密钥、部署权限的控制，只提供演示环境
3. **试运行授权轨**: 明确授权期限、到期行为（非破坏性）、永久授权触发条件
4. **最终移交门禁**: delivery_control_handover_trigger 绑定付款事件
5. **retained_scope 清单**: 明确尾款前开发者保留的控制范围
6. **脚本化校验**: delivery-control-validate.py 在 delivery 阶段检查一致性
7. **workflow-state.py 强制校验**: 后续阶段强制检查外包控制字段
8. **禁止后门/破坏性机制**: 合规边界明确
9. **水印归属保护**: ownership-proof 机制提供额外的归属证据

#### 缺口描述

1. **缺少渐进式付款里程碑**: 当前 payment 结构只明确 kickoff_payment_ratio（启动款）+ delivery_control_handover_trigger（通常为 final_payment_received），缺少中间里程碑付款的显式字段和门禁。assessment.md 中的"付款结构"和"工期/里程碑"是自由文本字段，可以记录里程碑付款，但没有机器可校验的字段如 `milestone_payments` 或 `progressive_payment_schedule`。
2. **缺少客户拒付尾款后的救济路径**: 当前机制侧重"防"（不交付直到收款），未覆盖"治"——如果客户在试运行后拒绝支付尾款，workflow 没有定义显式的退出/救济步骤。试运行授权的到期行为被限定为非破坏性（演示模式/只读模式），但这本身不足以催促付款。
3. **缺少争议仲裁触发机制**: 如果客户对交付质量有争议从而拒绝支付尾款，当前 workflow 没有定义争议仲裁流程。虽然验收标准在 PRD 中冻结，但"验收争议 → 付款争议"的升级路径未被显式建模。

#### 建议

1. 在 assessment.md 契约中增加 `milestone_payment_schedule` 结构化字段（可选），支持里程碑付款进度而非仅启动款+尾款的二元结构
2. 在交付控制机制中补充"尾款逾期处理预案"章节，至少包含：逾期通知、试运行授权到期后的非破坏性限制升级、开发者可单方面采取的合法保全动作边界
3. 考虑增加"验收争议升级路径"：从技术验证 → 项目经理仲裁 → 第三方仲裁的分级机制

## Caveats / Not Found

- 临时项目 `/tmp/trellis-0.5.9-2/.trellis/workflow.md` 中无直接法律风险/水印/工时/外包关键词，这是预期行为：该文件是 Trellis 基线 workflow.md，不包含当前 workflow 的阶段命令内容
- workflow_assets.py 中 `VALID_PROFILES = ("personal", "outsourcing")`，`DEFAULT_PROFILE = "outsourcing"`；personal profile 安装时会用 `_strip_conditional_blocks(content, "outsourcing")` 移除外包相关内容块，这意味着 personal profile 下外包控制字段在命令文档中不可见，但 HELPER_SCRIPTS 中的 delivery-control-validate.py 仍会被安装（它在 OUTSOURCING_ONLY_SCRIPTS 中，但当前 build_managed_asset_specs 仍将其包含在 HELPER_SCRIPTS 分发中）
