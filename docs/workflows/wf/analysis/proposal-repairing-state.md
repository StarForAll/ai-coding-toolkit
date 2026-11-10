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
| `imported` 条目**记录了 `findings`**（可用于核对"已处置但不可核实"） | `review.py:1163` |
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
             "slots_missing": [], "slots_stale": [], "single_provider": false,
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

### 1.2 取值优先级（**13 档（0–12）+ 1 条兜底行**）

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
| 3 | `undecided` 且存在 `missing`/`staged` 槽位 | `awaiting_reports` | 第 N 轮报告 i/m（缺 k） | 等报告（前置：槽位尚未产出） |
| 4 | `undecided` 且**存在 `stale` 槽位**（无 missing/staged） | `reports_stale` | 第 N 轮报告已到但锚点失效（k 份） | **重发新一轮**（前置：当前检查可用）；不能"继续等" |
| 5 | `undecided` 且全部 `imported` 且 `declared ≥ 2` | `imported_not_decided` | 第 N 轮报告到位（i/m），尚未判定 | 执行判定（前置：≥2 份 imported 且锚点一致） |
| 6 | `undecided` 且 `declared == 1` | `degraded_single` | 第 N 轮为单 provider（退化） | 补第二个异种 reviewer 后重发，或按不可用处置 |
| 7 | `blocking` 或 `blocking_unknown`（未降级）非空 | `open_blocking` | 未关闭 blocking N 条；另有 M 份报告不可核实 | 见 §4（两类**分别**列出口） |
| 8 | `verdict == "fail"` | `verdict_fail` | 第 r 轮判 fail（绑定：当前/旧检查） | 事实 + 候选（重查 / 重发），顺序由 AI 判断 |
| 9 | `verdict == "unavailable"` | `verdict_unavailable` | 不可用 | 补审查 / 人确认异常归档（**需放弃授权**，见 §6） |
| 10 | `verdict == "pass"` 且 `bound_to_current` | `pass_bound` | 已通过（绑定当前检查） | —— |
| 11 | `verdict == "pass"` 且 `!bound_to_current` | `pass_unbound` | 结论来自旧检查，当前检查未审查 | 重发（前置：检查可用）/ 先重查（前置：检查不可用） |
| 12 | 无 `launches` | `not_started`（complex）/ `none_required`（其他） | 见文案 | `review-launch` / —— |
| — | **兜底行**：以上均不命中（脏数据，如 `verdict=invalidated` 且 `active_round == result.round`） | `inconsistent` | 记录组合不自洽（列判据值） | 交人核对记录；**不得据此归档** |

**三处修正**：
- **`stale` 单列（第 4 档）**：`status_of_round` 的 `stale` 不计入 `arrived`，若与 `missing` 合并会显示"继续等"——而 anchor 失效的报告**等不到**任何新报告，正确动作是重发。材料缺失 / 材料失效 / 材料齐是三个不同机械事实。
- **单 provider 单列（第 6 档）**：`status_of_round` 在单 provider 轮返回 `required:1, arrived:1`（看起来齐），但 `decide` 必拒（`review.py:1272`）→ 若落第 5 档会给出注定失败的候选。
- **兜底行 `inconsistent`**：性质测试会立刻打出 `verdict=invalidated` 且 `active_round == result.round` 这类无行命中的组合；没有兜底行，性质测试第一批输入就打回表设计。

`invalidated` 的显示：作为**后缀**叠在第 1–6 档上（这些档的共同点是 `active_round > result.round`，与 `review.py:767` 的写入时机一致）——v10 把条件写成 `active_round is None`，而 invalidated 写入必然伴随新 launch，该分支**永不触发**。

---

## 2. 机制修补：`blocking_unknown` 必须有真正的退出路径

问题：`open_findings` 对不可读报告直接 `continue`（`review.py:184`），其 findings 不计入 `blocking`；`review-passed` 只核结论引用报告；`final_gate` 只在 `blocking` 非空时阻断 → **删掉带 blocking 的旧轮报告即可归档**（逃逸口，实测可构造）。

