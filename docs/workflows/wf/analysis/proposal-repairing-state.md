# ⑥ 修复态的表达：不新增阶段，用「事实 + 清除动作」吸收 `fixing` 的收益（v42）

> 状态：**待审 v42**。阶段：**方案审查阶段，实现零改动**（`review-phase-discipline.md`）。
> §6 是**待实施清单（全部未实施）**，**不是已完成的工作**；当前 `payload/`、`release/`、`scripts/tests/`
> 与基线 `8da2f23` **逐字节一致**（`git diff` 为空）。
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
  "rounds": [{"round": 1, "verdict": "pass", "check_id": "C1",
              "decided_at": "…", "invalidated_reason": null}],   // 逐轮决策事实（新增，见下）
  "latest_launch": {"round": 2, "imported": 2, "declared": 2, "form": "discovered"},
  "in_flight": {"round": 2, "imported": 2, "declared": 2,
                "usable": true,                                  // true | false | null
                "usable_blockers": ["report_invalid|anchor_stale|implementer_overlap|standard_drift_unjudged|insufficient_reviewers|material_missing"]},
  "redecidable_rounds": [1],        // 已判 pass、check 换代、报告仍匹配、未失效
  "open_blocking": [{"round": 1, "slot": "s1", "finding_id": "f1", "severity": "blocker"}],
  "unverifiable": [{"round": 1, "slot": "s1", "path": "…", "report_digest": "sha256:…",
                    "cause": "changed|missing|unreadable", "cited": false,
                    "release_allowed": true, "released": false, "consumed": false}],
  "conclusion": {"decided": false, "verdict": null, "round": null, "check_id": null,
                 "binding": false, "binding_blockers": [],
                 "check_valid": true, "check_blockers": []},
  "exits": [{"condition": "C4", "action": "relaunch_review", "preferred": null, "when": null}]
}
```

**判据（每项都写成"调用哪个共享判定"；枚举仅说明，以判定实现为准）**

| 事实 | 判据 |
|---|---|
| `review_required` | `plan.complexity == "complex"`（与 `review-passed` 的短路条件同源） |
| `open_blocking` | `open_findings(...)["blocking"]`（**门禁同源、全轮次**）；条目须带 `round`（见 §6 ①）。**只含 blocking severity**；`unaddressed` 里的非 blocking 项**不在本文范围**（它们是判断骨架的输入，不是归档阻断） |
| `unverifiable` | `open_findings(...)["unavailable"]`（唯一来源，条目带 `cause/round/report_digest`） |
| `rounds[]` | **新增的逐轮决策事实**（`review_decide` 追加，append-only）：每条 `{round, verdict, check_id, decided_at, invalidated_reason}`。它是 A10 的**最小形态**——不重建历史调度，只记「哪轮判过、判成什么」。写点在 `decide` 已有写路径内（`review.py:1436-1446` 同时写 `attempts`），成本一行级；有了它，`certain` 三值死区不再需要。<br>| `latest_launch` | 最新一轮 = `max(launches.round)`；带 `imported/declared` 与 **`form`**（`discovered` | `legacy`，见 §2.1a）。<br>| `in_flight` | **最大「未判定」轮** = `max(launches.round)` 中不在 `rounds[]` 里的轮；全部已判则为 `null`。历史不确定性不再影响材料核验——**这解决了上一版 `certain == false` 把「材料是否合格」一起降级的问题**。<br>**`usable` 三态**（只判**该轮材料与资格**，与历史无关）：<br>① 任一**硬失败** → `false`：`report_invalid`（←`review_report_problems`）、`anchor_stale`（同函数）、`implementer_overlap`（←`review_eligibility`，逐报告即判）、**`standard_drift_unjudged`**（该轮 `imported` 条目带 `standard_drift` 且无「标准变更/沿用」judgment——`decide` 进入即被 `standard_drift_gate` 拒，`review.py:1212`）<br>② 无硬失败，且已导入材料已足够（`form == discovered` 时按去重 reviewer CLI ≥2；`form == legacy` 时按声明槽位是否齐）→ `true`<br>③ 无硬失败、已导入不足、仍有槽位未到 → `null`<br>④ 无硬失败、已导入不足、槽位已齐 → `false`（`insufficient_reviewers`）<br>| `redecidable_rounds[]` | `rounds[]` 中满足：`verdict == pass` ∧ `check_id != 当前 check` ∧ 该轮报告**摘要一致且锚点匹配当前内容** ∧ `invalidated_reason == null`。可对该轮重新 `review-decide`（`decide(..., round_no=…)`，`review.py:1201`），不必新开。<br>**已判 fail 的轮不列入**：verdict 由报告载荷推导（`review.py:1351`），dispositions 不参与，重判仍 fail。<br>**`usable_blockers` 内容**：列出**全部**成立的项（含 `material_missing`），按严重度排序（硬失败在前）；`usable` 的取值只由上面的优先级决定，不由列表长度决定。<br>**如实说明（P3）**：部分导入时若强行 `review-decide`，报错是「single reviewer cannot produce a decision」（新形态下 `missing_slots` 恒为空，不报「声明槽位缺报告」）——AI 看到的是人数问题而非材料问题，两者不同源，指引不得混为一谈 |
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
                  "source": "user-declared",
                  "waive_unknown_findings": true}]}   // 必填：承认该报告未知 findings 一并豁免；恢复可核实后经受控写点置 consumed
```

