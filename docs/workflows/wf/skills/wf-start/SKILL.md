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

1. 若用户明确禁写 `.wf/`、明确要求不启用流程，或当前宿主策略已拒绝写运行态：**不要先跑 `enable` 或试写**，直接如实报告并进入下节「启用无法建立时」由人选择出口。否则先跑 `wf.py enable`，取得启用核对结果（Trellis 互斥、宿主身份能力、activation）。
   - `WF_FLOW_CONFLICT` / `WF_SEMANTIC_DECISION`：停，按 facts 清理或交人核实后再换新会话。
   - `WF_IDENTITY_UNRESOLVED`：停，按 facts 核实宿主身份能力。自动模式会为本会话签发 `issued_id`；
     旧对象的绑定已到终态、人想换新会话身份时用 `wf.py enable --new-session`（宿主无关轮换：
     旧附件/绑定保留为历史，新对象用 `task-new` 选择；对象仍在途会被 `WF_BINDING_MISMATCH` 拒并给出口）。
     宿主提供会话标识的平台（部署表 session_identity 声明）由适配层自动映射，`/clear` 后新会话标识
     使宿主身份换新；宿主标识缺位时同边界按在途会话续用（`host_identity_present`/`session_provider`
     facts 如实报告），在途期内 /clear 仍不可区分是已声明边界。
2. `enable` 的 `facts.binding` 给出当前绑定。已绑定：只恢复原对象，不换对象。人想开新任务时：旧对象已终态的，用 `wf.py enable --new-session` 在本边界换新会话后 `task-new`
   （宿主无关，普通宿主与有会话标识的宿主都走这一条）；只有需要**真正并行**推进两个对象时才另开终端/窗口。**不要用 `task-new` 试探**——对象在途时它只会报 `WF_BINDING_MISMATCH`。
3. 未绑定：由人选择
   - 新普通任务：`task-new`（`kind`/`title`/`template` 的取值见 `wf help task-new`）；
   - 既有就绪任务：`bind --task <id>`（可先 `wf ready` 看候选与阻断；`handover_pending` 表示对象在交接中间态）；
   - **工作流实例**（顺序见下节「定义与实例」：先取人的准备范围授权，再起草；定义还不存在时
     `definition validate` 必然报路径错误，不要先跑它）：`definition prepare`（取准备写权与校验） →
     `run create --authorization <人的创建授权>`；已有实例换到新会话接续用 `bind --run <id>`。
     实例的首次绑定由 `run create` 完成。
   - **接收写权交接**（四步不可换序）：① 接收方在**新执行边界**运行 `wf.py enable --json` 取得
     `facts.session_key`（此时项目还没有交接，`writer` 为空或由发起方持有都是正常的），把 key 转交发起方；
     ② 发起方 `writer-handover begin --to <key> --decision <文件>`；③ 接收方运行 `status --short`
     （或再次 `enable`），确认 `writer.handover.receiver_session_key` 是本会话 / `handover_for_me=true`；
     ④ 运行 `writer-handover accept` 接收对象。接收前不要 `task-new`/`bind`；key 打错只能按
     `wf repair` 恢复，转抄时核对回显。
4. 需要重新取得已被释放的写权时：`writer acquire`。
5. **自动模式下不手写 session 信封**：直接 `wf.py enable --json`，身份由执行边界派生
   （会话 leader + 进程链），`activation`/`instance_id` 由入口写进运行态附件并由后续命令自动读取。
   **写权代次同样不用手填**：取得写权时入口把代次记进本会话运行态，后续写命令缺省取它；
   显式 `inputs.generation` 仍可覆盖（过期会被 `WF_GENERATION_STALE` 拒）。
   只有在**拿不到执行边界**（容器逐命令、跨命名空间读不到 `/proc`）或需要兼容旧项目时，才用显式信封。
6. **把本次启用的结果变成会话缓存**（显式模式：由适配层按本次真实调用形成缓存，不是让运行时猜）：
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

