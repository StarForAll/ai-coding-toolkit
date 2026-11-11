# ⑥ 修复态的表达：不新增阶段，用「事实 + 清除动作」吸收 `fixing` 的收益（v35）

> 状态：**待审 v35**。阶段：**方案审查阶段，实现零改动**（`review-phase-discipline.md`）。
> **本文只回答 ⑥**：`fixing` 的收益如何在四阶段内表达。范围边界见 §8。

---

## 1. ⑥ 的问题

v42：K10（阶段含 `fixing`）、S4（`fail → fixing`）、S5（`plan → execute → fixing → finish`；**内容变化或 review 判 fail 进入 `fixing`**；由下一次 `task-check` 退出；**审查失败不再需要 replan/approve**）。
人裁：保留四阶段、`fixing` 不落盘；吸收其收益；人裁通道用于"人不在场"。

| `fixing` 提供 | 替代 |
|---|---|
| ① "在修"的位置 | `open_blocking`（要修什么）+ `conclusion`（旧结论是否仍绑定/仍适用） |
| ② fail 不强制 replan | **指引**：fail 不触发 replan；根因在规划时 `task-replan` 仍可用 |
| ③ 修完由下一次 `task-check` 退出 | 事实 `check_valid` + `binding`；**是否重查/重审由 AI 判断** |

---

## 1a. 主 agent 的主动性（设计约束）

（规范：`.trellis/spec/guides/main-agent-initiative.md`）

| # | 约束 | 落点 |
|---|---|---|
| 1 | 机制只给事实与可执行清除动作，**不排顺序、不产生"等待评审"状态** | §4 |
| 2 | 审查结论是输入：`fail` 不要求逐条执行报告，AI 可合并、可否定（需说明） | §4 / B5 |
| 3 | 不得把"取得外部审查结论"写成推进前提 | §4.1：只有 complex 的 C4 是完成条件 |
| 4 | 审查不得扩权：范围外只登记 | §8 + backlog |
| 5 | 主 agent 可主动扩展（授权内的相邻缺陷） | §4.2 处置不限于报告项 |

---

## 2. 机制给什么：四组事实 + 一条人裁记录

### 2.1 `repair_scope`（派生，不落盘；无单一状态枚举）

```json
"repair_scope": {
  "review_required": true,
  "open_blocking": [{"round": 1, "slot": "s1", "finding_id": "f1", "severity": "blocker"}],
  "unverifiable": [{"round": 1, "slot": "s1", "path": "…", "report_digest": "sha256:…",
                    "cause": "changed|missing|unreadable",
                    "cited": false, "release_allowed": true, "released": false}],
  "in_flight": {"round": 2, "imported": 2, "declared": 2,
                "usable": true,              // true | false | null(=无法判定)
                "usable_blockers": ["material_missing|eligibility_failed|anchor_stale"]},
  "exits": ["<未满足条件的清除动作 token，见 §4.2>"],
  "conclusion": {"verdict": "fail", "round": 1, "check_id": "C2",
                 "binding": true, "binding_blockers": [],
                 "check_valid": false, "check_blockers": ["check_anchor_drift"]}
}
```

**判据（每项都写成"调用哪个共享判定"；枚举仅说明，以判定实现为准）**

| 事实 | 判据 |
|---|---|
| `review_required` | `plan.complexity == "complex"`（与 `review-passed` 的短路条件同源） |
| `open_blocking` | `open_findings(...)["blocking"]`（**门禁同源、全轮次**）；条目须带 `round`（见 §6 ①）。**只含 blocking severity**；`unaddressed` 里的非 blocking 项**不在本文范围**（它们是判断骨架的输入，不是归档阻断） |
| `unverifiable` | `open_findings(...)["unavailable"]`（唯一来源，条目带 `cause/round/report_digest`） |
| `in_flight` | **轮次**：`reviews.launches` 中大于 `result.round` 的最大轮；**`result` 缺席时取全部 launches 的最大轮**；无 launches 则 `in_flight = null`。<br>**`usable` 三态**（`true/false/null`）：<br>· `material_missing` → `null`（报告未到齐可能只是还没到，不能算失效）<br>· `eligibility_failed`（人数/异种/与实施 CLI 重叠）→ `false`，判据来自 **`review_eligibility`**（自 `review-decide` 的 `input_problems` 提取的共享函数）<br>· `anchor_stale`（该轮报告锚点已不是当前 check）→ `false`<br>三者皆无 → `true` |
| `conclusion.binding` | **`review_binding`**（自 `review-passed` 提取）：`result.check_id == check.id` ∧ **结论至少引用一份已导入报告** ∧ 引用报告 `result_digest == recorded == 文件当前摘要`。<br>**"至少引用一份"必须写进判据**：门禁对 `cited` 为空是独立拒绝（`gates.py:695-696`），漏掉它会让空引用的结论算出 `binding == true` |
| `conclusion.check_valid` | **`check_validity`**（自 `check-passed` 提取）：`result == pass` ∧ anchor 相符 ∧ 未 `invalidated` ∧ `rule_version` 相符 ∧ **结构复核 `check_result_problems`** ∧ anchor 可算 |
| 便利派生 | `applicable = binding && check_valid` **仅作展示便利**，不作为任何完成条件（条件用 C1/C4 各自的原始事实） |

