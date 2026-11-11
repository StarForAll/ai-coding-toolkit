# ⑥ 修复态的表达：不新增阶段，用「事实 + 出口」吸收 `fixing` 的收益（v27）

> 状态：**待审 v27**。阶段：**方案审查阶段，实现零改动**（规则见 `.trellis/spec/guides/review-phase-discipline.md`）。
> **本文只回答 ⑥**；范围边界见 §8，被排除的条目登记在 `analysis/backlog-excluded-from-item6.md`。

---

## 1. ⑥ 的问题

v42 要求"审查失败进入修复态"：K10（阶段含 `fixing`）、S4（`fail → fixing`）、S5（`plan → execute → fixing → finish`；
**内容变化或 review 判 fail 进入 `fixing`**；由下一次 `task-check` 退出；**审查失败不再需要 replan/approve**）。

人裁：保留四阶段、`fixing` 不落盘（2026-11-09）；吸收其收益，人裁通道用于"人不在场"（2026-11-11 乙）。

`fixing` 提供三样东西，以及本方案的替代：

| `fixing` 提供 | 替代 |
|---|---|
| ① "在修"的位置 | `findings`（要修什么）+ `applicable`（旧结论是否仍适用于当前内容） |
| ② fail 不强制 replan 的默认 | **指引**（不是机制常量）：fail 不触发 replan；根因在规划时 `task-replan` 仍可用（协议已有 `check/finish → plan`） |
| ③ 修完由下一次 `task-check` 退出 | 事实：`check.valid` 与 `conclusion.binding`；**是否重查由 AI 判断**（轻量任务不因旧结论失效而承担重审义务） |

**S5 的"内容变化"触发**必须可见——但它的判据在 `task.check-passed`，不在 `review-passed`（见 §2.1）。

---

## 2. 机制给什么：三组事实 + 一条人裁记录

### 2.1 `repair_scope`（派生，不落盘；**无单一状态枚举**）

```json
"repair_scope": {
  "findings": [{"round": 1, "slot": "codex", "finding_id": "f1", "severity": "blocker"}],
  "unverifiable": [{"round": 1, "slot": "codex", "path": "…", "report_digest": "sha256:…",
                    "cause": "changed|missing|unreadable", "cited": false, "released": false}],
  "conclusion": {"verdict": "fail", "round": 2, "check_id": "C2",
                 "binding": false,          // ≡ task.review-passed 判据
                 "check_valid": true,       // ≡ task.check-passed 判据
                 "applicable": false,       // = binding && check_valid
                 "blockers": ["binding:cited_report_digest_mismatch"]}
}
```

| 事实 | 判据（**复用既有函数，不另写条件**） |
|---|---|
| `findings` | 门禁用的同一份 `open_findings(...)["blocking"]`（**全轮次**，不做 check 过滤），补 `round/slot` |
| `unverifiable` | **直接来自 `open_findings(...)["unavailable"]`**（唯一来源；其条目须带 `cause/round/report_digest`，见 §6）。`cited` = 该 `(round, slot)` 是否出现在 `reviews.result.imported`；`released` = 存在 `(round, slot, report_digest)` 全等且未撤销的放行 **且** `cited == false` |
| `conclusion.binding` | `task.review-passed` 的判定（`check_id` 相等 **且** 结论引用报告三重摘要一致） |
| `conclusion.check_valid` | `task.check-passed` 的判定（`check.result == pass` 且 `saved anchor == 当前 anchor` 且 `check.invalidated` 为空 且 `rule_version` 相符） |
| `conclusion.applicable` | `binding && check_valid` |

**为什么必须两层**：只复用 `review-passed` 无法发现"内容改了但没重跑 check"——那时 `check_id` 与报告摘要都没变，
`binding` 为 true，而结论对当前内容其实已不适用。内容变化由 `check-passed` 的 anchor 比对发现（`gates.py:639-654`）。
**两层都是既有判定，本文只做合取，不新增条件。**

### 2.2 人裁记录（乙通道）

**记录**：`reviews.unknown_acceptances[]`

