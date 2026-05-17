# PRD: 修复新项目开发工作流 8 项状态机与跨平台一致性问题

## 背景

基于 `/tmp/trellis-0.5.16-2` 临时项目中嵌入的工作流进行深度分析，确认 8 项问题全部真实存在。修复范围仅限 `docs/workflows/新项目开发工作流/` 目录。

## 问题确认与修复方案

### Issue 1: 旧三阶段残留与新强门禁模型并存

**现状**:
- `install-workflow.py` 的 `cleanup_legacy_breadcrumb_blocks()` 会移除旧 planning/in_progress/completed breadcrumb 标签，但嵌入后的 workflow.md 注释区（第 99-158 行）仍描述 "4 [workflow-state:STATUS] blocks" 和旧三阶段合同
- trellis-continue SKILL.md:30 仍按 `status=planning/in_progress` 路由

**修复**:
- 在 `inject_workflow_phase_index_patch()` 执行后，追加清理旧合同注释的逻辑（将 "4 [workflow-state:STATUS] blocks" 替换为 13 阶段强门禁合同描述）
- 在 `install-workflow.py` 的 Codex patch 中，更新 trellis-continue SKILL.md 的 Step 3 路由逻辑，将 planning/in_progress 路由替换为 `workflow-state.py route` 路由

### Issue 2: Claude/OpenCode hook 不读取 workflow-state.json.stage

**现状**:
- `patch_inject_workflow_state_hook()` 对 Codex 应用 Issue 1 补丁（prefer workflow-state.json.stage），但对 Claude 和 OpenCode 故意跳过（`apply_issue1=False`）
- 注释声称 "Claude's state resolution path does not go through this hook"，但实际上 Claude hook 的 `get_active_task()` 正是状态解析入口
- OpenCode 的 `inject-workflow-state.js` 也只读 `task.json.status`

**修复**:
- `install-workflow.py`: 修改 `patch_inject_workflow_state_hook()` 将 Claude hook 的 `apply_issue1` 改为 `True`
- `install-workflow.py`: 新增对 OpenCode `inject-workflow-state.js` 的补丁逻辑，在 `getActiveTask()` 函数中添加读取 `workflow-state.json.stage` 的逻辑

### Issue 3: 非执行阶段切换不强制 awaiting_user_confirmation

**现状**:
- `workflow-state.py:929-941` 的 `cmd_set` 仅对 `EXECUTION_STAGES` 检查 awaiting_user_confirmation
- brainstorm→design 等普通阶段切换可以绕过用户确认

**修复**:
- `workflow-state.py cmd_set`: 扩展 awaiting 检查到所有阶段切换（`new_stage != current_stage` 且 `new_stage not in {"feasibility"}` 时，必须 `stage_status == "awaiting_user_confirmation"`）
- 保留 `--force` 绕过路径

### Issue 4: route 在 awaiting 状态时跳过 readiness blockers

**现状**:
- `workflow-state.py:1181-1189`: 当 `stage_status == "awaiting_user_confirmation"` 时直接返回 `awaiting_confirmation`，不检查 readiness blockers
- 这允许提前设 awaiting 掩盖缺失项

**修复**:
- `workflow-state.py cmd_route`: 即使 `stage_status == "awaiting_user_confirmation"`，仍收集 readiness blockers 并附加到返回结果中
- 当有 blockers 时，action 改为 `"awaiting_confirmation_with_blockers"` 或在 awaiting_confirmation 结果中包含 blockers 字段

### Issue 5: implementation→check 文档命令缺少 --execution-authorized false

**现状**:
- `workflow.md:750` 文档命令 `implementation → check` 没有重置 `execution_authorized=false`
- `workflow-state.py:341` 的 `validate_execution_boundary` 禁止非执行阶段保留 `execution_authorized=true`
- 按文档命令执行会失败

**修复**:
- `workflow-state.py cmd_set`: 当从执行阶段切换到非执行阶段时，自动重置 `execution_authorized=false`（无需用户手动指定）
- 更新 workflow.md 模板中的 implementation→check 和 implementation→test-first 命令示例，移除手动指定 `--execution-authorized false` 的需求（因为自动处理）
- 同时更新 `install-workflow.py` 中的 phase index patch 模板

### Issue 6: 空 allowed_next_stages 不是终止门禁

**现状**:
- `workflow-state.py:926`: `if isinstance(allowed, list) and allowed and new_stage not in allowed` — 空 list 时 `and allowed` 为 False，跳过门禁
- record-session 的 `allowed_next_stages=[]` 不阻止非法回退

**修复**:
- `workflow-state.py cmd_set`: 当 `allowed_next_stages` 为空列表时，禁止任何阶段切换（空列表 = 终态锁定）
- 修改条件为：`if isinstance(allowed, list) and new_stage not in allowed`（移除 `and allowed` 前提）

### Issue 7: L0 brainstorm→implementation 路径不被状态机支持

**现状**:
- brainstorm SKILL.md:381 允许 L0 直接进入 `/trellis:continue`
- `STAGE_TRANSITIONS` 中 brainstorm 只能去 `["design", "plan"]`
- L0 路径在脚本上不可达

**修复**:
- `workflow-state.py STAGE_TRANSITIONS`: 在 brainstorm 的 allowed transitions 中添加 `"implementation"` 和 `"test-first"`
- 更新 workflow.md 阶段切换参考表，添加 brainstorm→implementation 和 brainstorm→test-first 的 L0 路径命令

### Issue 8: finish-work / delivery / record-session 顺序冲突

**现状**:
- 阶段链：finish-work → delivery → record-session
- finish-work 要求先 archive + add_session（清除 session runtime），再进 delivery
- archive 后 active task 丢失，delivery/record-session 不可达
- delivery SKILL.md:318 推荐 finish-work 作为后置（循环）

**修复**:
- 重排顺序为：finish-work → delivery → record-session，其中 archive 操作移到 record-session 之后
- finish-work 只做 commit checklist + close-out evidence，不做 archive
- delivery 保持不变
- record-session 负责最终 archive + add_session
- 更新 workflow.md 模板中的阶段链说明和 finish-work breadcrumb 内容

## 修改文件清单

| 文件 | 修改内容 |
|------|---------|
| `commands/shell/workflow-state.py` | Issue 3,4,5,6,7: 状态机核心修复 |
| `commands/shell/test_workflow_state.py` | 添加回归测试覆盖 Issue 3,4,5,6,7 |
| `commands/install-workflow.py` | Issue 1,2: 补丁逻辑扩展；Issue 5,7,8: 模板更新 |
| `commands/workflow_assets.py` | Issue 5,7,8: 更新 phase index/breadcrumb/no-task patch 内容 |

## 验证方案

1. 运行现有测试：`/ops/softwares/python/bin/python3 -m pytest commands/shell/test_workflow_state.py -v`
2. 新增回归测试覆盖每个 Issue 的修复
3. 在 `/tmp/trellis-0.5.16-2` 重新嵌入验证（dry-run + 实际嵌入后检查）

## 约束

- 修改范围仅限 `docs/workflows/新项目开发工作流/` 目录
- 不能引入新的状态机不一致
- 现有测试必须全部通过
- `--force` 绕过路径必须保留
