# 双轨交付控制完整流程模拟报告

## 目标

验证 `trial_authorization` 轨道下，`feasibility -> design -> plan -> delivery` 的关键产物、条件导入和校验链路是否可执行。

## 执行摘要

### 1. Feasibility

- 输入需求：`requirement.md`
- 执行命令：
  - `python3 docs/workflows/新项目开发工作流/commands/shell/feasibility-check.py --step compliance`
  - `python3 docs/workflows/新项目开发工作流/commands/shell/feasibility-check.py --step risk-analysis --task-dir .trellis/tasks/03-30-dual-track-e2e-simulation --requirement-file .trellis/tasks/03-30-dual-track-e2e-simulation/requirement.md`
- 输出：
  - `assessment.md`
  - `risk-analysis-guide.md`

### 2. Design

- 使用 `design-export.py --scaffold` 生成设计骨架
- 补齐：
  - `design/index.md`
  - `design/BRD.md`
  - `design/TAD.md`
  - `design/DDD.md`
  - `design/IDD.md`
  - `design/AID.md`
  - `design/ODD.md`
  - `design/specs/inspection-flow.md`
  - `design/pages/inspection-dashboard.md`

### 3. Asset Import

- 临时目标项目：`/tmp/dual-track-e2e-project`
- 执行命令：
  - `python3 trellis-library/cli.py assemble --target /tmp/dual-track-e2e-project ... --auto`
- 验证：
  - `.trellis/library-lock.yaml` 已记录 `delivery-control`
  - `.trellis/library-lock.yaml` 已记录 `authorization-management`
  - `.trellis/library-lock.yaml` 已记录 `transfer-checklist`
  - `.trellis/library-lock.yaml` 已记录 `secrets-and-config`

### 4. Plan

- 输出：`task_plan.md`
- 内容包含：
  - 试运行版交付任务
  - 授权状态与到期行为验证
  - 永久授权切换
  - 源码移交
  - 控制权移交
  - 密钥配置移交
  - 冻结后正式变更先评估再并入的门禁说明

### 5. Delivery

- 输出目录：`delivery/`
- 文件：
  - `test-report.md`
  - `acceptance.md`
  - `deliverables.md`
  - `transfer-checklist.md`
  - `retrospective.md`

### 6. Change Request Example

- 输出：`change-request-example.md`
- 作用：
  - 演示设计阶段客户临时提改动时，如何用轻量变更单记录
  - 演示对客说明如何与“冻结后变更流程”保持一致

### 7. Clarification Example

- 输出：`clarification-example.md`
- 作用：
  - 演示客户提出“纯澄清”时，如何留在当前阶段处理
  - 演示纯澄清不触发正式变更流程时，最小记录应该怎么写

## 验证命令

- `python3 docs/workflows/新项目开发工作流/commands/shell/design-export.py --validate .trellis/tasks/03-30-dual-track-e2e-simulation/design`
- `python3 docs/workflows/新项目开发工作流/commands/shell/plan-validate.py .trellis/tasks/03-30-dual-track-e2e-simulation`
- `rg -n "delivery-control|authorization-management|transfer-checklist|secrets-and-config" /tmp/dual-track-e2e-project/.trellis/library-lock.yaml`
- `/ops/softwares/python/bin/python3 -m py_compile docs/workflows/新项目开发工作流/commands/shell/feasibility-check.py`

## 结论

- 新的 `delivery_control_track` / `trial_authorization_terms` 契约已能从 feasibility 阶段贯穿到 delivery 阶段
- `authorization-management` 可作为条件资产被实际导入，而不是无条件强绑
- `transfer-checklist` 已可表达“交付事件”而不只是假设一次性最终移交
- 冻结后的小型正式变更可以通过轻量变更单快速落地，而不破坏主链交付边界
- 纯澄清和正式变更现在都有对应轻量样例，便于在实际沟通中快速分流