| 规则 | 语义 |
|---|---|
| digest 权威来源 | **导入记录里的登记摘要**，不是损坏文件的当前摘要；决定文件若与该值不等 → 整批拒绝（防 typo 生成永不匹配的记录） |
| 匹配 | `(round, slot, report_digest)` 三者全等，且该条在**当前** `unverifiable` 中出现 |
| 可放行条件 | `release_allowed = !(cited && review_required)`：complex 的引用证据不可放行；light 的引用证据可放行；非引用可放行 |
| **`released` 定义** | 存在 `(round, slot, report_digest)` 全等、**未撤销且未消费**（`revoked == false && consumed == false`）的放行记录；三者缺一即不算已放行 |
| 批次 | 全有或全无；任一项不合法 → 零写入 + `bad_items` |
| 不做预放行 | 指向当前不存在的 `(round, slot)` → 拒绝 |
| 幂等与重新批准 | 仅当**存在同一键的未撤销记录**时回报 `already_accepted` 且不新增；若唯一记录已撤销或**已消费**，再次批准**新增一条**（新 `batch`） |
| **一次一事件：恢复即消费** | 放行是针对「当次不可核实情形」的决定，不是永久豁免。**写点（三个，均为既有写命令）**：① `wf archive` 在 `final_gate` 之前的钩子（归档时必然扫到）；② `wf review-import`；③ `wf review-decide`。任一命令发现「某条放行记录对应的报告当前可核实」→ 置 `consumed: true`。**保证范围（精确化，第 35 轮）**：机制保证的是「**受控写点观察到恢复后，该放行失效**」；它**不**保证「任何一次恢复都结束原豁免」。未保护的端点是：恢复 → 期间无任何写命令 → 再次损坏 → 归档，此时所有观察点看到的都是「损坏」，旧放行生效——**归档前钩子只兜住「归档时报告仍可核实」那一支**，对这条端点无能为力。如实登记，不夸大兜底；若要更强，需要持久化恢复事件或更强信任模型（另案 A11） |
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

## 3a. 「问题是否已了结」的三种状态（本版新增，统一 C2/C3 的口径）

| 状态 | 事实来源 | 是否进 `closed` | 显示/文案要求 |
|---|---|---|---|
| **已处置** | `disposition.decision == "accepted"`（B5） | **进** | 可写"已关闭" |
| **已豁免（未知）** | 报告不可核实 + 人裁放行（`waive_unknown_findings: true`） | **不进** | 只能写"该证据已由人接受风险，其中未知 findings 一并豁免"；**不得**写"已处置/已关闭" |
| **未知（未放行）** | 报告不可核实、未放行 | —— | C3 未满足，阻断归档 |

