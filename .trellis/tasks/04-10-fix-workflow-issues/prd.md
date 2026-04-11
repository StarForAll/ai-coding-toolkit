# 修正新项目开发工作流文档和脚本问题

## Goal
修复 docs/workflows/新项目开发工作流 中 6 个分析点指出的文档-实现不一致问题。

## 修复清单

### 1. [严重] feasibility-check.py:351 TEMPLATE 未定义
- **问题**: `step_risk_analysis` 中引用 `TEMPLATE` 但变量名是 `ASSESSMENT_TEMPLATE`，导致 NameError
- **修复**: 将 `TEMPLATE` 改为 `ASSESSMENT_TEMPLATE`

### 2. [严重] check-quality.py:56 始终 return 0
- **判断**: 不是 bug。脚本定位为信息展示工具，非门禁。输出供用户判断，退出码固定为 0 是设计意图。

### 3. [严重] archive → record-session 顺序冲突
- **问题**: 文档要求先 archive 再 record-session，但 metadata-autocommit-guard.py 在 record-session pre-check 时要求有 current task，而 archive 会清除 current task
- **修复**:
  - 修改 metadata-autocommit-guard.py: record-session 模式不再要求 current task
  - 修改所有文档中的收尾顺序为: 先 record-session，再 archive

### 4. [中等] design.md 声明 vs design-export.py 校验不一致
- **问题**: design.md 声明输出含 AID.md/ODD.md/pages/，但脚本只强校验 index/BRD/TAD/DDD/IDD
- **修复**: 修正 design.md 描述，明确区分必需/可选/不校验的文件

### 5. [中等] delivery-control-validate.py 未接入主流程
- **问题**: 命令映射.md 定义了双轨验证命令，但 delivery.md 和完整流程演练.md 没引用
- **修复**: 在 delivery.md Step 4 和完整流程演练.md 阶段 5 中加入验证命令引用

### 6. [中等] CLI 适配 README installer 管理范围漂移
- **问题**: README 把 hooks/agents/config/instructions 讲成 workflow 承载面，但 installer 只管理 commands/skills/scripts
- **修复**: 在三个 CLI README 的部署映射表中增加"安装器管理"列，明确区分自动管理 vs 手动维护

## Acceptance Criteria
- [ ] feasibility-check.py risk-analysis 步骤不再 NameError
- [ ] metadata-autocommit-guard.py record-session 模式在无 current task 时也能通过
- [ ] 所有文档收尾顺序一致：record-session → archive
- [ ] design.md 输出描述与 design-export.py 实际行为一致
- [ ] delivery.md 和完整流程演练.md 引用 delivery-control-validate.py
- [ ] 三个 CLI README 部署映射表标注安装器管理范围
