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
- enforcement: `wflib/tasks.py::cmd_task_reassess`（挂起集合为空时通过）
- 动作：复评挂起任务；挂起集合为空时直接通过（不写记录、不返回不可用）。返工由 `task-rework` 承载（建 R、挂起 T、继承前置，已交付）。
- 出口：未持写权只报告「待复评」；第二阶段交付完整复评路径。

## 运行约定（会话纪律与执行器）

以下纪律是**唯一完整论述位**（2026-11-21 收敛）：各 skill 只保留一句判断 + 指针指向本节，不在别处复制论述。

1. **身份只经请求信封或宿主映射通道传递**：不读环境变量、不从命令行猜身份；自动模式下身份由入口按执行边界派生（`issued_id`，`source=auto`），宿主会话标识经适配层映射文件（`.wf/.runtime/host-session-map/`，等价于信封的宿主身份，机制稿 §1.4）或显式信封承载；取用次序＝边界在途会话续用 → 宿主标识 → 进程锚派生（在途续用仅在存在未终态在途对象时生效）。任何来源缺失或不可核时报 `WF_IDENTITY_UNRESOLVED`，不猜。
2. **不代人作答、不代跑终端确认与令牌**；人的决定只经命令契约声明的人类输入通道承载
   （`--decision`/`--plan`/`--disposition` 与 judgments、authorize、accept-unknown 等 `--file` 类输入；
   形状以 `wf help <命令>` 的 `inputs` 为准）。
3. **入口输出的 `tier` / `code` / `facts` / `next` 是唯一判定源**；不自行改写状态或补写门禁结论。
4. **解释器按本节「执行器」选择并整会话固定**；`WF_EXECUTOR_UNCONFIRMED` 或审批拒绝时停下报告，不换解释器重试。
5. **同一终端同时只推进一个任务**（见 task-flow.md 的任务并发约束）。
6. **证据文件纪律**：验证结果、门禁预览、提交清单与摘要等入口自产的结构不落自述性文件（"不要自建"与输入形状的判断见 `wf-continue`「证据文件纪律」）。
7. **命令取值一律加引号**：路径、标题、ID、决定文件名都可能含空格或 shell 元字符，调用时用单/双引号包住取值
   （引号由 shell 去掉，入口看到的是同一个值）；`wf help <命令>` 的示例已按此写法给出，直接照抄即可。

### 执行器

- 日常命令优先用系统级 `wf <子命令>`（在项目内自动定位 `.wf/`，不在项目根用 `wf --project <绝对路径> <子命令>`）；它只做定位与转交，最终仍由下述执行器运行 `.wf/bin/wf.py`。直接调用项目脚本时形如 `<解释器> <项目根>/.wf/bin/wf.py <子命令>`。解释器按下述唯一定义取，**取到即整会话固定复用**：
  ① `.wf/project-config.json` 的 `python_executable` 键（未设置再读 `~/.wf/config.json` 同名键，可直接读文件取值，不必先执行）；
  ② 系统 `python3`。
  不新增第三档回退（含"你自身运行时的 Python"——它不是登记的解析档位）；已设置项失效时**停下人确认，不降级续试**。
- `WF_EXECUTOR_UNCONFIRMED`（配置的执行器未确认/失效）或宿主审批拒绝：停下并报告事实，由人确认执行器或调整执行策略后重跑。
  **不要换另一个解释器重试同一条命令**，不要改写信封/路径绕过，也不要另做本地包装或 shell shim 来绕开执行器；系统 `wf` 是统一入口，不是执行器解析的替代。
- 卸载/repair 的独立入口例外：它们不导入运行时，可用系统或人显式选择的已核实 Python 直接运行自身。
