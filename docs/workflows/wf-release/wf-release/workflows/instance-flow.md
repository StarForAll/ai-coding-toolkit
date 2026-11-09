# 实例流程（instance-flow）

> 用户工作流定义、准备通道与实例编排。第二轮交付；未交付时命令存在并返回
> `tier=blocked` / `WF_CAPABILITY_UNAVAILABLE`，facts 记所属轮次。

## required 步骤

### control.definition.prepare [required · repeatable]

- 时点：准备定义动作结束
- enforcement: `wflib/runs.py::prepare`（第二轮；未交付返回 `WF_CAPABILITY_UNAVAILABLE`）
- 动作：人授权精确保留路径后取得准备范围，起草/校验定义并保存校验结果与待决项。
- 出口：静态校验失败 → `WF_DEFINITION_INVALID`；准备范围外写入 → `WF_SCOPE_VIOLATION`。

### control.run.advance [required · repeatable]

- 时点：实例推进动作结束
- enforcement: `wflib/runs.py::advance`（第二轮）
- 动作：核固定快照、游标与任务归属后推进步骤，必要时按展开规则创建任务与顺序边。
- 出口：快照/游标不明 → `WF_HISTORY_UNRESOLVED`；待决人判 → `WF_SEMANTIC_DECISION`。

### control.run.terminate [required · repeatable]

- 时点：实例终止动作结束
- enforcement: `wflib/runs.py::terminate`（第二轮）
- 动作：按人确认的批量计划逐任务放弃或保留，写实例终态并授权提交。
- 出口：改动去向未落实 → `WF_WORKSPACE_UNRESOLVED`；只报终止与保留风险，不报验收通过。

### control.dependency.change [required · repeatable]

- 时点：建边/删边动作结束
- enforcement: `wflib/cli.py::dep`（第二轮）
- 动作：校验两端存在、无自环无环后落边；删边只改未归档持有侧。
- 出口：环或悬空 → `WF_DEPENDENCY_UNMET`；无法解析 → `WF_HISTORY_UNRESOLVED`。

### control.task.rework [required · repeatable]

- 时点：返工动作结束
- enforcement: `wflib/cli.py::task-rework`（第二轮）
- 动作：建 R、继承原前置、给 T 挂起，并按实例/普通任务分别处置定位与写权。
- 出口：候选图不合法 → `WF_DEPENDENCY_UNMET`；T 挂起未完成 → 阻止 R 提前执行。

### control.task.replace [required · repeatable]

- 时点：替换动作结束
- enforcement: `wflib/cli.py::task-replace`（第二轮）
- 动作：继任者承接原前置、继承路径与在途实例映射，原任务异常归档。
- 出口：继任者未覆盖继承路径 → 回规划；图不一致 → `WF_SEMANTIC_DECISION`。
