# 提案（v7）：⑥ 只做「结构化未结事实」+ 文档裁定

> 状态：**待审 v7**（第六轮修正）。前六版形态均被否；本版补：缺行、报告不可读的真实出口、
> 只读门禁查询替代"试归档"、`--short` 旧字段冲突、`state` 与优先级表脱节、静态降级、归档边界。
> 本文件是决策提案，实现未开始。

---

## 0. 六轮审查的净结论

| 版本 | 形态 | 致命点 |
|---|---|---|
| v1 | 派生"修复中"+自称收敛 6 处判断 | 六处是六个命题；覆盖不到内容变化；改 v42 原文破坏冻结核查 |
| v2 | 派生"不可结案原因集合" | 与退出条件自相矛盾；五态装不下；review 原因不全；`no_check` 矫枉过正 |
| v3 | 新增 `fixing` 阶段 | 身份矛盾；漏 `PHASE_VALUES`/`legal_positions`；pass 落 check 逼出重复 check |
| v4 | 事件写入 `repair` 标记 | 主路径清不掉；两失败源共用槽位；撞名 `repair.py`；无时间戳 |
| v5 | 两行只读事实 | 缺结论绑定；"轻量=未要求"遮住 blocking；"出口见 next"不成立 |
| v6 | 结构化 `unresolved` | **缺"复杂任务从未审查"行**；报告不可读的出口执行不通；用"试归档"解释冲突会先产生提交副作用；`--short` 旧 `check` 字段与事实并存；`state` 枚举与优先级表脱节；降级触发含糊；归档边界丢失 |

**scope**：以上否掉的是**六个具体设计**，不据此断言"机器可读的未结态不可能"。本版保留机器可读形态（§1.1）。

---

## 1. 交付物：一个结构化事实 `unresolved`，挂 `facts.unresolved`

**挂载点（v6 未定）**：任务级命令（`status` 含 `--short`、`gate`、`judgments show`、以及任何返回任务 position 的结果）统一挂在结果 `facts.unresolved`；非任务级结果不挂。

### 1.1 schema

```json
"unresolved": {
  "check": {"usable": false,
            "reason": "archived | no_check | not_passed | invalidated_content_changed | anchor_mismatch | rule_changed | anchor_unavailable | structure_incomplete",
            "check_id": "20261110-A", "scope": "archive_gate", "detail": null},
  "review": {"state": "archived | none_required | not_started | awaiting_reports | imported_not_decided | open_blocking | verdict_fail | verdict_unavailable | invalidated | pass_bound | pass_unbound | reports_unreadable",
             "open_blocking": [], "verdict": null, "verdict_check_id": null, "bound_to_current": null,
             "unreadable": [{"slot": "slot-a", "path": "…", "cause": "changed | missing | unreadable", "round": 2}]},
  "omitted": null
}
```

- `omitted`：静态降级时取 `"cost"`（见 §4），否则 `null`。**v6 未把它写进 schema，本版补上。**
- `state` 与 §1.2 的优先级表**一一对应**（v6 的 `stale_verdict` 已删除——同一事实不再有两套表示）。

### 1.2 取值优先级（9 档，命中即停；**归档是固定第 1 行**）

| # | 条件 | `state` | 显示文本 | 出口提示 |
|---|---|---|---|---|
| 0 | `status == "archived"` | `archived` | `检查/审查：已归档，不再评估` | —— |
| 1 | 当前结论**引用**的报告不可读 | `reports_unreadable` | `审查：第 r 轮引用的 M 份报告不可读（cause）` | **不能原地重新导入**（同路径不同摘要会被拒，见 §3）；需**重发新一轮** |
| 2 | `open_blocking` 非空 | `open_blocking` | `审查：未关闭 blocking N 条（id…）（第 r 轮）` | 按 K4b 由非提出者复核关闭 |
| 3 | `verdict == "fail"`（**无论绑定**） | `verdict_fail` | `审查：第 r 轮判 fail` + 绑定状态后缀 | 先是修复/重查（检查行给出原因），再重发审查 |
| 4 | `verdict == "invalidated"` | `invalidated` | `审查：既有结论已失效（实施 CLI 变更），需重发` | 重发审查 |
| 5 | `verdict == "unavailable"` | `verdict_unavailable` | `审查：不可用（需补真实审查或人确认异常归档）` | 补审查 / 异常归档 |
| 6 | `verdict == "pass"` 且 `bound_to_current == false` | `pass_unbound` | `审查：结论来自旧检查（C1），当前检查未审查` | 检查可用→重发审查；检查不可用→先修复重查（见 §5 顺序） |
| 7 | `verdict == "pass"` 且 `bound_to_current` | `pass_bound` | `审查：已通过（绑定当前检查）` | —— |
| 8 | 有导入报告但未执行 decide | `imported_not_decided` | `审查：已导入 N 份报告，尚未判定` | 执行 `review-decide` |
| 9 | 已发起、报告未到齐 | `awaiting_reports` | `审查：第 r 轮已发起，报告 N/2` | 等报告 / `review-status` |
| 10 | 无任何 reviews，`complexity == "complex"` | `not_started` | `审查：未开始（复杂任务归档前必须审查）` | `review-launch` |
| 11 | 无任何 reviews，非 complex | `none_required` | `审查：未要求` | —— |