### 2.2 人裁记录（乙通道）

**决定文件（`--file`，必填 schema）**

```json
{"batch": "b-1",
 "acceptances": [{"round": 1, "slot": "s1",
                  "report_digest": "sha256:…",       // 必须等于该 (round, slot) 导入记录里的登记摘要
                  "quote": "这份报告丢失的风险我认",
                  "by": "human:xzc", "at": "2026-11-11T14:00:00.000000Z",
                  "source": "user-declared"}]}
```

| 规则 | 语义 |
|---|---|
| digest 权威来源 | **导入记录里的登记摘要**，不是损坏文件的当前摘要；决定文件若与该值不等 → 整批拒绝（防 typo 生成永不匹配的记录） |
| 匹配 | `(round, slot, report_digest)` 三者全等，且该条在**当前** `unverifiable` 中出现 |
| 可放行条件 | `release_allowed = !(cited && review_required)`：complex 的引用证据不可放行；light 的引用证据可放行；非引用可放行 |
| 批次 | 全有或全无；任一项不合法 → 零写入 + `bad_items` |
| 不做预放行 | 指向当前不存在的 `(round, slot)` → 拒绝 |
| 幂等与重新批准 | 仅当**存在同一键的未撤销记录**时回报 `already_accepted` 且不新增；若唯一记录已撤销，再次批准**新增一条**（新 `batch`） |
| 撤销 | `--revoke --batch <id>` 或 `--revoke --round --slot --digest`（二者同时给出则报错，不猜优先级）；置 `revoked: true`（不删）；只影响被撤销的记录 |
| 信任模型（定案） | 沿用 attestation 四件套（`by/at/quote/source` + 摘要入库），**不引入签名**。**残余风险如实登记**：决定文件由持写权会话提交，机制无法区分"人写的"与"AI 转录/伪造的"；这是全仓既有模型（`authorize` 同级），放行通道是该模型的最高价值用途 | 

**命令**：`wf review-accept-unknown --task <id> --file <决定.json>`（含 `--revoke`）。

---

## 3. 五条语义边界

| # | 边界 | 说明 |
|---|---|---|
| **B1** | 可核实性是**当前状态** | 找回原字节（摘要一致）→ 不再出现在 `unverifiable`；人裁只用于**无法恢复**的情形 |
| **B2** | 归档依据必须可核实 | complex：`cited` 损坏由 `review-passed` 拦；light：由本方案新增分支拦。**阻断与能否放行是两件事** |
| **B3** | fail 不强制 replan，但不是禁止 | 根因在规划时 `task-replan` 仍合法 |
| **B4** | `unavailable` ≠ 异常归档 | `--unavailable` 只表示审查做不成；`task-abandon` 是不跑最终门禁的终局出口 |
| **B5** | **只有 `disposition.decision == "accepted"` 会清零** | `rejected` / `amended` 只记录、**不关闭**（`review.py:173-176` 只收 `accepted`）。因此"经复核否定该 finding"也必须写成 `accepted`，并在 `reason` 里说明处置性质（误报/重分类/已修复）。这条反直觉语义必须进 AI 指引（§6 ③） |

---

## 4. 完成条件与清除动作

**原则**：每个条件都给出**可执行的清除动作**；条件可同时不满足，机制不排顺序（§4.3）。

### 4.1 ⑥ 相关的四个完成条件

