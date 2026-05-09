# Research: 修复点 #15-#18 汇总审计报告

- **Query**: 修复点 #15-#18 二次审计汇总
- **Scope**: internal
- **Date**: 2026-05-09

## 汇总表

| 修复点 | 标题 | 是否满足 | 与上次对比 | 关键缺口 |
|---|---|---|---|---|
| #15 | 项目初始化时必须强制分析法律风险 | ✅ 已满足 | 保持 | 无 |
| #16 | 项目个人水印 | ✅ 已满足 | 保持 | 无 |
| #17 | 项目总工时估算 | ⚠️ 部分满足 | 📈 较上次改善 | 缺少标准化的 `total_effort` 机器字段；工时估算分散在自然语言描述中 |
| #18 | 外包项目全款收取的保险措施 | ⚠️ 部分满足 | 📈 较上次改善 | (1) 渐进里程碑付款字段缺失; (2) 客户拒付尾款救济路径只有预防无事后救济; (3) 验收争议升级机制缺失 |

## 详细说明

### #15 项目初始化时必须强制分析法律风险

法律风险分析在可行性评估阶段作为硬门禁强制执行：
- Step 1: 法律与合规风险初筛（必须先做，不合规则立即终止）
- Step 1.5: 法律风险结构化分析（硬门禁，未完成前 Step 2/3/4 一律未开放）
- 机器校验: `feasibility-check.py --step validate` 验证 `法律/合规风险结论` 字段
- 阶段入口: feasibility 是新项目的强制前置门禁

### #16 项目个人水印

水印机制从 feasibility 到 delivery 全阶段覆盖：
- 四档模型: none / basic / hybrid / forensic
- 四层水印: W0(可见) + W1(零宽) + W2(不起眼代码标识) + W3(零水印记录)
- 阶段动作: feasibility 冻结字段 -> design 生成计划 -> plan 拆任务 -> delivery 产出证明
- 默认启用: `ownership_proof_required` 常规默认值为 `yes`
- 机器校验: `ownership-proof-validate.py` 覆盖四阶段

### #17 项目总工时估算

工时估算体系存在但缺少标准化机器字段：
- feasibility: 商务预判/区间策略（允许粗估）
- brainstorm: 项目级粗估硬门禁（必须落盘，由 `workflow-state.py validate` 检查）
- plan: 任务级 `预估工时` 字段
- 缺口: 无 `total_effort` / `总工时` 标准化字段，工时估算分散在自然语言描述中

### #18 外包项目全款收取的保险措施

已实现的保险措施：
- 启动款门禁 >= 30%（`kickoff_payment_ratio` + `kickoff_payment_received`）
- 双轨交付控制（托管部署 / 试运行授权）
- 尾款前控制权保留（`delivery_control_retained_scope`）
- 最终移交触发条件（`delivery_control_handover_trigger`）
- 源码水印/归属证明
- 完整的 delivery-control-validate.py 脚本

仍缺失的三个子项：
1. 渐进里程碑付款：当前只有首尾两段式，无中间里程碑付款
2. 拒付尾款救济：有预防（托管/试运行），无事后救济步骤
3. 验收争议升级：无客户与开发方验收分歧的升级路径

## 相关文件索引

| 文件 | 说明 |
|---|---|
| `.trellis/tasks/05-09-workflow-audit-history-fixpoints/research/fix-15-legal-risk-mandatory.md` | #15 详细审计 |
| `.trellis/tasks/05-09-workflow-audit-history-fixpoints/research/fix-16-project-personal-watermark.md` | #16 详细审计 |
| `.trellis/tasks/05-09-workflow-audit-history-fixpoints/research/fix-17-total-effort-estimation.md` | #17 详细审计 |
| `.trellis/tasks/05-09-workflow-audit-history-fixpoints/research/fix-18-outsourcing-insurance-measures.md` | #18 详细审计 |