**C2 与 C3 的分工（消除上一版的自相矛盾）**：`open_blocking` 只枚举**可读报告**里的 blocking；
不可核实报告里的 findings **从不进入 C2**（`open_findings` 整份跳过）。因此 C2 = "可枚举的 blocking 已清"，
**不等于"所有缺陷都已处置"**；后者包含不可枚举的部分，只能通过 C3 的人裁豁免来表达。
**放行既不会、也不需要改变 C2**——它只解除 C3，并把那一部分标记为"已豁免（未知）"。

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
**这是 ⑥ 唯一不交付「AI 自主闭环」的地方**：单项处置已有依据与复核，仍被整轮审查卡住。是否接受该成本见待裁 D3；不接受就把 A8 提升为前置（本版不擅自决定）。

### 4.2 每个条件的清除动作

| 条件 | 清除动作（`exits` 机制枚举，供 skill 渲染）。**`preferred` 只在机制能判定可行性时置 true**：`resume_inflight`（`usable == true`）可置 true；`restore_bytes` 的可行性机制不知道 → `preferred: null`；`human_release` 一律 `false` |
|---|---|
| **C1 失效** | `rerun_check`（重跑 `task-check` 产生新 check） |
| **C2 未空** | 逐项处置（修复代码 / 经复核否定或重分类）→ 由非提出者复核后补 disposition（**`decision` 必须写 `accepted`**，B5）→ `record_disposition` |
| **C3 未放行** | ① `restore_bytes`（找回原字节，不依赖身份）<br>② `human_release`（`release_allowed == true` 时）——**放行的语义边界（本版新增）**：某份报告不可核实时，它里面的 findings 也随之无法枚举（`open_findings` 跳过整份报告），因此放行**必然同时豁免该报告中未知的 findings**。决定文件必须显式承认这一点（`waive_unknown_findings: true`），缺失即拒；**且不得把放行描述成"缺陷已处置"**——C2 不会因此被满足，只是那部分问题从此不可枚举<br>③ `relaunch_review`——改变事实而不是硬闯：complex 的 `cited` 损坏不可放行，但可完成一次新审查；新结论引用新报告后，旧报告变成**非引用**证据 → 下一轮 `human_release` 即可用<br>④ 只有"上述全部不可行"才 `abandon_task`（**不得把"当前不能放行"直接推成"应放弃"**） |
| **C4 不成立** | 先看 `in_flight`：<br>· `in_flight == null`（全部轮已判）且 `redecidable_rounds` 为空 → `relaunch_review`<br>· `in_flight == null` 且 `redecidable_rounds` 非空 → `redecide_round`（对那轮重新 `review-decide`，不必新开；这是**另一个动作**，不是「续接在途轮」）<br>· `in_flight != null` 且 `usable == true` → 默认 `resume_inflight`（去把该轮判定完成）<br>· `in_flight != null` 且 `usable == false` → `relaunch_review`（`usable_blockers` 逐项给原因；含 `standard_drift_unjudged` 时先补标准判断）<br>· `in_flight != null` 且 `usable == null`（已导入不足、仍有槽位未到）→ `await_material` 与 `relaunch_review` 并列、均非默认<br>· 审查做不成（`unavailable` / 环境凑不齐）→ `pause_for_human` / `abandon_task`（B4）<br>**事实提示（非顺序强制）**：`check_valid == false` 只说明当前检查不能用于完成任务，不证明在途轮作废——结论绑定判定那一刻的 check（`review.py:1425`）；可先重查再核对材料后继续用原轮，只有结论写入后再重查才失绑。**已知盲区如实声明**：`usable`/`redecidable_rounds` 已含标准漂移与资格事实，但 `decide` 仍是权威——任何字段与实际判定不一致时以 `decide` 的报错为准 |

### 4.3 并存与顺序

- 条件可同时不满足；`repair_scope` **同时**给出全部事实，不做优先级遮蔽；
- 动作顺序、是否合并、先修哪项由 AI 判断（机制不排调度）；
- 旧结论能否复用由 C4 的事实判断，**不由表格顺序判断**。

**三个约束**：

1. **不要用"试归档"探路**（`tasks.py:3233` 会先业务提交）。**但这只防探路，不保护正常归档调用**：提交发生在 `final_gate` 之前，因此「业务已提交、归档因 C3 被拒」在 D4 落地前**仍可能发生**——所以 **D4（归档提交前预检）是⑥的安全前提**（见 §5）：不属可执行性前提，但缺它这条门禁就不安全；
2. **不得把"四条件满足"说成"可以归档"**：`wf gate` 只跑步骤面，`repair_scope` 只覆盖 ⑥ 的 C1–C4；
   escalated 待答、required 未核实、依赖未满足、debug 未裁、降级材料不完整**都不在这两处**，
   且当前**没有只读等价物**（见 §8）。此处「不依赖」指**完整性声明**不依赖 D4；**安全性**依赖见 §5 的安全前提；
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

