---
name: wf-start
description: 人显式调用：在当前会话启用 wf 框架，并选择或恢复本次受控对象（普通任务，或准备/创建工作流实例）。
disable-model-invocation: true
user-invoked: true
---

# wf-start

> **判断指引**：交付面（哪些文件算本次任务的交付）是判断不是判决——口径见 `wf-continue`「实施期要自己判的几件事」。

仅由人显式调用生效。它负责“启用 + 选对象 + 取得写权”；选定后继续该对象的第一步（新任务→PRD/规划；实例→`run advance`），不把“已启用”当终点；不代替人批准、Check 或归档。

## 步骤

1. 先跑 `wf.py enable`，取得启用核对结果（Trellis 互斥、宿主身份能力、activation）。
   - `WF_FLOW_CONFLICT` / `WF_SEMANTIC_DECISION`：停，按 facts 清理或交人核实后再换新会话。
   - `WF_IDENTITY_UNRESOLVED`：停，按 facts 核实宿主身份能力。自动模式会为本会话签发 `issued_id`；
     显式的“换一个新会话标识”命令尚未交付，不要引导人走这条路径。
2. `enable` 的 `facts.binding` 给出当前绑定。已绑定：只恢复原对象，不换对象。人想开新任务时，停止并说明需要新的执行边界（宿主提供会话标识时可用新会话；否则开新终端）；**不要用 `task-new` 试探**——它只会报 `WF_BINDING_MISMATCH`。
3. 未绑定：由人选择
   - 新普通任务：`task-new --kind ordinary|initialize|bootstrap --title <t> --template <项目根>/.wf/templates/task`；
   - 既有就绪任务：`bind --task <id>`；
   - **工作流实例**：`definition validate --id <id>` → `definition prepare --id <id>` → `run create --creation <path>`
     （准备与创建都在本入口，见下节）；已有实例换到新会话接续用 `bind --run <id>`（已交付）。
     实例的首次绑定由 `run create` 完成。
4. 需要重新取得已被释放的写权时：`writer acquire`。
5. **自动模式下不手写 session 信封**（2026-11-08 起）：直接 `wf.py enable --json`，身份由执行边界派生
   （会话 leader + 进程链），`activation`/`instance_id` 由入口写进运行态附件并由后续命令自动读取。
   **写权代次同样不用手填**：取得写权时入口把代次记进本会话运行态，后续写命令缺省取它；
   显式 `inputs.generation` 仍可覆盖（过期会被 `WF_GENERATION_STALE` 拒）。
   只有在**拿不到执行边界**（容器逐命令、跨命名空间读不到 `/proc`）或需要兼容旧项目时，才用显式信封。
6. **把本次启用的结果变成会话缓存**（显式模式；机制稿 §1.4：由适配层按本次真实调用形成缓存，不是让运行时猜）：
   `enable` 的 `facts.activation` 就是可缓存的启用事实——`activation_source=carried` 表示请求里已带，
   `formed_by_enable` 表示由本次启用形成；两种都原样缓存，并按 `facts.cache_hint` 随每次请求放进 `session.activation`。
   缓存丢了就重跑 `enable` 重新形成（`enable` 幂等，不改对象绑定）。
7. **显式模式**下记录入口回显的两项事实，后续请求都要携带：
   - `generation` → 信封 `inputs.generation`；
   - `enable`/`task-new`/`bind` 回显的 `activation`（`{enabled, start_source, enabled_at}`）→ 信封 `session.activation`，
     以及首次绑定生成的 `instance_id` → 信封 `session.instance_id`。
   **不携带 activation 会被 `WF_NOT_ENABLED` 拒（`bind`/`task-new`/`task-approve` 等都在核验集里）；不携带或携带不一致的
   `instance_id` 会被 `WF_IDENTITY_UNRESOLVED`/`WF_BINDING_MISMATCH` 拒**。这两项由适配层按每次请求重放，不靠模型记忆。

## 定义与实例（2026-11-12）

人要把一件事做成多步流程时，走「定义 → 准备 → 创建实例」。三步都在本入口，但它们**不是三次确认仪式**：
机制只核可观察的事实，其余交给你判断。

