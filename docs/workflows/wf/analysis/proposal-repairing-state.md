# ⑥ 修复态的表达：不新增阶段，用「事实 + 清除动作」吸收 `fixing` 的收益（v66，v67 文档订正）

> 状态：**已实施 v67**（2026-11-11）。阶段：**实现已落地并通过验收**（方案审查阶段结束）。
> §6 是**实施清单**，各行状态见该表；v67 只做**纯文档订正**（记录 A1/A6/C1 的落地裁定、
> 修掉文档内部矛盾与失准引用），**未改任何机制判据**。
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
| 3 | 不得把"取得外部审查结论"写成推进前提 | §4 的 C4 行：只有 complex 才要求 pass |
| 4 | 审查不得扩权：范围外只登记 | §8 + backlog |
| 5 | 主 agent 可主动扩展（授权内的相邻缺陷） | §4 的 C2 行允许处置范围不限于报告项 |

---

## 2. 机制给什么：四组事实 + 一条人裁记录

### 2.1 `repair_scope`（派生，不落盘；无单一状态枚举）

```json
{
"repair_scope": {
  "review_required": true,
  "rounds": [{"round": 1, "verdict": "pass", "check_id": "C1", "decided_at": "…",
              "inferred": false}],   // append-only；同轮取最新
  "launches": [                          // 逐轮原始事实（扁平，不做三态合成）
    {"round": 1, "form": "discovered", "imported": 2, "declared": 2,
     "decided": true, "blocked": []},
    {"round": 2, "form": "discovered", "imported": 1, "declared": 2,
     "decided": false, "blocked": ["material_missing"]}],
  "open_blocking": [{"round": 1, "slot": "s1", "finding_id": "f1", "severity": "blocker"}],
  "unverifiable": [{"round": 1, "slot": "s1", "path": "…", "report_digest": "sha256:…",
                    "cause": "changed|missing|unreadable", "cited": false,
                    "release_allowed": true, "released": false, "consumed": false}],
  "conclusion": {"decided": true, "verdict": "pass", "round": 1, "check_id": "C1",
                 "binding": false, "binding_blockers": ["check_id_changed"],
                 "check_valid": true, "check_blockers": [],
                 "stale_extra": []},        // 判定之后新导入、未被结论引用的报告 slot（派生，非门禁）
  "exits": [{"condition": "C4", "action": "await_material", "round": 2},
            {"condition": "C4", "action": "relaunch_review", "round": null},
            {"condition": "C4", "action": "redecide_round", "round": 1}]
}
}
```

**判据（每项都写成"调用哪个共享判定"；枚举仅说明，以判定实现为准）**

| 事实 | 判据 |
|---|---|
| `review_required` | `plan.complexity == "complex"`（与 `review-passed` 的短路条件同源） |
| `open_blocking` | `open_findings(...)["blocking"]`（**门禁同源、全轮次**）；条目须带 `round`（见 §6 ①）。**只含 blocking severity**；`unaddressed` 里的非 blocking 项**不在本文范围**（它们是判断骨架的输入，不是归档阻断） |
| `unverifiable` | `open_findings(...)["unavailable"]`（唯一来源，条目带 `cause/round/report_digest`） |
| `rounds[]` | **逐轮决策事实**（`decide` 追加，append-only）：`{round, verdict, check_id, decided_at}`。**消费规则（同轮取最新）**：同轮可能多条（重判）——所有消费方一律取 `decided_at` 最大的一条，**禁止各自实现**。**存量回退**：`rounds[]` 为空时按 `result` 推断一条（`inferred: true`、`decided_at: null` 视为最早），并在**下一次写入前落盘**。<br>**已撤回的机制（v66）**：不再由 `review-launch` 追加「失效记录」、`decide` 也不再据此拒绝——失效判定统一交给 `conclusion.binding` 的 CLI 校验（见上）；`rounds[]` 只记「哪轮判过、判成什么」。这消除三处双记录同步（失效追加的字段、写入顺序、`result` 与 `rounds` 分叉）。 |
| `conclusion.binding` | **`review_binding`**（自 `review-passed` 提取，**并新增一条 CLI 校验**：结论所在轮的 launch `implementation_cli` 必须等于**最新 launch 的 `implementation_cli`**——这一行把「**已发起过新 launch** 时旧 pass 仍可归档」堵在门禁上；**换宿主但未 launch** 的情形它看不见（两边都是旧 CLI），仍靠 §6a 的指引——见 §5 披露（**部分闭合**））：`result.check_id == check.id` ∧ **结论至少引用一份已导入报告** ∧ 引用报告 `result_digest == recorded == 文件当前摘要`。<br>**"至少引用一份"必须写进判据**：门禁对 `cited` 为空是独立拒绝（`review_binding` 的 `no_cited_reports` 分支），漏掉它会让空引用的结论算出 `binding == true` |
| `launches[]` | **逐轮原始事实，每轮一行**：`{round, form, imported, declared, decided, blocked}`。<br>· `form` = `discovered`／`legacy`／`null`（无导入）<br>· `decided` = 该轮在 `rounds[]` 中有决策记录<br>· `blocked` = **短原因列表**（只列已成立的事实，不做合成）：`report_invalid`／`anchor_stale`（`review_report_problems`）、`implementer_overlap`（任一份已导入报告的实施 CLI 与实施者相同）、`insufficient_reviewers`（**去重后互异 reviewer CLI < 2 且已无更多材料可等**：`discovered` 按「已导入 ≥ 声明」、`legacy` 按「声明槽位已齐」判）、`material_missing`（**已经导入的去重 CLI 仍 < 2，且还有槽位可能到**——**不因「已导入 < 声明」就记它**：发现式 2/3 已够判定）<br>**对外只给这些事实**：`exits` 用它们生成动作，AI 自己判断先做什么 |
| `conclusion.stale_extra` | **判定之后**该轮新导入、未被结论引用的报告 slot 列表（`reviews.imported` 该轮条目 − `result.imported`）。**派生事实，不是门禁条件**：门禁不比判定时的导入集（E3=甲，`review-passed` 语义不变），但这类报告可能让**重判**变 fail —— 事实交给 AI 判断（要归档就说明为何不重判），不再藏着。 |
| `conclusion.check_valid` | **`check_validity`**（自 `check-passed` 提取为 `check_validity`，逐分支不变）：**`rule_version` 相符**（`check.anchor.rule_version` 存在且 ≠ 当前版本即 `WF_CHECK_STALE`，`check_validity` 的 `rule_version` 分支）∧ 当前锚点**可算**（`current_check_anchor` 无 `error`）∧ **未 `invalidated`** ∧ `result == pass` 且 **anchor 存在** ∧ 保存的 `check_anchor` == 当前内容锚点 ∧ **结构复核 `check_result_problems` 为空**。（v46 曾以「门禁不比较 `rule_version`」为由删掉该条——那是我读代码时**从 639 行起截取**、漏看 633-638 所致；该修正作废，v47 恢复） |
| `exits` | 由 **`exits_for(facts)` 单点产出**，形状 `{condition, action, round}`（**无 `preferred`、无 `when`**）。**完整规则（四个条件都在这里）**：<br>· **C1**：`check_valid == false` → `rerun_check`<br>· **C2**：`open_blocking` 非空 → `record_disposition`（轮次由 §4 的处置时机决定，不在这里指定）<br>· **C3**：存在 `released == false` 的 `unverifiable` → `restore_bytes`；该条 `release_allowed == true` 时并给 `human_release`<br>· **C4**：对 `launches[]` 逐轮——`blocked` 为空 ∧ `decided == false` → `resume_inflight{round}`；`blocked` 为空 ∧ `decided == true` ∧ **该轮不是「当前 binding 的 pass 轮」**（含 verdict 为 fail／unavailable、以及 pass 但 check 已换代或 `result` 被他轮覆盖）→ `redecide_round{round}`；`blocked` 仅含 `material_missing` → `await_material{round}`。**`relaunch_review` 常列**（**不设「check 换代」门槛**：重判的真正前提是报告锚点仍匹配，而换代常因内容变化、反而重判不了）<br>· **常列**：`pause_for_human`、`abandon_task` |
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
| 幂等与重新批准 | 判据**与 `released` 完全同口径**：只有存在「同键 ∧ `revoked == false` ∧ `consumed == false`」的记录时，才回报 `already_accepted` 且不新增；否则（已撤销**或已消费**）**新增一条**（新 `batch`） |
| **一次一事件：恢复即消费** | 放行是针对「当次不可核实情形」的决定，不是永久豁免。**写点（三个，均为既有写命令）**：① `wf archive` 在 `final_gate` 之前的钩子（归档时必然扫到）；② `wf review-import`；③ `wf review-decide`。任一命令发现「某条放行记录对应的报告当前可核实」→ 置 `consumed: true`。**保证范围（精确化，第 35 轮）**：机制保证的是「**受控写点观察到恢复后，该放行失效**」；它**不**保证「任何一次恢复都结束原豁免」。未保护的端点是：恢复 → 期间无任何写命令 → 再次损坏 → 归档，此时所有观察点看到的都是「损坏」，旧放行生效——**归档前钩子只兜住「归档时报告仍可核实」那一支**，对这条端点无能为力。如实登记，不夸大兜底；若要更强，需要持久化恢复事件或更强信任模型（backlog A11） |
| 撤销 | `--revoke --batch <id>` 或 `--revoke --round --slot --digest`（二者同时给出则报错，不猜优先级）；置 `revoked: true`（不删）；只影响被撤销的记录 |
| 信任模型（定案） | 沿用 attestation 四件套（`by/at/quote/source` + 摘要入库），**不引入签名**。**残余风险如实登记**：决定文件由持写权会话提交，机制无法区分"人写的"与"AI 转录/伪造的"；这是全仓既有模型（`authorize` 同级），放行通道是该模型下**暴露面最大**的用途；**新增阻断越多、伪造激励越强（乘积关系，不是加法）**。缓解（放行进归档回显、挂 `task.sampled` 抽样池）→ backlog **A12** |