**前提（两层，均属另案，见 backlog）**

| 前提 | 为什么必须先做 |
|---|---|
| **A1 `slot` 身份稳定** | 放行键含 `slot`；`slot`/`agent` 混用会匹配不上 |
| **A4 导入端证据身份** | 现在可"删档后导入同轮同槽位另一份报告"顶掉历史证据 → C2/C3 可被静默清空 |
| **A7 K4b 关闭链** | `proposers_from_history` 从 `imported[].findings` 读提出者（记录不保存 findings）→ 真实修复后 disposition 被拒 |
| **A9 finding 精确身份**（新增） | 关闭匹配只按**裸 `finding_id`**（`review.py:173`）→ 旧关闭会静默关掉他轮/他槽位的同名新问题。**A7 只解决"读得到提出者"，不解决"关的是哪一个"** |
| **C1 读取归因** | `open_findings` / `review_binding` 都读摘要，权限故障会抛出；⑥ 自带这两处，其余五处属 C1 |
| ~~D4~~（**已纳入 §6 待实施清单**） | 原本确实需要它（C3 阻断挂在 `final_gate` 尾部、业务提交在前）。本版把 **D4-minimal** 写进 §6 的实施清单，**批准后**才做，因此不再是外部前提 |
| ~~A8~~（归入「成本前提」，见本节末） | A8 不属可执行性前提：没有它 light 关 C2 贵但能走通 |

**前提分层（本版明确，消除上一版的计数与性质混乱）**

| 层 | 项 | 缺了会怎样 |
|---|---|---|
| **可执行性前提** | A1、A4、A7、A9、C1 | ⑥ 的事实或清除动作**算不出来**，必须先做。（A10「逐轮决策事实」仅当要恢复「复用旧轮」能力时才成为前提——本文已撤回该能力，故不列） |
| **本方案自带（非外部前提）** | D4-minimal（归档提交前预检） | 已列入 §6 待实施清单（状态：未实施）；**批准后**才做 |
| **成本前提** | A8（轻量关闭入口） | light 关 C2 需要一整轮审查（贵但能走通）；建议先做，不作前置 |

**披露（机制自洽但不免费）**

| 代价 | 说明 |
|---|---|
| complex 多轮累积人裁 | C3 覆盖**全部轮次**的不可核实证据：round-1 的报告即使与最终 pass 无关，损坏也要一次放行 → 轮次越多签到越多 |
| light 关闭 C2 的入口成本 | 见 §4.1 末（A8） |
| 放行通道的信任残余 | 见 §2.2 末（声明式，可伪造，仅留痕） |

---

## 6. 待实施清单（**全部未实施**；批准后按此执行）

