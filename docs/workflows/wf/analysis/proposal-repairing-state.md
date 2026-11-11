# ⑥ 修复态的表达：不新增阶段，用「事实 + 出口」吸收 `fixing` 的收益（v28）

> 状态：**待审 v28**。阶段：**方案审查阶段，实现零改动**（规则见 `.trellis/spec/guides/review-phase-discipline.md`）。
> **本文只回答 ⑥**；范围边界见 §8，被排除条目见 `analysis/backlog-excluded-from-item6.md`。

---

## 1. ⑥ 的问题

v42：K10（阶段含 `fixing`）、S4（`fail → fixing`）、S5（`plan → execute → fixing → finish`；**内容变化或 review 判 fail 进入 `fixing`**；由下一次 `task-check` 退出；**审查失败不再需要 replan/approve**）。

人裁：保留四阶段、`fixing` 不落盘；吸收其收益；人裁通道用于"人不在场"。

| `fixing` 提供 | 替代 |
|---|---|
| ① "在修"的位置 | `findings` + `conclusion`（结论是否仍绑定/仍适用） |
| ② fail 不强制 replan | **指引**：fail 不触发 replan；根因在规划时 `task-replan` 仍可用 |
| ③ 修完由下一次 `task-check` 退出 | 事实 `check_valid` + `binding`；**是否重查/重审由 AI 按任务要求判断** |

---

## 2. 机制给什么：四组事实 + 一条人裁记录

### 2.1 `repair_scope`（派生，不落盘；无单一状态枚举）

```json
"repair_scope": {
  "review_required": true,          // = (plan.complexity == "complex")，与 review-passed 的短路条件同源
  "findings": [{"round": 1, "slot": "codex", "finding_id": "f1", "severity": "blocker"}],
  "unverifiable": [{"round": 1, "slot": "codex", "path": "…", "report_digest": "sha256:…",
                    "cause": "changed|missing|unreadable",
                    "cited": false,
                    "release_allowed": true,    // = !(cited && review_required)
                    "released": false}],        // = 有 (round, slot, digest) 全等的未撤销放行 && release_allowed
  "conclusion": {"verdict": "fail", "round": 2, "check_id": "C2",
                 "binding": true,  "binding_blockers": [],
                 "check_valid": false, "check_blockers": ["check_anchor_drift"],
                 "applicable": false}          // = binding && check_valid
}
```

**判据（每条都写成"调用哪个共享判定"，枚举仅作说明，以判定实现为准）**

| 事实 | 判定来源 |
|---|---|
| `findings` | `open_findings(...)["blocking"]`（门禁同源，全轮次，不做 check 过滤） |
| `unverifiable` | `open_findings(...)["unavailable"]`（唯一来源；条目带 `cause/round/report_digest`，见 §6） |
| `conclusion.binding` | **绑定子判定**（提取为共享函数 `review_binding`）：`result.check_id == check.id` ∧ 结论引用报告的 `result_digest == recorded == 文件当前摘要`。**不含 `verdict != pass` 门槛，也不含复杂度门槛**——上一版把整个 `review-passed` 步骤的返回值当 binding，导致"(fail, 未换代) 时 binding=false"与"(light 任务恒 true)"两种错读 |
| `conclusion.check_valid` | **`task.check-passed` 的判定**（提取为共享函数 `check_validity`）：`result == pass` ∧ anchor 相符 ∧ 未 `invalidated` ∧ `rule_version` 相符 ∧ **结构复核 `check_result_problems` 通过** ∧ 当前 anchor 可算。上一版枚举漏了结构复核与 anchor 计算失败，照抄即造第二套口径 |
| `conclusion.applicable` | `binding && check_valid`（合取；`verdict` 不参与——fail 的结论同样可以"仍适用于当前检查"） |

### 2.2 人裁记录（乙通道）

**记录**：`reviews.unknown_acceptances[]`（字段同前：`batch/round/slot/report_digest/path/cause/quote/by/at/source/attestation_digest/revoked`）