**命令**：`wf review-accept-unknown --task <id> --file <决定.json>`（含 `--revoke`）。

---

## 3. 五条语义边界

| # | 边界 | 说明 |
|---|---|---|
| **B1** | 可核实性是**当前状态** | 找回原字节（摘要一致）→ 不再出现在 `unverifiable`；人裁只用于**无法恢复**的情形 |
| **B2** | 归档依据必须可核实 | complex：`cited` 损坏由 `review-passed` 拦；light：由本方案新增分支拦。**阻断与能否放行是两件事** |
| **B3** | fail 不强制 replan，但不是禁止 | 根因在规划时 `task-replan` 仍合法 |
| **B4** | `unavailable` ≠ 异常归档 | `--unavailable` 只表示审查做不成；`task-abandon` 是不跑最终门禁的终局出口 |
| **B5** | **只有 `disposition.decision == "accepted"` 会清零** | `rejected` / `amended` 只记录、**不关闭**（`open_findings` 的 `closed` 集：只收 `accepted`）。**为什么不在机制侧改成「rejected 也关闭」**：那会让**存量**里「有意写的 rejected」被追溯关闭（当时语义是「只记录」），而无迁移又不可能逐个判定其真实意图——宁可保留反直觉映射，也不静默翻转历史。因此「经复核认定误报」必须写 `accepted`，并在 `reason` 里写明性质；`facts.not_closing` 会在写入 `rejected/amended` 时回报「未关闭」 |

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

**一张表**：条件、它的判据事实、它的清除动作放在一起（原先条件表与出口表各一张，同一事写两遍）。
条件可同时不满足；机制**不排顺序**，动作怎么走由 AI 判断。

