# ⑥ 修复态的表达：不新增阶段，用「事实 + 清除动作」吸收 `fixing` 的收益（v30）

> 状态：**待审 v30**。阶段：**方案审查阶段，实现零改动**（规则见 `.trellis/spec/guides/review-phase-discipline.md`）。
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
| **可放行条件** | `release_allowed = !(cited && review_required)`：<br>· complex 任务 + 当前结论引用的报告 → **不能放行**（它是归档依据，必须重发审查）<br>· **light 任务** + 被引用 → **可以放行**（light 的归档不依赖审查结论）。如实说明：**义务没有消失，只是换了承担者**——字节找不回时仍需**人裁放行**（或放弃）；对自愿证据而言这仍是一次收尾成本，取舍是「证据完整性优先」<br>· 非引用报告 → 可放行 |
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

## 4. 完成条件与清除动作（**事实 → 必须满足什么 → 怎么让它成立**）

**原则**：机制只保证三件事——每个未满足条件**都可见**、每个条件都有**可执行的清除动作**、放行**权限明确**。
**不排顺序、不拆并行**：条件可同时不满足，AI 可自行合并或并行（例：一轮新审查可同时完成"复核关闭"与"补充证据"；
根因在规划时可直接 `task-replan`）。

### 4.1 ⑥ 相关的四个完成条件

| # | 条件（归档时必须成立） | 事实来源 |
|---|---|---|
| **C1** | 检查有效 | `conclusion.check_valid`（≡ `check_validity`） |
| **C2** | 无未关闭 blocking | `findings == []` |
| **C3** | 无未放行的不可核实证据 | `unverifiable` 中 `released == false` 为空 |
| **C4** | **复杂任务**的审查结论存在、绑定当前 check 且为 pass | `review_required == true` 时要求 `verdict == "pass"` 且 `binding` |

**light 任务（`review_required == false`）不承担 C4**：不产生「必须取得新的审查结论」这项义务。
但其自愿审查的 blocking findings **仍受 C2 约束**（`WF_UNRESOLVED_BLOCKING` 不分复杂度）、其报告损坏**仍受 C3 约束**：义务收窄到「处置已发现的问题」，**不是「无义务」**。

### 4.2 每个条件的清除动作

| 条件 | 清除动作 | 禁用 / 注意 |
|---|---|---|
| **C1 失效** | 重跑 `task-check` 产生新 check（内容变了必须重查） | —— |
| **C2 未空** | 逐项处置（修复代码，或经复核**否定 / 重分类**该项）→ **由非提出者复核后补 dispositions**（B5，唯一清零路径） | 「处置」不等于「必须改代码」；重查、重审 pass 都**不**清 findings |
| **C3 未放行** | ① **找回原字节**（恢复即不再不可核实，B1，不依赖身份）<br>② **人裁放行**（`release_allowed == true` 时） | · complex 且 `cited` 损坏：**不可放行**——先让新结论落地（届时它变成非引用，转入 ②）<br>· 字节不可得且不可放行 → `task-abandon` |
| **C4 不成立** | ① **默认先用好在途轮次**（`invalidated` 只证明「曾发起过新一轮」，不等于该轮仍可用）<br>② 若该轮**材料 / 资格 / 锚点已不可用**（reviewer 与实施 CLI 重叠、人数不足被判不合格）→ **按既有出口重新发起** `review-launch`（`review.py:1389` 原文即「重新发起新一轮」）<br>③ 审查做不成（`unavailable` / 环境凑不齐）→ **暂停（人决定）或经人授权异常归档**（`review.py:1396`，B4） | 不得据此判 pass；根因在规划时可用 `task-replan`（B3）；`check_valid == false` 时先做 C1 |

### 4.3 并存时的行为

- 条件可**同时**不满足；`repair_scope` 会**同时**给出全部事实，**不做优先级遮蔽**；
- 动作顺序、是否合并、先修哪一项，全部由 AI 按任务要求判断（机制不排调度）；
- 旧结论能否复用由 C4 的事实判断，**不由任何表格顺序判断**。

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

## 7. 验收（21 项，全部属于 ⑥）

