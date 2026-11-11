# ⑥ 修复态的表达：不新增阶段，用「待修复事实」吸收 `fixing` 的收益（v25）

> 状态：**待审 v25**。阶段：**方案审查阶段，实现零改动**（规则见 `.trellis/spec/guides/review-phase-discipline.md`）。
>
> **本文只回答 ⑥，不包含其他条目。** 范围边界见 §7；超出范围的缺陷不在本文讨论，也不应作为本文的通过条件。

---

## 1. ⑥ 的问题

v42 的三处表述要求"审查失败进入修复阶段"：

| v42 | 原文要点 | 现状 |
|---|---|---|
| K10（L107） | 阶段只有 `plan/execute/**fixing**/finish` | 实现里没有 `fixing`，有 `check` |
| S4（L122） | `decide` 三态：`fail → **fixing**`、`pass → finish`、`unavailable`（异常归档） | `fail` 后 phase 停在 `check` |
| S5（L123） | `plan → execute → **fixing** → finish`；**内容变化或 review 判 fail 进入 `fixing`**，由下一次 `task-check` 退出；"审查失败不再需要 replan/approve" | 同 S4 |

2026-11-09 人裁：**保留四阶段、`fixing` 不落盘**（不引入第五个阶段值）。
2026-11-11 人裁（乙）：在该前提下**吸收 `fixing` 的收益**，人裁通道用于"人不在场"的情形。

**因此 ⑥ 要回答的只有三件事**：

1. **判 fail 之后，AI 怎么知道"该修什么、且不必 replan"**（S5 的核心收益）；
2. **"当前处于待修复"如何可见**（否则 AI 只能从"归档被拒"里反推）；
3. **人不在场时（审查做不成、证据不可核实）如何处置**（`fixing` 阶段原本也不解决这个，但它是同一段流程的出口）。

---

## 2. 方案：一个派生事实 + 一张出口表 + 一条人裁记录

### 2.1 派生事实 `repair_scope`（不落盘、不加阶段）

```json
"repair_scope": {
  "active": true,
  "reason": "review_fail | review_invalidated | evidence_unverifiable | null",
  "findings": [{"round": 1, "slot": "codex", "finding_id": "f1", "severity": "blocker"}],
  "recheck_required": true,
  "replan_not_needed": true,
  "phase_unchanged": "check"
}
```

**计算（一个函数，输入全是既有记录）**

| 字段 | 公式 |
|---|---|
| `active` | `reason != null` |
| `reason` | `review_fail`：最新审查结论 `verdict == "fail"`；<br>`review_invalidated`：`verdict == "invalidated"`（实施 CLI 变更使结论失效）；<br>`evidence_unverifiable`：存在已导入但**不可核实**的报告（摘要被改写/删除/读不到）且其对应轮次未被人裁放行；<br>否则 `null` |
| `findings` | 当 `reason` 为 `review_fail` 时，列出来自**可读且针对当前 check** 的报告中、`severity ∈ blocking` 且未被处置的 finding（带 `round/slot/finding_id`）；其余 reason 下为空列表 |
| `recheck_required` | `reason == "review_fail"` 时为 true（修完必须重跑 `task-check` 产生新 revision）；`review_invalidated` 时为 false（只需重发审查） |
| `replan_not_needed` | 恒为 true——这就是 S5 那句"审查失败不再需要 replan/approve"的显式化：**fail 不产生"重新规划"的出口** |
| `phase_unchanged` | 恒为当前 `phase`（不因 fail 改变） |

**为什么这是"吸收 fixing 的收益"**：`fixing` 作为阶段提供三样东西——(a) 明确的"在修"位置；(b) "不要 replan"的默认；(c) 修完由 `task-check` 退出。
本方案用 (a) `active=true` 事实、(b) `replan_not_needed=true`、(c) `recheck_required=true` 一一对应，**且不改 `phase` 取值域**（`protocol/states.json` 的 `phase.enum` 与 11 条迁移不变）。

**与位置指引的关系**：`next` 仍由位置驱动，不改（现文案已是 `in_progress/check → "wf task-check（按 fail 项修复后重新检查；修复回 execute）"`，与 S5 的"下一次 task-check 退出"一致）。`repair_scope` **不参与** `next` 计算——它只是事实，供 AI 判断。

### 2.2 出口表（把 `fixing` 那条流程拆成"下一步做什么"）