| # | 条件 | 事实来源 |
|---|---|---|
| **C1** | 检查有效 | `conclusion.check_valid` |
| **C2** | 无未关闭 blocking | `open_blocking == []` |
| **C3** | 无未放行的不可核实证据 | `unverifiable` 中 `released == false` 为空 |
| **C4** | **复杂任务**的审查结论存在、绑定当前 check 且为 pass | `review_required` 时要求 `verdict == "pass"` ∧ `binding` |

**light 任务（`review_required == false`）不承担 C4**，但 `open_blocking` 仍受 **C2**、报告损坏仍受 **C3** 约束。
**现状成本（如实）**：`dispositions` 只能经 `review-decide` 写入，而它先做人数/资格校验且**不分复杂度**——
所以 light 要关闭 C2 仍需组织一轮可判审查。**这个成本是真实负担**（也抑制自愿审查的意愿），
入口改造见 backlog **A8**（建议先做，但不是 ⑥ 的前置）。

### 4.2 每个条件的清除动作

| 条件 | 清除动作（`exits` 机制枚举，供 skill 渲染） |
|---|---|
| **C1 失效** | `rerun_check`（重跑 `task-check` 产生新 check） |
| **C2 未空** | 逐项处置（修复代码 / 经复核否定或重分类）→ 由非提出者复核后补 disposition（**`decision` 必须写 `accepted`**，B5）→ `record_disposition` |
| **C3 未放行** | ① `restore_bytes`（找回原字节，不依赖身份）② `human_release`（`release_allowed == true` 时）<br>③ **`relaunch_review`——改变事实而不是硬闯**：complex 的 `cited` 损坏不可放行，但可完成一次新审查；新结论引用新报告后，旧报告变成**非引用**证据 → 下一轮 `human_release` 即可用<br>④ 只有"上述全部不可行"才 `abandon_task`（**不得把"当前不能放行"直接推成"应放弃"**） |
| **C4 不成立** | 先看 `in_flight`：<br>· `usable == true` → `resume_inflight`（续接，不新开）<br>· `usable == false` → `relaunch_review`<br>· `usable == null`（判定不了，含 `material_missing`）或 `in_flight == null` → **`relaunch_review` 与"继续等材料"并列给出**，由 AI 判断（机制不替它选）<br>· 审查做不成（`unavailable` / 环境凑不齐）→ `pause_for_human` / `abandon_task`（B4）<br>· **事实提示（非顺序强制）**：若 `check_valid == false`，先做 C1 再发审查——否则新结论绑定的是发起时的旧 check，重查落地那一刻它立刻 `binding == false`，整轮白做 |

### 4.3 并存与顺序

- 条件可同时不满足；`repair_scope` **同时**给出全部事实，不做优先级遮蔽；
- 动作顺序、是否合并、先修哪项由 AI 判断（机制不排调度）；
- 旧结论能否复用由 C4 的事实判断，**不由表格顺序判断**。

**三个约束**：

1. **不要用"试归档"探路**（`tasks.py:3233` 会先业务提交；提交前预检见 backlog **D4**）；
2. **不得把"四条件满足"说成"可以归档"**：`wf gate` 只跑步骤面，`repair_scope` 只覆盖 ⑥ 的 C1–C4；
   escalated 待答、required 未核实、依赖未满足、debug 未裁、降级材料不完整**都不在这两处**，
   且当前**没有只读等价物**（见 §8；消除该空缺需先做 backlog **D4「归档提交前预检」**，本文不依赖它）；
3. 因此完整判断只能是"步骤面 + ⑥ 四条件 + 各自投影"，**并读三者仍不等于归档一定成功**——如实告知，不用措辞补足。

---

## 5. 与既有机制的关系 + 落地前提

| 机制 | 关系 |
|---|---|
| `phase` 枚举 / `protocol/states.json` / `next_by_position` | **不改**；`repair_scope` 不参与 `next` |
| `review-decide` 判定资格、`task-check` 语义 | **不改** |
| `review-passed` / `check-passed` | 行为不变，内部判定**提取为共享函数**（`review_binding` / `check_validity`），并在这两处做 OSError 归因 |
| `final_gate` | **只加一条**：存在 `released == false` 的 `unverifiable` → 阻断；出口按 `release_allowed` 分列 |
| `task-abandon` | **不改**：终局、不解除 |

**落地前提（五项，缺一 ⑥ 不可执行；均属另案，见 backlog）**

