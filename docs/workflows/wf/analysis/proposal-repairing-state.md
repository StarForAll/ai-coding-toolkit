# 提案（v15）：⑥ 只做「结构化未结事实」+ 一条人裁放行记录 + 文档裁定

> 状态：**待审 v15**（第十四轮修正）。
> 前十二版的形态与致命点见 §0。本文件是决策提案，实现未开始。

---

## 0. 十二轮审查的形态演进与净结论

| 版本 | 形态 | 致命点 |
|---|---|---|
| v1/v2 | 派生事实（"修复中"/"原因集合"） | 派生要复制门禁；定义与退出条件互斥；五态装不下 |
| v3 | 新增 `fixing` 阶段 | 身份矛盾（含 check 的五值 vs v42 无 check）；漏协议硬校验；pass→check 逼出重复 check |
| v4 | 事件写入 `repair` 标记 | 主路径清不掉；两失败源共用槽位；撞名 `repair.py` |
| v5/v6 | 两行 / 结构化 `unresolved` | 缺结论绑定；"未要求"遮住 blocking；缺"复杂未审查"行 |
| v7/v8 | 档位重排 | `gate` 只答步骤面；`pass_unbound` 死区；`invalidated` 死行 |
| v9/v10 | 当前轮优先 + 复用 `review-status` | 从未发起审查无命中路径；判定后证据失效；`round_complete` ≠ 可判定 |
| v11 | 三条自动退出 | **建在不存在的数据上**：`imported` 记录不含 findings（已核实）；且"新轮 pass"可绕开关闭 |
| v12 | 两条出口（重发 / 人裁） | **人裁通道不存在**：`authorize.ACTIONS` 固定五类、存储一键一文件后写覆盖、且无 `--choice` 标志；文档三处残留"三条退出"、版本号混乱 |
| **v14** | 证据身份约束 + 混槽位并列 + 拆档 | 仍漏两处：**发现模式下"已完成未导入"仍报 missing**（暂存文件按 reviewer 名产出，而查询按 s1/s2 找）；验收 4 与 13d 对同一输入断言相反；计数与 attestation 字段不一致；行 8 未标注"重发不解除"；性质测试缺"轮次关系"维度 |
| **v13** | 人裁放行改为独立记录 + 混槽位并列 | **证据可被替换**：删文件后导入同轮同槽位的另一份报告即可顶掉旧证据（既无 disposition 也无人裁放行）；`launches` 实际初始化是 `[]` 而非 `None`（无审查任务会掉进兜底）；行 8 引用 §2 但可读 blocking 的出口断链；性质测试枚举域与 schema 值域不一致 |

**已核实的产品级事实（本轮更正 v11 的引用错误）**

| 事实 | 位置 |
|---|---|
| `reviews.imported[]` **不含 findings**（只有 round/slot/report_path/report_digest/anchor） | `review.py:1131-1144` |
| 提出者只能**重解析报告**得到（已修，commit `7752520`）：`proposers_from_imported` | `review.py:573` |
| `reviews.result` **只保留最新一轮**（旧结果被覆盖） | `review.py:1484` |
| `authorize.ACTIONS` 固定五类；授权按动作一文件、后写覆盖 | `authorize.py:20-26 / 73` |
| `status_of_round` 的槽位可同时是 `stale` 与 `missing`（合法组合） | `review.py:355-390` |

---

## 1. 交付物：`unresolved`（挂 3 处）

挂载：`wf status`（含 `--short`）、`judgments show`、`wf review-status`。
不挂其余任务级命令；**死角**：`task-check` 失败走通用 except 层（`cli.py:2638`），不带 `unresolved`（独立缺口，另案）。

### 1.1 schema

```json
"unresolved": {
  "check": {"usable": false,
            "reason": "archived|no_check|not_passed|invalidated_content_changed|anchor_mismatch|rule_changed|anchor_unavailable|structure_incomplete",
            "check_id": "A", "scope": "archive_gate", "detail": null},
  "review": {"state": "<§1.2 的 15 档之一，或 inconsistent>",
             "round": 2, "launched": 2, "imported": 2, "declared": 2,
             "slots": [{"slot": "s1", "state": "imported|staged|stale|missing|unreadable", "round": 2}],
             "open_blocking": [{"finding_id": "f1", "severity": "blocker", "round": 1}],
             "blocking_unknown": [{"slot": "s1", "path": "…", "report_digest": "sha256:…",
                                   "round": 1, "cause": "changed|missing|unreadable",
                                   "accepted_by": null}],
             "verdict": "pass|fail|unavailable|invalidated|null",
             "verdict_round": 1, "verdict_check_id": "A", "bound_to_current": true},
  "nonstep": {"escalated": 0, "required_unverified": 0, "complexity_unconfirmed": false,
              "dependencies_unmet": [], "debug_unruled": [], "action_incomplete": null,
              "paused": false, "suspended": false}
}
```