| 文件 | 状态 | 改动 |
|---|---|---|
| `gates.py` | 未实施 | ① 提取 `review_binding`（含 **cited 非空**）与 `check_validity`（含结构复核），步骤行为不变；② 两处摘要读取包 `except OSError`；③ `final_gate` 追加 `unverifiable` 阻断，`exits` 用 §4.2 的**枚举 token**（`restore_bytes`/`human_release`/`relaunch_review`/`resume_inflight`/`pause_for_human`/`abandon_task`），并带 `facts.reason = "unverifiable_evidence"` |
| `review.py` | 未实施 | ① `open_findings` 的 `blocking`/`unaddressed` 条目补 **`round`**、`unavailable` 条目补 `cause/round/report_digest`，摘要读取包 `except OSError`；② `review-decide` **追加 `reviews.rounds[]`**（`{round, verdict, check_id, decided_at, invalidated_reason}`，与 `attempts` 同一写路径）；并对同批 `decision != accepted` 的 open finding 在 `facts.not_closing` 里回报（「已驳回但未关闭」）；`review-import` 与 `review-decide` 各加**消费检查**（对应报告当前可核实 → 置 `consumed`）； ③ 提取**两个**共享函数（对应 `review-decide` 的两个既有通道，不合并、不混态）：**`review_eligibility`** ← `input_problems`（人数/异种/与实施 CLI 重叠）、**`review_report_problems`** ← `problems`（该通道含：申报 verdict 与推导不一致、**报告锚点失配**、报告事后改写、缺 `read-scope`/`excluded-scope`、敏感面缺口、未覆盖全部审查轴等）；`latest_launch.usable` 只用这两个，不自行判资格；③ 新增 `repair_scope`（纯派生）与 **`exits_for(facts)`（唯一出口实现）**：返回 `[{condition, action, preferred, when}]`，`action ∈ {rerun_check, record_disposition, restore_bytes, human_release, relaunch_review, resume_inflight, await_material, pause_for_human, abandon_task}`；④ `unknown_acceptances` 读写与撤销（含决定文件 schema 校验、`release_allowed` 校验） |
| `tasks.py` | 未实施 | ① **D4-minimal（纳入本方案实施范围，批准后实施；当前未实施）**：`cmd_archive` 在**业务提交之前**跑只读预检——`open_blocking` 为空 ∧ 无未放行 `unverifiable` ∧ `nonstep` 无阻断；任一不满足即返回（**不提交**）；② `cmd_archive` 在业务提交与 `final_gate` **之前**加钩子：扫描 `unknown_acceptances`，凡对应报告**当前可核实**者置 `consumed: true`（消费写点 ①）；该钩子只写任务记录，不影响归档顺序 |
| `cli.py` | 未实施 | ① `wf status` 输出 `repair_scope`，`unverifiable` 条目**渲染三态标签**、`open_blocking` 中「已驳回但未关闭」单独标注；（未放行＝阻断 / `released`＝「已豁免（未知）」）；② `--short` 输出四条件是否满足 + `repair_scope.exits` 原样（按 `condition` 过滤，不重新推导）；③ 新增 `wf review-accept-unknown`（`--revoke`，含 `consumed` 标记逻辑） |
| `skills/`（**AI 指引交付**） | 未实施 | ① `wf-continue`：`in_progress/finish` 前先读 `repair_scope`，按 §4.2 处理，不直接引导收工；② `wf-finish`：收工前读 `repair_scope`；**不要试归档探路**；③ `wf-review-action`：处置形状从现状 `{finding, decision_ref, reason}`（`SKILL.md:26`）改为 `{finding_id, round, slot, decision, reason, recheck_by}`，并写明**`decision` 必须 `accepted` 才清零**（B5）；`round/slot` 是 A9 落地后的必填字段（A9 是可执行性前提，见 §5）——指引按 post-A9 形态写 |

**不做第二套口径**：`cause`/`round` 只在 `open_findings`；`binding`/`check_valid` 只在两个共享函数。

---

## 7. 验收

**分两档**：A 档=机制可测（代码/事实/门禁行为，可自动化）；B 档=文档审查（指引措辞，需人读，**不计入自动化计数**）。上一版把两档混在一张 49 项表里，导致「承诺名实不符」。

### A 档：机制可测（46 项）