| 前提 | 为什么必须先做 |
|---|---|
| **A1 `slot` 身份稳定** | 放行键含 `slot`；`slot`/`agent` 混用会匹配不上 |
| **A4 导入端证据身份** | 现在可"删档后导入同轮同槽位另一份报告"顶掉历史证据 → C2/C3 可被静默清空 |
| **A7 K4b 关闭链** | `proposers_from_history` 从 `imported[].findings` 读提出者（记录不保存 findings）→ 真实修复后 disposition 被拒 |
| **A9 finding 精确身份**（新增） | 关闭匹配只按**裸 `finding_id`**（`review.py:173`）→ 旧关闭会静默关掉他轮/他槽位的同名新问题。**A7 只解决"读得到提出者"，不解决"关的是哪一个"** |
| **C1 读取归因** | `open_findings` / `review_binding` 都读摘要，权限故障会抛出；⑥ 自带这两处，其余五处属 C1 |

**披露（机制自洽但不免费）**

| 代价 | 说明 |
|---|---|
| complex 多轮累积人裁 | C3 覆盖**全部轮次**的不可核实证据：round-1 的报告即使与最终 pass 无关，损坏也要一次放行 → 轮次越多签到越多 |
| light 关闭 C2 的入口成本 | 见 §4.1 末（A8） |
| 放行通道的信任残余 | 见 §2.2 末（声明式，可伪造，仅留痕） |

---

## 6. 实现落点（批准后执行；本轮不动代码）

| 文件 | 改动 |
|---|---|
| `gates.py` | ① 提取 `review_binding`（含 **cited 非空**）与 `check_validity`（含结构复核），步骤行为不变；② 两处摘要读取包 `except OSError`；③ `final_gate` 追加 `unverifiable` 阻断，`exits` 用 §4.2 的**枚举 token**（`restore_bytes`/`human_release`/`relaunch_review`/`resume_inflight`/`pause_for_human`/`abandon_task`），并带 `facts.reason = "unverifiable_evidence"` |
| `review.py` | ① `open_findings` 的 `blocking`/`unaddressed` 条目补 **`round`**、`unavailable` 条目补 `cause/round/report_digest`，摘要读取包 `except OSError`；② 提取 **`review_input_problems`**（自 `review-decide` 的 `input_problems`，含人数/异种/重叠/verdict 一致性/材料缺口）供 `in_flight.usable` 复用；③ 新增 `repair_scope`（纯派生）与 **`exits_for(facts)`（唯一出口实现）**：返回 `[{condition, action, preferred, when}]`，`action ∈ {rerun_check, record_disposition, restore_bytes, human_release, relaunch_review, resume_inflight, await_material, pause_for_human, abandon_task}`；④ `unknown_acceptances` 读写与撤销（含决定文件 schema 校验、`release_allowed` 校验） |
| `cli.py` | `wf status` 输出 `repair_scope`；**`--short` 输出四条件是否满足 + `repair_scope.exits` 原样（按 `condition` 过滤，不重新推导）**；新增 `wf review-accept-unknown`（`--revoke`） |
| `skills/`（**AI 指引交付**） | ① `wf-continue`：`in_progress/finish` 前先读 `repair_scope`，按 §4.2 处理，不直接引导收工；② `wf-finish`：收工前读 `repair_scope`；**不要试归档探路**；③ `wf-review-action`：处置形状从现状 `{finding, decision_ref, reason}`（`SKILL.md:26`）改为 `{finding_id, round, slot, decision, reason, recheck_by}`，并写明**`decision` 必须 `accepted` 才清零**（B5）；`round/slot` 是**A9 落地后**的必填字段（A9 是本文落地前提，见 §5）——指引按 post-A9 形态写 |

**不做第二套口径**：`cause`/`round` 只在 `open_findings`；`binding`/`check_valid` 只在两个共享函数。

---

## 7. 验收（34 项，全部属于 ⑥）