**v6 的漏洞在这里被补齐**：第 10 行正是"复杂任务 check 刚过、还没发起审查"——最常见的待审状态（v6 无行命中）；第 8/9 行覆盖"verdict 尚为 null"的两条正常路径（v6 的 `state=none` 没有映射）。

**检查行**：`usable` 决定文案；`reason` 逐值一句人话；`scope: "archive_gate"` 固定——不跨"发起口径"（`review.py:710` 少做结构复核，属另一口径，本提案不合并）。

---

## 2. 数据来源（既有函数，不复制逻辑）

| 事实 | 来源 |
|---|---|
| `check.*` | 把 `gates.py:631-654`（`task.check-passed` 门）整段提取为 `check_usability(ctx, task)`，门禁改为调它（行为一字不改） |
| `review.open_blocking` / `unreadable` | `review.open_findings(ctx, task)`；`unreadable` 需带 `cause`（v6 一律写"被改动"是错的，见 §3） |
| `review.verdict` / `verdict_check_id` / `bound_to_current` | `reviews.result` 与 `result.check_id == (check or {}).id` |
| `imported_not_decided` / `awaiting_reports` | `reviews.imported` 与 `reviews.launches` 的轮次计数（已有字段） |

**两种"检查失效"必须分开**：`invalidated_content_changed` 是记录内事实（受控回 check 时写入 `check.invalidated`）；`anchor_mismatch` 是读取时现场重算。

---

## 3. 报告不可读：真实出口（v6 的"需重新导入"执行不通）

`review.py:1117` 明确拒绝"同路径不同摘要"的导入——**项目内的报告一旦被改写，原地重新导入必然再次 `WF_REVIEW_INVALID`**。因此：

| `cause` | 含义 | 真实出口 |
|---|---|---|
| `changed` | 导入后摘要变化 | **重发新一轮**（新轮次新路径）；不能原地重导 |
| `missing` | 文件不存在 | 从暂存区重取并**发新轮**；或按 `--unavailable` 处置 |
| `unreadable` | 读取失败（权限/IO） | 修复可读性后仍走**新轮**；或 `--unavailable` |

文案按 `cause` 分派，不再统一写"需重新导入"。

**范围限定**：第 1 行只看**当前结论引用的那几份报告**（与 `gates.py:690` 的引用校验同口径）。`open_findings` 会扫**全部历史导入**，旧轮报告被改会让"不可读"永久非空——v6 把它放第 1 位，是"比门禁更宽的判据抢了第一位"。旧轮的报告改动不进入 `state`，只在 `unreadable[].round` 里留痕。

---

## 4. 展示点与成本（数字来自实测，降级条件改为静态）

| 展示点 | 内容 | 成本 |
|---|---|---|
| `wf status` / `--short` | `facts.unresolved` + 两行文本 | 锚点重算 **≈40 ms**（git 为主）+ `open_findings` **<1 ms**（5 份小报告实测 0.1 ms）→ 单次 <50 ms |
| `judgments show` | 两行 | 同上 |
| `wf gate --due before_archive` | 只读门禁断言（已存在，`gates.py:802` `evaluate_cli`） | 同一批判定 |

**静态降级**（替换 v6 的"若实测超出 200 ms"）：当 `len(reviews.imported) > 8` 时，`--short` 的 `facts.unresolved.review` 置 `null` 且 `omitted = "cost"`；**判据是份数，不是运行时计时** —— 同一任务两次调用形状一致（v2 §4.3 的"缺席歧义"不再回归）。

---

## 5. 与 `next` 的关系（撤回"试归档"这种兜底）

v6 用"next 说 archive，但 archive 会拒绝"解释冲突——**这不成立**：`tasks.py:3233` 在 `final_gate` 之前就会执行业务提交（有授权时）并写动作记录，**已明知有 blocking 时试归档会产生副作用**。

**改为明确契约**：

> `unresolved` 是事实；`next` 是位置指引（`states.json` 的 `next_by_position`，**不感知失败事实**）；
> 需要"能不能归档 / 缺什么"的**权威答案**时，用**只读查询** `wf gate --due before_archive`（`gates.evaluate_cli`，不写任何东西），**不要用"试着归档一次"来探路**。
> 三者冲突时以门禁返回的 code + exits 为准。

顺序约定（针对第 6 档文案）：当前检查不可用时，"先修复重查、后重发审查"——检查行给出原因，审查行不给"重发"这种次序错误的指引。

---