| # | 断言 |
|---|---|
| A1 | `open_blocking` 与 `final_gate` 的 `unaddressed_blocking` 逐项一致（同源、全轮次），且每条带 `round` |
| A2 | `binding` 是子判定：`verdict == "fail"`、check 未换代、引用摘要一致 → `binding == true`（不因 `verdict != pass` 而 false） |
| A3 | **`binding` 空引用即为 false**：结论 `imported` 为空时 `binding == false`（与 `gates.py:695` 的拒绝对齐） |
| A4 | `check_valid` 与门禁逐分支一致（结构复核、`invalidated`、anchor 计算失败、`rule_version`） |
| A5 | 内容改动未重查 → `check_valid == false`、`check_blockers` 含 anchor 漂移（C1 未满足） |
| A6 | 重查产生新 check → `binding == false`（`check_id_changed`），`open_blocking` 不消失（B5） |
| A7 | **只写 `accepted` 才清零**：`decision == "rejected"`/`"amended"` 后 `open_blocking` 仍非空（B5 反直觉语义） |
| A8 | `verdict == "fail"` ∧ `binding` ∧ `open_blocking` 已清 → C4 未满足，`exits` 含 `relaunch_review` / `resume_inflight` |
| A9 | `latest_launch.usable == true` 时**默认出口**是 `resume_inflight`（即使 `verdict` 仍是上一轮 fail）；`usable == false` 时才给 `relaunch_review` |
| A10 | complex：`cited` 损坏 → `release_allowed == false`，`human_release` 不在 `exits` |
| A11 | light：`cited` 损坏 → 仍阻断，且 `release_allowed == true`，`human_release` 在 `exits`；放行后 C3 满足 |
| A12 | 非引用损坏 + 摘要全等放行 → C3 满足；撤销后恢复；匹配需三元组全等 |
| A13 | **决定文件 schema**：digest 与登记摘要不等 → 整批拒绝（防 typo 生成永不匹配记录）；缺 `quote`/`source` → 拒绝 |
| A14 | 撤销后**可重新批准**：批准 → 撤销 → 再批准，`released` 回到 true；幂等只在"存在未撤销记录"时生效 |
| A15 | 报告恢复原字节 → 不再出现在 `unverifiable`（B1） |
| A16 | `cause` 三分只由 `open_findings` 产出，`repair_scope.unverifiable` 与之逐项一致 |
| A17 | 权限故障不崩：`open_findings`、`review_binding`、`status`、`wf gate` 全部走归因分支 |
| A18 | 并存无遮蔽：`open_blocking` 非空同时有未放行 `unverifiable` 时，两组事实**同时**出现 |
| A19 | 条件覆盖性：任一未满足的 C1–C4 都有 `exits`（非空枚举）；**每个事实要么映射到某个 C，要么用于选择某个 C 的清除动作**（`latest_launch` 属后者；`applicable` 仅便利派生，不算事实） |
| A20 | **light 不承担 C4**：自愿审查 `fail`/`unavailable`/`invalidated` 且 `open_blocking` 空、C1/C3 满足 → 不产生"必须取得新审查结论"义务 |
| A21 | 但 light 的 C2/C3 仍成立：自愿审查带 blocking → 未关闭时归档被 `WF_UNRESOLVED_BLOCKING` 拒；报告损坏 → C3 阻断 |
| A22 | **C4 的 unavailable 出口**：审查做不成 → `exits` 含 `pause_for_human` 与 `abandon_task`，且不含"判 pass"类出口 |
| A23 | 主动性约束：`repair_scope` 不含"等待评审/待评审确认"类状态；除 complex C4 外，未满足条件都能在不取得新审查结论的前提下推进 |
| A24 | `--short` 输出四条件+`exits`，不输出完整事实集；`task.check` 字段派生等其余 `--short` 改动仍属 backlog |
| A25 | 协议零改动：`phase.enum`、迁移数、`next_by_position` 逐字节一致；`repair_scope` 不参与 `next`；`task-abandon` 仍可终止且不解除阻断 |
| A26 | `latest_launch.usable` 三态合成：**硬失败**（`report_invalid` / `anchor_stale` / `implementer_overlap`）→ `false`；无硬失败且**发现式轮次**里已导入材料足够（≥2 个互异 reviewer CLI）→ `true`；已导入不足且仍有槽位未到 → `null`；已导入不足且槽位已齐 → `false`（`insufficient_reviewers`）；**旧槽位形态**下声明槽位未齐 → `null` |
| A27 | `usable` 与 decide 同源：`implementer_overlap`/`insufficient_reviewers` 来自 `review_eligibility`（`input_problems` 通道），`report_invalid`/`anchor_stale` 来自 `review_report_problems`（`problems` 通道）；两通道不得合并 |
| A28 | C3 有「改变事实」的出口：complex 的 `cited` 损坏时 `exits` 含 `relaunch_review`（新结论落地后旧报告变非引用）；`abandon_task` 不得作为首选 |
| A29 | C4 的事实提示**准确**：只说「结论写入后再重查会失绑」，**不得**声称「发起早就会失绑」；先重查是建议而非机制事实 |
| A30 | `usable` 吸收输入无效：已导入报告存在「申报 verdict 与推导不一致」→ `usable == false`、`usable_blockers` 含 `report_invalid`（判据来自 `review_report_problems`，与 `review-decide` 的 `problems` 通道同源） |
| A31 | **`check_valid == false` 不进 `usable_blockers`**：它只说明"当前检查不能用于完成任务"，不证明在途轮作废；此时 `exits` 必须给出「先重查，再核对材料后继续用原轮」的依据，而不是强制 `relaunch_review` |
| A32 | `exits` 形状与落点：`[{condition, action, preferred, when}]`，**只由 `exits_for` 产出**；`--short` 原样过滤输出，不重新推导（无第二份出口表） |
| A33 | `in_flight == null`（无任何已发起轮）时 `exits` 不含 `await_material`；`usable == null`（材料未到齐）时 `await_material` 与 `relaunch_review` 并列且**均非默认** |
| A34 | 决定文件四件套：缺 `by`/`at`/`quote`/`source` 任一 → 拒绝（`by` 必须 `human:` 前缀） |
| A35 | 共享函数二分：`implementer_overlap` / `insufficient_reviewers` 来自 `review_eligibility`（`input_problems` 通道），`report_invalid` 来自 `review_report_problems`（`problems` 通道）；两通道不得合并（否则搅浑 S4 的 invalid 态边界） |
| A36 | **部分导入 + 硬失败**：声明 2 槽位、只导入 1 份且该份 `report_invalid`/`anchor_stale` → `usable == false`（**不得**因材料未齐而报 `null`） |
| A37 | **部分导入（无硬失败）**：发现式轮次里声明 3 位只到 2 位且两位互异 → `usable == true`；只到 1 位 → `usable == null`；**旧槽位形态**下声明槽位未齐 → `null`（decide 会以 declared slots missing 拒） |
| A38 | **豁免后原字节恢复**：报告重新可核实 → 离开 `unverifiable`、findings 重新枚举 → C2 重新可能不满足；此前的 `waive` 记录**不**覆盖新枚举出的 findings（B1 的"事实变化"对偶面） |
| A39 | **一次一事件**：丢失→放行→恢复（离开 `unverifiable`）后该放行标 `consumed`；再次损坏时**旧放行不再生效**，C3 重新阻断，需新的放行决定 |
| A40 | **资格拆两类**：已导入报告的 reviewer CLI 与实施 CLI 相同 → 材料未齐时也立即 `usable == false`（`implementer_overlap`）；仅"去重人数不足"才等到材料齐后判定（`insufficient_reviewers`） |
| A41 | **`usable_blockers` 内容**：硬失败与 `material_missing` 并存时**全部列出**（硬失败在前），`usable` 取值只由优先级决定 |
| A42 | **`released` 三条件**：未撤销 **且未消费** 才算已放行；`consumed: true` 的旧记录不再解除 C3 |
| A43 | **消费写点**：`wf archive` 的 `final_gate` 前置钩子、`review-import`、`review-decide` 三处发现「记录对应报告当前可核实」即置 `consumed`；**残余窗口（恢复后未发生写命令又损坏）不在保证内**，归档钩子只兜住「归档时报告仍可核实」那一支 |
| A44 | **`reusable_rounds` 已撤回**：`repair_scope` 不含该字段；C4 的 `exits` 不出现基于「旧轮可复用」的推荐（逐轮决策/失效事实缺失，见 backlog A10） |
| A45 | **消费保证的范围**：只保证「受控写点观察到恢复即失效」；「恢复后在无写命令期间再次损坏」**不在保证内**，归档钩子只兜住「归档时报告仍可核实」那一支 |
| A46 | **`redecidable_rounds` 窄口径**：只含 `result.round` 那轮且 `verdict == pass`、其报告摘要与锚点仍匹配 → 可对该轮重新 decide；已判 fail 的轮不列入 |