| 条件 | 判据（事实来源） | 未满足时的清除动作（`exits` 由 `exits_for` 单点产出） |
|---|---|---|
| **C1** 检查有效 | `conclusion.check_valid` | `rerun_check`（重跑 `task-check` 产生新 check） |
| **C2** 无未关闭 blocking | `open_blocking == []` | **处置范围不限于报告所列项**（授权内的相邻缺陷可一并处置）。**关闭的前提是「处置结果已成立并经非提出者复核」**，不是「同意某种修法」——① 已修复且已重查通过 ② 经复核认定误报（无需改代码）③ 已重分类（本就不是问题）；**「同意修法但还没做」不得写 `accepted`**（finding 会立刻从 `open_blocking` 消失，light 无 C4 兜底）→ 保持 open，或写 `amended` + 理由（不关闭）。**在锚点仍匹配时**补 disposition（**处置结果已成立时** `decision` 写 `accepted`，B5）→ `record_disposition`。**时机约束（机制事实，必须进指引）**：`decide` 按**当前工作区内容**重算锚点（`check.anchor_parts` 按当前工作区内容算），代码改过之后旧轮报告就失配、在旧轮补处置必被 `WF_REVIEW_INVALID` 拒。两条合法路径**各自对应不同处置类型**：① 随 fail 轮那次 `decide` 一并写——**只适用于「误报 / 重分类」**（处置结果无需改代码即成立、内容未变）；② 随**修好 + 重查后的新一轮** `decide` 捎带——**「已修复」只能走这条**（内容必然已变）。**复核的边界（如实）**：机制只能校验 `recheck_by` 非空且异于提出者（`dispositions_problems`）；**它是否真的复核过、以及 `human:<来源>` 这类人工复核，机制无法机械验证**——收紧成「必须 ∈ 已导入 agent 集合」会直接堵死既有的 `broken-reference` 人工复核路径（该路径要求 `recheck_by` 以 `human:` 开头，见 `broken_reference_problems`），故**收回该收紧**，只保留如实披露：`accepted` 的可信度依赖人的判断与事后可查，不依赖机制证明 |
| **C3** 无未放行的不可核实证据 | **只统计仍承载未完成义务的不可核实证据**：① 当前 `result` **引用的**报告；② 所属轮**最新 verdict ≠ pass**（含未判定）；③ **属于当前 `result` 那一轮的任何报告**（即使未被引用——判定后新导入的报告同样阻断，否则「pass 之后补一份带 blocking 的报告，再让它损坏」就能让问题消失）。**只有「已 pass、且不在当前 result 所在轮、且未被引用」的历史报告不阻断**（仅记录在 `unverifiable` 里供追溯）——否则「主动多审几轮」反而要多签几次人裁，成本随审查历史累积 | ① `restore_bytes`（找回原字节，不依赖身份）<br>② `human_release`（`release_allowed == true` 时）——**决定文件由机制在模板里强制呈现登记在案的事实**（该轮 `verdict`、已导入数与 slot、是否被当前结论引用），让人在签字前知道自己在豁免什么（`quote` 之外不再要求新字段）——**放行的语义边界（本版新增）**：某份报告不可核实时，它里面的 findings 也随之无法枚举（`open_findings` 跳过整份报告），因此放行**必然同时豁免该报告中未知的 findings**。决定文件必须显式承认这一点（`waive_unknown_findings: true`），缺失即拒；**且不得把放行描述成"缺陷已处置"**——C2 不会因此被满足，只是那部分问题从此不可枚举<br>③ `relaunch_review`——改变事实而不是硬闯：complex 的 `cited` 损坏不可放行，但可完成一次新审查；新结论引用新报告后，旧报告变成**非引用**证据 → 下一轮 `human_release` 即可用<br>④ `abandon_task`：**不设技术前置**——上述技术出口仍可行时，AI 也可基于**任务价值**（目标已变、继续成本不合理）建议终止；同时**如实说明 C3 仍未满足**，不把放弃当成满足条件的手段。反向的护栏也不变：**不得把「当前不能放行」直接推成「应放弃」** |
| **C4** **复杂任务**的审查结论存在、绑定当前 check 且为 pass | `review_required` 时：`verdict == "pass"` ∧ `binding` | **出口见 §2.1 的 `exits` 判据行（单点定义，此处不重复）**。C4 本身只核 `verdict == "pass"` ∧ `binding`；`binding` 已含 CLI 校验。**AI 能否定审查结论的边界**：判 fail 的轮重判仍是 fail（`verdict` 由报告载荷推导，`derive_verdict` / `decide` 的载荷推导），否定只清 C2、不改 verdict —— complex 归档仍要一次 pass（E3=甲） |

> **注（v67 订正）**：C3 的技术出口 ③ `relaunch_review` 与 ④ `abandon_task` 在 `exits` 里的**条件标签**按 §2.1——
> `relaunch_review` 属 C4 常列；终局动作在 complex 标 C4、在 light 标 C3。这是**同一动作在两处出现**，
> 不是两套判据：complex 的引用证据损坏必然让 `binding == false`（C4 未满足），`relaunch_review` 因此必然出现在 `exits` 里。

### 4.3 并存与顺序

- 条件可同时不满足；`repair_scope` **同时**给出全部事实，不做优先级遮蔽；
- 动作顺序、是否合并、先修哪项由 AI 判断（机制不排调度）；
- 旧结论能否复用由 C4 的事实判断，**不由表格顺序判断**。

**三个约束**：

1. **不要用"试归档"探路**（`cmd_archive` 会先做业务提交）。**但这只防探路，不保护正常归档调用**：提交发生在 `final_gate` 之前，因此「业务已提交、归档因 C3 被拒」在 D4 落地前**仍可能发生**——所以 **D4（归档提交前预检）是⑥的安全前提**（见 §5）：不属可执行性前提，但缺它这条门禁就不安全；
2. **不得把"四条件满足"说成"可以归档"**：`wf gate` 只跑步骤面，`repair_scope` 只覆盖 ⑥ 的 C1–C4；
   escalated 待答、required 未核实、依赖未满足、debug 未裁、降级材料不完整**都不在这两处**，
   且当前**没有只读等价物**（见 §8）。此处「不依赖」指**完整性声明**不依赖 D4；**安全性**依赖见 §5 的安全前提；
3. 因此完整判断只能是"步骤面 + ⑥ 四条件 + 各自投影"，**并读三者仍不等于归档一定成功**——如实告知，不用措辞补足。

---

## 5. 与既有机制的关系 + 落地前提

| 机制 | 关系 |
|---|---|
| `phase` 枚举 / `protocol/states.json` / `next_by_position` | **不改**；`repair_scope` 不参与 `next` |
| `review-decide` 判定资格、`task-check` 语义 | **资格判定不改**；**不做失效拒绝**——失效判定统一在 `review_binding` 的 CLI 校验里（`gates.py` 行）。能力仍靠 §2.1 的 `exits` 表达，不靠入口拦截。 |
| `review-passed` / `check-passed` | 行为不变，内部判定**提取为共享函数**（`review_binding` / `check_validity`），并在这两处做 OSError 归因 |
| `final_gate` | **只加一条**：存在 `released == false` 的 `unverifiable` → 阻断；出口按 `release_allowed` 分列 |
| `task-abandon` | **不改**：终局、不解除 |

**前提（两层；A4/A7/A9/C1 仍属另案，A1/A6 按裁定由 ⑥ 自身口径承接，见 backlog）**