## 6. `--short` 的旧字段处理（v6 遗漏的"同对象内互相矛盾"）

`--short` 现有字段 `"check": (task.check).result`（`cli.py:726`）在锚点失配时仍会输出 `"pass"`，与新事实 `unresolved.check.usable == false` 直接矛盾。

**处理**：`--short` 的 `task.check` 字段改为**从 `unresolved.check` 派生**，取值 `usable ? "usable" : reason`（保留"是不是 pass"的信息在 `unresolved.check.usable` 与 `detail` 里）。
这是对该字段的**语义变更**，写进裁定文件与机制稿；不保留旧字段以免两套并存。

---

## 7. ⑥ 的实质处置：文档裁定（v42 不动）

新增 `analysis/ruling-repair-vs-fixing.md`：① 不引入 `fixing` 阶段，维持 2026-11-09 人裁的四阶段；② 五轮/六轮审查证据摘要（§0）；③ 与 v42 K10（L107）/S4（L122）/S5（L123）/§7.1（L401）的差异逐条登记；④ 只记录取舍，不写"单一布尔不可能"这类过度结论。
机制稿 §2.2/§9.4 各加一段：事实展示、`next` 的定位、**只读门禁查询**三个概念的边界。
v42 原文一个字节不改（sha256 `d06c57e7…cadd`）。

---

## 8. 明确不做

| 不做 | 对应审查 |
|---|---|
| 不新增阶段 / 不新增持久标记 / 不新增命令 | v3/v4 |
| 不改 `position` | v2/v4 |
| 不改 `next` 实现（只改契约表述） | 本文 §5 |
| 不在此提案修"错误返回 position 为空" | v4 a-4/b-4，独立缺口 |

---

## 9. 验收标准（11 条，全部可构造）

| # | 断言 | 防的失败 |
|---|---|---|
| 1 | `in_progress` + 无 check → `check.reason == "no_check"` | 把没检查当没问题（限定 in_progress，避免固化 plan 期噪声） |
| 2 | 受控回 check → `reason == "invalidated_content_changed"` | 记录内失效不可见 |
| 3 | execute 期改文件未重查 → `reason == "anchor_mismatch"` | 现场失效不可见（与 #2 不同分支） |
| 4 | 轻量任务 + 已导入 blocking → `state == "open_blocking"`（**不是未要求**） | v5 a-2/b-1 |
| 5 | `verdict=pass` 但 `verdict_check_id != 当前 check` → `state == "pass_unbound"` | v5 a-1 |
| 6 | **复杂任务 + 无任何 reviews → `state == "not_started"`** | **v6 无行命中（最常见待审状态）** |
| 7 | 导入报告但未 decide → `state == "imported_not_decided"`；已发起未到齐 → `awaiting_reports` | verdict=null 的正常路径无显示 |
| 8 | 当前结论引用的报告被改 → `state == "reports_unreadable"` 且 `cause == "changed"`；**旧轮报告被改则 `state` 不变** | v6 第 1 行过宽（比门禁宽） |
| 9 | `status=archived` → `state == "archived"`，且不再显示 blocking | 归档边界（已两次丢失，本版固定为第 0 行） |
| 10 | `unresolved.check.usable` 与 `gates` 判定不一致 → 测试失败（不变量） | 展示与门禁漂移（v6 只在 §8 提，未进验收） |
| 11 | 归档准入与改动前完全一致；`--short` 的 `task.check` 已改为派生值 | 展示被当门禁；旧字段撒谎 |

**计时**：不作为断言（CI 抖动）。改为**手动检查项**：5 份报告任务上 `wf status --short` 单次 < 1 s（数量级门槛），精确值记录在裁定文件里。

---

## 10. 风险与缓解

| 风险 | 缓解 |
|---|---|
| 提取 `check_usability` 动门禁 | 纯提取，先跑全量再改展示；验收 10 的不变量兜底 |
| 第 0–11 档的优先级仍有组合未覆盖 | 优先级表 + `state` 枚举一一对应；新增状态必须同时加行（写进裁定的维护规则） |
| `--short` 语义变更影响既有消费方 | 裁定文件记录；`unresolved.check.usable` 保留原信息 |
| 复杂任务"未开始"行会不会被当阻断 | 只是事实；门禁本来就拦（`gates.py:682`），本提案不新增阻断 |

---

## 11. 留给审查者的问题

1. 第 3 档（`verdict_fail`）不分绑定：旧 check 上的 fail 与当前 check 上的 fail 显示同一句，是否够用？还是也按绑定分两行？
2. `--short` 的 `task.check` 语义变更是否算破坏性变更（有外部消费方的话）？
3. 第 8 档"已导入未判定"与第 9 档"已发起未到齐"的先后：两者可能同时成立（部分 slot 到了），按哪档优先？
4. §4 的静态阈值（>8 份报告降级）是否合适？阈值本身要不要进裁定？