`nonstep` 七项全部**记录级只读**（`gates.debug_pending`、`tasks.dependency_blockers`、`plan.confirmed_source`、judgments、`check.acceptance_results`、`task.action`/`paused`/`suspended`），只取事实、不复制门禁分支。

### 1.2 取值优先级（**15 档（0–14）+ 1 条兜底**）

判据：
```
launches     = reviews.launches
active_round = max(launch.round) if launches else None
result       = reviews.result
undecided    = active_round is not None and (result is None or active_round > result.round)
no_launch    = not launches          # 初始化就是 []，不能写 `is None`
slots        = 该轮槽位状态集合（可同时含多种，见 §1.3）
```

| # | 条件 | `state` | 显示 | 候选动作（带前置） |
|---|---|---|---|---|
| 0 | `status == "archived"` | `archived` | 已归档，不再评估 | —— |
| 1 | 结论引用报告不可读 | `reports_unreadable` | 第 r 轮结论引用的 M 份不可读 | 见 §3 |
| 2 | `undecided` 且槽位含 `unreadable` | `reports_unreadable` | 第 N 轮 M 份不可读 | 见 §3 |
| 3 | `undecided` 且槽位含 `staged` | `report_staged` | 第 N 轮有 k 份已产出未导入 | **先导入**（前置：暂存目录在且 agent 标 done）；同时列出其余槽位事实（缺 / 失效） |
| 4 | `undecided` 且槽位含 `missing`（无 `stale`） | `awaiting_reports` | 第 N 轮缺 k 份 | 主：等（前置：仍可联系到该 reviewer）；并列：`--unavailable`（持续等不到时）、先导入 staged（若有） |
| 5 | `undecided` 且槽位含 `stale`（**无论是否另有 missing/staged**） | `reports_stale` | 第 N 轮 k 份锚点失效 | 主：**重发新一轮**（前置：当前检查可用）——stale 槽位使该轮**永远判不了**（`decide` 核锚点即拒）；并列：先导入 staged（若有）、`--unavailable` |
| 6 | `undecided` 且全部 `imported` 且 `declared ≥ 2` | `imported_not_decided` | 第 N 轮到位（i/m） | 执行判定（前置：≥2 份 imported 且锚点一致） |
| 7 | `undecided` 且 `declared == 1` | `degraded_single` | 第 N 轮为单 provider | 补异种 reviewer 重发（前置：可取第二个 CLI）/ `--unavailable` |
| 8 | `blocking` 或未放行的 `blocking_unknown` 非空 | `open_blocking` | 未关闭 blocking N 条；另有 M 份不可核实 | **可读 blocking**：K4b 复核关闭 / 人重分类 / 异常归档；**blocking_unknown**：`review-accept-unknown` 人裁放行（**只有它解除本条**）；"重发该轮"可并行推进工作但**不解除**，归档前仍需放行（见 §2） |
| 9 | `verdict == "fail"` | `verdict_fail` | 第 r 轮判 fail（绑定：当前/旧） | 事实 + 候选（重查 / 重发），顺序由 AI 判断 |
| 10 | `verdict == "unavailable"` | `verdict_unavailable` | 不可用 | 补审查 / 人确认异常归档（**需放弃授权**） |
| 11 | `verdict == "pass"` 且 `bound_to_current` | `pass_bound` | 已通过（绑定当前检查） | —— |
| 12 | `verdict == "pass"` 且 `!bound_to_current` | `pass_unbound` | 结论来自旧检查 | 主：重发（前置：检查可用）；并列：先重查（前置：不可用） |
| 13 | `no_launch` 且 `complexity == "complex"` | `not_started` | 未开始（复杂任务归档前必须审查） | `review-launch` |
| 14 | `no_launch` 且非 complex | `none_required` | 未要求（可按需发起） | —— |
| — | 以上均不命中 | `inconsistent` | 记录组合不自洽（列判据值） | 交人核对；**不得据此归档** |

