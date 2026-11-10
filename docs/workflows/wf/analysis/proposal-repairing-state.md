# 提案（v9）：⑥ 只做「结构化未结事实」+ 只读门禁两层对齐 + 文档裁定

> 状态：**待审 v9**（第八轮修正）。前八版形态均被否；本版修：`pass_unbound` 死区、
> `invalidated` 死行、`open_blocking` 的跨轮口径、报告可读性前置、`gate` 两层一次返回、档数。
> 本文件是决策提案，实现未开始。

---

## 0. 八轮审查的净结论

| 版本 | 形态 | 致命点 |
|---|---|---|
| v1/v2 | 派生事实 | 派生必须复制门禁；定义与退出条件互斥；五态装不下 |
| v3 | 新增 `fixing` 阶段 | 身份矛盾；漏协议硬校验；pass→check 逼出重复 check |
| v4 | 事件写入 `repair` 标记 | 主路径清不掉；两失败源共用槽位；撞名 `repair.py`；无时间戳 |
| v5 | 两行只读事实 | 缺结论绑定；"未要求"遮住 blocking；"出口见 next"不成立 |
| v6 | 结构化 `unresolved` | 缺"复杂从未审查"行；报告不可读出口执行不通；试归档有副作用 |
| v7 | 12 档 + `gate` 契约 | `gate` 只答步骤面；旧结论排在新轮进度前；按份数删信息 |
| v8 | 当前轮分桶重排 | **`pass_unbound` 落入死区（无行命中）**；`invalidated` 行不可达；行 4 的"当前轮"限定与数据源/门禁都不符；报告可读性排在判定提示之后；`gate` 逐层揭示未声明 |

**scope**：否掉的是八个具体设计，不断言"机器可读的未结态不可能"。

---

## 1. 交付物：结构化事实 `unresolved`

### 1.1 挂载点（只 4 处）

`wf status`（含 `--short`）、`wf gate --due before_archive`、`judgments show`。其余任务级命令不挂。
**死角如实声明**：`task-check` 失败走通用 except 层（`cli.py:2638`），不携带 `unresolved`；修它属独立缺口（另案），替代路径是 `wf status --short`。

### 1.2 schema

```json
"unresolved": {
  "check": {"usable": false,
            "reason": "archived|no_check|not_passed|invalidated_content_changed|anchor_mismatch|rule_changed|anchor_unavailable|structure_incomplete",
            "check_id": "A", "scope": "archive_gate", "detail": null},
  "review": {"state": "<下表 11 档之一>",
             "round": 2, "launched": 2, "imported": 2, "required": 2,
             "open_blocking": [], "verdict": "pass|fail|unavailable|invalidated|null",
             "verdict_round": 1, "verdict_check_id": "A", "bound_to_current": true,
             "verdict_invalidated": false,
             "unreadable": [{"slot": "slot-a", "path": "…", "cause": "changed|missing|unreadable", "round": 2}]}
}
```

### 1.3 取值优先级（**11 档（0–10），含固定归档行**；命中即停）

判据写死（v8 的死区根因就在这里）：

- `active_round` = `max(launches.round)`；`result` = `reviews.result`
- **`undecided`** = `result` 为空 **或** `active_round > result.round`
- **`round_complete`** = 该轮已导入 slot 数 ≥ 该轮声明 slot 数 **且** 该轮无 `unreadable` 报告

| # | 条件 | `state` | 显示 | 出口 |
|---|---|---|---|---|
| 0 | `status == "archived"` | `archived` | 已归档，不再评估 | —— |
| 1 | `undecided` 且该轮有不可读报告 | `reports_unreadable` | 第 N 轮 M 份报告不可读（cause） | 见 §3（cause 决定能否原地重导） |
| 2 | `undecided` 且 `!round_complete` | `awaiting_reports` | 第 N 轮已发起，报告 i/m | 等报告 / `review-status`（**不要**现在 decide） |
| 3 | `undecided` 且 `round_complete` | `imported_not_decided` | 第 N 轮报告齐（i/m），尚未判定 | `review-decide` |
| 4 | **`open_blocking` 非空（跨轮聚合）** | `open_blocking` | 未关闭 blocking N 条（id，含旧轮） | 按 K4b 由非提出者复核关闭 |
| 5 | `verdict == "fail"` | `verdict_fail` | 第 r 轮判 fail（后缀：绑定当前检查 / 旧检查） | 先修复重查，再重发审查 |
| 6 | `verdict == "unavailable"` | `verdict_unavailable` | 不可用 | 补真实审查 / 人确认异常归档 |
| 7 | `verdict == "pass"` 且 `bound_to_current` | `pass_bound` | 已通过（绑定当前检查） | —— |
| 8 | **`verdict == "pass"` 且 `!bound_to_current`** | `pass_unbound` | 结论来自旧检查（C1），当前检查未审查 | 检查可用→重发审查；不可用→先修复重查 |
| 9 | 无任何 reviews，`complexity == "complex"` | `not_started` | 未开始（复杂任务归档前必须审查） | `review-launch` |
| 10 | 无任何 reviews，非 complex | `none_required` | 未要求 | —— |