```json
{"batch": "b-1", "round": 1, "slot": "codex", "report_digest": "sha256:…",
 "path": "…", "cause": "changed", "quote": "这份报告丢失的风险我认",
 "by": "human:xzc", "at": "…", "source": "user-declared", "attestation_digest": "sha256:…",
 "revoked": false}
```

| 规则 | 语义 |
|---|---|
| 匹配 | `(round, slot, report_digest)` **三者全等**；摘要不同不匹配 |
| 只对**非引用**证据有效 | `cited == true` 不接受放行：它直接支撑当前归档依据，必须重发新一轮 |
| `released` 的封闭性 | 一旦某报告被新结论引用（成为当前轮），它就不再是"旧证据"；旧轮报告不会被未来结论引用，故"已放行后又变 cited"不可达 |
| 批次 | 一次一批、**全有或全无**；任一项不匹配 → 整批拒绝、零写入，返回 `bad_items` |
| 不做预放行 | 指向当前不存在的不可核实项 → 拒绝 |
| 幂等 | 同一键重复放行 → 不新增，回报 `already_accepted` |
| 撤销 | `--revoke --batch`，或 `--revoke --round --slot --digest`（必须带 digest，否则同槽多条时报错列候选）；置 `revoked: true`（不删记录） |
| 信任模型（**定案：不引入签名**） | 沿用 attestation 四件套 + 摘要入库；全仓无签名设施，`authorize`/`attestation` 同级；机制只保证绑定证据、留痕、撤销留痕 |

**命令**：`wf review-accept-unknown --task <id> --file <决定.json>`（含 `--revoke`）。

---

## 3. 五条语义边界

| # | 边界 | 说明 |
|---|---|---|
| **B1** | 可核实性是**当前状态** | 报告恢复（原字节、摘要一致）→ 不再出现在 `unverifiable`。这不是"解除"，是事实变化；人裁只用于**无法恢复**的情形 |
| **B2** | **归档依据必须可核实** | `cited` 报告损坏：**complex** 由既有 `review-passed` 拦（它做三重摘要核对）；**light 由本方案的新增分支拦**（因为 `review-passed` 对 light 任务直接返回满足，见 `gates.py:671-680`）。放行只适用非引用证据 |
| **B3** | fail 不强制 replan，**但不是禁止** | 机制只表达"fail 不自动回 plan"；根因在规划时 `task-replan` 仍合法（代价：原批准失效） |
| **B4** | `unavailable` ≠ 异常归档 | `--unavailable` 只表示审查做不成；`task-abandon` 是不跑最终门禁的终局出口 |
| **B5** | **`findings` 只能由 dispositions 清零** | 代码修复、`task-check`、重审 pass 都**不**清旧轮报告的 blocking：`decide` 的 verdict 由**报告载荷**推导（`review.py:1351`），不读 dispositions，所以同一轮重跑仍是 fail。清除路径只有 K4b：非提出者复核后补 `dispositions(decision=accepted)` |

---

## 4. 出口表（**指引**；给事实与可选动作，不排顺序）

| 事实组合 | 可做的事 | 明确不是 |
|---|---|---|
| `findings` 非空 | 修 → 由**非提出者复核后补 dispositions** 关闭该项（B5，这是唯一清零路径）→（需要时）重查 → 重发审查 | "修完代码 findings 就没了" |
| `findings` 为空，`conclusion.applicable == true` | 按常规推进（归档 / 或人要求的其他动作） | —— |
| `findings` 为空，`verdict == "fail"` 但已全部处置（`binding == true`） | 重发审查（新报告不再携带这些 finding，才会得到新结论） | "重跑同一轮 decide"（仍 fail） |
| `binding == true`、`check_valid == false`（内容已变） | 重跑 `task-check` 产生新 check → 重发审查 | "旧结论仍适用" |
| `binding == false`、`check_valid == true`（check 换代/CLI 变化） | 重发审查；若根因在规划，`task-replan` 可用 | "必须 replan" |
| **light 任务**且只有旧结论失效（findings 空、无未放行 unknown） | **是否重审取决于任务要求**：light 不因"旧结论不能复用"而承担收尾义务 | "必须重发审查" |
| `unverifiable` 有 `cited == false` 且未放行 | 找回原字节 / 人裁放行 / 放弃任务 | "重发新一轮就已解除" |
| `unverifiable` 有 `cited == true` | 重发新一轮（新检查 + 新结论）；人裁放行不适用 | "放行后即可归档" |
| `verdict == "invalidated"` | 完成**已在途**的那一轮（`invalidated` 只在 launch 时写入） | "再发一次审查" |
| 其他组合（含 `phase == "finish"` 但存在上述未结事实） | 按事实逐项处理，处理完再归档 | "位置说归档就可以归档" |