| 前提 | 为什么必须先做 |
|---|---|
| **A1 `slot` 身份稳定** | 放行键含 `slot`；`slot`/`agent` 混用会匹配不上。**落地裁定（2026-11-11，B）**：⑥ 直接以 `imported[].slot` **原值**为键，匹配键固定 `(round, slot, report_digest)`；**任何路径不得把 agent 名归一成 slot**（否则重新引入 A1）。`slot_key` 归一留 backlog，不阻塞 |
| **A4 导入端证据身份** | 现在可"删档后导入同轮同槽位另一份报告"顶掉历史证据 → C2/C3 可被静默清空 |
| **A7 K4b 关闭链** | `proposers_from_history` 从 `imported[].findings` 读提出者（记录不保存 findings）→ 真实修复后 disposition 被拒 |
| **A9 finding 精确身份**（新增） | 关闭匹配只按**裸 `finding_id`**（`open_findings` 的 `closed` 集）→ 旧关闭会静默关掉他轮/他槽位的同名新问题。**A7 只解决"读得到提出者"，不解决"关的是哪一个"** |
| **A6 缺 `report_digest` 的遗留导入记录** | C3 覆盖**全部轮次**，而这类记录无法恢复、机制也不提供放行（登记摘要为 `null`，不参与三元组匹配）→ 新门禁会把旧缺陷的等级从「体验」抬成「正常收尾被阻断」。**落地裁定（2026-11-11）**：① 不新增任何命令/字段/配置键；② 原文件不可得时，C3 **不把「缺登记摘要」条目计入阻断**，改为在 `status` 的 `legacy_unverifiable[]` 单列并标注「缺登记摘要，机制既不能核验也不能放行」；③ 补摘要只能借**现有** `review-import` 对同轮同槽位重导一次（要求报告 `check-anchor` 仍等于当前锚点），重导合法性依赖「文件内容未被篡改」，机制无法证明，属遗留风险 |
| **C1 读取归因** | `open_findings` / `review_binding` 都读摘要，权限故障会抛出；**这两处由 ⑥ 自带**（第 1、2 步各包 `except OSError`，按 `cause: "unreadable"` 归因），其余五处属 C1、不在 ⑥ 范围 |
| ~~D4~~（**已纳入 §6 实施清单并落地**） | 原本确实需要它（C3 阻断挂在 `final_gate` 尾部、业务提交在前）。**D4-minimal** 已写进 §6 并实施（`archive_precheck`：提交前只读预检），因此不再是外部前提 |
| ~~A8~~（归入「成本前提」，见本节末） | A8 不属可执行性前提：没有它 light 关 C2 贵但能走通 |

**前提分层（本版明确，消除上一版的计数与性质混乱）**

| 层 | 项 | 缺了会怎样 |
|---|---|---|
| **可执行性前提** | A4、A7、A9、C1（仅其余五处） | ⑥ 的事实或清除动作**算不出来**，必须先做。（A10「逐轮决策事实」已由 `rounds[]` 承接，故不列为外部前提；**A1** 按裁定 B 由 ⑥ 自身键口径承接、**A6** 按裁定改为「单列 + 不阻断」，二者不再阻塞） |
| **本方案自带（非外部前提）** | D4-minimal（归档提交前预检） | 已列入 §6 并已实施（`archive_precheck`） |
| **成本前提** | A8（轻量关闭入口） | light 关 C2 需要一整轮审查（贵但能走通）；建议先做，不作前置 |

**披露（机制自洽但不免费）**

| 代价 | 说明 |
|---|---|
| complex 多轮累积人裁 | C3 覆盖**全部轮次**的不可核实证据：round-1 的报告即使与最终 pass 无关，损坏也要一次放行 → 轮次越多签到越多 |
| light 关闭 C2 的入口成本 | 见 §4 的 C2 行（A8） |
| 放行通道的信任残余 | 见 §2.2 末（声明式，可伪造，仅留痕） |
| **实施换 CLI 但未发起新一轮** | **部分闭合**：`binding` 的 CLI 校验只能比较 **launch 对 launch**——**已发起过新 launch** 的情形被机械拦住；**换了宿主但没 launch** 时两边仍是旧 CLI，看不到这次交接。该情形只能靠指引（§6a：换实施宿主先 `review-launch`）。**不声称完全闭合** |

---

## 6. 实施清单（**已实施**：2026-11-11，工作树未提交；验收载体见 §7）

| 文件 | 状态 | 改动 |
|---|---|---|
| `gates.py` | 已实施 | ① 提取 `review_binding`（含 **cited 非空**）与 `check_validity`（含 `rule_version`、结构复核）供 `repair_scope` 复用，步骤行为不变；② 两处摘要读取包 `except OSError`；③ `final_gate` 追加 `unverifiable`（C3）阻断——**该分支必须位于被提取的 `final_gate_nonstep` 内部**（否则预检覆盖不到它，正是 §4.3 约束 1 要防的「业务已提交、归档因 C3 被拒」）；`exits` 用 §4 的 token 并带 `facts.reason = "unverifiable_evidence"` |
| `review.py` | 已实施 | ① **移除 `review-launch` 里对 `result.verdict` 的 `invalidated` 改写**：失效不再靠改 verdict，改由 `review_binding` 的 CLI 校验判定（现有逻辑比较「全部历史实施 CLI 集合」，会把合法的 pass 误杀）；② `open_findings` 的 `blocking`/`unaddressed` 条目补 `round`、`unavailable` 条目补 `cause/round/report_digest`（`cause` 须**区分 `missing`（`file_digest` 返回 `None`）与 `changed`（摘要不符）**），摘要读取包 `except OSError`；③ `review-decide` **不再做失效拒绝**（改由 `review_binding` 的 CLI 校验统一拦截，见 `gates.py` 行）；只保留「先落盘按 `result` 推断的 `rounds[]`」这一写前步骤；④ 追加 `reviews.rounds[]`（**只记决策，不记失效**）；⑤ 提取 `review_eligibility`（←`input_problems`）与 `review_report_problems`（←`problems`）两个共享函数，不合并；⑥ `repair_scope` 纯派生 + `exits_for`（**唯一出口实现**，返回 `[{condition, action, round}]`，**无 `preferred`/`when`**）；⑦ `facts.not_closing` 回报未关闭项（closed 集**不改**，见 B5） |
| `tasks.py` | 已实施 | ① **D4-minimal**：`cmd_archive` 在业务提交前跑只读预检。**为什么不能只调一次 `final_gate`**：它是**顺序短路**结构（`final_gate` 的顺序短路：先跑 `evaluate` 的步骤面，任一步 missing 即返回 `{missing, all}`），而预检发生在提交之前 → `changes-persisted` 必 missing → **nonstep 十项一次都不会跑**，等于漏检 escalated/required/依赖/debug/`paused` 与 ⑥ 的 C3 阻断。**正确契约**：把 `final_gate` 的 nonstep 段**提取为可复用函数** `final_gate_nonstep(ctx, task, ignore_action_id=None)`（原 `final_gate` 的 nonstep 段原样搬出，`final_gate` 改为先跑步骤面、再调它——**不是第二套实现**；搬移必须**行为等价**：对既有失败场景（escalated/required/依赖/debug/action/paused）返回的 `code` 与 `facts` 逐字段相同，见 §7 矩阵 #49（提取行为等价））；预检 = ① `final_gate_nonstep(ctx, task, ignore_action_id=task.action.id)` ∧ ② `evaluate(ctx, task, "before_archive")` 的结果**先按 `id` 排除 `task.changes-persisted`、再取 `status == "missing"` 的条目**，这些必须为空（`evaluate` 对每个适用步骤都返回条目，`status ∈ {missing, completed, reused, satisfied}`（`evaluate` 的 `status` 取值）——**「列表为空」是错的判据**，正常任务也会有 completed/satisfied 条目）∧ ③ **授权覆盖判定**：`pending ⊄ 本次提交路径集` → 拒（`WF_WIP_UNRESOLVED`；**不要直接复用** `changes_persisted_fact` 的同码分支——它的判据是「已声明授权却仍有待提交路径」，在提交前必然成立，直接复用会拒掉每次正常归档）。三者任一不过即拒绝（不提交）；②被过滤掉的那一步由归档自身的提交满足，③补位防「授权只覆盖部分待提交路径」；② 的调用**只传 `rule_version`**（`evaluate` 没有 `ignore_action_id`，`evaluate` 的签名；失败返回的 facts 是 `{missing, all}`、成功才是 `{steps}`，`evaluate` / `final_gate` 的返回 facts）；④ `unknown_acceptances` 消费钩子（预检之前） |
| `cli.py` | 已实施 | ① `wf status` 输出 `repair_scope`，`unverifiable` 条目渲染三态、`open_blocking` 标「已驳回未关闭」、**`rounds[]` 标 `inferred` 边界**（`inferred` 属 `rounds[]`，不属于 `launches[]`，见 §7 矩阵 #43）；② `--short` 原样输出四条件 + `exits`（含 `round`），不重新推导；③ 新增 `wf review-accept-unknown`（`--revoke`，含 `consumed`）；④ **归档与 `status` 强制回显当前放行清单**，且**放行记录并入 `task.sampled` 抽样冻结集**（与 C3 阻断同批，不留后补）；⑤ `--short` 复用与 D4 预检**同一个函数**给出「还有哪些确定阻断」，不另写一份 |
| `skills/` | 已实施 | 见 **§6a 的文件清单**（具体要求在 §7 矩阵 类型=`文档` 的行） |

