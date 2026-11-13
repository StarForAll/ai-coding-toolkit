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

## 运行约定（执行器）

- 日常命令形如 `<解释器> <项目根>/.wf/bin/wf.py <子命令>`。解释器按此顺序取，**取到能跑的就整会话固定复用**：
  ① `.wf/project-config.json` 的 `python_executable`（未设置再读 `~/.wf/config.json` 同名键，可直接读文件取值，不必先执行）；
  ② 你自身运行时的 Python 可执行文件；
  ③ 系统 `python3`。
- `WF_EXECUTOR_UNCONFIRMED`（配置的执行器未确认/失效）或宿主审批拒绝：停下并报告事实，由人确认执行器或调整执行策略后重跑。
  **不要换另一个解释器重试同一条命令**，不要改写信封/路径绕过，不装 PATH、不做 shell shim。
- 卸载/repair 的独立入口例外按设计稿 §1.1：它们不导入运行时，可用系统或人显式选择的已核实 Python 直接运行自身。