1. **写定义** `.wf/user-workflows/<workflow-id>.md`：唯一 `<!-- wf-definition:v1 -->` 标记 + 紧邻 `json` 块。
   机制会拒的（`WF_DEFINITION_INVALID`，按 `problems[].stage` 顺序修）：结构/schema、id 重复与保留前缀
   （人判点 id 不得以 `plan-q-`/`debug-ruling-` 开头）、引用来源与顺序（`from` 只能取 input/project/secret_ref/step/action，
   `step` 必须指向更早步骤且引用它已声明的产物）、产物路径（`delivery` 相对项目根、`step_artifact` 落在实例产物根）、
   必需与可略的冲突、`skip.downstream.consumer` 必须真实存在、每条任务步骤都要承载验证。
   **机制不会替你判**：`purpose`/`applicability` 写得够不够清楚、`completion` 的条件是否真的覆盖目标、
   某个 `skip.condition` 该不该被认可 —— 这些写不清，定义即使过了校验也没有意义。
2. `definition prepare --id <id>`：落准备记录（`.wf/preparations/<id>.json`），记住**准备范围归发起它的会话**。
   校验不过时准备记录**照常保留**（草稿），`validation.ok=false` 留痕；修完重跑即可。
3. `run create --creation <path>`：creation 文件给 `{definition_id, definition_digest, inputs, steps, expansion?}`。
   机制会拒的：`definition_digest` 与当前文件字节不符（定义在确认后改过）、必填输入缺失或类型不符、
   `secret_ref` 输入写成明文、未声明的输入、没有本会话的有效准备记录、目标路径已存在。
   **实例创建只取得"规划权限"**：它不批准任何业务、不建任务、不推进游标。

创建后 `run locate --run <id>` 可以随时只读回读（`cursor`/`step_results`/`task_map`/各步骤任务的状态）。
推进、暂停、以及"实例暂停怎么恢复"的判读口径见 `wf-continue`。

## 启用无法建立时（宿主拒绝写入 / 身份不可核实）

`enable` 是启用步骤，不是一个可以跳过的仪式：它要写本会话运行态（`.wf/.runtime/`）。遇到下面任一情形，
先**如实报告"本次未启用"及事实**，再由人从固定出口里选一条：

- 宿主执行策略拒绝写入 `.wf/`：报告被拒绝的路径、拒绝来源（宿主策略/沙箱）与 `enable` 的错误码；
- `WF_IDENTITY_UNRESOLVED` / `WF_FLOW_CONFLICT` / `WF_SEMANTIC_DECISION`：按 facts 与 `next` 处理。

出口（只按人明确选择的一条走；模型不代选）：
1. 解除写限制（允许 `.wf/` 下的运行态写入）后重跑 `enable`；
2. 换到满足条件的宿主/新会话后重跑 `/wf-start`；
3. 人明确选择"本次按普通开发继续"——此时如实说明：本次没有任务、没有 PRD、没有 wf 门禁，
   结果不能称为 wf 流程产物。"先做后补流程"不在出口内（设计稿 §4.2 要求开工门禁先于业务改动）。

## 不做

- 不批准规划、不 Check、不归档；`run create` 只建实例，不建任务（任务由 `run advance` 在首达步骤时建）。
- 不因“只有一个活动任务”推断当前对象。

## 工作习惯（2026-11-08 起）

- **同一终端同时只推进一个任务**；需要并行时另开终端或窗口。
  同一终端内的第二个 agent 会被 `WF_IDENTITY_UNRESOLVED(concurrent_unregistered_caller)` 阻断，
  必须由人显式 `wf.py enable` 登记后才放行，且此后与前者**共享同一执行会话**。

## 纪律

- 身份只在请求信封里：不读环境变量、不从命令行或文件猜身份；信封缺失就报 `WF_IDENTITY_UNRESOLVED`。
- 不代人作答、不代跑终端确认与令牌；人的决定只经 `--decision` / `--plan` / `--disposition` 文件承载。
- 入口输出的 `tier` / `code` / `facts` / `next` 是唯一判定源；不自行改写状态或补写门禁结论。
- 解释器按 `.wf/workflows/session-flow.md`「运行约定」选择并整会话固定；`WF_EXECUTOR_UNCONFIRMED` 或审批拒绝时停下报告，不换解释器重试。