| # | 断言 |
|---|---|
| 1 | `findings` 与 `final_gate` 的 `unaddressed_blocking` 逐项一致（同源、不做 check 过滤） |
| 2 | **`binding` 是子判定**：`verdict == "fail"`、check 未换代、引用报告摘要一致 → `binding == true`（不得因 `verdict != pass` 而为 false）；light 无审查结论时由事实计算，不得恒为 true |
| 3 | **`check_valid` 与门禁逐分支一致**（含结构复核 `check_result_problems`、`invalidated`、anchor 计算失败、`rule_version`） |
| 4 | 内容改动但未重跑 `task-check` → `check_valid == false`、`applicable == false`、`check_blockers` 指明 anchor 漂移（C1 未满足，必须重查） |
| 5 | 重跑 `task-check` 产生新 check → `binding == false`（`check_id_changed`）；`findings` **不消失**（B5） |
| 6 | **`findings` 只能由 dispositions 清零**：修复+重查+重审 pass 后未补 dispositions → `findings` 仍非空（C2 未满足） |
| 7 | `verdict == "fail"` 且 `binding == true` 且 `findings` 已全部处置 → C4 未满足，指引为**重发审查**；重跑同一轮 `decide` 仍 fail |
| 8 | **complex**：`cited` 报告损坏 → 归档被既有 `review-passed` 拒绝；`release_allowed == false`，放行被拒（C3 未满足且不可放行） |
| 9 | **light**：`cited` 报告损坏 → 归档被**新增分支**拒绝；`release_allowed == true`（可人裁放行），放行后 C3 满足 |
| 10 | 非引用报告损坏 + 摘要全等放行 → C3 满足；撤销后恢复；匹配需三元组全等 |
| 11 | 报告恢复（原字节、摘要一致）→ 不再出现在 `unverifiable`（C3 自动满足，B1） |
| 12 | `cause` 三分只由 `open_findings` 产出；`repair_scope.unverifiable` 与其逐项一致 |
| 13 | **权限故障不崩**：`PermissionError` 时 `open_findings`、`review_binding`、`status`、`wf gate` 全部走归因分支 |
| 14 | `verdict == "invalidated"` → C4 的清除动作**首选完成在途那一轮**；当该轮被判资格不合格（reviewer 与实施 CLI 重叠等）时，**必须允许**重新发起（定向用例：指引含两者，且不出现「禁止重新发起」） |
| 15 | **并存无遮蔽**：`findings` 非空 + 存在未放行 `unverifiable` 时，两组事实**同时**出现在 `repair_scope`（不以任一为另一的替代） |
| 16 | **条件覆盖性**：任一未满足的 C1–C4 都能在 §4.2 找到对应清除动作；每个事实都能映射到某个 C（无孤立事实） |
| 17 | **light 任务不承担 C4**：自愿审查 `fail`/`unavailable`/`invalidated` 且 `findings` 空、C1/C3 满足 → 不产生「必须取得新审查结论」义务 |
| 18 | **但 light 的 C2/C3 仍成立**：自愿审查带 blocking findings → 未补 dispositions 时归档被 `WF_UNRESOLVED_BLOCKING` 拒绝；其报告损坏 → C3 阻断（不得因"不承担 C4"而跳过） |
| 19 | **C4 的 `unavailable` 出口存在**：审查做不成时清除动作含「暂停（人决定）」与「经人授权异常归档」，且**不含**「判 pass」 |
| 20 | **C1 与 C4 分离**：`verdict == "pass"` 但 `check_valid == false` 时，指引必须含「重查」（不得只写「可选重审」） |
| 21 | 协议零改动：`phase.enum`、迁移数、`next_by_position` 逐字节一致；`repair_scope` 不参与 `next`；`task-abandon` 仍可终止且不解除阻断 |

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
| **v28** | 两个共享子判定 + `release_allowed` + 互斥出口表 | 出口表仍是固定优先级：light 的 fail/unavailable 被写成义务；`invalidated`+cited 被顺序遮住（应完成在途轮）；`fail ∧ !binding ∧ findings 空` 落入兜底；「恰好命中一行」性质测试恒真 |
| **v29** | **完成条件 C1–C4 + 每条件的清除动作**（不再排序） | 本文 |
| **v30** | C4 出口恢复既有语义 + light 义务收窄 | `invalidated` 被写成「禁止重新发起」，与 `review.py:1389` 的既有出口（重新发起新一轮）冲突；C4 缺 `unavailable` 的暂停/异常归档出口；light 表述说成「不产生义务」，漏了 C2/C3 仍成立 |

---

## 10. 已定项（2026-11-11 人裁）

| # | 问题 | 裁定 |
|---|---|---|
| D1 | 不可核实证据阻断用哪个码 | 复用 `WF_REVIEW_INVALID` + `facts.reason = "unverifiable_evidence"` |
| D2 | 人裁是否引入签名 | 不引入：沿用声明式 attestation |

> Q1=乙（批次形状）、Q2=甲（两类阻断分列）亦已定。本文无待决项。
