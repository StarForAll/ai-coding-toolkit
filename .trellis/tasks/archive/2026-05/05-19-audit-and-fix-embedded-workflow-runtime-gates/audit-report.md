# Audit Report

## Audit Boundary

- Workflow Path: `docs/workflows/新项目开发工作流/`
- Runtime Evidence Project: `/tmp/trellis-0.5.17-2`
- Compatible Anchor Version: `0.5.17`
- Current Trellis Version: `0.5.17`
- Version Gate: `passed`
- Current CLI: `codex`
- Edit Scope: `docs/workflows/新项目开发工作流/` and this task directory only

## Candidate Issues

1. `workflow-state.py route` 在非执行阶段把全局门禁降级为 warning。
2. Codex patched skills 完整性检查漏检 `trellis-continue` / `trellis-finish-work` 语义漂移。
3. 工作流文档把 customization 的真实维护边界说错。
4. degraded active-task fallback 会把恢复辅助与自动选中当前任务混在一起。
5. 旧 phase/step 模型残留会误导入口和维护者。
6. 任务状态视图动态调用 `cmd_route`，带来观测与性能问题。

## Findings

### Confirmed And Repaired

#### [P1] `route` 在非执行阶段把强门禁降成 warning

- Conclusion: 真实存在。
- Runtime evidence:
  - `/tmp/trellis-0.5.17-2/.trellis/scripts/workflow/workflow-state.py` 在非执行阶段只把 `validate_external_project_controls` / `validate_ownership_policy_controls` 塞进 `warnings` 后继续返回 `reenter`。
  - 同一目标项目中的 `cmd_set` 仍把这些门禁作为硬阻断处理，因此 route 与 set 语义不一致。
- Source-layer repair:
  - `docs/workflows/新项目开发工作流/commands/shell/workflow-state.py` 现在在非执行阶段统一收集当前阶段门禁并直接返回 `blocked`。
  - 同时把 `validate_project_doc_boundary` 一并纳入非执行态重入校验，补上同类缺口（例如 `plan` 阶段缺少 `context7-review.md` 时不再只是“看起来还能继续”）。
- Validation action:
  - 新增/更新 `test_cmd_route_blocks_design_reentry_when_ownership_policy_is_invalid`
  - 新增/更新 `test_cmd_route_blocks_plan_reentry_when_project_doc_boundary_is_invalid`

#### [P1] Codex patched skill 完整性自检只严查 `trellis-start`

- Conclusion: 真实存在。
- Runtime evidence:
  - `/tmp/trellis-0.5.17-2/.trellis/workflow-installed.json` 声明了 `trellis-continue`、`trellis-finish-work`、`trellis-start` 三个 patched Codex skills。
  - `/tmp/trellis-0.5.17-2/.trellis/scripts/workflow/workflow-state.py` 的 `_detect_missing_patched_codex_skills()` 仅对 `trellis-start` 检查 Phase Router 补丁语义，其余两个只查文件存在。
- Source-layer repair:
  - `docs/workflows/新项目开发工作流/commands/shell/workflow-state.py` 现在为三类 patched skills 定义 `must_contain` / `must_not_contain` 语义片段，缺失或残留旧语义都会触发 `embed_invalid`。
- Validation action:
  - 新增 `test_cmd_route_embed_invalid_when_patched_codex_continue_skill_drifts`
  - 新增 `test_cmd_route_embed_invalid_when_patched_codex_finish_work_skill_drifts`

#### [P1] degraded active-task fallback 被 route 直接当成当前任务

- Conclusion: 真实存在。
- Runtime evidence:
  - `/tmp/trellis-0.5.17-2/.trellis/scripts/workflow/workflow-state.py` 在无 session active task 时，会先读取 degraded fallback 并直接把它当成 `task_dir` 继续 route。
  - `/tmp/trellis-0.5.17-2/.trellis/scripts/task.py` 又会在 degraded 模式下写入 runtime-keyed / shared degraded 文件，因此“恢复线索”和“自动选中当前任务”被混在一起。
- Source-layer repair:
  - `docs/workflows/新项目开发工作流/commands/shell/workflow-state.py` 现在只把 degraded 文件当作 `recovery_needed` 提示来源，不再静默自动续跑。
  - keyed degraded 文件的优先级仍保留，但只用于提示哪个候选更可信。
  - `validate_session_active_task()` 继续保留 degraded fallback 支持，用于显式校验当前 task 时的恢复辅助。
