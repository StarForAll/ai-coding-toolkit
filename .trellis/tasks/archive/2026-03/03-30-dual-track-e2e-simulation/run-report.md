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

### 5. Delivery

- 输出目录：`delivery/`
- 文件：
  - `test-report.md`
  - `acceptance.md`
  - `deliverables.md`
  - `transfer-checklist.md`
  - `retrospective.md`

## 验证命令

- `python3 docs/workflows/新项目开发工作流/commands/shell/design-export.py --validate .trellis/tasks/03-30-dual-track-e2e-simulation/design`
- `python3 docs/workflows/新项目开发工作流/commands/shell/plan-validate.py .trellis/tasks/03-30-dual-track-e2e-simulation`
- `rg -n "delivery-control|authorization-management|transfer-checklist|secrets-and-config" /tmp/dual-track-e2e-project/.trellis/library-lock.yaml`
- `/ops/softwares/python/bin/python3 -m py_compile docs/workflows/新项目开发工作流/commands/shell/feasibility-check.py`

## 结论

- 新的 `delivery_control_track` / `trial_authorization_terms` 契约已能从 feasibility 阶段贯穿到 delivery 阶段
- `authorization-management` 可作为条件资产被实际导入，而不是无条件强绑
- `transfer-checklist` 已可表达“交付事件”而不只是假设一次性最终移交