1. **先取人的准备范围授权，再起草**：准备入口的只读授权骨架会把范围与摘要预填好（形状见
   `wf help definition`）；请人确认"允许准备哪些路径"后，把 TODO 换成人的答复再落准备记录
   （`.wf/preparations/<id>.json`）。这一步同时**取得限定到该定义路径的准备写权**——准备期间的编辑
   因此仍是单写者，别的会话拿不到写权。**没有授权就停在需人决策**（不会写一条自报 `source=human` 的记录）；
   定义还不存在时也可以先跑这一步固定范围（校验必然不过，准备记录照常保留为草稿）。
   **准备通道只给未绑定会话**：已绑定对象（含实例内任务）要改定义，走其已批准任务的 Plan 范围，不借准备通道改绑。
2. **在已授权的范围内起草** `.wf/user-workflows/<workflow-id>.md`：唯一 `<!-- wf-definition:v1 -->` 标记 + 紧邻 `json` 块。
   机制会拒的（`WF_DEFINITION_INVALID`，按 `problems[].stage` 顺序修）：结构/schema、id 重复与保留前缀
   （人判点 id 不得以 `plan-q-`/`debug-ruling-` 开头）、引用来源与顺序（`from` 只能取 input/project/secret_ref/step/action，
   `step` 必须指向更早步骤且引用它已声明的产物）、产物路径（`delivery` 相对项目根、`step_artifact` 落在实例产物根）、
   必需与可略的冲突、`skip.downstream.consumer` 必须真实存在、每条任务步骤都要承载验证。
   **机制不会替你判**：`purpose`/`applicability` 写得够不够清楚、`completion` 的条件是否真的覆盖目标、
   某个 `skip.condition` 该不该被认可 —— 这些写不清，定义即使过了校验也没有意义。
3. **起草后重跑** `definition prepare --id <id>`（同一命令、同一范围）固定校验结果——**同范围复用已签授权，
   不必重复索取**；改范围才要新签。定稿后二选一收口：直接 `run create`（创建实例即准备的天然收口，
   准备写权随之释放），或只备不建时 `definition prepare --end`。`--end` 认两条**事实**出路：定义已由人
   提交或移走；或按条件**保留**草稿（disposition 里 `action=retain` + `risk` + `pending`，机制记内容摘要、
   暂存事实与保留范围）。都没有就报 `WF_WORKSPACE_UNRESOLVED`——**准备通道不授权提交**：提交/移走由人做，
   你只按人给的处置转录；保留的草稿仍在共享工作区，会挡后续 `task-start` 的外来改动核对，别把它当已定稿。
4. **创建实例要人确认确切输入**：先取创建输入的只读骨架补齐输入值与每步适用性，再取创建授权的只读骨架
   （两者形状与旗标见 `wf help run`），请人确认后转录成决定文件，最后带授权创建实例。
   机制会拒的：定义摘要与当前文件字节不符（定义在确认后改过）、必填输入缺失或类型不符、
   `secret_ref` 输入写成明文、未声明的输入、没有本会话的有效准备记录（含授权）、创建输入与授权摘要不符、
   目标路径已存在。**创建授权绑定的是这份创建输入**：版本/输入/适用性任一变动都要重出决定。
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
   结果不能称为 wf 流程产物。"先做后补流程"不在出口内（开工门禁必须先于业务改动）。

## 不做

- 不批准规划、不 Check、不归档；`run create` 只建实例，不建任务（任务由 `run advance` 在首达步骤时建）。
  这不算违反：启用、建任务/实例、绑定与取得写权是本入口的份内事。
- 不因“只有一个活动任务”推断当前对象。

## 工作习惯

- 同一终端只推进一个任务；自动模式不手写信封——完整定义见 `wf-continue`「工作习惯」
  （唯一完整定义位），此处不重复论述。

## 纪律

- 运行纪律见 `.wf/workflows/session-flow.md`「运行约定」：身份只经信封或宿主映射通道；不代人作答；入口输出是唯一判定源；解释器整会话固定、失效即停。
