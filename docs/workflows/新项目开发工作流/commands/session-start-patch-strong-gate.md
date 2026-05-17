## SessionStart Strong-Gate Patch

### 概述

安装器在嵌入目标项目时，将 `patch-session-start-strong-gate.py` 应用于 `.claude/hooks/session-start.py`，使其 `_get_task_status()` 函数在强门禁模式下优先使用 `workflow-state.py route` 的路由结果，而非旧的 PLANNING/READY 逻辑。

### 背景

原始 `_get_task_status()` 使用 `task.json.status` 的 PLANNING/READY 判断路由：

- `PLANNING`: 无 prd.md 或 implement.jsonl 无条目 -> 建议加载 `trellis-brainstorm`
- `READY`: prd.md + curated jsonl 存在 -> 建议分发 `trellis-implement`

在强门禁模型中，路由依据应为 `workflow-state.json` 的 `stage` 字段，由 `workflow-state.py route` 命令计算。旧逻辑无法区分具体阶段（feasibility/brainstorm/design/plan/implementation/test-first/check/review-gate/finish-work/delivery/record-session），也无法反映阶段门禁状态。

### 补丁行为

在 `_get_task_status()` 函数中，`task_title` 和 `task_status` 均已解析后、旧 Case 3（completed）判断之前，注入强门禁路由逻辑：

1. 检查 `task_dir / "workflow-state.json"` 是否存在
2. 若存在，读取 `stage` 字段，验证其属于合法强门禁阶段集合
3. 若阶段有效，执行 `workflow-state.py route --task-dir <task_dir>` 获取路由 JSON
4. 构建结构化状态字符串，包含 `Status`（强门禁阶段）、`Action`、`Blockers` 等，直接返回
5. 若 `workflow-state.json` 不存在或补丁逻辑异常，静默 fallback 到旧逻辑

### 合法强门禁阶段

```python
{
    "feasibility", "brainstorm", "design", "plan",
    "implementation", "test-first", "project-audit",
    "check", "review-gate", "finish-work", "delivery", "record-session",
}
```

### 补丁输出格式

当强门禁路由生效时，`<task-status>` 块的格式变为：

```
Status: STRONG-GATE (<stage>)
Task: <task_title>
Source: <active.source>
Stage-Status: <stage_status>
Action: <action>
Target-Stage: <target>        (仅当 target 非空)
Reason: <reason>              (仅当 reason 非空)
Blockers: <blocker1>; <blocker2>  (仅当有 blockers)
Next-Action: Follow the action above...
```

### 补丁脚本

- 脚本路径：`<WORKFLOW_DIR>/commands/shell/patch-session-start-strong-gate.py`
- 注册位置：`workflow_assets.py` 的 `HELPER_SCRIPTS` 列表
- 安装器在嵌入时调用，目标为 `.claude/hooks/session-start.py`

### 冪等性

补丁通过 `# strong-gate-session-start-patch-applied` 标记检测是否已应用。重复调用不会重复注入。

### Fallback 行为

以下情况补丁不生效，自动 fallback 到旧 PLANNING/READY 逻辑：

- `workflow-state.json` 不存在于 task 目录
- `stage` 字段为空或不在合法阶段集合中
- `workflow-state.py` 脚本未找到
- `workflow-state.py route` 执行失败或输出非法 JSON
- 补丁逻辑抛出任何异常（被 `except Exception` 静默捕获）
