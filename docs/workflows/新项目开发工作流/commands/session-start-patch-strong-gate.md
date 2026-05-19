## SessionStart Strong-Gate Patch

### 概述

安装器在嵌入目标项目时，将 `patch-session-start-strong-gate.py` 应用于 `.claude/hooks/session-start.py`，使其 `_get_task_status()` 函数在强门禁模式下统一委托 `workflow-state.py route`，而非旧的 PLANNING/READY 逻辑。

### 背景

原始 `_get_task_status()` 使用 `task.json.status` 的 PLANNING/READY 判断路由：

- `PLANNING`: 无 prd.md 或 implement.jsonl 无条目 -> 建议加载 `trellis-brainstorm`
- `READY`: prd.md + curated jsonl 存在 -> 建议分发 `trellis-implement`

在强门禁模型中，路由依据应为 `workflow-state.json` 的 `stage` 字段，由 `workflow-state.py route` 命令计算。旧逻辑无法区分具体阶段（feasibility/brainstorm/design/plan/implementation/test-first/check/review-gate/finish-work/delivery/record-session），也无法反映阶段门禁状态。

### 补丁行为

在 `_get_task_status()` 函数中，`task_title` 和 `task_status` 均已解析后，直接以强门禁 route-first 逻辑**替换旧的 task-status 尾路由**（而不是前插一个总是 return 的补丁块）：

1. 定位 `.trellis/scripts/workflow/workflow-state.py`
2. 无论 `workflow-state.json` 是否存在，都执行 `workflow-state.py route <task_dir> --project-root <project-root>`
3. 读取路由 JSON 中的 `action`、`stage`、`stage_status`、`blockers`、`target`、`reason`
4. 构建结构化状态字符串并直接返回
5. 只有在 route helper 缺失、route 执行失败、或输出非法 JSON 时，才退回简单 `ACTIVE` 状态

这样 `repair_needed`、`context_needed`、`awaiting_confirmation_with_blockers` 等正式路由结果不会被 SessionStart 隐藏。

维护约束：

- 不要保留旧的 `PLANNING` / `READY` / `COMPLETED` 尾逻辑作为不可达死代码
- 补丁升级时应保证 `_get_task_status()` 中只保留一套 route-first 结果分支和必要 fallback，避免维护者误改死分支

### 补丁输出格式

当强门禁路由生效时，`<task-status>` 块的格式变为：

```
Status: STRONG-GATE (<stage-or-action>)
Task: <task_title>
Source: workflow-state.route
Stage-Status: <stage_status>
Action: <action>
Target-Stage: <target>        (仅当 target 非空)
Reason: <reason>              (仅当 reason 非空)
Blockers: <blocker1>; <blocker2>  (仅当有 blockers)
Warnings: <warning1>; <warning2>  (仅当有 warnings)
Next-Action: Follow the action above...
```

### 补丁脚本

- 脚本路径：`<WORKFLOW_DIR>/commands/shell/patch-session-start-strong-gate.py`
- 注册位置：`workflow_assets.py` 的 `HELPER_SCRIPTS` 列表
- 安装器在嵌入时调用，目标为 `.claude/hooks/session-start.py`

### 冪等性

补丁通过 `# strong-gate-session-start-patch-applied` 与 `# [workflow-embed-patch:session-start-route-first]` 标记检测是否已升级到 route-first 版本。重复调用不会重复注入。

### Fallback 行为

以下情况补丁返回简单 `ACTIVE` 状态（不 fallback 到旧 PLANNING/READY 逻辑）：

- `workflow-state.py` 脚本未找到
- `workflow-state.py route` 执行失败或输出非法 JSON
- 补丁逻辑抛出任何异常（被 `except Exception` 捕获后返回 ACTIVE 状态）

注意：`workflow-state.json` 缺失或损坏时，不应再回退为 `ACTIVE`；应由 `workflow-state.py route` 返回 `repair_needed`。