**三处修正对应三条审查意见**：

1. **第 8 档去掉"无当前轮"限定**。`pass_unbound` 的本质是"`verdict==pass` 且未绑定当前 check"，与"有没有当前轮"无关。v8 把它塞进"无当前轮"桶 → 改码重查后（已判定轮就是 active_round）12 行全部不命中，而验收 6 又断言它（表与验收自相矛盾）。现在第 8 档无条件可命中。
2. **`invalidated` 不再单列一行**（v8 的行 8 不可达：`verdict=invalidated` 只在新一轮 launch 时写入，那一刻 `active_round > result.round` 必然成立，第 1–3 档必先命中）。改为**后缀标记** `verdict_invalidated`，叠在胜出的那一档上显示"（旧结论已失效，需重发）"。档数因此从 12 行变 11 行（0–10）。
3. **第 4 档去掉"当前轮"限定**：`open_blocking` 的唯一来源 `open_findings()` 是**全轮聚合**（遍历全部 `imported` + 跨轮 dispositions），`final_gate` 拦的也是这个聚合（`gates.py:903`）。若按字面过滤到当前轮，**旧轮未关闭的 blocking 会从显示消失而门禁照拦**——正是 v1 的病灶。第 4 档条件就是"`open_blocking` 非空"。

---

## 2. 数据来源（既有函数，不复制逻辑）

| 事实 | 来源 |
|---|---|
| `check.*` | `gates.py:631-654` 整段提取为 `check_usability(ctx, task)`，门禁改调它（行为不变） |
| `review.open_blocking` / `unreadable` | `review.open_findings(ctx, task)`（聚合全轮；`unreadable` 带 `cause`） |
| 轮次进度 | `reviews.launches` / `reviews.imported` / `reviews.result` |
| `bound_to_current` | `result.check_id == (check or {}).id` |

---

## 3. 报告不可读：按 `cause` 给真实短路径

| `cause` | 能否原地恢复 | 出口 |
|---|---|---|
| `changed` | 不能（`review.py:1117` 拒绝同路径不同摘要） | 重发**新一轮** |
| `missing` | 能（`existing_digest` 为空时导入放行重写，`review.py:1123-1125`） | 取回原始字节后**原地重导**；拿不到则 `--unavailable` |
| `unreadable` | 能（摘要未变即可） | 恢复可读后原地重导；仍不可读则 `--unavailable` |

**第 1 档必须排在判定提示之前**（v8 把它排在第 3 位之后）：两份报告已导入、判定前其中一份被删/改 → 导入计数仍满足"报告齐"，会一直提示 `review-decide`，而判定必然拒绝且不写结论 → 死循环。`round_complete` 现在把"该轮无不可读报告"纳入判据，从根上消掉这个循环。

---

## 4. 只读门禁：**两层一次返回**（不再逐层揭示）

实测两处事实：

- `evaluate_cli`（`gates.py:802`）只调 `evaluate(...)`（步骤面 10 步）；`final_gate`（`gates.py:863`）另加：未关闭 blocking（轻量任务步骤直接跳过这条）、escalated、required 未核实、复杂确认、依赖、debug 倍数、暂停/挂起/动作未完成；`final_gate` 经核实**纯只读**。
- `task.changes-persisted` 步骤在**业务变更未提交时返回缺项**（`tasks.py:1012`：即使有提交授权也返回 `WF_WIP_UNRESOLVED`）→ 若"步骤面无缺项才追加非步骤条件"，**escalated/blocking 这类阻断要等提交完才暴露**，"提交前发现"的收益落空。

**修法**：
1. 把 `final_gate` 的非步骤部分提取为 `final_gate_nonstep(ctx, task)`（纯只读），`final_gate` 与 `evaluate_cli` 共用；
2. `evaluate_cli` 在 `due == "before_archive"` 时**同时**返回两层：`missing`（步骤缺项）+ `nonstep`（非步骤阻断），一次给全。

**契约（写进裁定与机制稿）**：

> `unresolved` 是事实；`next` 是位置指引（不感知失败事实）；"能不能归档"的权威答案是
> `wf gate --due before_archive`——它**一次返回两层**（步骤面 + 非步骤条件）；
> 冲突时以门禁 code + exits 为准；**不要用"试归档"探路**（`tasks.py:3233` 会先做业务提交）。

文档同步多一项：`gate` 在 `before_archive` 下语义变化（从步骤面扩为两层）。

---

## 5. 成本（实测）与"不做"

