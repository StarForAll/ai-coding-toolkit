# PRD: 修复新项目开发工作流 — 旧语义残留、缺失规范引用、语义漂移、恢复提示精度

## Problem Statement

新项目开发工作流（`docs/workflows/新项目开发工作流/`）经 `install-workflow.py` 嵌入目标项目后，存在四类系统性缺陷，会导致维护者被误导、知识闭环断裂、操作边界模糊、恢复提示不精确。核心状态机（route/set/validate 主链）是自洽的，但围绕它的文档层和提示层存在残留和漂移。

## Root Cause Analysis

1. **旧三态语义残留**：`change-task-lifecycle.md` 仍声称 `[workflow-state:planning]` 是"live breadcrumb"，与强门禁模型（workflow-state.json.stage 为唯一真相源）直接冲突。该文件未被 `patch_trellis_meta_references()` 补丁覆盖。
2. **缺失规范引用**：`change-task-lifecycle.md:76` 引用的 `workflow-state-contract.md` 从未存在；`spec-system.md`/`task-system.md` 中的 JSONL 示例使用 `cli/` 包路径，对单仓库项目具有误导性。
3. **create/start 语义漂移**：workflow.md 的 no_task 块说 `task.py start` "只刷新 active-task 指针"，但实际代码在无 `workflow-state.json` 时仍执行 `planning → in_progress` 翻转。文档描述对强门禁安装基本准确，但对 pre-feasibility 场景和调试场景具有误导性。
4. **恢复路径精度不足**：`repair_needed` 被用于 7 种不同条件，涵盖"状态真正损坏"和"操作上下文不对"两类截然不同的问题；parent-with-children 场景的消息完全不具备操作性（不说有哪些 children、不说怎么切换）。

## Scope

### 修复范围
仅限 `docs/workflows/新项目开发工作流/` 目录内的源资产文件。其他目录不修改。

### 修复策略
- **文档类修复**：在 `trellis-meta-strong-gate/` 目录新增/更新补丁文件，由 `patch_trellis_meta_references()` 在安装时传播到目标项目
- **代码类修复**：在 `commands/shell/` 新增补丁脚本或更新现有脚本，由 `install-workflow.py` 在安装时应用
- **协议文档修复**：更新 `阶段状态机与强门禁协议.md` 等源文档

### 不修改
- Trellis 原生脚本（不在工作流目录内的 `.trellis/scripts/`）
- 当前项目自身使用的工作流文件（`.trellis/workflow.md` 等）
- `install-workflow.py` 的主安装流程逻辑（仅新增补丁调用）

## Detailed Requirements

### R1: 清除 change-task-lifecycle.md 中的旧三态语义 [HIGH]

**现状**：`change-task-lifecycle.md` 行 71-74 声称 `[workflow-state:planning]` 是 live breadcrumb，行 76 引用不存在的 `workflow-state-contract.md`。

**修复**：
1. 在 `trellis-meta-strong-gate/customize-local/` 新增 `change-task-lifecycle.md` 的强门禁版本，替换旧三态叙述：
   - 行 71: `status=planning` → `task.json 记录 status=planning 仅为簿记字段，不驱动路由；强门禁模式下由 workflow-state.json.stage 决定当前阶段`
   - 行 72: 移除 `[workflow-state:planning]` 引用，说明 "active pointer 指向新任务，下一轮 route 将以 workflow-state.json.stage 为准"
   - 行 74: 移除 `[workflow-state:planning]` 是 "live breadcrumb" 的叙述，改为 "brainstorm 和 JSONL curation 阶段由 workflow-state.json.stage=brainstorm 驱动"
   - 行 76: 替换 `workflow-state-contract.md` 引用为实际存在的文件（`workflow-state.py` 的 `cmd_set`/`cmd_route` 函数，以及 `.trellis/workflow.md` 中的阶段切换协议）

### R2: 修复 task-system.md 中的旧 status 描述和 JSONL 示例路径 [HIGH]

**现状**：`task-system.md` 行 36 将 `planning` 列为"主要 status"；行 66 的 JSONL 示例使用 `cli/backend/` 路径。

**修复**：
1. 在 `trellis-meta-strong-gate/local-architecture/` 新增 `task-system.md` 的强门禁版本：
   - 行 36: 添加注释说明 `task.json.status` 在强门禁模式下为簿记字段，阶段路由以 `workflow-state.json.stage` 为准
   - 行 66: JSONL 示例改为通用单仓库格式 `backend/index.md`（无 `cli/` 前缀），或使用 `<package>/` 占位符并注释说明应根据项目包结构调整

### R3: 修复 spec-system.md 中的 JSONL 示例路径 [MEDIUM]

**现状**：`spec-system.md` 行 70-71 的 JSONL 示例使用 `cli/backend/` 和 `cli/unit-test/` 路径。

