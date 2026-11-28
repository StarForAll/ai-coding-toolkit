# 实例流程（instance-flow）

> 用户工作流定义、准备通道与实例编排。`definition prepare` 与 `run *` 均为当前发行已交付能力，
> 子命令均已实现；升级/导出入口属维护面（系统级 `wf upgrade`，说明见 maintenance-flow），启动与推进的日常子命令用项目脚本 `.wf/bin/wf.py` 运行，不依赖系统命令。

## required 步骤

### control.definition.prepare [required · repeatable]

- 时点：准备定义动作结束
- enforcement: `wflib/runs.py::prepare`
- 动作：人给出准备范围授权（`--authorization`，`choice=准备定义` + `scope_paths` + 范围摘要）后固定准备范围，
  并**取得限定到该路径的准备写权**（准备期仍是单写者）；起草/校验定义并保存校验结果与待决项；
  同范围重跑复用已签授权，改范围须新签；定稿后 `prepare --end` 或直接 `run create` 收口释放写权——`--end` 要求
  范围内未提交路径已由人提交/移走，或按 `retain` 记风险与待处置项保留草稿（准备通道不授权提交）。
- 出口：缺授权 → `WF_SEMANTIC_DECISION`（给 `--authorization-draft` 骨架）；已绑定会话调用 → `WF_BINDING_MISMATCH`（准备通道只给未绑定会话）；未处置编辑就结束 → `WF_WORKSPACE_UNRESOLVED`；静校失败 → `WF_DEFINITION_INVALID`。
  **准备会话丢失**（终端关闭/宿主会话不可续）时写权仍由旧会话持有：由人确认旧会话已停止后运行
  `wf repair`（预览 → 指纹 → `--apply`）复位写者；准备记录与草稿保留，再由新会话 `definition prepare`
  接续。不要手改 `.wf/writer.json`，也不要把准备写权当空闲。

### control.run.advance [required · repeatable]

- 时点：实例推进动作结束
- enforcement: `wflib/runs.py::advance`
- 动作：核固定快照、游标与任务归属后推进步骤，必要时按展开规则创建任务与顺序边；人判/略过步骤按已落盘结果结案推进。
  为步骤建任务时把该步骤的**契约**写进任务记录 `execution`：`step`（workflow/step/定义摘要）、
  `actions`（必做动作，`result` 初始 `pending`）、`human_points`、`verifications`（声明摘要）——
  它们随后由 Check 消费（见 `task-flow` 的 `control.task.check`），机制只搬运声明，不解释业务语义。
- 出口：快照/游标不明 → `WF_HISTORY_UNRESOLVED`；待决人判 → `WF_SEMANTIC_DECISION`（任务已异常归档时给实例层出口）。

### control.run.terminate [required · repeatable]

- 时点：实例终止动作结束
- enforcement: `wflib/runs.py::terminate`（已交付）
- 动作：按人确认的批量计划逐任务放弃或保留，写实例终态并授权提交。
- 出口：改动去向未落实 → `WF_WORKSPACE_UNRESOLVED`；只报终止与保留风险，不报验收通过。

### control.dependency.change [required · repeatable]

- 时点：建边/删边动作结束
- enforcement: `wflib/tasks.py::cmd_dep`（已交付）
- 动作：校验两端存在、无自环无环后落边；删边只改未归档持有侧。
- 出口：环或悬空 → `WF_DEPENDENCY_UNMET`；无法解析 → `WF_HISTORY_UNRESOLVED`。

### control.task.rework [required · repeatable]

- 时点：返工动作结束
- enforcement: `wflib/tasks.py::cmd_task_rework`（已交付）
- 动作：建 R、继承原前置、给 T 挂起，并按实例/普通任务分别处置定位与写权。
- 出口：候选图不合法 → `WF_DEPENDENCY_UNMET`；T 挂起未完成 → 阻止 R 提前执行。

### control.task.replace [required · repeatable]

- 时点：替换动作结束
- enforcement: `wflib/tasks.py::cmd_task_replace`（已交付）
- 动作：继任者承接原前置、继承路径与在途实例映射，原任务异常归档。
- 出口：继任者未覆盖继承路径 → 回规划；图不一致 → `WF_SEMANTIC_DECISION`。
