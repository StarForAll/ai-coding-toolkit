# Audit Report - 新项目开发工作流阶段门禁与嵌入行为

## Audit Boundary

- Workflow Root: `docs/workflows/新项目开发工作流/`
- Target Project Fixture: `/tmp/trellis-0.5.17-2`
- Compatible Anchor Version: `0.5.17`
- Current Trellis Version: `0.5.17`
- Version Gate: `passed`
- Execution Mode: `task-based runtime validation`

## Candidate Issues

1. `--allowed-next` 示例可能锁死合法出口。
2. `project-audit` 到确认边界时，route 未提前暴露缺少 `project_audit_gate_status`。
3. `delivery` 的任务级 `check` 与项目级 `project-audit` 双证据绑定可能不完整。
4. `project-audit -> check/review-gate` 可能仍被建模成同一 `<task-dir>` 切换，缺少任务级载体选择。
5. `check.md` 中文“验证结果”标题可能绕过 `check_gate_status` 与 fail/pass 一致性检查。
6. `review-gate` 的 `recommended + full` 模式可能没有强制 reviewer 数量。

## Evidence Log

- 已确认版本门禁通过：`COMPATIBLE_TRELLIS_VERSION = 0.5.17`，`trellis -v = 0.5.17`
- 已定位主要实现与文档入口：
  - `commands/shell/workflow-state.py`
  - `commands/shell/validators_gates.py`
  - `commands/shell/test_workflow_state.py`
  - `commands/project-audit.md`
  - `commands/delivery.md`
  - `commands/review-gate.md`
  - `commands/workflow-patch-projectization.md`

## Preliminary Status

- 已完成版本门禁、源/装后副本对齐、候选问题复现。
- 按用户要求，在给出修正方案并得到同意前，不对工作流源文件做修改。

## Findings

### Confirmed Issues

1. `--allowed-next` 示例会锁死合法出口。
   - 目标项目 `.trellis/workflow.md` 中进入 `project-audit` 的示例仍把 `allowed-next` 写成 `check,review-gate`，缺少 canonical 合法出口 `delivery`。
   - `check -> review-gate` 的示例仍把 `review-gate` 的 `allowed-next` 写成 `delivery,implementation`，缺少 canonical 合法出口 `project-audit`。
   - 复现结果：
     - 按该示例进入 `project-audit` 后，再切 `delivery` 会被 `allowed-next` 拒绝。
     - 按该示例进入 `review-gate` 后，再切 `project-audit` 会被 `allowed-next` 拒绝。
   - 传播面：
     - `commands/workflow-patch-projectization.md`
     - 由其补丁生成的目标项目 `.trellis/workflow.md`

2. `project-audit` 到确认边界时，`route` 不会提前暴露缺少 `project_audit_gate_status`。
   - `workflow-state.py` 的 `_collect_exit_gate_blockers()` 对 `project-audit` 只调用 `validate_project_audit_gate(task_dir, blockers)`，没有开启 `require_exit_gate_status=True`。
   - 复现结果：`project_audit_gate_status` 缺失时，`route` 仍返回 `awaiting_confirmation`，`blockers=[]`。

3. `delivery` 的双证据绑定存在残缺分支。
   - `validate_project_audit_gate(... require_delivery_linkage=True)` 内部已经会按 `project-audit.md` 的显式 `task_level_check_task` 解析真实 owner。
   - 但 `validate_delivery_gate()` 入口仍先调用 `_resolve_task_level_check_task_dir(task_dir)` 做 self/parent 预校验。
   - 复现结果：当 `delivery` 运行在独立 formal `PROJECT-AUDIT` carrier 上，且 `task_level_check_task` 显式指向 sibling task 时，即使显式绑定正确，仍会先因 carrier 本身缺少 `check.md` 被拦下。
   - 结论：这是“部分已修、入口仍漏”的真实缺陷。

4. `project-audit -> task-level review-gate/check` 仍被建模成同一 `<task-dir>` 切换。
   - 当前 state machine 没有跨 task 切换语义。
   - 对独立 `PROJECT-AUDIT` carrier，若仍在 carrier 上执行 `project-audit -> review-gate`，门禁会直接要求当前 carrier 自己持有 `check.md`。
   - 复现结果：独立 carrier 从 `project-audit` 切 `review-gate` 时，被 `缺少 check.md；check 阶段产物未生成，不得进入 review-gate` 直接阻断。
   - 同类问题也影响“回到任务级 check”的叙述与操作模型，只是 `check` 场景的错误会更晚暴露。

5. `check.md` 中文“验证结果”会绕过 fail/pass 一致性检查。
   - `validate_check_gate()` 允许标题 `Verification Results|验证结果`。
   - 但当 `check_gate_status=pass` 时，后续只从英文 `Verification Results` 提取 section body。
   - 复现结果：`## 验证结果` 下出现 `fail`，仍可成功从 `check` 进入 `delivery`。

6. `review-gate` 的 `recommended + full` 没有强制 2 份 reviewer 报告。
   - 当前 `validators_gates.py` 只对 `required + full` 强制 `len(reviewer_reports) >= 2`。
   - 复现结果：`recommended + full` 仅 1 份 reviewer 报告，`workflow-state.py validate` 仍返回通过。

### Similar / Related Issues

- Issue 1 不是单点：所有“进入 `project-audit`”的示例都要补上 `delivery`，所有“进入 `review-gate`”且后续允许回 `project-audit` 的示例都要保留该出口。
- Issue 4 不是只影响 `review-gate`：同样的 carrier/task-level 混用，也会影响“回到任务级 `check`”的叙述与操作边界。

### False Alarm / Narrowed Claims

- “`project-audit` 到 `review-gate` / `delivery` 的正式阶段切换时完全不校验 `project_audit_gate_status`”这一说法不成立。
  - `workflow-state.py set --stage ...` 的正式切换路径里已经通过 `validate_stage_transition_gates()` + `validate_project_audit_gate(... require_exit_gate_status=True)` 做了拦截。
  - 真正漏掉的是 `route` 在“等待用户确认”边界上的提前暴露能力。