| 规则 | 语义 |
|---|---|
| 匹配 | `(round, slot, report_digest)` 三者全等；摘要不同不匹配 |
| **可放行条件** | `release_allowed = !(cited && review_required)`：<br>· complex 任务 + 当前结论引用的报告 → **不能放行**（它是归档依据，必须重发审查）<br>· **light 任务** + 被引用 → **可以放行**（light 的归档不依赖审查结论，那份报告只是自愿证据，不能因此衍生重审义务）<br>· 非引用报告 → 可放行 |
| 批次 | 一次一批、全有或全无；任一项不合法 → 整批拒绝、零写入，返回 `bad_items` |
| 不做预放行 | 指向当前不存在的不可核实项 → 拒绝 |
| 幂等 | 同一键重复放行 → 不新增，回报 `already_accepted` |
| 撤销 | `--revoke --batch`，或 `--revoke --round --slot --digest`（必须带 digest）；置 `revoked: true`（不删记录） |
| 信任模型（定案） | 沿用 attestation 四件套 + 摘要入库；**不引入签名**（全仓无签名设施，`authorize`/`attestation` 同级） |

**命令**：`wf review-accept-unknown --task <id> --file <决定.json>`（含 `--revoke`）。

---

## 3. 五条语义边界

| # | 边界 | 说明 |
|---|---|---|
| **B1** | 可核实性是**当前状态** | 报告恢复（原字节、摘要一致）→ 不再出现在 `unverifiable`。这不是"解除"，是事实变化；人裁只用于**无法恢复**的情形 |
| **B2** | 归档依据必须可核实 | complex：`cited` 报告损坏由既有 `review-passed` 拦；light：由本方案新增分支拦（`review-passed` 对 light 短路）。**是否阻断与能否放行是两件事**：`cited && review_required` 时仍阻断且不可放行 |
| **B3** | fail 不强制 replan，但不是禁止 | 根因在规划时 `task-replan` 仍合法（代价：原批准失效） |
| **B4** | `unavailable` ≠ 异常归档 | `--unavailable` 只表示审查做不成；`task-abandon` 是不跑最终门禁的终局出口 |
| **B5** | `findings` 只能由 dispositions 清零 | 代码修复、`task-check`、重审 pass 都**不**清旧轮报告的 blocking：`decide` 的 verdict 由报告载荷推导（`review.py:1351`），不读 dispositions，同轮重跑仍 fail。唯一路径是 K4b：**非提出者复核**后补 `dispositions(decision=accepted)` |

---

## 4. 出口表（**指引**；10 行**叶子条件互斥**、命中即停；行内动作顺序由 AI 决定）

| # | 条件（互斥，按序匹配） | 指引 |
|---|---|---|
| R1 | `findings` 非空 | 按项修复 → **由非提出者复核后补 dispositions 关闭**（B5，唯一清零路径）→ 内容变了就重查 → 需要时重发审查 |
| R2 | 有 `unverifiable` 且 `released == false`，**且** 该条 `cited && review_required` | **重发审查**（在同一有效 check 上；只有内容也变了才需要重查）；放行不适用 |
| R3 | 有 `unverifiable` 且 `released == false`，其余（含 light 的 `cited`、非引用报告） | 找回原字节（恢复即不再不可核实）/ **人裁放行** / 放弃任务 |
| R4 | `verdict == "invalidated"` | 完成**已在途**的那一轮（`invalidated` 只在 launch 时写入） |
| R5 | `verdict == "fail"` 且 `binding == true` | 重发审查（同轮重跑仍 fail）；若 `check_valid == false` 先重查 |
| R6 | `verdict == "unavailable"` | 补真实审查，或经人授权异常归档 |
| R7 | `verdict == "pass"` 且 `applicable == true` | 常规推进（归档） |
| R8 | `verdict == "pass"` 且 `applicable == false` 且 `review_required == true` | `check_valid == false` 先重查；然后**重发审查** |
| R9 | `verdict == "pass"` 且 `applicable == false` 且 `review_required == false`（light） | **可选**：是否重审取决于任务要求；旧结论失效不构成收尾义务 |
| R10 | 其他（无结论、`phase == "finish"` 但仍有上述未结事实等） | 按事实逐项处理，处理完再归档 |