- Validation action:
  - 更新 4 个 degraded route 回归测试，确认现在统一要求 `task.py start <task-dir>` 明确确认。

#### [P2] task 列表视图动态执行 `cmd_route`，并在异常时静默降级

- Conclusion: 真实存在。
- Runtime evidence:
  - `/tmp/trellis-0.5.17-2/.trellis/scripts/common/tasks.py` 里的 `_route_status_summary()` 会对每个 task 动态 import + 执行 `workflow-state.py cmd_route`，异常时直接返回 `(None, None)`。
  - 这会把 route 失败藏进列表展示层，同时让任务列表性能与 router 工作量线性耦合。
- Source-layer repair:
  - `docs/workflows/新项目开发工作流/commands/install-workflow.py` 的 `patch_task_status_views()` 已改为只读 `workflow-state.json` 和 `stage_status/current_block` 摘要，不再在列表热路径执行 route。
- Validation action:
  - 更新 installer 回归测试，断言生成的 `common/tasks.py` 不再包含 `_route_status_summary()` / `_module_cache` / `cmd_route(`。

#### [P2] workflow 文档把维护边界写成 “scripts are parsers only”

- Conclusion: 真实存在。
- Runtime evidence:
  - `/tmp/trellis-0.5.17-2/.trellis/workflow.md` 的 Customizing Trellis 段仍保留这句描述。
  - 但当前工作流实际把运行时门禁、恢复、完整性校验、carrier patch 都放在脚本层，显然不是 parser-only。
- Source-layer repair:
  - `docs/workflows/新项目开发工作流/commands/workflow-patch-projectization.md` 已改为明确提示：改 stage semantics / routing / degraded recovery / gate behavior 时必须同步改 runtime script 与 patch 模板。

#### [P2] Codex `trellis-start` / `trellis-continue` 仍带旧 phase/step 描述

- Conclusion: 真实存在。
- Runtime evidence:
  - `/tmp/trellis-0.5.17-2/.agents/skills/trellis-start/SKILL.md` 与 `trellis-continue/SKILL.md` 的 description 仍沿用旧的 “Phase Index / phase/step” 话术。
- Source-layer repair:
  - `docs/workflows/新项目开发工作流/commands/install-workflow.py` 现在在注入 Phase Router patch 时会同步重写 `trellis-start` / `trellis-continue` 的 description 与开场说明，避免 patch body 已更新但元信息仍误导。
  - 上述 drift 也被纳入 Codex patched skill 语义自检。

### Confirmed But No Additional Source Patch Needed

#### 旧 `workflow_phase.py` step 提取逻辑仍在 Trellis 基线里残留

- Conclusion: 属于维护债务，但在当前工作流源中已经被强门禁补丁硬阻断，不是这轮还在漏修的运行时缺口。
- Evidence:
  - `/tmp/trellis-0.5.17-2/.trellis/scripts/common/workflow_phase.py` 仍保留旧 step 提取逻辑。
  - 但同文件也已通过 `workflow-phase-strong-gate` 补丁明确拒绝旧 step 查询，并提示改用 `workflow-state.py route`。
- Decision:
  - 本轮只修仍在误导安装结果的 `trellis-start` / `trellis-continue` 元信息，不重复改已被补丁封死的 Trellis 基线 helper。

## Validation Log

- `PASS` `/ops/softwares/python/bin/python3 -m unittest docs.workflows.新项目开发工作流.commands.shell.test_workflow_state`
  - Ran 118 tests in 16.824s
- `PASS` `PYTHONPATH=docs/workflows/新项目开发工作流/commands /ops/softwares/python/bin/python3 -m unittest docs.workflows.新项目开发工作流.commands.test_workflow_installers`
  - Ran 116 tests in 224.664s

## Spec Sync Decision

- Reviewed per `trellis-update-spec`.
- Decision: no additional `.trellis/spec/` edit in this task.
- Reason:
  - The learned contract is specific to the workflow product under `docs/workflows/新项目开发工作流/`, and has already been preserved in source docs, installer patch logic, runtime script guards, and regression tests.
  - The user explicitly restricted source edits to the workflow directory and current task directory.

## Files Changed

- `docs/workflows/新项目开发工作流/commands/shell/workflow-state.py`
- `docs/workflows/新项目开发工作流/commands/install-workflow.py`
- `docs/workflows/新项目开发工作流/commands/workflow-patch-projectization.md`
- `docs/workflows/新项目开发工作流/commands/shell/test_workflow_state.py`
- `docs/workflows/新项目开发工作流/commands/test_workflow_installers.py`
