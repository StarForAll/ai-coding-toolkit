---
name: wf-start
description: 人显式调用：在当前会话启用 wf 框架，并选择或恢复本次受控对象（普通任务；实例属第二轮）。
disable-model-invocation: true
user-invoked: true
---

# wf-start

仅由人显式调用生效。它负责“启用 + 选对象 + 取得写权”，不推进业务。

## 步骤

1. 先跑 `wf.py enable`，取得启用核对结果（Trellis 互斥、宿主身份能力、activation）。
   - `WF_FLOW_CONFLICT` / `WF_SEMANTIC_DECISION`：停，按 facts 清理或交人核实后再换新会话。
   - `WF_IDENTITY_UNRESOLVED`：停，按 facts 核实宿主身份能力。`provider=wf`（wf 签发 `issued_id`）的**显式签发命令尚未交付**
     （登记为第二轮事项），当前不可作为可用出口；不要引导人走这条路径。
2. 已绑定：只恢复原对象，不换对象。
3. 未绑定：由人选择
   - 新普通任务：`task-new --kind ordinary|initialize|bootstrap --title <t> --template <项目根>/.wf/templates/task`；
   - 既有就绪对象：`bind --task <id>`（实例用 `--run <id>`，第二轮）。
4. 需要重新取得已被释放的写权时：`writer acquire`。
5. **把本次启用的结果变成会话缓存**（机制稿 §1.4：由适配层按本次真实调用形成缓存，不是让运行时猜）：
   `enable` 的 `facts.activation` 就是可缓存的启用事实——`activation_source=carried` 表示请求里已带，
   `formed_by_enable` 表示由本次启用形成；两种都原样缓存，并按 `facts.cache_hint` 随每次请求放进 `session.activation`。
   缓存丢了就重跑 `enable` 重新形成（`enable` 幂等，不改对象绑定）。
6. 记录入口回显的两项事实，后续请求都要携带：
   - `generation` → 信封 `inputs.generation`；
   - `enable`/`task-new`/`bind` 回显的 `activation`（`{enabled, start_source, enabled_at}`）→ 信封 `session.activation`，
     以及首次绑定生成的 `instance_id` → 信封 `session.instance_id`。
   **不携带 activation 会被 `WF_NOT_ENABLED` 拒（`bind`/`task-new`/`task-approve` 等都在核验集里）；不携带或携带不一致的
   `instance_id` 会被 `WF_IDENTITY_UNRESOLVED`/`WF_BINDING_MISMATCH` 拒**。这两项由适配层按每次请求重放，不靠模型记忆。

## 不做

- 不创建实例（第二轮）、不批准规划、不 Check、不归档。
- 不因“只有一个活动任务”推断当前对象。

## 纪律

- 身份只在请求信封里：不读环境变量、不从命令行或文件猜身份；信封缺失就报 `WF_IDENTITY_UNRESOLVED`。
- 不代人作答、不代跑终端确认与令牌；人的决定只经 `--decision` / `--plan` / `--disposition` 文件承载。
- 入口输出的 `tier` / `code` / `facts` / `next` 是唯一判定源；不自行改写状态或补写门禁结论。
- 命令一律形如 `python3 <项目根>/.wf/bin/wf.py <子命令>`；不装 PATH、不做 shell shim。