| # | 断言 |
|---|---|
| 1 | `open_blocking` 与 `final_gate` 的 `unaddressed_blocking` 逐项一致（同源、全轮次），且每条带 `round` |
| 2 | `binding` 是子判定：`verdict == "fail"`、check 未换代、引用摘要一致 → `binding == true`（不因 `verdict != pass` 而 false） |
| 3 | **`binding` 空引用即为 false**：结论 `imported` 为空时 `binding == false`（与 `gates.py:695` 的拒绝对齐） |
| 4 | `check_valid` 与门禁逐分支一致（结构复核、`invalidated`、anchor 计算失败、`rule_version`） |
| 5 | 内容改动未重查 → `check_valid == false`、`check_blockers` 含 anchor 漂移（C1 未满足） |
| 6 | 重查产生新 check → `binding == false`（`check_id_changed`），`open_blocking` 不消失（B5） |
| 7 | **只写 `accepted` 才清零**：`decision == "rejected"`/`"amended"` 后 `open_blocking` 仍非空（B5 反直觉语义） |
| 8 | `verdict == "fail"` ∧ `binding` ∧ `open_blocking` 已清 → C4 未满足，`exits` 含 `relaunch_review` / `resume_inflight` |
| 9 | **`in_flight.usable == true` 时默认出口是 `resume_inflight`**（`verdict` 仍是上一轮 fail 也要先续接）；不可用才 `relaunch_review` |
| 10 | complex：`cited` 损坏 → `release_allowed == false`，`human_release` 不在 `exits` |
| 11 | light：`cited` 损坏 → 仍阻断，且 `release_allowed == true`，`human_release` 在 `exits`；放行后 C3 满足 |
| 12 | 非引用损坏 + 摘要全等放行 → C3 满足；撤销后恢复；匹配需三元组全等 |
| 13 | **决定文件 schema**：digest 与登记摘要不等 → 整批拒绝（防 typo 生成永不匹配记录）；缺 `quote`/`source` → 拒绝 |
| 14 | 撤销后**可重新批准**：批准 → 撤销 → 再批准，`released` 回到 true；幂等只在"存在未撤销记录"时生效 |
| 15 | 报告恢复原字节 → 不再出现在 `unverifiable`（B1） |
| 16 | `cause` 三分只由 `open_findings` 产出，`repair_scope.unverifiable` 与之逐项一致 |
| 17 | 权限故障不崩：`open_findings`、`review_binding`、`status`、`wf gate` 全部走归因分支 |
| 18 | 并存无遮蔽：`open_blocking` 非空同时有未放行 `unverifiable` 时，两组事实**同时**出现 |
| 19 | 条件覆盖性：任一未满足的 C1–C4 都有 `exits`（非空枚举）；**每个事实要么映射到某个 C，要么用于选择某个 C 的清除动作**（`in_flight` 属后者；`applicable` 仅便利派生，不算事实） |
| 20 | **light 不承担 C4**：自愿审查 `fail`/`unavailable`/`invalidated` 且 `open_blocking` 空、C1/C3 满足 → 不产生"必须取得新审查结论"义务 |
| 21 | 但 light 的 C2/C3 仍成立：自愿审查带 blocking → 未关闭时归档被 `WF_UNRESOLVED_BLOCKING` 拒；报告损坏 → C3 阻断 |
| 22 | **C4 的 unavailable 出口**：审查做不成 → `exits` 含 `pause_for_human` 与 `abandon_task`，且不含"判 pass"类出口 |
| 23 | 主动性约束：`repair_scope` 不含"等待评审/待评审确认"类状态；除 complex C4 外，未满足条件都能在不取得新审查结论的前提下推进 |
| 24 | `--short` 输出四条件+`exits`，不输出完整事实集；`task.check` 字段派生等其余 `--short` 改动仍属 backlog |
| 25 | 协议零改动：`phase.enum`、迁移数、`next_by_position` 逐字节一致；`repair_scope` 不参与 `next`；`task-abandon` 仍可终止且不解除阻断 |
| 26 | `in_flight.usable` 三态：`material_missing` → `null`（不得算失效）；资格不合格 / 锚点失效 → `false`；皆无 → `true`；`result` 缺席时轮次取 launches 最大值；无 launches 时 `in_flight == null` |
| 27 | `usable` 与 decide 同源：`eligibility_failed` 的判据来自 `review_eligibility`（自 `review-decide` 的 `input_problems` 提取），不得另写一套 |
| 28 | C3 有「改变事实」的出口：complex 的 `cited` 损坏时 `exits` 含 `relaunch_review`（新结论落地后旧报告变非引用）；`abandon_task` 不得作为首选 |
| 29 | C4 的事实提示**准确**：只说「结论写入后再重查会失绑」，**不得**声称「发起早就会失绑」；先重查是建议而非机制事实 |
| 30 | `usable` 吸收输入无效：已导入报告存在"申报 verdict 与推导不一致"→ `usable == false` 且 `usable_blockers` 含 `input_invalid`（判据来自 `review_input_problems`，与 `review-decide` 同源） |
| 31 | `usable` 吸收检查过期：`check_valid == false`（内容已变未重查）→ `usable == false`、`usable_blockers` 含 `check_stale`，此时**不得**以 `resume_inflight` 作默认出口 |
| 32 | `exits` 形状与落点：`[{condition, action, preferred, when}]`，**只由 `exits_for` 产出**；`--short` 原样过滤输出，不重新推导（无第二份出口表） |
| 33 | `in_flight == null`（无任何已发起轮）时 `exits` 不含 `await_material`；`usable == null`（材料未到齐）时 `await_material` 与 `relaunch_review` 并列且**均非默认** |
| 34 | 决定文件四件套：缺 `by`/`at`/`quote`/`source` 任一 → 拒绝（`by` 必须 `human:` 前缀） |

