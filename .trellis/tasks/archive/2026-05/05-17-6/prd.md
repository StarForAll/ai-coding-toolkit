# PRD: 修复工作流嵌入 6 项一致性问题

## 背景

当前工作流（docs/workflows/新项目开发工作流）在嵌入目标项目后存在 6 项一致性问题，导致强门禁模型在目标项目中无法完整运作。这些问题在工作流源资产层修复，确保安装器嵌入后目标项目行为正确。

## 问题清单与修复方案

### P1: record-session 契约断裂（CRITICAL）

**现象**: `ADDED_COMMANDS` 包含 `record-session`，但 `DISTRIBUTED_COMMANDS` 不包含它。安装器只遍历 `DISTRIBUTED_COMMANDS` 部署命令，导致目标项目中无 record-session.md 入口。安装记录声称 `added_commands` 包含 record-session 但实际未部署。

**根因**: record-session 被归入 PATCH_BASELINE_COMMANDS（期望来自 Trellis 基线），但 Trellis 0.5.16 基线不提供此命令。

**修复**:
1. 在 `workflow_assets.py` 的 `DISTRIBUTED_COMMANDS` 中添加 `"record-session"`
2. 同步更新 Codex 的 `CODEX_SHARED_SKILL_CLEANUP_NAMES` 确保 record-session skill 也能被正确部署和清理
3. 安装记录的 `commands` 字段自然包含 record-session（因为写入逻辑用 DISTRIBUTED_COMMANDS）

### P2: upgrade-compat --check 漏检 record-session 缺失（HIGH）

**现象**: 对临时项目运行 `--check` 返回 0 冲突，但 record-session 实际未部署。

**根因**: upgrade-compat 的冲突检测逻辑未验证 ADDED_COMMANDS 中声明的命令是否在目标项目文件系统中实际存在。

**修复**: 在 upgrade-compat.py 的检测逻辑中，对 `added_commands` 列表中的每个命令验证对应文件是否存在于目标项目。缺失时报告为冲突。

### P3: patch-workflow-phase.py 未执行且含 bug（HIGH）

**现象**: 安装器分发 patch-workflow-phase.py 到 `.trellis/scripts/workflow/` 但不执行它。该补丁引用 `task_dir` 变量（get_step() 函数作用域中不存在），即便手动执行也会被 except 静默吞掉。

**根因**: 
1. 安装器未调用补丁
2. 补丁代码假设 `task_dir` 在 `dir()` 中，但 get_step() 不接受此参数

**修复**:
1. 修复 patch-workflow-phase.py 中的 `task_dir` 引用：改为从 `Path(__file__)` 向上查找含 workflow-state.json 的任务目录
2. 在 install-workflow.py 中，辅助脚本部署后执行 patch-workflow-phase.py 对 `workflow_phase.py` 打补丁
3. 在 upgrade-compat.py 的 --merge 模式中同样执行此补丁

### P4: continue/trellis-continue 保留旧 status 路由（HIGH）

**现象**: 嵌入后 continue.md 和 trellis-continue SKILL.md 在 Phase Router 之前仍保留 `status=planning/in_progress` 旧路由。

**根因**: start-patch-phase-router.md 仅追加 Phase Router 块，未删除旧 Step 3（status routing）内容。

**修复**:
1. 修改 install-workflow.py 中的 Phase Router 注入逻辑：注入新 Phase Router 的同时，删除旧 Step 3 (Decide Where You Are) 的 status-based routing 内容
2. 具体做法：在 `inject_codex_phase_router_skill_patch` 和 Claude/OpenCode 的 Phase Router 注入中，识别并删除 `status=planning` / `status=in_progress` 路由块
3. 同时更新 start-patch-phase-router.md 和 start-skill-patch-phase-router.md 的内容，使其包含强门禁路由替代说明

### P5: finish-work.md Step 3/4 与补丁冲突（CRITICAL）

**现象**: 嵌入后的 finish-work.md 前半段 Step 3 要求执行 archive，Step 4 要求执行 add_session，但补丁又说强门禁模式下不执行。同一入口内强冲突。

**根因**: `build_finish_work_content()` 替换范围仅覆盖 "### 1. Code Quality" 到 "### 1.5. Test Coverage"，不覆盖 Step 3/4。

**修复**:
1. 修改 `build_finish_work_content()` 扩展替换范围，将 Step 3 (Archive task(s)) 和 Step 4 (Record session journal) 也纳入替换区域
2. 补丁文本中已包含替代说明（Step 3 → 确认 finish-work-checklist.md 已落盘），只需确保旧内容被移除
3. 替换范围从 "### 1. Code Quality" 延伸到 Step 4 末尾（即 `---` 分隔线前）

### P6: workflow-state.py cmd_set 门禁校验用旧 stage（HIGH）

**现象**: `validate_external_project_controls` 读取 `state.get("stage")`（旧值）判断是否进入执行阶段，而非用 `new_stage`。这导致从 brainstorm 直接到 implementation 时，启动款检查不会触发。

**根因**: `validate_stage_transition_gates` 传递 `state` 而不传递 `new_stage`，子函数只能从 state 中读取当前 stage。

**修复**:
1. 修改 `validate_stage_transition_gates` 签名，增加 `new_stage` 参数传递
2. 修改 `validate_external_project_controls` 签名，增加 `target_stage` 参数
3. 在启动款检查中使用 `target_stage` 而非 `state.get("stage")`
4. 在 `cmd_set` 中调用时传入 `new_stage`

### 附加修复: workflow.md 旧 Phase 1/2/3 残留

**现象**: 安装器替换了 "## Phase Index" 到 "### Phase 1: Plan" 之间的内容，但 Phase 1/2/3 的详细步骤内容仍保留在文件中。

**修复**: 修改 `inject_workflow_phase_index_patch` 扩展替换范围，从 "## Phase Index" 一直替换到 "## Customizing Trellis" 之前，将旧 Phase 1/2/3 内容一并移除。

## 约束

- 所有修改仅在 `docs/workflows/新项目开发工作流/` 目录内进行
- 不能引入新的问题，需确保安装器已有逻辑不受破坏
- 修复后安装器嵌入到新目标项目时应不再出现这些问题
- 对 Trellis 原生问题的兼容通过补丁机制处理

## 验证

修复完成后，重新对 `/tmp/trellis-0.5.16-2` 执行 `upgrade-compat.py --merge` 应能修复已有问题；全新嵌入应不再出现这些问题。
