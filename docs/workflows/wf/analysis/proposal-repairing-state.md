# 提案（v11）：⑥ 只做「结构化未结事实」+ 复用既有只读查询 + 一处机制修补

> 状态：**待审 v11**（第十轮修正）。修：收工前置的循环依赖、`blocking_unknown` 无退出路径、
> `review-status` 的真实能力边界、`stale` 单独成档、非步骤阻断覆盖不全、行 5 出口悬空、
> schema 缺失、`invalidated` 死分支、性质测试缺兜底行、误伤面。
> 本文件是决策提案，实现未开始。

---

## 0. 关键事实（本轮重新核实，全部有代码位置）

| 事实 | 位置 |
|---|---|
| `changes_persisted_fact` 在业务文件未提交时返回缺项，**即使已有授权**（`WF_WIP_UNRESOLVED`） | `tasks.py:1012` |
| **`imported` 条目不含 findings**（只有 round/slot/report_path/report_digest/anchor） | `review.py:1131-1144`（本轮更正 v11 的错误引用） |
| 提出者只能**重解析报告**得到（已修，见 commit 7752520）；报告不可读时给出"无法核对"而非"不存在" | `review.py:573` `proposers_from_imported` |
| `dependency_blockers(root, task)` 只读任务记录 | `tasks.py:2990` |
| `debug_pending(task, threshold)` 只读任务记录（`execution.debug_declarations` + `check_history`） | `gates.py:166` |
| `status_of_round` 的 `stale` 不计入 `arrived`；单 provider 轮 `required:1, arrived:1` 看起来"齐"；函数内直接算摘要（`PermissionError` 会冲出） | `review.py:359/385` |
| `verdict=invalidated` **只在 launch 时写入** → 那一刻 `active_round > result.round` 必然成立 | `review.py:767` |

---

## 1. 交付物：`unresolved`（挂 3 处）

挂载：`wf status`（含 `--short`）、`judgments show`、`wf review-status`（补片段）。
不挂其余任务级命令；**死角**：`task-check` 失败走通用 except 层，不带 `unresolved`（独立缺口，另案）。

### 1.1 schema（**随版本重述**）

```json
"unresolved": {
  "check": {"usable": false,
            "reason": "archived|no_check|not_passed|invalidated_content_changed|anchor_mismatch|rule_changed|anchor_unavailable|structure_incomplete",
            "check_id": "A", "scope": "archive_gate", "detail": null},
  "review": {"state": "<下表 13 档之一，或兜底的 inconsistent>",
             "round": 2, "launched": 2, "imported": 2, "declared": 2,
             "slots_missing": [], "slots_staged": [], "slots_stale": [], "slots_unreadable": [],
             "single_provider": false,
             "open_blocking": [{"finding_id": "f1", "severity": "blocker", "round": 1}],
             "blocking_unknown": [{"slot": "a", "path": "…", "round": 1, "cause": "changed|missing|unreadable",
                                   "recorded_findings": ["f1"], "all_closed": false}],
             "verdict": "pass|fail|unavailable|invalidated|null",
             "verdict_round": 1, "verdict_check_id": "A", "bound_to_current": true,
             "invalidated_superseded": false},
  "nonstep": {"escalated": 0, "required_unverified": 0, "complexity_unconfirmed": false,
              "dependencies_unmet": [], "debug_unruled": [], "action_incomplete": null,
              "paused": false, "suspended": false}
}
```

`nonstep` 七项**全部是记录级只读**（`gates.py:166` 的 debug、`tasks.py:2990` 的依赖、`plan.confirmed_source` 的复杂确认、judgments 的 escalated、`check.acceptance_results` 的 required 未核实、`task.action`/`paused`/`suspended`），**不复制门禁分支**，只是把同一批事实取出来。

### 1.2 取值优先级（**14 档（0–13）+ 1 条兜底行**）