## 8. 范围边界（防跑偏，硬约束）

本文只回答 ⑥。不在范围（详见 `analysis/backlog-excluded-from-item6.md`）：
`slot`/`agent` 身份域（**A1 为前提**）、导入端证据身份与 `--restore`（**A4 为前提**）、
关闭链提出者（**A7**）、**finding 精确身份（A9）**、`review-status` 的 ready/material 语义、
六处读取健壮中的其余五处（**C1**）、`gate` 的 `fulfilled_by`、其余 `--short` 字段派生与展示分组、
维护入口令牌交互、码表新增（⑦）、历史 dispositions 迁移、归档提交前预检（**D4**）、
仅登记复核关闭的轻量入口（**A8**）。

---

## 9. 本文的历史（只留与 ⑥ 相关的关键否决）

| 版本 | 形态 | 为什么被否 |
|---|---|---|
| v3 / v4 | `fixing` 阶段 / `repair` 标记 | 与 v42 枚举冲突；主路径清不掉 |
| v20–v24 | 大 schema | 偏题；事实过载 |
| v25 | 单值 `reason` + 常量字段 | 并存事实互相遮蔽；指引伪装成事实 |
| v26 | 三组事实 + 出口表 | `bound_to_current` 漏内容变化；`cited` 排除使 light 漏检；无清零路径 |
| v27 | 加 `check_valid` | `binding` 误用整个 `review-passed` 返回值；`check_valid` 枚举漏结构复核；出口表行间重叠 |
| v28 | 共享子判定 + `release_allowed` | 出口表仍是固定优先级；light 的 fail/unavailable 写成义务 |
| v29 | 完成条件 C1–C4 | C4 丢默认动作；light 写成「无义务」；`invalidated` 被写成禁止重新发起 |
| v30 | 恢复 C4 出口 + light 义务收窄 | 前提漏 A7/A9；技能层未交付；撤销后重新批准未定义 |
| v31 | 落地前提**四项**（A1/A4/A7/C1）+ 技能交付 | `binding` 缺「引用非空」；`decision` 语义未交代；`open_blocking` 缺 `round`；示例把 `agent` 当 `slot`；决定文件 schema 未定义 |
| v32 | 增「主动性」设计约束（§1a） | 规范本身要求固定顺序与产出数量，反而制造工作 |
| v33 | `binding` 含引用非空、`in_flight`、`exits` 枚举、决定文件 schema、B5、前提增 A9（五项） | 「gate + repair_scope 是完整依据」过度承诺；决定文件缺 `by/at`；C3 把「暂时不能放行」推成「应放弃」；`usable` 无判据 |
| v34 | `usable` 三态 + `review_eligibility`、C3 补「改事实」出口、完整性口径三段、`by/at` 入 schema | `usable` 未吸收「输入无效」与「检查过期」；`exits` 形状与落点未定（第三份出口表风险）；「先重查否则白做」的依据与实现不符；§4.3 引错 backlog 条目 |
| **v35** | `usable` 五项判据（含 `input_invalid`/`check_stale`）、`exits_for` 单点产出 + 对象形状、`await_material` token、事实提示纠正、引用改正 | 本文 |

## 10. 已定项（2026-11-11 人裁）

| # | 问题 | 裁定 |
|---|---|---|
| D1 | 不可核实证据阻断用哪个码 | 复用 `WF_REVIEW_INVALID` + `facts.reason = "unverifiable_evidence"` |
| D2 | 人裁是否引入签名 | 不引入；沿用声明式 attestation（残余风险见 §2.2） |

> Q1=乙、Q2=甲 亦已定。本文无待决项。