> 注：第 12 档按 `no_launch` 判定，**先把 12 拆成两档**（见下）：`not_started`（complex）与 `none_required`（其他）各占一档，避免"共用编号 + 隐式优先级"让性质测试的"仅命中一档"出现歧义（第十三轮指出）。

**关键修正**：第 3/4/5 档的条件是"**含**某类槽位"而不是"**只有**某类槽位"——`stale + missing`、`staged + stale` 都是合法组合（实测 `status_of_round` 会返回 `['stale','missing']`）。v12 把它们写成互斥，正常组合会掉进 `inconsistent`，把 AI 本可自处的情形升级成人审。

### 1.2a 槽位发现口径（已实现，第十四轮补）

暂存文件按**实际 reviewer 名**产出（`review-codex.md`、`review-gemini.md`），而声明槽位是 `s1/s2`。
`status_of_round` 现在做两层对应：

1. 已导入记录：按名称匹配，剩余按**位置**分配给未满足的声明槽位；
2. **未认领的发现式暂存文件**（round 目录里 `review-<agent>.md`、既未导入也未被槽位名占用）：按顺序分配给未满足的槽位，标 `staged`。

否则"两份报告已产出且都 done"会显示 `missing=2`，AI 去等一份已经存在的报告（实测）。
回归测试覆盖"未导入但已产出"与"已导入"两种形态。

### 1.3 槽位事实并列（不合并、不排序）

`slots` 字段原样列出每个槽位的状态；**显示层必须把"立即能做的"与"需要等的"并列**：
`第 N 轮：s1 已导入 / s2 失效（需重发）/ s3 已产出未导入（可立即导入）/ s4 缺失（等或改不可用）`。
候选动作按 §1.2 命中的那一档给出**主候选**，同时把其余可执行项并列——不因为优先级把可执行项压掉。

---

## 2. 人裁放行：**用独立记录，不用 `authorize`**（v12 的通道不存在）

v12 写"走既有 K6 授权通道"，实测三处都不成立：`ACTIONS` 固定五类（无 `review_unknown_accept`）、命令无 `--choice` 标志、授权**按动作一文件后写覆盖**（两份放行会互相覆盖）。因此改为**专用记录**：

### 2.1 记录形状（`reviews.unknown_acceptances[]`，逐报告、绑定摘要）

```json
{"round": 1, "slot": "s1", "path": "review/…/s1.md", "report_digest": "sha256:…",
 "cause": "changed", "at": "…", "by": "human:xzc", "quote": "…",
 "source": "user-declared", "attestation_digest": "sha256:…"}
```

- **必须绑定 `report_digest`**：同位置重新导入内容不同的报告会换摘要 → 旧放行**自动失效**（v12 只绑 round/slot/path，可被后续同位置报告复用）；
- 写入走**已实现的人通道** `wflib/attestation.py`（乙口径：`by/at/quote/source` + 摘要入库），与 `sampling confirm` / `judgments add --attestation` 同一套；
- 新命令：`wf review-accept-unknown --task <id> --file <确认.json>`（写入上面这条记录，需持写权）。

### 2.2 阻断与解除

| 环节 | 行为 |
|---|---|
| 阻断 | `open_findings` 增出 `blocking_unknown`；`final_gate` 在其**未放行**条目非空时阻断（`WF_REVIEW_INVALID`） |
| 放行 | 存在与 `(round, slot, report_digest)` **三者全等**的 acceptance → 该条降级为留痕，不再阻断 |
| 不放行 | **新轮 pass 与 `--unavailable` 都不解除**（第十一轮否掉的理由：前者绕开关闭、后者只证明做不成审查） |
| 显示 | `blocking_unknown[].accepted_by` 为 null 表示未放行；放行的在显示里标"已由人放行（quote 摘要）" |

### 2.3 前置机制约束：导入端必须保证**证据身份不可替换**

实测漏洞：删掉某轮某槽位的报告后，导入一份"同轮、同槽位、同锚点但内容不同（不含原来的 blocking finding）"的报告，
入口返回 `WF_OK` 并覆盖该槽位的导入摘要 → `blocking` 与 `unreadable` 同时清零，**既无 disposition 也无人裁放行**。
放行记录管不到这一步：此时不是"旧放行被复用"，而是**旧证据被替换**。

