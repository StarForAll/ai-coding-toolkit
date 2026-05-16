# PRD: 修复新项目开发工作流嵌入后7个一致性问题

## 背景

当前 `docs/workflows/新项目开发工作流/` 通过 `install-workflow.py` 嵌入目标项目后，存在 7 个一致性问题，导致强门禁阶段状态机无法正常运作。这些问题在 `/tmp/trellis-0.5.16-2` 中已确认存在。

**约束**: 修复范围仅限 `docs/workflows/新项目开发工作流/`，其他目录不能修改。

## 问题清单与修复方案

### Issue 1: 入口路由冲突，绕过 feasibility

**现象**: `workflow.md` 的 `[workflow-state:no_task]` breadcrumb 直接路由到 `task.py create` → `trellis-brainstorm`，跳过了 feasibility 门禁。AGENTS.md 明确声明"首次立项必经 feasibility"，但 per-turn hook 每轮都会注入绕过 feasibility 的引导文本。

**根因**: Trellis 基线 `workflow.md` 的 no_task breadcrumb 是旧三阶段模型的内容，installer 只替换 `## Development Process` 区块，不修改 breadcrumb。

**修复方案**: 在 `install-workflow.py` 中新增 `inject_workflow_no_task_patch()` 函数，将 `[workflow-state:no_task]` 区块替换为强门禁版本：
- B 路径改为先检查 feasibility：`workflow-state.py route` → first_entry 则走 `/trellis:feasibility`
- 保留 A（直接回答）和 C（inline 跳出）不变
- 增加 profile 判断：outsourcing profile 需要强门禁入口；personal profile 保留原逻辑
- 在 `workflow-patch-projectization.md` 末尾增加 no_task 替换模板（作为 patch 内容源）

**修改文件**:
- `commands/install-workflow.py`: 新增 `inject_workflow_no_task_patch()` 函数
- `commands/workflow-patch-projectization.md`: 增加 no_task breadcrumb 强门禁替换模板

### Issue 2: Codex per-turn hook 不使用强门禁状态机

**现象**: `.codex/hooks/inject-workflow-state.py` 只读 `task.json.status`（planning/in_progress），不读 `workflow-state.json`。AI 在 per-turn breadcrumb 中看到的是旧三阶段引导，而非当前强门禁阶段。

**根因**: hook 是 Trellis 基线管理的，installer 不修改它。hook 按 `task.json.status` 查找 `[workflow-state:STATUS]` 标签，而强门禁阶段名（feasibility/brainstorm/design 等）不存在于 `task.json.status` 中。

**修复方案**: 在 `install-workflow.py` 中新增 `inject_hook_workflow_state_patch()` 函数，修改 hook 的 breadcrumb 查找逻辑：
- 在 `get_active_task` 返回结果后，增加 `workflow-state.json` 读取逻辑
- 若 `workflow-state.json` 存在，用 `state.stage` 替代 `task.json.status` 作为 breadcrumb key
- 若不存在，保持原逻辑（向后兼容）
- 同时在 `workflow.md` 中增加 `[workflow-state:feasibility]` 等强门禁阶段 breadcrumb 标签

**修改文件**:
- `commands/install-workflow.py`: 新增 hook 补丁注入函数
- `commands/workflow-patch-projectization.md`: 增加强门禁阶段 breadcrumb 标签模板

### Issue 3: workflow.md 仍是旧三阶段主模型

**现象**: `.trellis/workflow.md` 的 Phase Index 仍是 `Phase 1: Plan → Phase 2: Execute → Phase 3: Finish`，和已安装的 outsourcing profile 强门禁模型不一致。AGENTS.md 同时有旧三阶段和新强门禁两个事实来源。

**修复方案**: 在 `install-workflow.py` 中新增 `inject_workflow_phase_index_patch()` 函数，将 Phase Index 区块替换为强门禁版本：
- 替换 `## Phase Index` ... `### Phase 1: Plan` 之间的内容
- 新 Phase Index 列出完整强门禁链：feasibility → brainstorm → design → plan → implementation → test-first → check → review-gate → finish-work → delivery
- profile 判断：outsourcing 用强门禁版；personal 保留旧版

**修改文件**:
- `commands/install-workflow.py`: 新增 Phase Index 补丁注入函数
- `commands/workflow-patch-projectization.md`: 增加 Phase Index 替换模板

### Issue 4: workflow-state.json 初始化依赖人工步骤

