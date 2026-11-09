# 会话流程（session-flow）

> 会话身份、持久绑定、写权与两段交接。身份只经请求信封传递；绑定终身不变；
> 同一时刻只有一个写者。

## required 步骤

### control.session.bind [required · repeatable]

- 时点：首次绑定动作结束
- enforcement: `wflib/cli.py::cmd_bind`（写权获取动作内成组写入）
- 动作：空闲态下新会话对既有就绪对象的首次绑定；建立会话实例标识。
- 出口：已绑定其他对象 → `WF_BINDING_MISMATCH`；写者被占 → `WF_WRITER_BUSY`。

### control.writer.acquire [required · repeatable]

- 时点：写权获取动作结束
- enforcement: `wflib/cli.py::_writer_acquire`
- 动作：核身份、绑定与工作区后授予新代次；旧代次立即失效。
- 出口：身份不可核 → `WF_IDENTITY_UNRESOLVED`；未空闲 → `WF_WRITER_BUSY`。

### control.writer.release [required · repeatable]

- 时点：写权释放动作结束
- enforcement: `wflib/cli.py::_writer_release`
- 动作：对象已暂停/终态且工作区满足边界后释放为空闲；绑定保留。
- 出口：工作区未处置 → `WF_WORKSPACE_UNRESOLVED`。

### control.writer.handover.begin [required · repeatable]

- 时点：交接第一段结束
- enforcement: `wflib/cli.py::_handover_begin`
- 动作：旧写者保存进度与 WIP 处置，使旧代次失效并写接收者与待恢复范围。
- 出口：中间态双方均无业务写权；未持写权 → `WF_WRITER_BUSY`。

### control.writer.handover.accept [required · repeatable]

- 时点：交接第二段结束
- enforcement: `wflib/cli.py::_handover_accept`
- 动作：接收方核自身绑定、对象与真实工作区后授予新代次并补检查点。
- 出口：非声明接收者 → `WF_BINDING_MISMATCH`；状态不符 → `WF_WRITER_BUSY`。

### control.task.reassess [required · repeatable]

- 时点：归档持久化核实后与启动校验通过后
- enforcement: `wflib/tasks.py::cmd_task_reassess`（首轮按空挂起集合通过）
- 动作：复评挂起任务；首轮无返工能力，挂起集合为空时直接通过，不写记录、不返回不可用。
- 出口：未持写权只报告「待复评」；第二阶段交付完整复评路径。