修法（机制侧，已实现）：`import_report` 在写入前查"该轮该槽位是否已有导入记录"，
**已有则只允许幂等重入（摘要相同）**；摘要不同即拒，出口两条：另开新一轮 / `--unavailable` 留痕后由人处置。
这条约束把它从"AI 指引能否遵守"升级为"机械不可能"。

**为什么不再试图自动判定**：`reviews.result` 只保留最新一轮（`review.py:1484`），历史每轮 verdict 与其 check 绑定**不可重建**；"新证据是否足以承接旧问题"是判断，不是比较。解除必须有人签字，且签字绑定到具体那份证据。

---

## 3. `cause` 与健壮性

| `cause` | 出口 |
|---|---|
| `changed` | 重发新一轮（同路径不同摘要被拒，`review.py:1117`） |
| `missing` | 取回原始字节后重导（前置：`check-anchor` 一致且暂存目录在）；否则新轮 / `--unavailable` |
| `unreadable` | 恢复可读后重导；否则新轮 / `--unavailable` |

健壮性：`open_findings` 与 `status_of_round` 都在函数内直接算摘要，而 `records.file_digest` 只捕获 `FileNotFoundError`（`records.py:62`）→ 权限不足会 `PermissionError` 冲出查询入口。两处统一 `except OSError` 并归入 `unreadable`。

---

## 4. 只读门禁：不重构 `final_gate`

- `evaluate_cli` **保持原样**（步骤面只读预检，输出结构不变）；
- 非步骤阻断由 `unresolved.nonstep`（七类）提供；
- **契约**：`wf gate --due before_archive` 是**步骤面**预检；非步骤阻断见 `unresolved`；两者**并读**才是归档前的完整依据；**gate 通过 ≠ 归档必成**（归档内还有 `repo_rules`/`delete` 确认、业务提交先于门禁）；**不要用"试归档"探路**（`tasks.py:3233` 会先做业务提交）。

---

## 5. 候选动作：唯一来源是 §1.2

本节**不再重复列一遍候选**（v12 在 §1.2 与 §5 各写一份且不一致，是本次被判的硬伤）。候选动作与前置事实只在 §1.2 表里定义，别处一律引用该表。

唯一需要单独强调的规则：

> 候选必须带**前置事实**（"重发（前置：当前检查可用）"），不得写成命令序列；多条候选并存时**并列列出**，由 AI 按当前进展选择顺序。

---

## 6. 技能层衔接

| 技能 | 加一行 |
|---|---|
| `wf-finish` | ① 读 `unresolved`（非步骤事实）有则先处理；② 仍跑 `wf gate --due before_archive`，步骤缺项按**封闭规则**：**除 `changes-persisted` 外全部算前置**（`changes-persisted` 由收工动作本身完成；`check-passed` 的失效事实已由 `unresolved.check` 覆盖） |
| `wf-continue` | `in_progress/finish` 路由前先看 `unresolved`；有未结事实先处理，不直接引导收工 |

---

## 7. ⑥ 的实质处置：文档裁定（v42 不动）

新增 `analysis/ruling-repair-vs-fixing.md`：不引入 `fixing` 阶段（维持 2026-11-09 人裁）；**十五轮**审查证据摘要（§0 表）；与 v42 K10（L107）/S4（L122）/S5（L123）/§7.1（L401）差异逐条登记；记录两处语义压缩（`--short` 的 `task.check` 压成 `usable/reason`；`unresolved` 只报事实不报"能否结案"）；登记 §2 的放行记录与其绑定规则。

---

## 8. 影响面（含新增命令与记录字段）

| 项 | 数量 |
|---|---|
| 机制修补（K 级） | 2（① `blocking_unknown` + 放行记录 + `final_gate` 阻断；② **导入端证据身份约束**——已实现并回归） |
| **新增命令** | 1（`wf review-accept-unknown`，走既有 attestation 通道） |
| **任务记录新增字段** | 1（`reviews.unknown_acceptances[]`，逐报告 + 摘要绑定） |
| `open_findings` / `status_of_round` 结构化 + OSError 健壮 | 2 处 |
| 提取共享函数 | 1（`check_usability`） |
| `unresolved.nonstep` 七类事实 | 1 处（记录级读取） |
| 展示点 | 3 |
| skill 文本 | 2 |
| 协议码表 / `final_gate` 结构 / `authorize.ACTIONS` | **0** |
| 测试 | **20 项**（§9：1–17 + 13b/13c/13d） |
| 已完成（前几轮）：K4b 关闭链修复、`status_of_round` 发现模式槽位对应 | 见 commits `7752520` / `d6266c4` |