**修复**：
1. 在 `trellis-meta-strong-gate/local-architecture/` 新增 `spec-system.md` 的强门禁版本：
   - 行 70-71: JSONL 示例改为 `backend/index.md` + `backend/test-conventions.md`，或使用通用占位符

### R4: 改进 workflow-state.py route 恢复提示精度 [MEDIUM]

**现状**：5 处提示精度不足。

**修复**（直接修改 `commands/shell/workflow-state.py`）：

1. **行 1676-1680**（recovery_needed）：枚举现有任务列表
   - 当 tasks 存在但 session 无 active task 时，遍历 `.trellis/tasks/` 下的任务目录，收集有 `task.json` 的任务名和 stage，附加到 reason 消息中
   - 示例：`"当前 session 未解析到 active task。已有任务: 05-18-foo(brainstorm), 05-18-bar(plan)。请执行 task.py start <task-dir> 切换到目标任务"`

2. **行 1716**（parent-with-children）：区分上下文切换和状态损坏
   - 将 action 从 `repair_needed` 改为 `context_needed`（新增 action）
   - reason 改为：`"当前 task 处于 leaf-required stage={stage} 但含有 children，需切换到子任务执行。子任务: {children_list}。请执行 task.py start <child-task-dir>"`
   - 在 `_route_result` 中支持 `context_needed` action

3. **行 1692**（缺少 workflow-state.json）：提示修复方法
   - reason 改为：`"缺少 workflow-state.json（可能因任务创建于工作流安装之前）。请执行 workflow-state.py init <task-dir> --stage feasibility 初始化"`

4. **行 1609-1610**（stale active task）：区分归档和路径失效
   - 检查 stale path 是否指向 archive 目录，给出不同提示：
     - 已归档：`"活动任务已归档: {path}。请 task.py start 切换到其他活跃任务"`
     - 路径不存在：`"活动任务路径无效: {path}。请 task.py start <task-dir> 重新指定"`

5. **行 1747**（readiness blockers 非执行/非 plan 阶段）：使用 `blocked` 而非 `repair_needed`
   - 将 `repair_needed` 改为 `blocked`，因为这些是"阶段产物未齐"，不是"状态损坏"

### R5: 补充 workflow.md no_task 块对 start 条件性翻转的说明 [MEDIUM]

**现状**：workflow.md 行 408 说 `task.py start` "只刷新 active-task 指针"，省略了条件性翻转。

**修复**：在 `workflow-patch-projectization.md`（或 install-workflow.py 中相应的注入内容）的 no_task 块中，添加说明：
- `task.py start` 在强门禁安装下（当 `workflow-state.json` 已存在时）跳过 `planning → in_progress` 翻转
- 在 `workflow-state.json` 尚未创建时（如 feasibility 之前），`start` 仍会执行翻转
- 阶段推进始终由 `workflow-state.py set` 控制，`task.py start` 不推进阶段

### R6: 更新阶段状态机协议文档 [LOW]

**现状**：`阶段状态机与强门禁协议.md` 行 43-46 的"恢复当前任务/明确当前任务"分支未区分"上下文未切换"和"状态损坏"。

**修复**：
- 在协议文档中明确区分 `recovery_needed`（需明确任务上下文）和 `repair_needed`（状态文件损坏/不一致）和新增的 `context_needed`（需切换到子任务）
- 给出每种 action 的典型触发场景和推荐操作

## Acceptance Criteria

1. `trellis-meta-strong-gate/customize-local/change-task-lifecycle.md` 存在且不包含 `[workflow-state:planning]` 引用，不引用 `workflow-state-contract.md`
2. `trellis-meta-strong-gate/local-architecture/task-system.md` 存在且 status 字段描述标注为簿记字段，JSONL 示例不使用 `cli/` 前缀
3. `trellis-meta-strong-gate/local-architecture/spec-system.md` 存在且 JSONL 示例不使用 `cli/` 前缀
4. `commands/shell/workflow-state.py` 的 5 处提示位点已改进，新增 `context_needed` action
5. workflow.md 的 no_task 块说明 start 的条件性翻转行为
6. `阶段状态机与强门禁协议.md` 区分 recovery_needed / repair_needed / context_needed
7. 所有修改仅限于 `docs/workflows/新项目开发工作流/` 目录内
8. 修改不引入新的知识闭环断裂（所有引用指向实际存在的文件）
9. 修改不破坏现有安装流程（`install-workflow.py` 的现有逻辑不受影响）

## Out of Scope

- 修改 Trellis 原生 `task.py`/`task_store.py`/`task_queue.py` 的 baseline（这些不在工作流目录内）
- 修改当前项目自身的 `.trellis/` 文件
- 修改 `install-workflow.py` 的主安装流程（仅新增补丁文件供现有机制消费）
- 修改 `.agents/skills/trellis-meta/` 基线文件（这些由 Trellis 发布，不属于工作流资产）