| 情形 | 机制给的出口 | **明确的"不做"** |
|---|---|---|
| `review_fail` | 修 `findings` → 重跑 `task-check` → 重发审查（轻量任务修完可直接收工） | 不 replan、不改 phase、不要求重新批准计划 |
| `review_invalidated` | 重发审查（实施 CLI 已变，旧结论不可复用） | 不要求改代码、不 replan |
| `evidence_unverifiable` | 人裁放行（§2.3）/ 重发新一轮（让当前工作能继续）/ 放弃任务（`task-abandon`） | **重发与 `--unavailable` 都不解除该条未知**（见 §3） |
| `verdict == "pass"` 且绑定当前 check | 归档 | —— |

### 2.3 人裁记录（乙通道：只在"人不在场/证据不可核实"时使用）

**记录**（新增，落盘）：`reviews.unknown_acceptances[]`

```json
{"batch": "b-20261111-1", "round": 1, "slot": "codex",
 "report_digest": "sha256:…", "path": "…", "cause": "changed|missing|unreadable",
 "quote": "这份报告丢失的风险我认", "by": "human:xzc", "at": "…", "source": "user-declared",
 "attestation_digest": "sha256:…", "revoked": false}
```

| 规则 | 语义 |
|---|---|
| 绑定 | 匹配键 `(round, slot, report_digest)` **三者全等**；摘要不同不匹配（换过内容的报告不能被旧放行覆盖） |
| 批次 | 一次一批、**全有或全无**：任一项不匹配 → 整批拒绝、零写入，返回 `bad_items` |
| 不做预放行 | 指向当前不存在的不可核实项 → 拒绝（避免"它将来失效时自动生效"） |
| 幂等 | 同一键重复放行 → 不新增，回报 `already_accepted` |
| 撤销 | `--revoke` 置 `revoked: true`（**不删记录**，留痕），撤销后立即恢复阻断 |
| 信任模型（如实） | 沿用 attestation：`by/at/quote/source` + 摘要入库。**挡不住持写权的 AI 伪造**；只保证绑定到具体证据、留痕可审计。不宣称"AI 无法自签" |

**命令**：`wf review-accept-unknown --task <id> --file <决定.json>`，撤销用 `--revoke --round/--slot` 或 `--revoke --batch`。

---

## 3. 三条语义边界（这是 ⑥ 的核心，容易写错的地方）

| # | 边界 | 为什么必须写死 |
|---|---|---|
| B1 | **"让流程继续" ≠ "解除阻断"** | 重发新一轮、`--unavailable`、恢复历史报告都只让当前工作能继续；`evidence_unverifiable` 的解除**只有**人裁放行（摘要全等），否则归档仍被拒。上一版曾把"重发"当解除出口 → 重审成功也无法收尾 |
| B2 | **`fail` 不等于需要 replan** | S5 的收益就是"fail 不回到 plan"；必须作为事实给出（`replan_not_needed=true`），否则 AI 会按"重来一遍"处理 |
| B3 | **`unavailable` 不等于异常归档** | `--unavailable` 只表示"这次审查做不成"；异常归档（`task-abandon`）是不跑最终门禁的**终局**出口，两者不可互相替代 |

---

## 4. 与既有机制的关系（**不改的东西**）

| 机制 | 关系 |
|---|---|
| `phase` 枚举（`plan/execute/check/finish`） | **不改**；不新增 `fixing` |
| `protocol/states.json`（36 码 / 16 配置键 / 11 迁移 / `next_by_position`） | **不改**；`repair_scope` 不参与 `next` |
| `review-decide` 的判定资格（人数/非实施者/输入成立性） | **不改**；`repair_scope` 只读它的结论 |
| `task-check` 的 fail 语义与 revision | **不改**；fail 仍是"产生新 revision 的输入" |
| `final_gate` 结构 | **只加一条**：存在未放行的 `evidence_unverifiable` 时阻断归档（`WF_REVIEW_INVALID` + `facts.reason = "unverifiable_evidence"`）。不改其余顺序 |
| `task-abandon` | **不改**；定位为"不解除阻断的终局出口" |

---

## 5. 实现落点（批准后执行；本轮不动代码）

| 文件 | 改动 |
|---|---|
| `review.py` | 新增 `repair_scope(ctx, task)`（纯派生，单一实现）；`unknown_acceptances` 匹配与撤销；`open_findings` 输出中标注"不可核实"项与其登记摘要 |
| `gates.py` | `final_gate` 末尾追加 `evidence_unverifiable` 阻断（一条分支，附出口三条） |
| `cli.py` | `wf status`（含 `--short`）输出 `repair_scope`；新增 `wf review-accept-unknown`（含 `--revoke`） |
| `templates/` | 不改（`repair_scope` 派生；`unknown_acceptances` 可选） |