**唯一硬约束**：不要用"试归档"探路（`tasks.py:3233` 会先业务提交）。需要"能不能归档"的只读答案时并读 `wf gate`（步骤面，已只读）与 `repair_scope`。

---

## 5. 与既有机制的关系（不改的东西 + **硬前置依赖**）

| 机制 | 关系 |
|---|---|
| `phase` 枚举 / `protocol/states.json` / `next_by_position` | **不改**；`repair_scope` 不参与 `next` |
| `review-decide` 判定资格、`task-check` 语义 | **不改**；只读它们的结论 |
| `final_gate` 结构 | **只加一条**：存在**未放行的 `unverifiable`（不区分 `cited`）** 时阻断（`WF_REVIEW_INVALID` + `facts.reason = "unverifiable_evidence"`）。`cited` 只影响"能否放行"，不影响"是否阻断"——否则 light 任务的引用报告损坏会**无人拦截** |
| `task-abandon` | **不改**：终局、不解除 |

**硬前置依赖（不是"降级可用"）**

| 依赖 | 为什么是硬的 | 未就绪的后果 |
|---|---|---|
| **A1 `slot` 身份稳定**（backlog A1） | 放行键是 `(round, slot, digest)`；`slot` 与 `agent` 混用会匹配不上，而**重发新一轮不会解除**非引用 unknown（B1/B2） | 未就绪时，唯一收尾路径是 `task-abandon`；本文不再把"重发"列为降级出口 |
| **C1 读取归因**（backlog C1） | `open_findings` 在 try 之外调 `records.file_digest`（`review.py:185`），权限故障会直接抛出；`unverifiable` 与门禁分支都靠它 | ⑥ **自带这一处**的最小归因（见 §6），其余五处仍属 C1 |

---

## 6. 实现落点（批准后执行；本轮不动代码）

| 文件 | 改动 |
|---|---|
| `review.py` | ① `open_findings` 的 `unavailable` 条目补 `cause/round/report_digest`，并把该处 `file_digest` 包进 `except OSError`（**唯一来源 + 最小兜底**）；② 新增 `repair_scope(ctx, task)`（纯派生）：`findings` 取 `blocking`、`unverifiable` 取 `unavailable`、`conclusion` 由 `review-passed`/`check-passed` 两个既有判定合取；③ `unknown_acceptances` 读写与撤销 |
| `gates.py` | `final_gate` 末尾追加一条：存在未放行的 `unverifiable` → 阻断（附三条出口：找回原字节并恢复 / 人裁放行（仅非引用）/ 放弃任务） |
| `cli.py` | `wf status`（含 `--short`）输出 `repair_scope`；新增 `wf review-accept-unknown`（`--revoke`） |
| `templates/` | 不改 |

**不复用为第二套口径**：`cause` 三分只在 `open_findings` 一处产出，`repair_scope` 只搬运（自查清单第 1 条）。

---

## 7. 验收（15 项，全部属于 ⑥）