**说明**：表格是**指引**，按"阻断归档的第一原因"排序并**命中即停**——这解决同一状态匹配多行、指引互相矛盾的毛病；具体执行顺序仍由 AI 决定。
**唯一硬约束**：不要用"试归档"探路（`tasks.py:3233` 会先业务提交）；需要只读答案时并读 `wf gate`（步骤面）与 `repair_scope`。

## 5. 与既有机制的关系（不改的东西 + 硬前置依赖）

| 机制 | 关系 |
|---|---|
| `phase` 枚举 / `protocol/states.json` / `next_by_position` | **不改**；`repair_scope` 不参与 `next` |
| `review-decide` 判定资格、`task-check` 语义 | **不改** |
| `review-passed` / `check-passed` | **行为不变**，但内部判定**提取为共享函数**（`review_binding` / `check_validity`），供 `repair_scope` 复用（避免第二套口径，也把 OSError 归因收到一处） |
| `final_gate` 结构 | **只加一条**：存在 `released == false` 的 `unverifiable` 时阻断；出口按 `cited && review_required` 分列（见 §6） |
| `task-abandon` | **不改**：终局、不解除 |

**硬前置依赖**

| 依赖 | 为什么硬 | 未就绪时 |
|---|---|---|
| **A1 `slot` 身份稳定**（backlog） | 放行键 `(round, slot, digest)`；`slot`/`agent` 混用会导致匹配不上 | 放行不可用 → **先找回原字节**（不依赖身份）；字节不可得才 `task-abandon`。不把"重发"当降级出口 |
| **C1 读取归因**（backlog） | `open_findings` 与 `review_binding` 都会读摘要，权限故障会抛出 | ⑥ 自带这两处归因（见 §6）；其余五处仍属 C1 |

---

## 6. 实现落点（批准后执行；本轮不动代码）

| 文件 | 改动 |
|---|---|
| `gates.py` | ① 把 `review-passed` 的**绑定核验**与 `check-passed` 的**有效性核验**各自提取为共享函数（`review_binding` / `check_validity`），步骤行为不变；② 两个函数内的摘要读取包 `except OSError`（`PermissionError` 不再外溢）；③ `final_gate` 末尾追加 `unverifiable` 阻断，出口按 `cited && review_required` 分列：<br>· 该情形 → 「找回原字节」「重发审查」「放弃任务」<br>· 其余 → 「找回原字节」「人裁放行」「放弃任务」 |
| `review.py` | ① `open_findings` 的 `unavailable` 条目补 `cause/round/report_digest`，并把摘要读取包进 `except OSError`（唯一来源 + 最小兜底）；② 新增 `repair_scope(ctx, task)`：`findings`/`unverifiable` 取上述两处，`conclusion` 调 `review_binding`+`check_validity`；③ `unknown_acceptances` 读写与撤销（含 `release_allowed` 校验） |
| `cli.py` | `wf status`（含 `--short`）输出 `repair_scope`；新增 `wf review-accept-unknown`（`--revoke`） |
| `templates/` | 不改 |

**不做第二套口径**：`cause` 三分只在 `open_findings`；`binding`/`check_valid` 只在两个共享函数；`repair_scope` 只搬运。

---

## 7. 验收（19 项，全部属于 ⑥）