> **实施记录（v67 订正）**：五行改动均已落地并通过验收（运行时套件与 68 条 repro 全绿、单测全绿、
> release `--verify` 字节复现通过）。与本文的已知差异都记在 §5 的落地注里：A1 以 `imported[].slot` 为键（裁定 B）、
> A6 改为「单列 + 不阻断」、C1 其余五处不在范围。门禁 C3 的 `exits` 沿用 `final_gate` 既有形态
> （散文串里点名同一组动作），未改成裸 token 列表。

### 6a. 指引交付（与机制同批）

**要交付哪个文件**（具体要求见 §7 矩阵里 类型=`文档` 的行，这里不重复写）：

| 文件 | 动作 |
|---|---|
| `skills/wf-review-action/SKILL.md` | 改：处置形状（只有 `accepted` 清零；误报也写 `accepted` + reason 说明性质）、`--round` 必须显式传、处置时机与类型对应、`recheck_by` 可与 `human:` 前缀并存 |
| `skills/wf-repair-loop/SKILL.md` | **新增**：`repair_scope` 判读、十个动作 token、`stale_extra` 非空时的判断点、换实施宿主先 `review-launch` |
| `skills/wf-continue/SKILL.md`、`skills/wf-finish/SKILL.md` | 改：路由/收工前先读 `repair_scope` 与 `gate`；不要试归档探路 |
| `skills/wf-review-accept-unknown/SKILL.md` | **新增**：人机交互（何时问人、呈现哪些证据、`quote` 如何采集） |

## 7. 验收矩阵（61 项）

**验证面**：类型=`机制` 指「可用代码/事实/门禁行为验证」，载体为 `scripts/tests/wf_runtime/test_repair_scope.py`（每条断言至少一个用例）；类型=`文档` 指检查 `skills/` 交付物是否写明。

