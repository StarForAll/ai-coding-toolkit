---
name: wf-review-accept-unknown
description: 人裁放行：向人呈现不可核实证据的登记事实、采集 quote、写放行记录或撤销。
disable-model-invocation: false
---

# wf-review-accept-unknown

放行是**人对"当次不可核实情形"的决定**，不是永久豁免，也不是"缺陷已处置"。
本 skill 只管人机分工与文件形状；判据在入口（`status` 的 `unverifiable[]` 与 `release_allowed`）。

## 1. 什么时候问人

只有一种情形值得问：`unverifiable[]` 里有条目 **且** 找回原字节已经不可行（`cause` 为
`missing` / `changed` / `unreadable`，`restore_bytes` 走不通）。

- **不要**在还能 `restore_bytes` 时问人：先把原字节找回来放回原路径，该条会离开 `unverifiable`。
- **不要**把放行说成"问题解决了"：放行只解除 C3；`open_blocking`（C2）不会因此变化。
- 若是 complex 的**引用证据**（`release_allowed == false`），**不能放行**：
  先 `review-launch` 做一次新审查，让旧报告变成非引用证据，再回头问人。

## 2. 呈现哪些事实（签字前必须让人看到）

逐条给出（都来自 `wf status --json` 的 `repair_scope.unverifiable[]`）：

| 字段 | 为什么必须给人看 |
|---|---|
| `round` / `slot` | 是哪一轮、哪一份报告 |
| `cause` | `missing`（文件没了）/ `changed`（摘要不符）/ `unreadable`（读不出） |
| `report_digest` | 登记的摘要（放行键的一部分；`null` 表示遗留记录缺摘要） |
| `cited` | 是否被**当前结论**引用（引用证据在 complex 下不可放行） |
| `release_allowed` | 现在能不能放行（取**当前** complexity，降级会翻转） |
| `state` | `unresolved`（未放行）/ `accepted-risk`（已放行）/ `consumed`（放行已失效） |

另附事实：该轮 `verdict` 与已导入/声明数量（`launches[]` 对应行）。

## 3. `release_allowed` 的取值含义

`release_allowed = !(cited && review_required)`：

- complex 的引用证据 → `false`（不可放行，只能改事实）；
- light 的引用证据 → `true`；
- 非引用证据 → `true`（不分复杂度）。

`review_required` 取**当前** `plan.complexity`：complex→light 降级后，同一份损坏证据的
放行资格会翻转。不要凭印象，读该条目的现值。

## 4. 「未知 findings 一并豁免」意味着什么

报告不可核实时，里面的 findings 也随之无法枚举（`open_findings` 整份跳过）。
因此放行**必然同时豁免该报告中未知的 findings**——这不是副作用，是放行的定义。
决定文件必须显式写 `"waive_unknown_findings": true`（缺失即整批拒绝）；
`quote` 里要能看出人知道这一点，**不要**把放行描述成"已处置/已关闭"。

## 5. 决定文件与命令

```json
{"batch": "b-1",
 "acceptances": [{"round": 1, "slot": "s1",
                  "report_digest": "sha256:…",
                  "quote": "这份报告丢失的风险我认",
                  "by": "human:xzc", "at": "2026-11-11T14:00:00.000000Z",
                  "source": "user-declared",
                  "waive_unknown_findings": true}]}
```

```bash
<python> <项目根>/.wf/bin/wf.py review-accept-unknown --task <id> --file <决定.json> --json
<python> <项目根>/.wf/bin/wf.py review-accept-unknown --task <id> --revoke --batch b-1 --json
<python> <项目根>/.wf/bin/wf.py review-accept-unknown --task <id> --revoke --round 1 --slot s1 --digest sha256:… --json
```

规则（由入口执行，不要自己绕）：

- `report_digest` 必须等于**导入记录里的登记摘要**，不是损坏文件的当前摘要；不等 → 整批拒绝。
- 该 `(round, slot, report_digest)` 必须**当前**在 `unverifiable` 里；不做预放行。
- 批次**全有或全无**：任一项不合法即零写入，错误里给 `bad_items`。
- 幂等：同键且未撤销、未消费 → 回报 `already_accepted`，不新增；已撤销或已消费 → 新增一条（新 batch）。
- `--revoke` 只标记不删除；`--batch` 与 `--round/--slot/--digest` 同时给出会报错（不猜优先级）。
- 一次一事件：报告一旦恢复可核实，受控写点（`archive` 预检 / `review-import` / `review-decide`）
  会把该放行标 `consumed`，旧放行不再生效。**归档时报告仍损坏**不在兜底范围——如实说，不要承诺。

## 6. `quote` 怎么采集

- 让本人写一句能指回**这份证据风险**的原话；不要代写、不要润色成"已确认无误"。
- `by` 写 `human:<来源>`，`at` 写实际时间，`source` 写 `user-declared`（声明式，无签名）。
- 采集完把整条决定文件**原样**保存，用 `--file` 提交；不要手工改任务记录。

## 纪律

- 身份只在请求信封里：不读环境变量、不从命令行或文件猜身份；信封缺失就报 `WF_IDENTITY_UNRESOLVED`。
- 不代人作答、不代跑终端确认与令牌；人的决定只经 `--file` / `--decision` 文件承载。
- 入口输出的 `tier` / `code` / `facts` / `next` 是唯一判定源；不自行改写状态或补写门禁结论。
- 命令形如 `<python> <项目根>/.wf/bin/wf.py <子命令>`。`<python>` 按此顺序取，**取到能跑的就整会话固定复用**：
  ① `.wf/project-config.json` 的 `python_executable`（未设置再读 `~/.wf/config.json` 同名键，可直接读文件取值，不必先执行）；
  ② 你自身运行时的 Python 可执行文件；
  ③ 系统 `python3`。
  若宿主执行策略要求审批或不在白名单（`WF_EXECUTOR_UNCONFIRMED` / 审批拒绝），改用策略允许的已核实 Python 绝对路径并固定下来；
  **不要每条命令换解释器**，也不要因为被拒就改成手写信封或换路径重试同一效果。不装 PATH、不做 shell shim。