| # | 断言 |
|---|---|
| 1 | `findings` 与 `final_gate` 的 `unaddressed_blocking` 逐项一致（同源、不做 check 过滤） |
| 2 | 审查判 fail 且 `binding` 为真（check 未换代）→ `conclusion.verdict == "fail"`、`applicable == true`（当 `check_valid` 亦真） |
| 3 | **内容改动但未重跑 `task-check`** → `check_valid == false`、`applicable == false`、`blockers` 指明 `check` 侧原因（S5 的"内容变化"可见） |
| 4 | 重跑 `task-check` 产生新 check（不改 `reviews.result`）→ `binding == false`、`blockers` 含 `check_id_changed`；`findings` **不消失**（B5） |
| 5 | **`findings` 只能由 dispositions 清零**：修复代码 + 重跑 check + 重审 pass 后，若未补 dispositions，`findings` 仍非空（验收 4 的延伸） |
| 6 | `verdict == "fail"`、`binding == true`、`findings` 已全部处置 → 出口指引为"重发审查"，且重跑同一轮 `decide` 仍为 fail（不被误当作已完成） |
| 7 | **complex** 任务：`cited` 报告损坏 → 归档被既有 `review-passed` 拒绝（三重摘要核对） |
| 8 | **light** 任务：`cited` 报告损坏 → 归档被**本方案新增分支**拒绝（`review-passed` 对 light 短路，不得据此认为已覆盖） |
| 9 | 非引用报告损坏 + 摘要全等放行 → 不再阻断；撤销后恢复阻断；放行键匹配需 `(round, slot, digest)` 全等 |
| 10 | 报告恢复（原字节、摘要一致）→ 该项不再出现在 `unverifiable`（B1） |
| 11 | `cause` 三分**只**由 `open_findings` 产出；`repair_scope.unverifiable` 与其逐项一致（无第二套分类） |
| 12 | 权限故障（`PermissionError`）不再从 `open_findings` 抛出：该条归入 `unverifiable`（`cause=unreadable`），`status` 与 `gate` 均不崩 |
| 13 | `verdict == "invalidated"` → 出口为"完成已在途那一轮"，不是"再发一次" |
| 14 | **light 任务**仅有旧结论失效（无 findings、无未放行 unknown）→ 出口含"是否重审取决于任务要求"，不把重审写成义务 |
| 15 | 协议零改动：`phase.enum`、迁移数、`next_by_position` 逐字节一致；`repair_scope` 不参与 `next`；`task-abandon` 仍可终止且不解除任何阻断 |

---

## 8. 范围边界（防跑偏，硬约束）

**本文只回答 ⑥。** 以下不在本文范围，不作为通过条件（详见 `analysis/backlog-excluded-from-item6.md`）：
`slot`/`agent` 身份域与 finding 跨轮同名（**但 A1 是本文硬前置**）、导入端证据身份与 `--restore`、
`review-status` 的 ready/material 语义、六处读取健壮中的另外五处、`gate` 的 `fulfilled_by`、
`--short` 字段派生与展示分组、维护入口令牌交互、码表新增（⑦）、历史 dispositions 迁移。

---

## 9. 本文的历史（只留与 ⑥ 相关的关键否决）

| 版本 | 形态 | 为什么被否 |
|---|---|---|
| v3 | 新增 `fixing` 阶段 | 与 v42 枚举冲突；牵动协议与迁移 |
| v4 | 事件写入 `repair` 标记 | 主路径清不掉；两失败源共用槽位 |
| v20–v24 | 大 schema 表达全部未结事实 | 偏题；事实过载 |
| v25 | 单值 `reason` + 常量字段 | 并存事实互相遮蔽；指引伪装成事实；cited 损坏无出口 |
| v26 | 三组独立事实 + 出口表 | **`bound_to_current` 只比 check_id 与摘要，发现不了内容变化**；`cited` 排除让 light 任务漏检；出口表未写"findings 靠 dispositions 清零"；依赖被写成"可降级"（实际两条是硬前置） |
| **v27** | 三层事实（findings / unverifiable / conclusion=binding∧check_valid）+ 出口表含清零路径 | 本文；`cause` 单一来源；cited 只影响放行不影响阻断 |

---

## 10. 已定项（2026-11-11 人裁）

| # | 问题 | 裁定 |
|---|---|---|
| D1 | 非引用不可核实证据的阻断用哪个码 | **复用 `WF_REVIEW_INVALID` + `facts.reason = "unverifiable_evidence"`**（协议零改动） |
| D2 | 人裁是否引入签名 | **不引入**：沿用声明式 attestation（`by/at/quote/source` + 摘要），如实登记为已知限制 |

> 早期 **Q1=乙**（放行批次形状）、**Q2=甲**（两类阻断分列）亦已定。本文无待决项。