| # | 类型 | 断言 / 要求 |
|---|---|---|
| 1 | 机制 | `open_blocking` 与 `final_gate` 的 `unaddressed_blocking` 逐项一致（同源、全轮次），且每条带 `round` |
| 2 | 机制 | `binding` 是子判定：`verdict == "fail"`、check 未换代、引用摘要一致 → `binding == true`（不因 `verdict != pass` 而 false） |
| 3 | 机制 | **`binding` 空引用即为 false**：结论 `imported` 为空时 `binding == false`（与 `review_binding` 的空引用拒绝同源） |
| 4 | 机制 | `check_valid` 与 `check-passed`（`check_validity` 的逐分支）逐分支一致：**`rule_version` 不符→false**、锚点不可算→false、`invalidated`→false、`result != pass`→false、anchor 缺失→false、anchor 不符→false、`check_result_problems` 非空→false |
| 5 | 机制 | 内容改动未重查 → `check_valid == false`、`check_blockers` 含 anchor 漂移（C1 未满足） |
| 6 | 机制 | 重查产生新 check → `binding == false`（`check_id_changed`），`open_blocking` 不消失（B5） |
| 7 | 机制 | **`accepted` 或 `rejected` 清零、`amended` 不清零**：写 `amended` 后 `open_blocking` 仍非空；`facts.not_closing` 列出未关闭项 |
| 8 | 机制 | `verdict == "fail"` ∧ `binding` ∧ `open_blocking` 已清 → C4 未满足，`exits` 含 `relaunch_review` / `resume_inflight` |
| 9 | 机制 | **C3 只统计仍承载未完成义务的证据**（当前 `result` 引用的 + **最新 verdict ≠ pass** 的轮，**含未判定轮**）；已 pass 且不再被引用的历史报告不阻断 |
| 10 | 机制 | light：`cited` 损坏 → 仍阻断，且 `release_allowed == true`，`human_release` 在 `exits`；放行后 C3 满足 |
| 11 | 机制 | 非引用损坏 + 摘要全等放行 → C3 满足；撤销后恢复；匹配需三元组全等 |
| 12 | 机制 | **决定文件 schema**：digest 与登记摘要不等 → 整批拒绝（防 typo 生成永不匹配记录）；缺 `quote`/`source` → 拒绝 |
| 13 | 机制 | 撤销后**可重新批准**：批准 → 撤销 → 再批准，`released` 回到 true；幂等只在「同键 ∧ 未撤销 ∧ 未消费」时生效 |
| 14 | 机制 | 报告恢复原字节 → 不再出现在 `unverifiable`（B1） |
| 15 | 机制 | `cause` 三分只由 `open_findings` 产出，`repair_scope.unverifiable` 与之逐项一致 |
| 16 | 机制 | 权限故障不崩：`open_findings`、`review_binding`、`status`、`wf gate` 全部走归因分支 |
| 17 | 机制 | 并存无遮蔽：`open_blocking` 非空同时有未放行 `unverifiable` 时，两组事实**同时**出现 |
| 18 | 机制 | **light 不承担 C4**：自愿审查 `fail`/`unavailable`/`invalidated` 且 `open_blocking` 空、C1/C3 满足 → 不产生"必须取得新审查结论"义务 |
| 19 | 机制 | 但 light 的 C2/C3 仍成立：自愿审查带 blocking → 未关闭时归档被 `WF_UNRESOLVED_BLOCKING` 拒；报告损坏 → C3 阻断 |
| 20 | 机制 | 主动性约束：`repair_scope` 不含"等待评审/待评审确认"类状态；除 complex C4 外，未满足条件都能在不取得新审查结论的前提下推进 |
| 21 | 机制 | `--short` 输出四条件+`exits`，不输出完整事实集；`task.check` 字段派生等其余 `--short` 改动仍属 backlog |
| 22 | 机制 | 协议零改动：`phase.enum`、迁移数、`next_by_position` 逐字节一致；`repair_scope` 不参与 `next`；`task-abandon` 仍可终止且不解除阻断 |
| 23 | 机制 | `pause_for_human`/`abandon_task` **在 C4 未满足时始终出现**（不减其它动作），且 `abandon_task` **不得被当作推荐**（不得把「当前推进不动」推成「应放弃」） |
| 24 | 机制 | C4 的事实提示**准确**：只说「结论写入后再重查会失绑」，不得声称「发起早就会失绑」；先重查是建议而非机制事实 |
| 25 | 机制 | `exits` 形状 `{condition, action, round}`（**无 `preferred`、无 `when`**），只由 `exits_for` 产出；`--short` 原样过滤输出，不重新推导 |
| 26 | 机制 | 无任何 launch 时 `exits` 不含 `await_material`/`resume_inflight`；`blocked` 仅含 `material_missing` 的轮才给 `await_material`，与 `resume_inflight` 并列、机制不排序 |
| 27 | 机制 | 决定文件四件套：缺 `by`/`at`/`quote`/`source` 任一 → 拒绝（`by` 必须 `human:` 前缀） |
| 28 | 机制 | 共享函数二分：`implementer_overlap` / `insufficient_reviewers` 来自 `review_eligibility`（`input_problems` 通道），`report_invalid` 来自 `review_report_problems`（`problems` 通道）；两通道不得合并（否则搅浑 S4 的 invalid 态边界） |
| 29 | 机制 | **部分导入 + 硬失败**：声明 2 槽位、只导入 1 份且该份 `report_invalid`/`anchor_stale` → `blocked` 含硬失败（`report_invalid`/`anchor_stale`/`implementer_overlap`）（**不得**因材料未齐而报 `null`） |
| 30 | 机制 | **发现式 2/3 可判**：声明 3 位只到 2 位且两位互异 → 该轮 `blocked` **不含** `material_missing`（decide 不要求声明槽位齐）；只到 1 位 → `blocked` 含 `material_missing` |
| 31 | 机制 | **豁免后原字节恢复**：报告重新可核实 → 离开 `unverifiable`、findings 重新枚举 → C2 重新可能不满足；此前的 `waive` 记录**不**覆盖新枚举出的 findings（B1 的"事实变化"对偶面） |
| 32 | 机制 | **一次一事件**：丢失→放行→恢复（离开 `unverifiable`）后该放行标 `consumed`；再次损坏时**旧放行不再生效**，C3 重新阻断，需新的放行决定 |
| 33 | 机制 | **资格拆两类**：已导入报告的 reviewer CLI 与实施 CLI 相同 → 材料未齐时也立即 `blocked` 含硬失败（`report_invalid`/`anchor_stale`/`implementer_overlap`）（`implementer_overlap`）；仅"去重人数不足"才等到材料齐后判定（`insufficient_reviewers`） |
| 34 | 机制 | **消费保证的范围**：只保证「受控写点观察到恢复即失效」；「恢复后在无写命令期间再次损坏」**不在保证内**，归档钩子只兜住「归档时报告仍可核实」那一支 |
| 35 | 机制 | `decided` 语义：该轮在 `rounds[]` 中有决策记录；**被放弃的坏轮也算未判定**（`decided == false`），但不得因此把 `redecide_round` 藏起来 |
| 36 | 机制 | **失效判定唯一落点是 `binding`**：结论所在轮 launch CLI ≠ 最新 launch CLI → `binding == false`；`decide` 不做失效拒绝，`rounds[]` 不记失效 |
| 37 | 机制 | **D4 预检契约（单条完整断言）**：① 构成 = `final_gate_nonstep(ctx, task, ignore_action_id=task.action.id)` ∧ `evaluate(ctx, task, "before_archive", rule_version=…)` 排除 `id == "task.changes-persisted"` 后 **`status == "missing"` 的条目为空** ∧ 授权覆盖判定（`pending ⊄ 提交路径集` → 拒）；② 调用契约 = `evaluate` 只传 `rule_version`（`evaluate` 没有 `ignore_action_id`）；③ **禁止**以单次 `final_gate` 实现（`final_gate` 顺序短路，提交前只看到步骤缺项） |
| 38 | 机制 | `released` 三条件：存在 `(round, slot, report_digest)` 全等、**未撤销且未消费**的放行记录；缺一即不算已放行 |
| 39 | 机制 | 消费写点三处：`wf archive` 的 `final_gate` 前置钩子、`review-import`、`review-decide` 发现「记录对应报告当前可核实」即置 `consumed` |
| 40 | 机制 | 存量回填：`rounds[]` 为空时按 `result` 推断一条并在**首次写入前落盘**（`inferred: true`，`decided_at: null` 视为最早） |
| 41 | 机制 | **A6 的处置口径（v67 订正）**：缺 `report_digest` 的遗留记录在 C3 下无法恢复、机制也不提供放行 → **不计入 C3 阻断**，在 `status` 的 `legacy_unverifiable[]` 单列；补摘要只能借现有 `review-import` 重导（锚点仍匹配时），合法性依赖「文件未被篡改」，属遗留风险 |
| 42 | 机制 | **发现式 2/3 可判**：声明 3 位只到 2 位且两位互异 → 该轮 `blocked` **不含** `material_missing`（decide 不要求声明槽位齐）；只到 1 位 → `blocked` 含 `material_missing` |
| 43 | 机制 | **存量历史轮是推断残缺**：`rounds[]` 只按 `result` 推断一条，其余轮显示 `decided == false` 但历史不可知；`status`/`--short` 须标 `inferred` 边界（`inferred` 属 `rounds[]`，不属于 `launches[]`） |
| 44 | 机制 | **`release_allowed` 随 complexity 漂移**：定义取**当前** `plan.complexity`；complex→light 降级后同一 `cited` 损坏证据的放行资格会翻转——**归属**：`status` 渲染须显示该条目的 `release_allowed` 现值 |
| 45 | 机制 | **`cause` 三分可判**：`file_digest` 返回 `None` → `missing`；摘要 ≠ 登记摘要 → `changed`；读取抛 `OSError` → `unreadable` |
| 46 | 机制 | **归档回显放行清单 + 抽样冻结**：`wf archive` 与 `wf status` 强制列出当前生效的 `unknown_acceptances`（含 `by/at/quote`），并把放行记录并入 `task.sampled` 抽样冻结集（与 C3 阻断同批） |
| 47 | 机制 | `exits` 由 `exits_for` 单点产出，四个条件的动作都在 §2.1 的 `exits` 判据行里；C4 逐轮按 `blocked`/`decided` 给出口，`relaunch_review` 与两个终局动作常列 |
| 48 | 机制 | **C2 的关闭语义**：`accepted` 只能表示「**处置结果已成立并经非提出者复核**」——① 已修复且已重查通过、② 经复核认定误报（无需改代码）、③ 已重分类（本就不是问题）。**「同意某种修法但还没做」不得写 `accepted`**（否则 finding 立刻从 `open_blocking` 消失，light 又没有 C4 兜底）；此时保持 open，或写 `amended` + 理由（不关闭） |
| 49 | 机制 | **提取行为等价**：`final_gate_nonstep` 提取后，既有失败场景（escalated/required/complex 未确认/降级不完整/依赖/`unruled_debug_multiples`/`action_incomplete`/`paused`）返回的 `code` 与 `facts` 与提取前**逐字段相同**；`paused` 与 `action_incomplete` 的交织顺序不变 |
| 50 | 机制 | **C3 分支归属**：新增的 `unverifiable` 阻断位于 `final_gate_nonstep` 内——预检在提交前即可看到它（否则「业务已提交、归档因 C3 被拒」） |
| 51 | 机制 | **`binding` 含 CLI 校验**：结论所在轮 launch 的 `implementation_cli` ≠ 最新 launch 的 → `binding == false`（旧 pass 在换实施宿主后不再能归档；这是失效判定的唯一落点） |
| 52 | 文档 | `wf-review-action`：处置形状正确、**只有 `accepted` 清零**（误报也写 `accepted` 并说明性质）、**必须显式传 `--round`**（默认取最大 launch 轮，与 `exits.round` 可能不同） |
| 53 | 文档 | `wf-review-action`：写明**处置时机与类型的对应**——① 路径（随 fail 轮同批）**只用于误报/重分类**；② 「已修复」只能随**修好+重查后的新一轮** decide 捎带；「同意修法但还没做」不写 `accepted` |
| 54 | 文档 | `wf-repair-loop`（新）：读 `repair_scope` 的判读顺序、`launches[]` 逐轮看、存量 `inferred` 边界、`check_valid == false` 的两种走法、**fail 轮重判仍 fail**、**否定只清 C2**及后果 |
| 55 | 文档 | `wf-continue` / `wf-finish`：路由与收工前先读 `repair_scope` 与 `gate`，**不要试归档探路** |
| 56 | 文档 | `wf-review-accept-unknown`：人与机制的分工——何时问人、呈现哪些不可核实证据、`release_allowed` 取值含义（含 **complex→light 降级会翻转它**）、未知 findings 一并豁免意味着什么、`quote` 如何采集 |
| 57 | 文档 | `wf-repair-loop`：写明 `stale_extra` 非空时**先读新增报告**再决定（重判 / 说明理由），不得跳过实质检查 |
| 58 | 机制 | **`launches[].blocked` 只列事实、不做优先级合成**：材料没到写作 `material_missing`，确认不合格写作对应硬失败原因；不出现三态分数 |
| 59 | 机制 | **`exits` 的 C4 规则与 `blocked`/`decided` 一致**：`blocked` 空且未判定 → `resume_inflight`；空且已判 pass、check 换代 → `redecide_round`；仅 `material_missing` → `await_material`；`relaunch_review` 常列 |
| 60 | 机制 | **C3 覆盖统计口径**：① 当前 `result` 引用的报告 ② 所属轮最新 verdict ≠ pass（含未判定）③ **属于当前 `result` 所在轮的任何报告**（判定后新导入的也阻断）；仅「已 pass ∧ 不在 result 轮 ∧ 未被引用」的历史报告豁免 |
| 61 | 机制 | **`exits` 的 C4 不设「check 换代」门槛**：`blocked` 空 ∧ `decided` ∧ 该轮不是「当前 binding 的 pass 轮」→ `redecide_round`；`unavailable` 后材料补齐的轮因此仍有出口 |