修补：`open_findings` 增出 `blocking_unknown`；`final_gate` 在其非空时阻断（复用 `WF_REVIEW_INVALID`，exit 三条）。

**v10 的三个出口有两个其实解不开**（第十轮指出）：新一轮只追加记录、不移除旧导入；`--unavailable` 只写判定结果、不处置旧报告。本版给出**三条真实退出**：

| 退出 | 判定规则（全部记录级、可复算） |
|---|---|
| ① 被后续轮次取代 | 若 `max(pass_round) > unknown.round`（该轮结论 pass 且绑定当次 check），则该 unknown **降级为留痕、不再阻断**——更新证据已接管旧证据 |
| ② 声明不可用 | 该轮 `verdict == "unavailable"`（`--unavailable` 留痕）→ 降级为留痕、不阻断；出口是补审查或人确认异常归档 |
| ③ 已处置且可核对 | 报告不可读，但 `imported` 条目**记录过它的 findings**（`review.py:1163`）；若这些 finding id **全部**被 dispositions 以 `accepted` 关闭 → 降级为留痕（"已处置但不可核实"不再强制重发） |

③ 正是"误伤面"的收窄：v10 会把"findings 早已关闭、只是文件没了"也判成必须重发。三者任一成立即不再阻断，阻断时 `blocking_unknown[].all_closed`/`cause`/`round` 都随事实输出，便于人核对。

---

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
| `wf-finish` | 收工前读 `wf status` 的 `unresolved`（**非步骤**事实：blocking / blocking_unknown / escalated / required 未核实 / 复杂确认 / 依赖 / debug / 动作）；有则先处理。**`wf gate` 的 `changes-persisted` 缺项由收工动作本身完成，不作为"请求确认"的前置** |
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
| 4 | 报告**缺失** → `awaiting_reports`；报告**锚点失效** → `reports_stale`（两者必须分开） |
| 5 | 单 provider 轮（`declared==1`）→ `degraded_single`（不是 `imported_not_decided`） |
| 6 | 已判定 pass 绑定 C1 → 改码重查 → `pass_unbound` |
| 7 | 旧轮 blocking 未关、新轮 pass → 仍 `open_blocking` |
| 8 | **删掉带 blocking 的旧轮报告 → `blocking_unknown` 非空且归档被拒；随后（a）新轮 pass（b）`--unavailable`（c）findings 已全关，三者任一 → 降级留痕且可归档** |
| 9 | 权限不足（`PermissionError`）不再让 `status`/`review-status` 崩溃，而归入 `unreadable` |
| 10 | `wf gate` 输出结构未变；`unresolved.nonstep` 七类齐全（含复杂确认/依赖/debug） |
| 11 | 归档准入与改动前一致（除 §2 的修补外）；`archived` → `archived` 档；`usable` 与 `gates` 不一致即失败；`--short` 的 `task.check` 已派生 |
| 12 | 收工流程：业务文件未提交时 `wf-finish` **仍可请求确认**（`changes-persisted` 不算前置） |
| 13 | `verdict=invalidated` 在 `active_round > result.round` 时作为后缀显示；**不再有永不触发的分支** |
| 14 | **性质测试**：对判据全组合（launches 有无 × undecided × slot 状态四值 × blocking/unknown × verdict 四值 × bound × complexity）穷举，断言**必命中且仅命中一档**（兜底行吸收脏组合） |

---

## 10. 留给审查者的问题

1. §2 的三条退出里，② "`--unavailable` 即降级为留痕"是否过宽（一条 unavailable 就解除所有 old-round 未知）？还是只解除该轮？
2. §1.2 第 7 档把 `blocking` 与 `blocking_unknown` 合档但出口分列——是否该直接拆成两档（可关闭 vs 只能重发/留痕）？
3. `unresolved.nonstep` 把 debug/依赖/复杂确认都纳入，等于在 `status` 里复述了 `final_gate` 一半的事实。这算"机制该定死的口径"还是"又复制了一遍门禁"？
4. §6 改 skill 只加两行；是否需要在 `wf-review` 里也加"先读 unresolved"的接入？