判据：
```
launches     = reviews.launches
active_round = max(launch.round) if launches else None
result       = reviews.result
undecided    = active_round is not None and (result is None or active_round > result.round)
slots        = 该轮 slot 状态（来自 status_of_round：missing / staged / imported / stale）
```

| # | 条件 | `state` | 显示 | 候选动作（**带前置**） |
|---|---|---|---|---|
| 0 | `status == "archived"` | `archived` | 已归档，不再评估 | —— |
| 1 | 结论引用报告不可读 | `reports_unreadable` | 第 r 轮结论引用的 M 份报告不可读 | 见 §3 |
| 2 | `undecided` 且该轮有不可读报告 | `reports_unreadable` | 第 N 轮 M 份报告不可读 | 见 §3 |
| 3 | `undecided` 且存在 `missing` 槽位（无 staged/stale） | `awaiting_reports` | 第 N 轮报告 i/m（缺 k） | 等报告（前置：仍可联系到该 reviewer / 暂存目录仍在）；**永久等不到时 `review-decide --unavailable`（零导入亦可用）** |
| 4 | `undecided` 且存在 `staged` 槽位（无 stale） | `report_staged` | 第 N 轮有 k 份报告已产出未导入 | **执行导入**（前置：暂存目录在且 agent 标 done）；等待不会让它自己变成 imported |
| 5 | `undecided` 且**存在 `stale` 槽位**（无 missing/staged） | `reports_stale` | 第 N 轮报告已到但锚点失效（k 份） | **重发新一轮**（前置：当前检查可用）；不能"继续等" |
| 6 | `undecided` 且全部 `imported` 且 `declared ≥ 2` | `imported_not_decided` | 第 N 轮报告到位（i/m），尚未判定 | 执行判定（前置：≥2 份 imported 且锚点一致） |
| 7 | `undecided` 且 `declared == 1` | `degraded_single` | 第 N 轮为单 provider（退化） | 补第二个异种 reviewer 后重发，或按不可用处置 |
| 8 | `blocking` 或 `blocking_unknown`（未降级）非空 | `open_blocking` | 未关闭 blocking N 条；另有 M 份报告不可核实 | 见 §4（两类**分别**列出口） |
| 9 | `verdict == "fail"` | `verdict_fail` | 第 r 轮判 fail（绑定：当前/旧检查） | 事实 + 候选（重查 / 重发），顺序由 AI 判断 |
| 10 | `verdict == "unavailable"` | `verdict_unavailable` | 不可用 | 补审查 / 人确认异常归档（**需放弃授权**，见 §6） |
| 11 | `verdict == "pass"` 且 `bound_to_current` | `pass_bound` | 已通过（绑定当前检查） | —— |
| 12 | `verdict == "pass"` 且 `!bound_to_current` | `pass_unbound` | 结论来自旧检查，当前检查未审查 | 重发（前置：检查可用）/ 先重查（前置：检查不可用） |
| 13 | 无 `launches` | `not_started`（complex）/ `none_required`（其他） | 见文案 | `review-launch` / —— |
| — | **兜底行**：以上均不命中（脏数据，如 `verdict=invalidated` 且 `active_round == result.round`） | `inconsistent` | 记录组合不自洽（列判据值） | 交人核对记录；**不得据此归档** |

**三处修正**：
- **`stale` 单列（第 5 档）**：`status_of_round` 的 `stale` 不计入 `arrived`，若与 `missing` 合并会显示"继续等"——而 anchor 失效的报告**等不到**任何新报告，正确动作是重发。材料缺失 / 材料失效 / 材料齐是三个不同机械事实。
- **单 provider 单列（第 6 档）**：`status_of_round` 在单 provider 轮返回 `required:1, arrived:1`（看起来齐），但 `decide` 必拒（`review.py:1272`）→ 若落第 5 档会给出注定失败的候选。
- **兜底行 `inconsistent`**：性质测试会立刻打出 `verdict=invalidated` 且 `active_round == result.round` 这类无行命中的组合；没有兜底行，性质测试第一批输入就打回表设计。