**现象**: `task.py create` 不创建 `workflow-state.json`，需要每个 skill 手动调用 `workflow-state.py init`。一旦漏掉，route 返回 `repair_needed`，workflow 卡住。

**修复方案**: 修改 `commands/shell/workflow-state.py`：
1. `cmd_route` 在发现 `workflow-state.json` 缺失时，自动调用 `build_default_state()` 并写入，stage 默认为 `feasibility`（首次入口场景），然后正常路由，而非返回 `repair_needed`
2. 在 `cmd_init` 中自动填充 `allowed_next_stages`（基于当前 stage 推算下一步允许的阶段）
3. 增加 `STAGE_TRANSITIONS` 常量，定义每个阶段允许的下一阶段列表

**修改文件**:
- `commands/shell/workflow-state.py`: 修改 `cmd_route`、`cmd_init`、`build_default_state`

### Issue 5: 阶段切换门禁不完整

**现象**: `allowed_next_stages` 只做格式校验（是否为合法阶段名），不在 `cmd_set` 中真正约束阶段切换。`cmd_set` 允许任意阶段变更。

**修复方案**: 修改 `commands/shell/workflow-state.py`：
1. 增加 `STAGE_TRANSITIONS` 常量（与 Issue 4 共享）
2. 在 `cmd_set` 中增加阶段切换校验：若新 stage 不在当前 `allowed_next_stages` 中（且列表非空），拒绝切换并提示
3. 增加 `--force` 参数跳过此校验（用于 repair 场景）

**修改文件**:
- `commands/shell/workflow-state.py`: 修改 `cmd_set`

### Issue 6: degraded active-task 行为制造恢复问题

**现象**: `task.py start` 在 degraded 模式下静默成功（return 0），但不持久化 active-task pointer，导致后续 route 返回 `recovery_needed`。workflow.md 说"retry"，但实际不报错。

**修复方案**: 这个问题的根因在 `.trellis/scripts/task.py`（Trellis 基线），不在 workflow 源文件范围内。但可以在 `workflow-state.py` 中做缓解：
1. 在 `cmd_route` 的 `resolve_degraded_task_dir()` 分支中，增加对 `task.json.status == "in_progress"` 的已存在任务的自动发现逻辑
2. 若发现 in_progress 任务但没有 active-task pointer，自动写入 `degraded-active-task.json` 作为恢复路径

**修改文件**:
- `commands/shell/workflow-state.py`: 修改 `cmd_route` 中 degraded 场景处理

### Issue 7: 残留文档引用缺失

**现象**:
1. AGENTS.md 引用 `工作流全局流转说明（通俗版）.md` 但该文件未嵌入目标项目
2. workflow.md 引用 `.trellis/spec/cli/backend/workflow-state-contract.md` 但该文件不存在
3. workflow.md 引用 `.trellis/scripts/inject-workflow-state.py` 但实际路径是 `.codex/hooks/` 或 `.claude/hooks/`

**修复方案**:
1. 在 `install-workflow.py` 的 `_NL_ROUTING_SECTION` 中，将 `工作流全局流转说明（通俗版）.md` 引用改为 `.trellis/workflow-docs/` 下的对应文件或 AGENTS.md 自身路由表
2. 在 `workflow-patch-projectization.md` 中修正 `workflow-state-contract.md` 引用：删除该引用或替换为实际存在的文档路径
3. 在 `workflow-patch-projectization.md` 中修正 `inject-workflow-state.py` 路径引用

**修改文件**:
- `commands/install-workflow.py`: 修改 `_NL_ROUTING_SECTION`
- `commands/workflow-patch-projectization.md`: 修正残留引用

## 修改文件汇总

| 文件 | 修改类型 | 涉及 Issue |
|------|---------|-----------|
| `commands/shell/workflow-state.py` | 修改代码 | #4, #5, #6 |
| `commands/install-workflow.py` | 修改代码 | #1, #2, #3, #7 |
| `commands/workflow-patch-projectization.md` | 修改内容 | #1, #2, #3, #7 |

## 风险控制

- 所有修改仅在 `docs/workflows/新项目开发工作流/` 目录内
- installer 补丁必须幂等（重复运行不重复注入）
- `workflow-state.py` 修改需保持向后兼容（缺 workflow-state.json 时仍能工作）
- 修改后需在 `/tmp/trellis-0.5.16-2` 上验证修复效果