| 点 | 成本 |
|---|---|
| `status` / `--short` / `judgments show` / `gate --due before_archive` | 锚点重算 **≈40 ms**（git 为主）+ `open_findings` **<1 ms**（5 份小报告 0.1 ms）→ 单次 **<50 ms** |

**不做**：按报告份数省略（v7 的 `>8` 已删）；`omitted` 字段（已删）；挂载面扩张（v7 已撤回）。
若报告体量成为瓶颈，按"总字节 + 实测"另立提案。

---

## 6. `--short` 的旧字段

`--short` 现有 `"check": task.check.result`（`cli.py:726`）在锚点失配时仍输出 `"pass"` → 改为从 `unresolved.check` 派生（`usable ? "usable" : reason`），不保留旧字段；属该字段语义变更，写进裁定。

---

## 7. ⑥ 的实质处置：文档裁定（v42 不动）

新增 `analysis/ruling-repair-vs-fixing.md`：① 不引入 `fixing` 阶段，维持 2026-11-09 人裁；② 八轮审查证据摘要（§0）；③ 与 v42 K10（L107）/S4（L122）/S5（L123）/§7.1（L401）差异逐条登记；④ 只记录取舍。机制稿 §2.2/§9.4 加段：事实展示、`next` 定位、**两层只读门禁**三者边界。
v42 原文一字不改（sha256 `d06c57e7…cadd`）。

---

## 8. 影响面

| 项 | 数量 |
|---|---|
| 提取共享函数 | 2（`check_usability`、`final_gate_nonstep`） |
| `evaluate_cli` 两层返回 | 1 处 |
| 展示点 | 3 |
| 协议 / 门禁判定 / 模板 / position | **0** |
| 测试 | 11 条（§9） |
| 文档 | 1 份裁定 + 机制稿 2 段（含 `gate` 语义变化） |

---

## 9. 验收标准（11 条）

| # | 断言 | 防的失败 |
|---|---|---|
| 1 | `in_progress` + 无 check → `reason == "no_check"` | 把没检查当没问题 |
| 2 | 受控回 check → `invalidated_content_changed`；execute 期改文件未重查 → `anchor_mismatch`（分开构造） | 两种失效混淆 |
| 3 | 轻量任务 + 已导入 blocking → `state == "open_blocking"` | "未要求"遮住 blocking |
| 4 | 复杂任务 + 无 reviews → `not_started` | 无行命中 |
| 5 | 1/2 报告到达 → `awaiting_reports`；2/2 到达未判 → `imported_not_decided`；**decide 判 invalid 后仍为 `imported_not_decided`**（轮次比较） | 提示注定失败的 decide |
| 6 | 已判定 pass 绑定 C1 → 改码重查产生 C2（未发起新轮）→ **`state == "pass_unbound"`** | **v8 的 12 行全不命中（死区）** |
| 7 | 第 1 轮 blocking 未关闭、第 2 轮 pass 且绑定 → **仍为 `open_blocking`**（不得进 `pass_bound`） | 跨轮聚合被"当前轮"限定漏掉 |
| 8 | 2/2 报告已导入但其中一份被改 → **`reports_unreadable`**（不是 `imported_not_decided`） | v8 的判定提示死循环 |
| 9 | 换实施 CLI 后 → 胜出档带 `verdict_invalidated == true` 后缀（不再有独立的 `invalidated` 档） | v8 的死行 |
| 10 | **同时存在未提交变更与 escalated 待答时，`wf gate --due before_archive` 一次返回两层**（`missing` 与 `nonstep` 都非空） | 逐层揭示把阻断推后到提交之后 |
| 11 | 归档准入与改动前完全一致；`archived` 时 `state == "archived"`；`usable` 与 `gates` 判定不一致即失败（不变量）；`--short` 的 `task.check` 已派生 | 展示被当门禁 / 旧字段撒谎 / 归档边界 |

计时：手动检查项（5 份报告下 `status --short` < 1 s），不作断言。

---

## 10. 留给审查者的问题

1. 第 4 档（`open_blocking` 聚合）排在第 5 档（`verdict_fail`）之前：fail 结论但 blocking 已全部关闭时走第 5 档、显示"判 fail"，此时正确动作是重发审查——这句措辞够不够？
2. 第 1 档用 `unreadable` 判定"报告不可读"，但 `open_findings` 的 `unavailable` 还包含"报告路径不可读"以外的情况（例如 slot 记录缺失）——是否都要进第 1 档？
3. §4 让 `evaluate_cli` 一次返回两层，会让 `wf gate` 的输出结构变化（新增 `nonstep`）。既有消费方（若有脚本解析 `missing`）是否需要兼容期？
4. 第 9/10 档用 `complexity` 判断"是否需要审查"；轻量任务被人为发起审查但尚无 reviews 时显示"未要求"，是否该改成"未发起（可按需发起）"？
