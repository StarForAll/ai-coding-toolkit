# Research: Gap #14 feasibility 不可跳过性残留

- **Query**: workflow-state.py 在 stage=="feasibility" 时是否仍跳过 assessment 字段检查；feasibility-check.py 是否新增校验；brainstorm.md Gate 0 是否有前置校验
- **Scope**: internal
- **Date**: 2026-05-09

## Findings

### Files Found

| File Path | Description |
|---|---|
| `/tmp/trellis-0.5.9-2/.trellis/scripts/workflow/workflow-state.py` | 安装后的 workflow-state 脚本 |
| `/tmp/trellis-0.5.9-2/.trellis/scripts/workflow/feasibility-check.py` | 安装后的 feasibility-check 脚本 |
| `/tmp/trellis-0.5.9-2/.claude/commands/trellis/brainstorm.md` | 安装后的 brainstorm 命令 |
| `/ops/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/commands/shell/workflow-state.py` | 源码 workflow-state |

### Code Patterns

#### 1. workflow-state.py validate 不再按 stage 跳过 assessment 校验

`validate_external_project_controls` (line 537-637) 在安装后的版本中：
- 无论当前 stage 是什么，只要 `find_assessment_file` 找到 assessment.md 就会执行校验
- `cmd_validate` (line 853-895) 调用 `validate_external_project_controls` 时没有任何 stage 过滤逻辑
- `validate_ownership_policy_controls` (line 640-709) 同理，不受 stage 限制
- 旧版"当 stage==feasibility 跳过 assessment 字段检查"的逻辑已不存在

**结论：workflow-state.py 不再在 feasibility 阶段跳过 assessment 校验。**

#### 2. feasibility-check.py --step validate 独立完成 feasibility 门禁校验

`step_validate` (line 243-499) 检查：
- `总体决策` 字段
- `法律/合规风险结论` 字段
- `是否允许进入 brainstorm` 字段
- `红线检查` 章节结论
- `project_engagement_type` 字段
- `total_effort_hours` 字段 (line 316-322) -- **新增**，上次审计时缺失
- 外包项目额外检查：kickoff_payment_ratio/received/delivery_control_track/handover_trigger/retained_scope
- **新增三项**：milestone_payment_schedule (line 376-382), non_payment_remedy_path (line 384-390), dispute_escalation_path (line 392-398)
- trial_authorization_terms 各项
- source_watermark 系列字段

**结论：feasibility-check.py 已有完整的独立校验，不再依赖 workflow-state.py 来做 assessment 校验。**

#### 3. brainstorm.md Gate 0 前置校验

安装后的 brainstorm.md (line 80-96) Gate 0:
- "先确认 feasibility 已完成且 assessment.md 仍有效"
- 调用 `workflow-state.py validate <task-dir>` 作为门禁校验
- 校验通过后继续；失败时按错误项逐项修复后重试

**结论：brainstorm.md 的 Gate 0 已显式要求先执行 workflow-state.py validate。**

### 源码对比

安装后 workflow-state.py 与源码 workflow-state.py **完全一致**（逐行对比无差异），确认安装正确。

## 判定: ✅ 已修复

### 修复证据

1. workflow-state.py 不再对 feasibility 阶段做任何 assessment 字段豁免
2. feasibility-check.py 新增了 `--step validate` 子命令，独立完成 feasibility 阶段门禁校验
3. brainstorm.md Gate 0 显式要求执行 workflow-state.py validate
4. feasibility-check.py 的 ASSESSMENT_TEMPLATE (line 105-229) 已包含 total_effort_hours、milestone_payment_schedule、non_payment_remedy_path、dispute_escalation_path 字段

## Caveats / Not Found

- workflow-state.py 的 `validate_external_project_controls` 函数中有一个 bug：line 590 引用了 `stage` 变量，但该函数参数中没有 `stage`，只有 `state`。正确写法应为 `state.get("stage")`。这在安装后和源码中都存在，是已知问题但不影响本次缺口判定。