---

## 9. 验收标准（20 项：1–17 + 13b/13c/13d）

| # | 断言 |
|---|---|
| 1 | 无 check → `no_check`；受控失效 → `invalidated_content_changed`；execute 期改文件 → `anchor_mismatch` |
| 2 | 无 `launches` 的复杂任务 → `not_started`；非 complex → `none_required` |
| 3 | 判定完成后引用报告被改 → `reports_unreadable`（不是 `pass_bound`） |
| 4 | （已合并进 13d；原"命中 `awaiting_reports`"与行 5 的"含 stale 即 `reports_stale`"矛盾，按行 5 为准） |
| 5 | **`staged + missing` 混合 → 命中第 3 档（`report_staged`），候选含"先导入已产出"与"等/改不可用"并列** |
| 6 | `staged` 单槽位 → `report_staged`；`missing` 单槽位 → `awaiting_reports` 且带 `--unavailable` 逃逸 |
| 7 | `stale` 单槽位 → `reports_stale` 且候选是"重发"，不是"继续等" |
| 8 | 发现模式（真实 reviewer 名）两份报告已导入 → `status_of_round` 不报 missing；第 6 档命中 |
| 9 | 单 provider 轮 → `degraded_single` |
| 10 | 已判定 pass 绑定 C1 → 改码重查 → `pass_unbound` |
| 11 | 旧轮 blocking 未关、新轮 pass → 仍 `open_blocking` |
| 12 | 删掉带 blocking 的旧轮报告 → `blocking_unknown` 非空且归档被拒；**新轮 pass 与 `--unavailable` 都不解除** |
| 13 | **`review-accept-unknown` 写入记录后该条降级并放行；同位置重新导入**内容不同**的报告（摘要变化）→ 旧放行失效、重新阻断** |
| 13b | **删掉某轮槽位报告后导入"同轮同槽位、内容不同"的报告 → 被拒（证据身份不可替换），出口两条** |
| 13c | **`reviews.launches == []` 的任务 → `not_started`/`none_required`，不得落 `inconsistent`** |
| 13d | **`stale + missing` 混合 → 落 `reports_stale`、主候选是"重发新一轮"（"等"降为并列），且 `slots` 并列显示两种事实、不得落 `inconsistent`** |
| 14 | 两份不同报告的放行记录**并存**（不互相覆盖） |
| 15 | 权限不足（`PermissionError`）不再让 `status`/`review-status` 崩溃，归入 `unreadable` |
| 16 | `wf gate` 输出结构未变；`unresolved.nonstep` 七类齐全 |
| 17 | **性质测试**：枚举域**与 schema 值域严格一致**——`launches` 有无（falsy 判定）× **轮次关系四值**（无 result / result 落后于 active / 相等 / 超前）× 槽位**五值**（`imported/staged/stale/missing/unreadable`）的**所有子集** × `blocking` 有无 × 未放行 `blocking_unknown` 有无 × `verdict` **五值（含 null 与 invalidated）** × `bound_to_current` × `complexity`；断言**合法组合必命中非兜底档**、仅**真不自洽**（如 `verdict=invalidated` 且 `active==result`）落 `inconsistent`；"一档"按 `state` 口径（编号已不共用） |

---

## 10. 留给审查者的问题

1. §2 的放行记录要求人签一次/每份不可读报告；若同时有 3 份不可读，是否允许**一次确认覆盖多份**（决定文件里写多条）？
2. 第 8 档把 `blocking`（可关闭）与 `blocking_unknown`（只能重发/人裁放行）合档但出口分列——是否该拆两档？
3. `unresolved.nonstep` 复述了 `final_gate` 一半事实，算"该定死的口径"还是"复制门禁"？
4. `wf-review` 是否也需"先读 unresolved"的接入？`wf-finish` 的封闭规则（除 changes-persisted 外全算前置）是否要写进 `wf-continue`？