`invalidated` 的显示：作为**后缀**叠在第 1–6 档上（这些档的共同点是 `active_round > result.round`，与 `review.py:767` 的写入时机一致）——v10 把条件写成 `active_round is None`，而 invalidated 写入必然伴随新 launch，该分支**永不触发**。

---

## 2. 机制修补：不可读报告不能被当成"没有缺陷"，但**退出只能由人给**

**为什么必须补**：`open_findings` 对不可读报告直接 `continue`（`review.py:184`），其 findings 不计入
`blocking`；`review-passed` 只核结论引用报告；`final_gate` 只在 `blocking` 非空时阻断 →
**删掉带 blocking 的旧轮报告即可归档**（实测可构造）。

**为什么退出只能由人给**（第十一轮把我 v11 的三条自动退出全部否掉，理由已核实）：

| v11 的自动退出 | 被否的理由（我核实属实） |
|---|---|
| ① 被后续 pass 轮取代 | `reviews.result` **只保留最新一轮**（`review.py:1425`），`attempts.outcome` 是尝试级摘要且单调保留 fail，**无法还原"每轮 verdict 与其 check 绑定"** → "`max(pass_round) > unknown.round`" 无数据可算；而且"新轮 pass"并不等于"旧轮的 blocking 已被处置"——它会被用来**绕开关闭** |
| ② `--unavailable` 即降级 | unavailable 只证明"审查做不成"，**不证明缺陷已关闭**；一条 unavailable 解除全部未知 = 又一条绕过路径 |
| ③ 已处置且可核对 | 依据"imported 记录过 findings"**是错的**（记录里没有）；即便将来持久化，也只对**今后**的导入生效，而该场景恰恰是**旧轮**报告已丢 → 对它最需要服务的历史数据永久失效 |

**本版定案**：

1. `open_findings` 增出 `blocking_unknown = [{slot, path, round, cause}]`；
2. `final_gate` 在 `blocking_unknown` 非空时阻断（复用 `WF_REVIEW_INVALID`）；
3. 出口**只有两条**：
   - **重发该轮**（新报告可核对）——但它**不自动解除**旧 unknown，因为"新证据是否足以承接旧问题"是判断不是比较；
   - **人裁留痕**：决定文件里写一条放行记录（`authorize record --choice review_unknown_accept`，走既有 K6 授权通道），
     记录内容含 `round/slot/path/原因/人/quote`；`open_findings` 见该记录即把对应 unknown 降级为留痕。
4. 出口只有两条是**有意的保守**：证据不可核实 ≠ 没有缺陷；解除必须有人签字。

这样 §2 从"造新的判定逻辑"变成"**加一条阻断 + 走既有授权通道**"，与本提案"机制只做事实、判断留人"的定位一致；
F1/F2（记录里没有 findings、关闭链历史数据不可识别）也就不再是阻塞项——它们作为**独立缺口**另案处理（见 §8）。

## 3. `cause` 与健壮性

| 分支 | `cause` | 出口 |
|---|---|---|
| 摘要不一致 | `changed` | 重发新一轮（同路径不同摘要被拒，`review.py:1117`） |
| 文件不存在 | `missing` | 取回原始字节后重导（前置：`check-anchor` 一致且暂存目录在，`review.py:1043/1097`）；否则新轮 / `--unavailable` |
| 读取/O 错误 | `unreadable` | 恢复可读后重导；否则新轮 / `--unavailable` |

健壮性：`records.file_digest` 只捕获 `FileNotFoundError`（`records.py:62`），`open_findings` 与 `status_of_round` **都在函数内直接算摘要** → 权限不足会 `PermissionError` 冲出查询入口。修补：两处统一 `except OSError` 并按 `unreadable` 归类；`status_of_round` 的 slot 状态同步得到 `unreadable` 归类。

---

## 4. 只读门禁：不重构 `final_gate`，把覆盖范围写全