## 8. 范围边界（防跑偏，硬约束）

本文只回答 ⑥。不在范围（详见 `analysis/backlog-excluded-from-item6.md`）：
`slot`/`agent` 身份域（**A1**：⑥ 以 `imported[].slot` 为键，`slot_key` 归一仍属 backlog）、导入端证据身份与 `--restore`（**A4 为前提**）、
关闭链提出者（**A7**）、**finding 精确身份（A9）**、**缺 `report_digest` 的遗留记录（A6：已按裁定单列 `legacy_unverifiable`、不计入 C3 阻断）**、`review-status` 的 ready/material 语义、
读取健壮中的其余五处（**C1**：`status_of_round`、`review-import` 的既有摘要与写后摘要、`review-decide`、`all_findings`；连 ⑥ 自带的两处共七处）、`gate` 的 `fulfilled_by`、其余 `--short` 字段派生与展示分组、
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
| **v40** | 撤回 `reusable_rounds`（登记 A10）、消费保证范围精确化（登记 backlog A11）、`usable` 区分轮次形态、§6 补 `tasks.py` 归档钩子 | 本文 |
| **v41** | `latest_launch.certain`、`redecidable_rounds` 窄口径、C4 出口接新事实 | 本文 |
| **v42** | `rounds[]`（A10 最小形态）取代 `certain`、`form` 事实、D4-minimal 纳入实施范围、exits 加 `redecide_round`、验收分两档 | 本文 |
| **v43** | `rounds[]` 生命周期与消费规则、`undecided` 取代 `in_flight`、`redecide_round` 与在途轮并行、D4 覆盖 C1–C4、标准漂移移出硬失败 | 本文 |
| **v44** | 失效同步覆盖全部旧轮、判据行补回、示例自洽、`nonstep` 定义、存量回填衔接、backlog A12 登记 | 本文 |
| **v45** | `decide` 拒绝重判已失效轮、失效同步覆盖全部受影响轮、回填统一为「落盘」、D4 未覆盖清单按代码修正 | 本文 |
| **v46** | 全维度自查：`nonstep` 按 `final_gate` 十项重写、`check_validity` 去掉 `rule_version`、`when`/`preferred` 通用规则、D4 未覆盖清单按代码改正、A11/A12 前缀消歧 | 本文 |
| **v47** | 恢复 `rule_version` 判据（v46 误删）、D4 恢复步骤面、`preferred` 枚举化、④ 限制归因改正 | 本文 |
| **v48** | 逐轮 `launches[]`（每轮一行的 usable/redecidable）、出口带 `round` 且去掉 `preferred`、`changes-persisted` 拆两问、A6 升为前置、`nonstep` 顺序按代码 | 本文 |
| **v49** | 逐轮 `launches[]` 的资格/材料分开、`decide` 入口加 CLI 一致性、§6 重写 + §6a 指引交付、A12 最小缓解进交付、处置时机约束 | 本文 |
| **v50** | 撤回 v49 的 `usable` 重写（恢复与 decide 同源口径）、CLI 口径统一为最新 launch、终局出口常列、nonstep 十项回列 §6 | 本文 |
| **v51** | D4 调用契约按签名改正（走 `final_gate`、按 `id` 过滤）、A27/A45/A21 同步、换宿主窗口登记 + G3 指引 | 本文 |
| **v52** | D4 改为「提取 `final_gate_nonstep` + 过滤后的 `evaluate` + 授权覆盖」三段、C2 关闭语义（`accepted` 仅表示结果已成立）、G4/B4 补齐 | 本文 |
| **v53** | 预检判据改「`status == missing` 为空」、C3 分支归入 `final_gate_nonstep`、提取行为等价断言、C2 两条路径按处置类型限定 | 本文 |
| **v54** | C4 追加 `eligible`、复核人可核验收紧、`--unavailable` 禁写 disposition、预检断言合并为一条、G2 同步 | 本文 |
| **v55** | 记录人裁 **E3 = 甲**（维持 `review-passed` 语义，复杂任务仍需一次 pass） | 本文 |
| **v56** | 撤回 `eligible` 与两条收紧（复核人集合、`--unavailable` 禁写）、修 §4.2 表格结构、数字引用改标题引用 | 本文 |
| **v57** | G2 ④ 与撤回后的现状对齐、`conclusion.stale_extra` 作为派生事实呈现（不改门禁）、G 档重排 | 本文 |
| **v58** | 修 §4.1 C1 行与 §2.1 check_valid 行的表格损坏；G5 补「先读新增报告」；B 档补 B7 | 本文 |
| **v59** | 引入只读 doc-lint 并修其报出的 4 处真实缺陷（两处表格列数、判据表缺 `exits` 行） | 本文 |
| **v60** | 结构减负：A/B/G 三处合并为**一张验收矩阵**、§4.1+§4.2 合并为**一张条件表**；副本从 8 处降到 3 处（事实契约 / 条件+出口 / 验收矩阵） | 本文 |
| **v61** | 修 v60 合并留下的死引用、lint 加严（严格 §引用 + 标签检查 + 覆盖声明）、补回 E3 两条机制事实、C3 的 `abandon_task` 不设技术前置 | 本文 |
| **v62** | 修 #57/#62 自指、#70 扩为五条读法（含 C3 放弃授权与 E3 两条事实）、#72 补降级翻转、lint 增类型限定语校验 | 本文 |
| **v63** | **把防线移到真正消费 pass 的地方**：`review_binding` 增 CLI 校验，撤回 `rounds[]` 失效同步与 `decide` 失效拒绝；C3 只对仍承载义务的证据追责；幂等与 `released` 同口径；`exits` 补全四条件的单点判据、删 `when`、`relaunch_review` 常列；放行决定文件强制呈现登记事实；抽样池进交付 | 本文 |
| **v64** | 收口 v63 遗留的两套口径（§4 出口改指 §2.1、§5 与 §6 的 decide 口径、`when`/`invalidated_reason` 清零）；C3 口径改为「最新 verdict ≠ pass（含未判定）」；幂等与 `released` 同口径；换宿主窗口改口径为「部分闭合」；B5 改为 `accepted`/`rejected` 都关闭（机制侧） | 本文 |
| **v65** | **B2 降级**：`launches[]` 改为扁平原始事实（`decided` + `blocked` 短原因），撤掉 `usable` 三态合成与 `redecidable` 五条件作为对外契约；矩阵删 9 条、留 2 条替代 → 59 项 | 本文 |
| **v66** | 收口 A2/A3：`exits` 的 C4 去掉「check 换代」门槛、`material_missing` 只在「去重 <2 且还有材料」时记；C3 补「result 所在轮的任何报告」；B5 **回退**为 accepted-only（拒绝追溯翻转历史）；§6 补「移除 launch 的 result 失效改写」 | 本文 |
| **v67** | **纯文档订正**：记录 A1/A6/C1 的落地裁定；§6 改为「已实施」；修 §6 cli ① 的 `launches[]`→`rounds[]`、§6 tasks ③ 的失准行号与 #59→#49、全篇 `file.py:行号` 引用改指函数/分支名（行号随实现漂移）、§8 的「六处」计数、C3 出口标签归属注、#41 的「无法放行」；`review.py` 行内编号归位 | 本文 |

## 10. 已定项（2026-11-11 人裁）

| # | 问题 | 裁定 |
|---|---|---|
| D1 | 不可核实证据阻断用哪个码 | 复用 `WF_REVIEW_INVALID` + `facts.reason = "unverifiable_evidence"` |
| D2 | 人裁是否引入签名 | 不引入；沿用声明式 attestation（残余风险见 §2.2） |
| **E3（已定：甲）** | 「已全部处置的 fail」是否也满足 complex 归档？ | **不满足**：`review-passed` 语义不变，复杂任务仍需一次 pass；AI 的否定只清 C2、不改 verdict |
| **D3（已定：选 A）** | light 关闭单个问题是否必须整轮审查？ | **接受成本**：A8 归 backlog 后补；⑥ 不声称交付「light 自主闭环修复」，该口径已写进 §4.1 |

> Q1=乙、Q2=甲 亦已定；D3 裁为**选 A**、E3 裁为**甲**（2026-11-11）。**本文无待决项。**