### B 档：文档审查（2 项，人读勾选）

| # | 要求 |
|---|---|
| B1 | 放行的语义边界（可测形式）：决定文件缺 `waive_unknown_findings: true` → 拒绝；**放行命令不写任何 disposition、不向 `closed` 添加条目**（放行只改 C3，不改 C2）；`wf status` 必须把 `released` 条目渲染为「已豁免（未知）」而非「已关闭」 |
| B2 | **部分导入时 decide 的报错形态**：指引须说明报错是「single reviewer cannot produce a decision」，不是「声明槽位缺报告」 |

## 8. 范围边界（防跑偏，硬约束）

本文只回答 ⑥。不在范围（详见 `analysis/backlog-excluded-from-item6.md`）：
`slot`/`agent` 身份域（**A1 为前提**）、导入端证据身份与 `--restore`（**A4 为前提**）、
关闭链提出者（**A7**）、**finding 精确身份（A9）**、`review-status` 的 ready/material 语义、
六处读取健壮中的其余五处（**C1**）、`gate` 的 `fulfilled_by`、其余 `--short` 字段派生与展示分组、
维护入口令牌交互、码表新增（⑦）、历史 dispositions 迁移、~~归档提交前预检（D4）~~（已列入 §6 待实施清单）、
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
| v33 | `binding` 含引用非空、`latest_launch`、`exits` 枚举、决定文件 schema、B5、前提增 A9（五项） | 「gate + repair_scope 是完整依据」过度承诺；决定文件缺 `by/at`；C3 把「暂时不能放行」推成「应放弃」；`usable` 无判据 |
| v34 | `usable` 三态 + `review_eligibility`、C3 补「改事实」出口、完整性口径三段、`by/at` 入 schema | `usable` 未吸收「输入无效」与「检查过期」；`exits` 形状与落点未定（第三份出口表风险）；「先重查否则白做」的依据与实现不符；§4.3 引错 backlog 条目 |
| v35 | `usable` 五项判据、`exits_for` 单点产出、事实提示纠正 | `check_stale` 被塞进 `usable` 是**过度收紧**：`check_valid == false` 只说明当前检查不能用于完成任务，不证明在途轮作废（含 rule_version 变化等非内容原因），会把仍可续接的轮次误杀成 `relaunch_review`；两种 null 仍被合并在同一分支 |
| v36 | 放行语义边界、共享函数二分、`check_stale` 移出 `usable`、C4 拆两种 null | C2 的语义仍未闭环（放行后「C2 是否满足」两解）；`usable` 的「按序」会让材料未齐遮住已确认的硬失败；#30 仍用旧名 `input_invalid`/`review_input_problems`；`anchor_stale` 无判据来源 |
| v37 | 三态语义表、`usable` 硬失败优先合成、`anchor_stale` 归 `review_report_problems` | `usable` 以「声明槽位未齐」为不可判条件，比 decide 更严（发现模式 2/3 已可判） |
| v38 | 放行一次一事件、`reusable_rounds`、资格拆两类、D4 升为前提 | `consumed` 无写点（只读查询与纯派生无法记录恢复事件）；`reusable_rounds` 混同「锚点新鲜」与「重判能解除阻断」；C4 出口把旧轮复用锁在 `in_flight == null` 一种情形 |
| v39 | 消费写点三处、`reusable_rounds` 收窄、`usable` 按已导入材料判、前提分层 | `reusable_rounds` 依赖的逐轮事实不存在（无 launch 级 invalidated、result 只留最新、round 会回退）；消费保证写成「任何恢复都失效」，实际只覆盖受控写点 |
| **v40** | 撤回 `reusable_rounds`（登记 A10）、消费保证范围精确化（登记 A11）、`usable` 区分轮次形态、§6 补 `tasks.py` 归档钩子 | 本文 |
| **v41** | `latest_launch.certain`、`redecidable_rounds` 窄口径、C4 出口接新事实 | 本文 |
| **v42** | `rounds[]`（A10 最小形态）取代 `certain`、`form` 事实、D4-minimal 纳入实施范围、exits 加 `redecide_round`、验收分两档 | 本文 |

## 10. 已定项（2026-11-11 人裁）

| # | 问题 | 裁定 |
|---|---|---|
| D1 | 不可核实证据阻断用哪个码 | 复用 `WF_REVIEW_INVALID` + `facts.reason = "unverifiable_evidence"` |
| D2 | 人裁是否引入签名 | 不引入；沿用声明式 attestation（残余风险见 §2.2） |
| **D3（已定：选 A）** | light 关闭单个问题是否必须整轮审查？ | **接受成本**：A8 归 backlog 后补；⑥ 不声称交付「light 自主闭环修复」，该口径已写进 §4.1 |

> Q1=乙、Q2=甲 亦已定；D3 已于 2026-11-11 裁为**选 A**。**本文无待决项。**
