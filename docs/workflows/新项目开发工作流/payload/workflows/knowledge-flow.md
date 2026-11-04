# 知识流程（knowledge-flow）

> 本地 spec 的准入、策展、读取、变更与统计。默认路径不依赖外部 MCP、索引服务或知识图谱；
> 全部操作在项目内以文件与只读 Git 事实完成。

## required 步骤

### control.spec.update [required · repeatable]

- 时点：知识变更动作结束
- enforcement: `wflib/spec.py::apply_changes`（`wflib/tasks.py::cmd_spec_update` 调用）
- 动作：按人审变更成组写 spec 文件、元数据与索引；改名同步活动引用，删除前逐项解除依赖。
- 出口：活动依赖未解除 → `WF_SEMANTIC_DECISION`（先解除/推迟/指定替代）；路径非法 → `WF_PATH_INVALID`。

### control.task.curate [required · repeatable]

- 时点：策展写入动作结束
- enforcement: `wflib/tasks.py::cmd_task_curate`
- 动作：把选定 spec 的路径、摘要、用途与时间写入任务策展清单；Plan 选、执行中补。
- 出口：文件缺失 → `WF_PATH_INVALID`；清单缺失不等于零引用，须显式写入空数组。

### control.task.knowledge-dispose [required · repeatable]

- 时点：知识处置动作结束
- enforcement: `wflib/tasks.py::cmd_task_knowledge`
- 动作：记录 `no-update` 或 `updated` 及具体变更；「无更新」也是实际处置。
- 出口：缺处置记录 → `WF_SEMANTIC_DECISION`；不得以空建议冒充规则。