**迁移影响**：无历史改写。已有任务在下次读取时即得到 `repair_scope`（派生）。

---

## 6. 验收（10 项，全部属于 ⑥）

| # | 断言 |
|---|---|
| 1 | 审查判 `fail` → `repair_scope.active == true`、`reason == "review_fail"`、`findings` 列出未关闭的 blocking 项（带 `round/slot/finding_id`） |
| 2 | 同一次 fail 后 `replan_not_needed == true`、`recheck_required == true`，且 `phase` **仍为 `check`**（未新增阶段值） |
| 3 | 修复后重跑 `task-check` 产生 pass → `repair_scope.active == false` |
| 4 | `verdict == "invalidated"` → `reason == "review_invalidated"`、`findings == []`、`recheck_required == false` |
| 5 | 报告不可核实（改写/删除/读不到）→ `reason == "evidence_unverifiable"`，`archive` 被拒并给三条出口 |
| 6 | 人裁放行（`(round, slot, digest)` 全等）→ 该条不再阻断；摘要不同 → 不匹配仍阻断 |
| 7 | 撤销放行 → 立即恢复阻断（记录保留 `revoked: true`） |
| 8 | `review-decide --unavailable` 与"重发新一轮 pass"**都不解除** `evidence_unverifiable`（B1） |
| 9 | 协议零改动：`phase.enum`、迁移数、`next_by_position` 与改动前逐字节一致；`repair_scope` 不参与 `next` 计算 |
| 10 | `task-abandon` 仍可终止任务，且**不**把 `evidence_unverifiable` 标为"已解除"（B3） |

---

## 7. 范围边界（防止审查跑偏，这一节是硬约束）

**本文只回答 ⑥（`fixing` 的收益如何在四阶段内表达）。以下均不在本文范围**，也不应作为本文的通过条件：

| 不属 ⑥ | 归属 |
|---|---|
| 审查链的身份问题（`slot`/`agent` 混用、finding 跨轮同名） | 关闭链/槽位身份，另案 |
| 证据身份（导入端可否替换、`--restore`、幂等重入三态） | 导入链，另案 |
| `review-status` 的 `reports_ready`/`material_blockers`/`eligibility_hints` 语义 | 该命令自身，另案 |
| 六处读取健壮（`OSError` 归因）、`file_digest_or_raise` | 健壮性，另案 |
| `gate` 的 `fulfilled_by`、`changes-persisted` 语义 | 步骤语义，另案 |
| 展示层字段派生（`--short` 的 `task.check`） | 展示，另案 |

**本文的自检**：`repair_scope` 只依赖 `reviews.result`、`reviews.imported`（可读性）、`reviews.dispositions`、`task.check` 四类既有记录；不引入新身份、不改任何既有判定。

---

## 8. 本文自身的历史（只留 ⑥ 相关的关键否决，避免重犯）

| 版本 | 形态 | 为什么被否（**与 ⑥ 直接相关**） |
|---|---|---|
| v3 | 新增 `fixing` 阶段 | 与 v42 的枚举（无 `check`）冲突；且现有 `check` 已承载"动作后状态"，加第五值会牵动协议与迁移 |
| v4 | 事件写入 `repair` 标记 | 主路径清除不掉（改码→新 check→重审通过也不清）；两个失败源共用一个槽位会互相覆盖 |
| v20–v24 | 用大 schema 表达"全部未结事实" | 偏题：把其它组件缺陷装进 ⑥，导致 ⑥ 永远"未完成"；且事实过载，AI 需要先理解 20 个概念 |
| **v25（本文）** | **一个派生事实 `repair_scope` + 出口表 + 一条人裁记录** | 只回答 ⑥；不新增阶段、不改协议、不改 `next` |

---

## 9. 需要你裁的（只有 2 条，均有默认）

| # | 问题 | 默认 |
|---|---|---|
| Q1 | `evidence_unverifiable` 阻断复用 `WF_REVIEW_INVALID`（+`facts.reason`）还是新增协议码（36→37）？ | 复用（零协议改动） |
| Q2 | 人裁放行的信任模型：接受"AI 可转录/伪造 + 留痕可审计"，还是要求人直接在决定文件签名？ | 接受现状，如实登记 |