`final_gate` 内部逐项早退、带 `ignore_action_id`（`tasks.py:3239`），提取易丢语义 → **不动它**；`evaluate_cli` 也**保持原样**（步骤面）。

`unresolved.nonstep` 覆盖 `final_gate` 的**全部**非步骤阻断（v10 只列了 4 类，漏了 3 类）：

| 非步骤阻断 | 来源（记录级） |
|---|---|
| 未关闭 blocking / blocking_unknown | `open_findings` |
| escalated 待答 | `judgments` |
| required 验收未核实 | `check.acceptance_results` + 处置记录 |
| **复杂分级未由人确认**（`confirmed_source != "decision"`） | `plan` |
| **依赖未满足** | `tasks.dependency_blockers`（`tasks.py:2990`） |
| **debug 倍数未裁定** | `gates.debug_pending`（`gates.py:166`） |
| 动作未完成 / 暂停 / 挂起 | `task.action`/`paused`/`suspended` |

**契约**：

> `wf gate --due before_archive` = **步骤面**只读预检（结构不变）；
> **非步骤阻断**见 `unresolved.nonstep`（上表七类，全部记录级）；
> 两者**并读**才是归档前的完整依据；**gate 通过 ≠ 归档必成**（归档内还有 `repo_rules`/`delete` 确认、业务提交先于门禁）；
> **不要用"试归档"探路**（`tasks.py:3233` 会先做业务提交）。

---

## 5. 出口写法：事实 + 候选动作（带前置），不写命令序列

原则（v10 已立，v11 落实）：候选动作必须带**前置事实**，否则 AI 会拿到注定失败的候选。

| 档 | 候选（带前置） |
|---|---|
| 3 `awaiting_reports` | 等报告（前置：槽位未产出） |
| 4 `reports_stale` | 重发新一轮（前置：当前检查可用）；**不可"继续等"** |
| 5 `imported_not_decided` | 执行判定（前置：≥2 份 imported 且锚点一致） |
| 6 `degraded_single` | 补异种 reviewer 重发（前置：可取得第二个 CLI）/ 按不可用处置 |
| 7 `open_blocking` | **blocking**：K4b 复核关闭 / 人重分类 / 异常归档；**blocking_unknown**：§2 的三条退出 |
| 8 `verdict_fail` | 事实（结论 fail + 绑定状态）+"重查"或"重发"，前置分别列出 |

异常归档**不是**"人不在场时的合法路径"：`task-abandon` 需要决定文件，且异常退出还要落实改动处置。展示面必须写明**前置：已有覆盖本任务的放弃/替换授权**；没有授权时的出口是**保留未结事实、等待授权**，不是结束任务。

---

## 6. 技能层衔接（并消除循环依赖）

v10 写"status 与 gate 都无阻断再请求收工"——但 `changes_persisted_fact` 在业务文件未提交时必然缺项（即使有授权），而提交授权/业务提交都在**收工动作之内** → 正常场景永远无法请求确认。本版改写：

| 技能 | 加一行 |
|---|---|
| `wf-finish` | ① 读 `wf status` 的 `unresolved`（非步骤事实：blocking/blocking_unknown/escalated/required 未核实/复杂确认/依赖/debug/动作），有则先处理；② **仍要跑 `wf gate --due before_archive`**，其步骤缺项按下列规则处理：`changes-persisted` **不算前置**（由收工动作本身完成）；`sampled`、`knowledge-disposed`、`retrospective-done`、`review-passed`、`spec-loaded` **算前置**，缺则先补 |
| `wf-continue` | `in_progress/finish` 路由前先看 `unresolved`；有未结事实时先处理，不要直接引导收工 |

---

## 7. ⑥ 的处置：文档裁定（v42 不动）

新增 `analysis/ruling-repair-vs-fixing.md`：不引入 `fixing` 阶段（维持 2026-11-09 人裁）；十轮审查证据摘要；与 v42 K10/S4/S5/§7.1 差异逐条登记；记录两处语义压缩（`--short` 的 `task.check` 压成 `usable/reason`；`unresolved` 只报事实不报"能否结案"）；登记 §2 的 K 级修补与其三条退出。

