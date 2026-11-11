---
name: wf-repair-loop
description: 修复态判读：读 repair_scope 的四组事实与 exits，决定下一步动作（重查/重判/重发/放行/终止）。
disable-model-invocation: false
---

# wf-repair-loop

`repair_scope` 是**事实集**，不是状态机：它同时给出全部四组事实与可执行出口，
**不排顺序**、不产生"等待评审"状态。怎么走由你判断；判断不是自由发挥，要按下面的事实读。

## 1. 先读什么

```bash
<python> <项目根>/.wf/bin/wf.py status --short --json     # 四条件 + exits + 确定阻断
<python> <项目根>/.wf/bin/wf.py status --json             # 需要细节时再取全量 facts
```

`--short` 里的 `repair_scope` 是**原样过滤**：

| 字段 | 含义 |
|---|---|
| `conditions` | `C1_check_valid` / `C2_no_open_blocking` / `C3_no_unreleased_evidence` / `C4_review_bound_pass` 的真假 |
| `exits` | `[{condition, action, round}]`——机制产出的全部出口，没有优先级 |
| `blocking` | 与归档预检**同一个函数**给出的"还有哪些确定阻断"（`stage` 标明来自 nonstep 还是步骤面） |
| `open_blocking` | 未关闭的 blocking（每条带 `round`；已写 `rejected`/`amended` 的条目带 `disposition`，仍算**未关闭**） |
| `unverifiable` | 不可核实的证据（见 §3） |
| `rounds` | 逐轮决策（`inferred: true` 见 §4） |

## 2. 十个动作 token

`exits[].condition` 说明是哪个条件未满足，`action` 是要执行的动作：

| action | 对应命令 | 说明 |
|---|---|---|
| `rerun_check` | `task-check` | C1：当前检查不能用于完成任务（内容变了 / 规则版本变了 / 失效登记） |
| `record_disposition` | `review-decide --plan <file>` | C2：关闭 blocking；只有 `accepted` 清零（见 `wf-review-action`） |
| `restore_bytes` | 找回原字节放回原路径 | C3：恢复后该条离开 `unverifiable`（不依赖身份） |
| `human_release` | `review-accept-unknown --file <决定.json>` | C3：只在该条 `release_allowed == true` 时出现 |
| `resume_inflight` | 继续该轮证据收集后 `review-import` / `review-decide` | C4：该轮 `blocked` 为空且未判定 |
| `redecide_round` | `review-decide --round <n>` | C4：该轮已判定但不是"当前绑定的 pass 轮" |
| `await_material` | 等材料到达 | C4：该轮 `blocked` 仅含 `material_missing` |
| `relaunch_review` | `review-launch` | C4：改变事实（新轮新报告），常列 |
| `pause_for_human` | `task-pause` | 终局动作之一 |
| `abandon_task` | `task-abandon` | 终局动作之一；**不得**把"当前推进不动"推成"应放弃" |

## 3. `launches[]` 逐轮看，`unverifiable[]` 按三态看

- `launches[]` 每轮一行：`{round, form, imported, declared, decided, blocked}`。
  `blocked` 是**已成立的事实列表**（`report_invalid` / `anchor_stale` / `implementer_overlap` /
  `insufficient_reviewers` / `material_missing`），不是分数、不做优先级合成。
  - `material_missing` = 还可能有材料到（已导入去重后仍 < 2）；
  - `insufficient_reviewers` = 已无更多材料可等（例如声明只有 1 个槽位）。
- `unverifiable[]` 每条带 `cause`（`missing` / `changed` / `unreadable`）与 `state`：
  - `unresolved`：未放行（C3 未满足，阻断归档）；
  - `accepted-risk`：已由人裁放行（**只**解除 C3，不等于"已处置/已关闭"）；
  - `consumed`：放行已失效（报告曾恢复又被再次损坏；需要新的放行决定）。
- `release_allowed` 取**当前** `complexity`：complex 的引用证据不可放行，light 的引用证据可放行。
  因此 complex→light 降级会翻转同一份损坏证据的放行资格；不要凭记忆，读现值。

## 4. `rounds[]` 的 `inferred` 边界

存量任务的 `rounds[]` 为空时，机制按 `result` **推断一条**（`inferred: true`、`decided_at: null`）。
推断只说明"最后一次判定是什么"，**其余轮次的历史不可知**：那些轮显示 `decided == false`
但不代表当时没判过。要处置这些轮，优先 `redecide_round` 取新事实，而不是沿用推断。

## 5. 四条容易误判的地方

1. **`check_valid == false` 有两种走法**：内容没变（规则版本/失效登记）通常重查即可；
   内容已变则先重查还是先重判由你判断——注意**结论写入后再重查会让结论失绑**，这是事实提示，
   不是"发起早就会失绑"。先重查是建议，不是机制事实。
2. **fail 轮重判仍是 fail**：`verdict` 由报告载荷推导（存在 blocking finding 即 fail），
   重判不改结论。
3. **你的否定只清 C2**：把 finding 以 `accepted` 关闭可以让 `open_blocking` 清零，
   但 complex 任务的 C4 仍要求一次 `pass`——否定不能替代审查结论。
4. **`stale_extra` 非空**：判定之后该轮又导入了未被引用的报告。先读这些新报告，
   再决定重判（`redecide_round`）或在收工时说明为何不重判；不得跳过实质检查。

## 6. 换实施宿主

`review_binding` 的 CLI 校验只能比较 **launch 对 launch**：已发起过新 launch 时旧 pass 会被门禁拦住；
但**换了实施 CLI 却没有 launch** 时两边都是旧值，机制看不见这次交接。
所以换实施宿主时**先 `review-launch`**，再继续该轮审查。

## 7. 不要试归档探路

归档会先做业务提交；虽然 `archive` 现在有提交前只读预检（阻断会先于提交返回），
预检通过也**不等于**可以归档——步骤面、escalated 待答、required 未核实、依赖、debug 未裁
各自还有自己的门禁。要问"还差什么"就读 `status --short` / `gate --due before_archive`，
不要用 `archive` 试探。

## 纪律

- 入口输出的 `tier` / `code` / `facts` / `next` 是唯一判定源；不自行改写状态或补写门禁结论。
- 身份只在请求信封里：不读环境变量、不从命令行或文件猜身份；信封缺失就报 `WF_IDENTITY_UNRESOLVED`。
- 不代人作答、不代跑终端确认与令牌；人的决定只经 `--decision` / `--plan` / `--disposition` 文件承载。
- 命令形如 `<python> <项目根>/.wf/bin/wf.py <子命令>`。`<python>` 按此顺序取，**取到能跑的就整会话固定复用**：
  ① `.wf/project-config.json` 的 `python_executable`（未设置再读 `~/.wf/config.json` 同名键，可直接读文件取值，不必先执行）；
  ② 你自身运行时的 Python 可执行文件；
  ③ 系统 `python3`。
  若宿主执行策略要求审批或不在白名单（`WF_EXECUTOR_UNCONFIRMED` / 审批拒绝），改用策略允许的已核实 Python 绝对路径并固定下来；
  **不要每条命令换解释器**，也不要因为被拒就改成手写信封或换路径重试同一效果。不装 PATH、不做 shell shim。