| # | 断言 |
|---|---|
| 1 | `findings` 与 `final_gate` 的 `unaddressed_blocking` 逐项一致（同源、不做 check 过滤） |
| 2 | **`binding` 是子判定**：`verdict == "fail"` 且 check 未换代、引用报告摘要一致 → `binding == true`（**不得**因 `verdict != pass` 而为 false）；light 任务无审查结论时 `binding` 由事实计算，**不得**恒为 true |
| 3 | **`check_valid` 与门禁逐分支一致**（含结构复核 `check_result_problems`、`invalidated`、anchor 计算失败、rule_version） |
| 4 | 内容改动但未重跑 `task-check` → `check_valid == false`、`applicable == false`、`check_blockers` 指明 anchor 漂移（S5 的"内容变化"可见） |
| 5 | 重跑 `task-check` 产生新 check（不改 `reviews.result`）→ `binding == false`、`binding_blockers` 含 `check_id_changed`；`findings` **不消失**（B5） |
| 6 | `findings` 只能由 dispositions 清零：修复+重查+重审 pass 后未补 dispositions → `findings` 仍非空 |
| 7 | `verdict == "fail"` 且 `binding == true` 且 `findings` 已全部处置 → 出口为 **R5**"重发审查"；重跑同一轮 `decide` 仍 fail |
| 8 | **complex**：`cited` 报告损坏 → 归档被既有 `review-passed` 拒绝；`release_allowed == false`，放行被拒 |
| 9 | **light**：`cited` 报告损坏 → 归档被**新增分支**拒绝；**`release_allowed == true`**（可人裁放行），放行后不再阻断 |
| 10 | 非引用报告损坏 + 摘要全等放行 → 不再阻断；撤销后恢复阻断；匹配需三元组全等 |
| 11 | 报告恢复（原字节、摘要一致）→ 不再出现在 `unverifiable`（B1） |
| 12 | `cause` 三分只由 `open_findings` 产出；`repair_scope.unverifiable` 与其逐项一致 |
| 13 | **权限故障不崩**：`PermissionError` 时 `open_findings`、`review_binding`、`status`、`wf gate` 全部走归因分支（不抛内部错误） |
| 14 | `verdict == "invalidated"` → **R4**"完成已在途那一轮"，不是"再发一次" |
| 15 | 出口表**行间互斥**（性质测试：对事实组合穷举，断言**恰好命中一行**） |
| 16 | **R2** 的指引**不强制新检查**：`cited && review_required` 且 `check_valid == true` 时，出口只要求重发审查 |
| 17 | **light 任务**仅旧结论失效、无 findings、无未放行 unknown → 命中 **R9**（可选重审），不出现"必须重审" |
| 18 | **门禁出口内容**：`cited && review_required` 的阻断出口含「重发审查」且**不含**「人裁放行」；其余阻断出口含「找回原字节」与「人裁放行」 |
| 19 | 协议零改动：`phase.enum`、迁移数、`next_by_position` 逐字节一致；`repair_scope` 不参与 `next`；`task-abandon` 仍可终止且不解除阻断 |

---

## 8. 范围边界（防跑偏，硬约束）

本文只回答 ⑥。不在范围（详见 backlog）：`slot`/`agent` 身份域与 finding 跨轮同名（**A1 为本文硬前置**）、导入端证据身份与 `--restore`、`review-status` 的 ready/material 语义、六处读取健壮中的其余五处、`gate` 的 `fulfilled_by`、`--short` 字段派生与展示分组、维护入口令牌交互、码表新增（⑦）、历史 dispositions 迁移。

---

## 9. 本文的历史（只留与 ⑥ 相关的关键否决）

| 版本 | 形态 | 为什么被否 |
|---|---|---|
| v3 / v4 | `fixing` 阶段 / `repair` 标记 | 与 v42 枚举冲突；主路径清不掉 |
| v20–v24 | 大 schema | 偏题；事实过载 |
| v25 | 单值 `reason` + 常量字段 | 并存事实互相遮蔽；指引伪装成事实 |
| v26 | 三组事实 + 出口表 | `bound_to_current` 漏内容变化；`cited` 排除使 light 漏检；无清零路径；依赖写成"可降级" |
| v27 | 加 `check_valid`、cited 不再排除阻断 | **`binding` 误用整个 `review-passed` 返回值**（fail 时被 false、light 时恒 true）；`check_valid` 枚举漏结构复核；出口表行间重叠；light 的 `cited` 被禁止放行 → 可选审查衍生重审义务；R2 出口缺"重发审查" |
| **v28** | 两个共享子判定 + `release_allowed` + 互斥出口表 | 本文 |

---

## 10. 已定项（2026-11-11 人裁）

| # | 问题 | 裁定 |
|---|---|---|
| D1 | 不可核实证据阻断用哪个码 | 复用 `WF_REVIEW_INVALID` + `facts.reason = "unverifiable_evidence"` |
| D2 | 人裁是否引入签名 | 不引入：沿用声明式 attestation |

> Q1=乙（批次形状）、Q2=甲（两类阻断分列）亦已定。本文无待决项。