---

## 8. 影响面

| 项 | 数量 |
|---|---|
| 机制修补（K 级） | 1（`blocking_unknown` + 三条退出 + `final_gate` 阻断） |
| `open_findings` / `status_of_round` 结构化与 OSError 健壮 | 2 处 |
| 提取共享函数 | 1（`check_usability`） |
| `unresolved.nonstep` 七类事实 | 1 处（记录级读取，不改门禁） |
| 展示点 | 3 |
| skill 文本 | 2 |
| 协议 / `final_gate` 结构 / 模板 / position | **0** |
| 测试 | 14 条（含性质测试与兜底行，§9） |

---

## 9. 验收标准（14 条）

| # | 断言 |
|---|---|
| 1 | 无 check → `no_check`；受控失效 → `invalidated_content_changed`；execute 期改文件 → `anchor_mismatch` |
| 2 | 无 `launches` 的复杂任务 → `not_started`；非 complex → `none_required` |
| 3 | 判定完成后引用报告被改 → `reports_unreadable`（不是 `pass_bound`） |
| 5 | 报告**缺失** → `awaiting_reports`；报告**锚点失效** → `reports_stale`（两者必须分开） |
| 6 | 单 provider 轮（`declared==1`）→ `degraded_single`（不是 `imported_not_decided`） |
| 7 | 已判定 pass 绑定 C1 → 改码重查 → `pass_unbound` |
| 8 | 旧轮 blocking 未关、新轮 pass → 仍 `open_blocking` |
| 9 | **删掉带 blocking 的旧轮报告 → `blocking_unknown` 非空且归档被拒；新轮 pass 与 `--unavailable` 均**不**自动解除；只有 `authorize record --choice review_unknown_accept`（人裁留痕）后降级并放行** |
| 9b | `staged` 槽位 → `report_staged` 且候选是"执行导入"；`missing` 槽位 → `awaiting_reports` 且带 `--unavailable` 逃逸 |
| 9c | 发现模式（真实 reviewer 名）两份报告已导入 → `status_of_round` 不报 missing；第 6 档可命中 |
| 10 | 权限不足（`PermissionError`）不再让 `status`/`review-status` 崩溃，而归入 `unreadable` |
| 11 | `wf gate` 输出结构未变；`unresolved.nonstep` 七类齐全（含复杂确认/依赖/debug） |
| 12 | 归档准入与改动前一致（除 §2 的修补外）；`archived` → `archived` 档；`usable` 与 `gates` 不一致即失败；`--short` 的 `task.check` 已派生 |
| 13 | 收工流程：业务文件未提交时 `wf-finish` **仍可请求确认**（`changes-persisted` 不算前置） |
| 13b | `verdict=invalidated` 在 `active_round > result.round` 时作为后缀显示；**不再有永不触发的分支** |
| 14 | **性质测试**：对判据全组合（launches 有无 × undecided × slot 状态四值 × blocking/unknown × verdict 四值 × bound × complexity）穷举，断言**必命中且仅命中一档**（兜底行吸收脏组合） |

---

## 10. 留给审查者的问题

1. §2 的三条退出里，② "`--unavailable` 即降级为留痕"是否过宽（一条 unavailable 就解除所有 old-round 未知）？还是只解除该轮？
2. §1.2 第 7 档把 `blocking` 与 `blocking_unknown` 合档但出口分列——是否该直接拆成两档（可关闭 vs 只能重发/留痕）？
3. `unresolved.nonstep` 把 debug/依赖/复杂确认都纳入，等于在 `status` 里复述了 `final_gate` 一半的事实。这算"机制该定死的口径"还是"又复制了一遍门禁"？
4. §6 改 skill 只加两行；是否需要在 `wf-review` 里也加"先读 unresolved"的接入？
