# ⑥ 修复态的表达：不新增阶段，用「事实 + 清除动作」吸收 `fixing` 的收益（v53）

> 状态：**待审 v53**。阶段：**方案审查阶段，实现零改动**（`review-phase-discipline.md`）。
> §6 是**待实施清单（全部未实施）**，**不是已完成的工作**；当前 `docs/workflows/wf/payload/` 与基线 `8da2f23`
> **逐字节一致**（`git diff` 为空）。
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
{
"repair_scope": {
  "review_required": true,
  "rounds": [{"round": 1, "verdict": "pass", "check_id": "C1", "decided_at": "…",
              "invalidated_reason": null, "inferred": false}],   // append-only；同轮取最新
  "launches": [                                                   // 逐轮事实（每轮一行，不替 AI 挑轮）
    {"round": 1, "form": "discovered", "imported": 2, "declared": 2,
     "undecided": false, "redecidable": true,
     "usable": true, "usable_blockers": []},
    {"round": 2, "form": "discovered", "imported": 1, "declared": 2,
     "undecided": true, "redecidable": false,
     "usable": null, "usable_blockers": ["material_missing"]}],
  "open_blocking": [{"round": 1, "slot": "s1", "finding_id": "f1", "severity": "blocker"}],
  "unverifiable": [{"round": 1, "slot": "s1", "path": "…", "report_digest": "sha256:…",
                    "cause": "changed|missing|unreadable", "cited": false,
                    "release_allowed": true, "released": false, "consumed": false}],
  "conclusion": {"decided": true, "verdict": "pass", "round": 1, "check_id": "C1",
                 "binding": false, "binding_blockers": ["check_id_changed"],
                 "check_valid": true, "check_blockers": []},
  "exits": [{"condition": "C4", "action": "await_material", "round": 2, "when": null},
            {"condition": "C4", "action": "relaunch_review", "round": null, "when": null},
            {"condition": "C4", "action": "redecide_round", "round": 1, "when": null}]
}
}
```

**判据（每项都写成"调用哪个共享判定"；枚举仅说明，以判定实现为准）**

| 事实 | 判据 |
|---|---|
| `review_required` | `plan.complexity == "complex"`（与 `review-passed` 的短路条件同源） |
| `open_blocking` | `open_findings(...)["blocking"]`（**门禁同源、全轮次**）；条目须带 `round`（见 §6 ①）。**只含 blocking severity**；`unaddressed` 里的非 blocking 项**不在本文范围**（它们是判断骨架的输入，不是归档阻断） |
| `unverifiable` | `open_findings(...)["unavailable"]`（唯一来源，条目带 `cause/round/report_digest`） |
| `rounds[]` | **新增的逐轮决策事实**（`decide` 追加，append-only）：`{round, verdict, check_id, decided_at, invalidated_reason}`。**消费规则（同轮取最新）**：同一轮可能有多条（重判、失效追加）——所有消费方一律取该轮 `decided_at` 最大的一条，**禁止各自实现**。**失效同步（写点 `review-launch`）**：实施 CLI 变更时不能只处理当前 `result` 那一轮——**要对所有 `launch.implementation_cli` 与新 CLI 不同的轮各追加一条失效记录**（`invalidated_reason: "implementation CLI changed"`），否则旧的 pass 记录会永远是 pass 并被 `redecidable_rounds` 选中；而重判旧轮用的是**该轮 launch 保存的 CLI**（`review.py:1255`），根本发现不了与当前实施者的冲突。**失效优先级高于 verdict**：该轮最新记录带 `invalidated_reason` 即不可复用。**存量回退（无迁移）**：`rounds[]` 为空时按 `result` 推断一条 `{round: result.round, verdict: result.verdict ∈ {pass, fail} 时原值，否则 null, invalidated_reason: result.verdict == "invalidated" ? "implementation CLI changed" : null, decided_at: null, inferred: true}`，并在**下一次 `decide` 追加新记录时先把这条推断记录落盘**，避免 `result` 被覆盖后旧事实丢失。**消费排序**：`decided_at == null`（推断）视为最早，真实记录优先。<br>| `conclusion.binding` | **`review_binding`**（自 `review-passed` 提取）：`result.check_id == check.id` ∧ **结论至少引用一份已导入报告** ∧ 引用报告 `result_digest == recorded == 文件当前摘要`。<br>**"至少引用一份"必须写进判据**：门禁对 `cited` 为空是独立拒绝（`gates.py:695-696`），漏掉它会让空引用的结论算出 `binding == true` |
| `launches[]` | **逐轮事实，每轮一行**（不替 AI 挑轮）：`{round, form, imported, declared, undecided, redecidable, usable, usable_blockers}`。<br>· `form` = `discovered`（该轮导入记录带 `agent`）／`legacy`（显式 `--report/--slot`）／`null`（尚无导入，无法判定）<br>· `undecided` = 该轮在 `rounds[]` 中**没有记录**<br>· `usable`（**与 `decide` 同源**；不含标准漂移）。**资格、材料、质量三类事实分开，且「还不够」≠「不合格」**：<br>　**报告质量**（`review_report_problems`）：`report_invalid`、`anchor_stale`<br>　**资格**（`review_eligibility`）：`implementer_overlap`（任一已导入报告的 CLI == 实施 CLI，**逐报告即判、立即可知**）；`insufficient_reviewers`（已导入报告**按 CLI 去重**后 < 2——但这只在「已无更多材料可等」时才算不合格）<br>　**材料**：`discovered` 形态按「已导入数 < launch 声明数」判「还可能到」；`legacy` 形态按「声明槽位是否齐」判（`decide` 在 `discovered` 下**不要求**声明槽位齐，`review.py:1264-1284`）<br>**合成（按序，与 decide 的行为对齐）**：<br>① 任一**报告硬失败**或 `implementer_overlap` → `false`<br>② 无硬失败 ∧ 已导入去重 CLI ≥ 2 ∧（`discovered` 形态不再看声明槽位；`legacy` 形态槽位齐）→ **`true`**<br>③ 无硬失败 ∧ 去重 CLI < 2 ∧ **还有材料可能到达**（`discovered`：已导入 < 声明；`legacy`：槽位未齐）→ **`null`**<br>④ 无硬失败 ∧ 去重 CLI < 2 ∧ **已无更多材料可等** → `false`（`insufficient_reviewers`）<br>**这就是 v48 的语义 + legacy 区分**：v49 曾把 `insufficient_reviewers` 一律塞进硬失败、并用「已导入 < 声明」判材料，既把「等第二份报告」误判成失败，又把发现式的 2/3 判成 `null`——已撤回。<br>· `redecidable` = 该轮最新记录 `verdict == pass` ∧ 报告摘要与锚点仍匹配 ∧ `invalidated_reason == null` ∧ 该轮 launch 的 `implementation_cli` == **最新 launch 的 CLI**（纯派生；`decide` 入口用**同一条口径**把关，两者不再分叉）∧ **该轮当前 `usable == true`**（历史上判过 pass 不等于现在仍可重判——判定轮仍可继续导入报告，补入一份与实施 CLI 重叠的报告就会让该轮资格失效）。**不要求 check 换代**：同 check 的旧 pass 轮在 `result` 被后来的 `unavailable` 覆盖时同样值得重判<br>**`usable_blockers` 内容**：列出**全部**成立项（含 `material_missing`），硬失败在前；`usable` 取值只由 ①–④ 决定。 |
| `conclusion.check_valid` | **`check_validity`**（自 `check-passed` 提取，逐分支对齐 `gates.py:631-660`）：**`rule_version` 相符**（`check.anchor.rule_version` 存在且 ≠ 当前版本即 `WF_CHECK_STALE`，`gates.py:633-638`）∧ 当前锚点**可算**（`current_check_anchor` 无 `error`）∧ **未 `invalidated`** ∧ `result == pass` 且 **anchor 存在** ∧ 保存的 `check_anchor` == 当前内容锚点 ∧ **结构复核 `check_result_problems` 为空**。（v46 曾以「门禁不比较 `rule_version`」为由删掉该条——那是我读代码时**从 639 行起截取**、漏看 633-638 所致；该修正作废，v47 恢复） |
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
**这是 ⑥ 唯一不交付「AI 自主闭环」的地方**：单项处置已有依据与复核，仍被整轮审查卡住。该成本已由 **D3 = 选 A** 裁定接受（A8 后补）。

### 4.2 每个条件的清除动作

| 条件 | 清除动作（`exits` 机制枚举：`{condition, action, round, when}`，skill 只渲染不判断）。**`round` = 该动作的目标轮**（`redecide_round`/`resume_inflight`/`await_material` 必带；无轮次语境的动作为 `null`）。**`when`** = 该动作可执行的前置事实表达式，`null` 表示无条件。**不设 `preferred`**：偏好属于 AI 结合上下文的判断 |
|---|---|
| **C1 失效** | `rerun_check`（重跑 `task-check` 产生新 check） |
| **C2 未空** | **关闭的前提是「处置结果已成立并经非提出者复核」**，不是「同意某种修法」——① 已修复且已重查通过 ② 经复核认定误报（无需改代码）③ 已重分类（本就不是问题）；**「同意修法但还没做」不得写 `accepted`**（finding 会立刻从 `open_blocking` 消失，light 无 C4 兜底）→ 保持 open，或写 `amended` + 理由（不关闭）。**在锚点仍匹配时**补 disposition（**`decision` 必须写 `accepted`**，B5）→ `record_disposition`。**时机约束（机制事实，必须进指引）**：`decide` 按**当前工作区内容**重算锚点（`check.py:118`），代码改过之后旧轮报告就失配、在旧轮补处置必被 `WF_REVIEW_INVALID` 拒。两条合法路径**各自对应不同处置类型**：① 随 fail 轮那次 `decide` 一并写——**只适用于「误报 / 重分类」**（处置结果无需改代码即成立、内容未变）；② 随**修好 + 重查后的新一轮** `decide` 捎带——**「已修复」只能走这条**（内容必然已变）。**「同意修法但还没做」不得写 `accepted`**（见 A67） |
| **C3 未放行** | ① `restore_bytes`（找回原字节，不依赖身份）<br>② `human_release`（`release_allowed == true` 时）——**放行的语义边界（本版新增）**：某份报告不可核实时，它里面的 findings 也随之无法枚举（`open_findings` 跳过整份报告），因此放行**必然同时豁免该报告中未知的 findings**。决定文件必须显式承认这一点（`waive_unknown_findings: true`），缺失即拒；**且不得把放行描述成"缺陷已处置"**——C2 不会因此被满足，只是那部分问题从此不可枚举<br>③ `relaunch_review`——改变事实而不是硬闯：complex 的 `cited` 损坏不可放行，但可完成一次新审查；新结论引用新报告后，旧报告变成**非引用**证据 → 下一轮 `human_release` 即可用<br>④ 只有"上述全部不可行"才 `abandon_task`（**不得把"当前不能放行"直接推成"应放弃"**） |
| **C4 不成立** | **按 `launches[]` 逐轮给出口，每条带 `round` 目标；机制不表达优先级**（无 `preferred` 字段）：<br>· 对每个 `undecided == true` 的轮：`usable == true` → `resume_inflight{round}`；`usable == false` → `relaunch_review`（`usable_blockers` 一并给出）；`usable == null` → `await_material{round}` 与 `relaunch_review` 并列<br>· 对每个 `redecidable == true` 的轮：`redecide_round{round}`——**与上面并行给出，不互斥**（重判旧轮与新轮推进可同时进行）<br>· 无任何轮可用（既无 undecided-usable，也无 redecidable）→ `relaunch_review`<br>· **`pause_for_human` / `abandon_task` 始终给出**：它们是「需人/终局」选项，不依赖可派生事实（`unavailable` 是记录事实，「环境凑不齐」派生不出来——所以不做条件化，常列即可）。**护栏**：常列不等于推荐——`abandon_task` 与 C3 ④ 同一口径，**不得把「当前推进不动」推成「应放弃」**；G4 指引必须写明这一点<br>**为什么去掉 `preferred`**：材料是否够判是机制事实，**先重查、先修复还是先续判属于结合上下文的判断**。`check_valid == false ∧ usable == true` 就是典型：先续判会绑到旧 check，重查后又失绑——这个取舍机制无权代决。<br>**事实提示（非顺序强制）**：`check_valid == false` 只说明当前检查不能用于完成任务，不证明在途轮作废；结论绑定判定那一刻的 check（`review.py:1425`）。**已知盲区**：`usable` 不含标准漂移（导入时标记是历史事件，`standard_drift_gate` 在 decide 时重算，`review.py:482`），`decide` 始终是权威 |

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
| `review-decide` 判定资格、`task-check` 语义 | **资格判定不改**，但 `decide` **新增一条入口校验**（见 §6 ②）：目标轮最新 `rounds[]` 记录带 `invalidated_reason` 时**拒绝重判**（`WF_REVIEW_INVALID`，出口＝发起新一轮）；否则按 §2.1 的自述，重判会用该轮旧 launch 的 CLI 校验、把失效静默挤掉。<br>**理由**：出口层不推荐 ≠ 机制保证——§4.2 宣称「decide 始终是权威」，权威命令就必须拦这条。 |
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
| **A6 缺 `report_digest` 的遗留导入记录** | C3 覆盖**全部轮次**，而这类记录既无法恢复、也无法放行 → 新门禁把旧缺陷的等级从「体验」抬成「正常收尾被阻断」，必须开工前处置（补摘要或先排除该轮） | 顺带补一条：⑥ 不新造无法放行的历史条目 |
| **C1 读取归因** | `open_findings` / `review_binding` 都读摘要，权限故障会抛出；⑥ 自带这两处，其余五处属 C1 |
| ~~D4~~（**已纳入 §6 待实施清单**） | 原本确实需要它（C3 阻断挂在 `final_gate` 尾部、业务提交在前）。本版把 **D4-minimal** 写进 §6 的实施清单，**批准后**才做，因此不再是外部前提 |
| ~~A8~~（归入「成本前提」，见本节末） | A8 不属可执行性前提：没有它 light 关 C2 贵但能走通 |

**前提分层（本版明确，消除上一版的计数与性质混乱）**

| 层 | 项 | 缺了会怎样 |
|---|---|---|
| **可执行性前提** | A1、A4、A7、A9、C1 | ⑥ 的事实或清除动作**算不出来**，必须先做。（A10「逐轮决策事实」已由本方案的 `rounds[]` 承接，故不列为外部前提） |
| **本方案自带（非外部前提）** | D4-minimal（归档提交前预检） | 已列入 §6 待实施清单（状态：未实施）；**批准后**才做 |
| **成本前提** | A8（轻量关闭入口） | light 关 C2 需要一整轮审查（贵但能走通）；建议先做，不作前置 |

**披露（机制自洽但不免费）**

| 代价 | 说明 |
|---|---|
| complex 多轮累积人裁 | C3 覆盖**全部轮次**的不可核实证据：round-1 的报告即使与最终 pass 无关，损坏也要一次放行 → 轮次越多签到越多 |
| light 关闭 C2 的入口成本 | 见 §4.1 末（A8） |
| 放行通道的信任残余 | 见 §2.2 末（声明式，可伪造，仅留痕） |
| **实施换 CLI 但未发起新一轮** | 失效同步只在下一次 `review-launch` 时发生；此窗口内 `decide` 仍用该轮保存的旧 CLI 校验、门禁也不复核 CLI。自动身份模式下无法用会话身份关闭，只能靠指引（G3：换宿主先 launch）——如实登记为残余 |

---

## 6. 待实施清单（**全部未实施**；批准后按此执行）

| 文件 | 状态 | 改动 |
|---|---|---|
| `gates.py` | 未实施 | ① 提取 `review_binding`（含 **cited 非空**）与 `check_validity`（含 `rule_version`、结构复核）供 `repair_scope` 复用，步骤行为不变；② 两处摘要读取包 `except OSError`；③ `final_gate` 追加 `unverifiable`（C3）阻断——**该分支必须位于被提取的 `final_gate_nonstep` 内部**（否则预检覆盖不到它，正是 §4.3 约束 1 要防的「业务已提交、归档因 C3 被拒」）；`exits` 用 §4.2 的 token 并带 `facts.reason = "unverifiable_evidence"` |
| `review.py` | 未实施 | ① `open_findings` 的 `blocking`/`unaddressed` 条目补 `round`、`unavailable` 条目补 `cause/round/report_digest`（`cause` 须**区分 `missing`（`file_digest` 返回 `None`）与 `changed`（摘要不符）**），摘要读取包 `except OSError`；② `review-decide` 入口校验：**先落盘按 `result` 推断的记录**，再做两条拒绝——目标轮最新记录带 `invalidated_reason`，**或**该轮 launch 的 `implementation_cli` ≠ **最新 launch 的 `implementation_cli`**（即任务当前生效的实施声明；**不用会话身份**——自动身份模式下拿不到宿主 CLI，用会话会把合法交接误判为换人）→ `WF_REVIEW_INVALID`，出口＝发起新一轮；③ 追加 `reviews.rounds[]`；④ 提取 `review_eligibility`（←`input_problems`）与 `review_report_problems`（←`problems`）两个共享函数，不合并；⑤ `repair_scope` 纯派生 + `exits_for`（**唯一出口实现**，返回 `[{condition, action, round, when}]`，**无 `preferred`**） |
| `tasks.py` | 未实施 | ① **D4-minimal**：`cmd_archive` 在业务提交前跑只读预检。**为什么不能只调一次 `final_gate`**：它是**顺序短路**结构（`gates.py:865-871`：先跑 `evaluate` 的步骤面，任一步 missing 即返回 `{missing, all}`），而预检发生在提交之前 → `changes-persisted` 必 missing → **nonstep 十项一次都不会跑**，等于漏检 escalated/required/依赖/debug/`paused` 与 ⑥ 的 C3 阻断。**正确契约**：把 `final_gate` 的 nonstep 段**提取为可复用函数** `final_gate_nonstep(ctx, task, ignore_action_id=None)`（现 `gates.py:873-951` 的内容原样搬出，`final_gate` 改为先跑步骤面、再调它——**不是第二套实现**；搬移必须**行为等价**：对既有失败场景（escalated/required/依赖/debug/action/paused）返回的 `code` 与 `facts` 逐字段相同，见 A68）；预检 = ① `final_gate_nonstep(ctx, task, ignore_action_id=task.action.id)` ∧ ② `evaluate(ctx, task, "before_archive")` 的结果**先按 `id` 排除 `task.changes-persisted`、再取 `status == "missing"` 的条目**，这些必须为空（`evaluate` 对每个适用步骤都返回条目，`status ∈ {missing, completed, reused, satisfied}`（`gates.py:789-793`）——**「列表为空」是错的判据**，正常任务也会有 completed/satisfied 条目）∧ ③ **授权覆盖判定**：`pending ⊄ 本次提交路径集` → 拒（`WF_WIP_UNRESOLVED`，`tasks.py:1009-1015`）。三者任一不过即拒绝（不提交）；②被过滤掉的那一步由归档自身的提交满足，③补位防「授权只覆盖部分待提交路径」；② 的调用**只传 `rule_version`**（`evaluate` 没有 `ignore_action_id`，`gates.py:764`；失败返回的 facts 是 `{missing, all}`、成功才是 `{steps}`，`gates.py:871/952`）；④ `unknown_acceptances` 消费钩子（预检之前） |
| `cli.py` | 未实施 | ① `wf status` 输出 `repair_scope`，`unverifiable` 条目渲染三态、`open_blocking` 标「已驳回未关闭」、**`launches[]` 标 `inferred` 边界**；② `--short` 原样输出四条件 + `exits`（含 `round`），不重新推导；③ 新增 `wf review-accept-unknown`（`--revoke`，含 `consumed`）；④ **归档与 `status` 强制回显当前放行清单**（A12 的最小缓解，见 §6a） |
| `skills/` | 未实施 | 见 **§6a 指引交付大纲**（独立交付物，含验收 B1–B6） |

### 6a. 指引交付（与机制同批，不是附属品）

机制给事实，指引负责「拿到事实后怎么合法行动」。交付四份改动 + 一份新增 **`wf-repair-loop`**（新指引，落地时加入 `skills/`）：

| # | 文件 | 必须讲清的内容 |
|---|---|---|
| G1 | `wf-review-action` | 处置形状 `{finding_id, round, slot, decision, reason, recheck_by}`；**只有 `accepted` 清零**（`rejected`/`amended` 只记录）；**`--round` 必须显式传**——`decide` 默认取最大 launch 轮，与 `exits.round` 可能不同 |
| G2 | `wf-review-action` | **处置的时机约束**：`decide` 会按**当前工作区内容**重算锚点，代码一旦改动，旧轮报告即失配 → 在旧轮补处置会撞 `WF_REVIEW_INVALID`。合法路径只有两条：随 fail 轮那次 decide 写；或随**修好+重查后的新一轮** decide 捎带 |
| G3 | `wf-repair-loop`（新） | **换实施宿主后必须先 `review-launch` 再判定**（自动身份模式拿不到宿主 CLI，这是唯一能闭合「实施已换、尚未发起新一轮」窗口的手段）；读 `repair_scope` 的顺序与判读：`launches[]` 逐轮看 `usable/redecidable`；`undecided` 在存量任务里可能是**推断残缺**（`inferred`），不代表可续判；`check_valid == false` 时「先重查还是先续判」由 AI 判断，并给出两条路径各自的后果 |
| G4 | `wf-repair-loop` | **动作空间**：十个 token 的含义、哪些需要 `round`、哪些是终局；并列出口如何选（机制不排序，AI 选定后说明理由）；**三条读法**：① `usable_blockers` 非空 ≠ 不可用（看 `usable` 取值）；② `abandon_task` 常列 ≠ 推荐放弃；③ `accepted` 仅表示处置结果已成立（「同意修法但还没做」不写） |
| G5 | `wf-continue` / `wf-finish` | `in_progress/finish` 路由前先读 `repair_scope`；收工前读 `gate` 与 `repair_scope`，**不要试归档探路** |
| G6 | `wf-review-accept-unknown` | 人机交互：何时问人、呈现什么（哪些证据不可核实、`release_allowed` 为何值、未知 findings 一并豁免意味着什么）、`quote` 如何采集、决定文件如何写 |

**不做第二套口径**：`cause`/`round` 只在 `open_findings`；`binding`/`check_valid` 只在两个共享函数。

---

## 7. 验收

**分两档**：A 档=机制可测（代码/事实/门禁行为，可自动化）；B 档=文档审查（指引措辞，需人读，**不计入自动化计数**）。上一版把两档混在一张 49 项表里，导致「承诺名实不符」。

### A 档：机制可测（69 项）

| # | 断言 |
|---|---|
| A1 | `open_blocking` 与 `final_gate` 的 `unaddressed_blocking` 逐项一致（同源、全轮次），且每条带 `round` |
| A2 | `binding` 是子判定：`verdict == "fail"`、check 未换代、引用摘要一致 → `binding == true`（不因 `verdict != pass` 而 false） |
| A3 | **`binding` 空引用即为 false**：结论 `imported` 为空时 `binding == false`（与 `gates.py:695` 的拒绝对齐） |
| A4 | `check_valid` 与 `check-passed`（`gates.py:631-660`）逐分支一致：**`rule_version` 不符→false**、锚点不可算→false、`invalidated`→false、`result != pass`→false、anchor 缺失→false、anchor 不符→false、`check_result_problems` 非空→false |
| A5 | 内容改动未重查 → `check_valid == false`、`check_blockers` 含 anchor 漂移（C1 未满足） |
| A6 | 重查产生新 check → `binding == false`（`check_id_changed`），`open_blocking` 不消失（B5） |
| A7 | **只写 `accepted` 才清零**：`decision == "rejected"`/`"amended"` 后 `open_blocking` 仍非空（B5 反直觉语义） |
| A8 | `verdict == "fail"` ∧ `binding` ∧ `open_blocking` 已清 → C4 未满足，`exits` 含 `relaunch_review` / `resume_inflight` |
| A9 | **`exits` 是集合、无序**：某轮 `undecided ∧ usable == true` 时 `exits` **必须包含** `resume_inflight{round}`（可与 `redecide_round{round}` 等并存，不排优先级） |
| A10 | complex：`cited` 损坏 → `release_allowed == false`，`human_release` 不在 `exits` |
| A11 | light：`cited` 损坏 → 仍阻断，且 `release_allowed == true`，`human_release` 在 `exits`；放行后 C3 满足 |
| A12 | 非引用损坏 + 摘要全等放行 → C3 满足；撤销后恢复；匹配需三元组全等 |
| A13 | **决定文件 schema**：digest 与登记摘要不等 → 整批拒绝（防 typo 生成永不匹配记录）；缺 `quote`/`source` → 拒绝 |
| A14 | 撤销后**可重新批准**：批准 → 撤销 → 再批准，`released` 回到 true；幂等只在"存在未撤销记录"时生效 |
| A15 | 报告恢复原字节 → 不再出现在 `unverifiable`（B1） |
| A16 | `cause` 三分只由 `open_findings` 产出，`repair_scope.unverifiable` 与之逐项一致 |
| A17 | 权限故障不崩：`open_findings`、`review_binding`、`status`、`wf gate` 全部走归因分支 |
| A18 | 并存无遮蔽：`open_blocking` 非空同时有未放行 `unverifiable` 时，两组事实**同时**出现 |
| A19 | **light 不承担 C4**：自愿审查 `fail`/`unavailable`/`invalidated` 且 `open_blocking` 空、C1/C3 满足 → 不产生"必须取得新审查结论"义务 |
| A20 | 但 light 的 C2/C3 仍成立：自愿审查带 blocking → 未关闭时归档被 `WF_UNRESOLVED_BLOCKING` 拒；报告损坏 → C3 阻断 |
| A21 | **C3 出口门控（可测）**：`unverifiable` 条目 `release_allowed == false` 时，`exits` **不含** `human_release`；`release_allowed == true` 时**含** `human_release`（同一断言见 A10，此处只保留一条） |
| A22 | 主动性约束：`repair_scope` 不含"等待评审/待评审确认"类状态；除 complex C4 外，未满足条件都能在不取得新审查结论的前提下推进 |
| A23 | `--short` 输出四条件+`exits`，不输出完整事实集；`task.check` 字段派生等其余 `--short` 改动仍属 backlog |
| A24 | 协议零改动：`phase.enum`、迁移数、`next_by_position` 逐字节一致；`repair_scope` 不参与 `next`；`task-abandon` 仍可终止且不解除阻断 |
| A25 | `usable` 三态合成（与 `decide` 同源）：① 报告硬失败（`report_invalid`/`anchor_stale`）或 `implementer_overlap` → `false`；② 无硬失败 ∧ 已导入去重 CLI ≥ 2 ∧（`discovered` 不看声明槽位；`legacy` 槽位齐）→ `true`；③ 去重 CLI < 2 ∧ 还有材料可能到达（`discovered`：已导入 < 声明；`legacy`：槽位未齐）→ `null`；④ 去重 CLI < 2 ∧ 已无更多材料可等 → `false`（`insufficient_reviewers`） |
| A26 | `usable` 与 decide 同源：`implementer_overlap`/`insufficient_reviewers` 来自 `review_eligibility`（`input_problems` 通道），`report_invalid`/`anchor_stale` 来自 `review_report_problems`（`problems` 通道）；两通道不得合并 |
| A27 | `pause_for_human`/`abandon_task` **在 C4 未满足时始终出现**（不减其它动作），且 `abandon_task` **不得被当作推荐**（不得把「当前推进不动」推成「应放弃」） |
| A28 | C4 的事实提示**准确**：只说「结论写入后再重查会失绑」，**不得**声称「发起早就会失绑」；先重查是建议而非机制事实 |
| A29 | `usable` 吸收输入无效：已导入报告存在「申报 verdict 与推导不一致」→ `usable == false`、`usable_blockers` 含 `report_invalid`（判据来自 `review_report_problems`，与 `review-decide` 的 `problems` 通道同源） |
| A30 | **`check_valid == false` 不进 `usable_blockers`**：它只说明"当前检查不能用于完成任务"，不证明在途轮作废；此时 `exits` 必须给出「先重查，再核对材料后继续用原轮」的依据，而不是强制 `relaunch_review` |
| A31 | `exits` 形状与落点：`[{condition, action, round, when}]`，只由 `exits_for` 产出；**无 `preferred`**；`redecide_round`/`resume_inflight`/`await_material` 必带 `round`；`pause_for_human`/`abandon_task` **在 C4 未满足时始终出现** |
| A32 | `undecided.rounds == []`（全部已判或从未发起）时 `exits` 不含 `await_material`；`usable == null`（材料未到齐）时 `await_material` 与 `relaunch_review` 并列且**均非默认** |
| A33 | 决定文件四件套：缺 `by`/`at`/`quote`/`source` 任一 → 拒绝（`by` 必须 `human:` 前缀） |
| A34 | 共享函数二分：`implementer_overlap` / `insufficient_reviewers` 来自 `review_eligibility`（`input_problems` 通道），`report_invalid` 来自 `review_report_problems`（`problems` 通道）；两通道不得合并（否则搅浑 S4 的 invalid 态边界） |
| A35 | **部分导入 + 硬失败**：声明 2 槽位、只导入 1 份且该份 `report_invalid`/`anchor_stale` → `usable == false`（**不得**因材料未齐而报 `null`） |
| A36 | **发现式 2/3 可判**：声明 3 位只到 2 位且两位互异 → `usable == true`（decide 不要求声明槽位齐）；只到 1 位 → `null`（等得起） |
| A37 | **豁免后原字节恢复**：报告重新可核实 → 离开 `unverifiable`、findings 重新枚举 → C2 重新可能不满足；此前的 `waive` 记录**不**覆盖新枚举出的 findings（B1 的"事实变化"对偶面） |
| A38 | **一次一事件**：丢失→放行→恢复（离开 `unverifiable`）后该放行标 `consumed`；再次损坏时**旧放行不再生效**，C3 重新阻断，需新的放行决定 |
| A39 | **资格拆两类**：已导入报告的 reviewer CLI 与实施 CLI 相同 → 材料未齐时也立即 `usable == false`（`implementer_overlap`）；仅"去重人数不足"才等到材料齐后判定（`insufficient_reviewers`） |
| A40 | **消费保证的范围**：只保证「受控写点观察到恢复即失效」；「恢复后在无写命令期间再次损坏」**不在保证内**，归档钩子只兜住「归档时报告仍可核实」那一支 |
| A41 | `rounds[]` 生命周期：同轮多条取 `decided_at` 最新；`review-launch` 遇 CLI 变更**对所有受影响轮各追加失效记录**；`rounds[]` 为空时按 `result` 推断一条（`inferred: true`），**并在第一次写入前先把它落盘** |
| A42 | `undecided` 语义：只有「尚无判定记录」的 launch 轮；**被放弃的坏轮也算未判定**，但不得因此把 `redecide_round` 藏起来 |
| A43 | **出口逐轮给出**：对每个 `undecided ∧ usable == true` 的轮给 `resume_inflight{round}`，对每个 `redecidable` 的轮给 `redecide_round{round}`，**两者并行不互斥**；无可用轮才 `relaunch_review` |
| A44 | `usable` **不含**标准漂移判断（导入时标记是历史事件、`standard_drift_gate` 在 decide 时重算），且 `decide` 为权威 |
| A45 | `launches[].redecidable` = 该轮最新记录 `verdict == pass` ∧ 报告摘要与锚点仍匹配 ∧ `invalidated_reason == null` ∧ **该轮 launch CLI == 最新 launch CLI** ∧ **该轮 `usable == true`**（不要求 check 换代） |
| A46 | `rounds[]` 新增字段与失效同步出现在 §6 待实施清单（`review-decide` 追加、`review-launch` 追加失效记录） |
| A47 | D4 预检 = `final_gate_nonstep(ignore_action_id=task.action.id)` ∧ `evaluate("before_archive")` 排除 `id == "task.changes-persisted"` 后 **`status == "missing"` 的条目为空** ∧ 授权覆盖判定（`pending ⊄ 提交路径集` → 拒）；**不得**以「单次 `final_gate` 调用」实现（顺序短路会在提交前只看到步骤缺项，nonstep 十项全漏） |
| A48 | `usable_blockers` 内容：硬失败与 `material_missing` 并存时**全部列出**（硬失败在前），`usable` 取值只由 ①–④ 优先级决定 |
| A49 | `released` 三条件：存在 `(round, slot, report_digest)` 全等、**未撤销且未消费**的放行记录；缺一即不算已放行 |
| A50 | 消费写点三处：`wf archive` 的 `final_gate` 前置钩子、`review-import`、`review-decide` 发现「记录对应报告当前可核实」即置 `consumed` |
| A51 | **`decide` 拒绝重判已失效轮**：目标轮最新 `rounds[]` 记录带 `invalidated_reason` → `WF_REVIEW_INVALID`（出口＝发起新一轮），不得静默产出 pass |
| A52 | 失效同步范围：`review-launch` 遇实施 CLI 变更时，对**所有** `launch.implementation_cli` 不同的轮各追加失效记录 |
| A53 | 存量回填：`rounds[]` 为空时按 `result` 推断一条并在**首次写入前落盘**（`inferred: true`，`decided_at: null` 视为最早） |
| A54 | **预检的调用契约**：`evaluate(ctx, task, "before_archive")` 只传 `rule_version`（无 `ignore_action_id`）；nonstep 段由**提取出的 `final_gate_nonstep(ctx, task, ignore_action_id=…)`** 提供，二者与正式门禁同源 |
| A55 | **`check_valid` 含 `rule_version`**：`check.anchor.rule_version` 与当前版本不等 → `check_valid == false`（C1 未满足）；D4 预检据此不会在规则换代后放行提交 |
| A56 | **A6 成为前置**：缺 `report_digest` 的遗留导入记录在 C3 下**无法恢复也无法放行** → 必须在开工前明确处置（迁移补摘要 / 或先归档排除），不得留作「互不阻塞的独立事项」 |
| A57 | **`legacy` 形态**：槽位齐但两份报告同一 CLI → `usable == false`（`insufficient_reviewers`）；槽位未齐 → `null`（等得起） |
| A58 | **`redecidable` 与 `usable` 一致**：`usable == false` 的轮不得 `redecidable == true`；`redecidable` 判据 = 最新记录 `pass` ∧ 报告匹配 ∧ 未失效 ∧ 该轮 launch CLI == 最新 launch CLI ∧ 该轮 `usable == true` |
| A59 | **存量 `undecided` 是推断残缺**：其余历史轮显示 `undecided` 但历史不可知；`status`/`--short` 须标 `inferred` 边界 |
| A60 | **`release_allowed` 随 complexity 漂移**：定义取**当前** `plan.complexity`；complex→light 降级后同一 `cited` 损坏证据的放行资格会翻转——**归属**：`status` 渲染须显示该条目的 `release_allowed` 现值，G6 指引须说明降级会改变它 |
| A61 | **`cause` 三分可判**：`file_digest` 返回 `None` → `missing`；摘要 ≠ 登记摘要 → `changed`；读取抛 `OSError` → `unreadable` |
| A62 | **归档回显放行清单**（A12 最小缓解）：`wf archive` 与 `wf status` 强制列出当前生效的 `unknown_acceptances`（含 `by/at/quote`） |
| A63 | **`decide` 入口两条拒绝**：目标轮最新记录带 `invalidated_reason` → 拒；该轮 launch CLI ≠ 最新 launch CLI → 拒（`WF_REVIEW_INVALID`，出口＝新一轮）。**不用会话身份**（自动身份模式无宿主 CLI） |
| A64 | **退出口径一致**：`exits` 里的 `redecide_round{round}` 与 `decide` 入口校验用**同一口径**（该轮 launch CLI vs 最新 launch CLI），不得分叉 |
| A65 | **`usable_blockers` 非空 ≠ 不可用**：`usable == true` 时该列表仍可能含 `material_missing` 等**事实**（如发现式 2/3）；G4 指引须写明读法（看 `usable` 取值，`blockers` 是事实清单而非阻断清单） |
| A66 | **预检的三段构成**：`final_gate_nonstep(ignore_action_id=…)` ∧ `evaluate("before_archive")` 排除 `task.changes-persisted` 后 **`status == "missing"` 为空** ∧ 授权覆盖判定；**不得**用单次 `final_gate`（顺序短路会漏掉 nonstep 段） |
| A67 | **C2 的关闭语义**：`accepted` 只能表示「**处置结果已成立并经非提出者复核**」——① 已修复且已重查通过、② 经复核认定误报（无需改代码）、③ 已重分类（本就不是问题）。**「同意某种修法但还没做」不得写 `accepted`**（否则 finding 立刻从 `open_blocking` 消失，light 又没有 C4 兜底）；此时保持 open，或写 `amended` + 理由（不关闭） |
| A68 | **提取行为等价**：`final_gate_nonstep` 提取后，既有失败场景（escalated/required/complex 未确认/降级不完整/依赖/`unruled_debug_multiples`/`action_incomplete`/`paused`）返回的 `code` 与 `facts` 与提取前**逐字段相同**；`paused` 与 `action_incomplete` 的交织顺序不变 |
| A69 | **C3 分支归属**：新增的 `unverifiable` 阻断位于 `final_gate_nonstep` 内——预检在提交前即可看到它（否则「业务已提交、归档因 C3 被拒」） |

### B 档：文档审查（6 项，人读勾选；不计入自动化计数）

| # | 要求 |
|---|---|
| B1 | `wf-review-action`：处置形状正确、**只有 `accepted` 清零**、**必须显式传 `--round`**（默认取最大 launch 轮，与 `exits.round` 可能不同） |
| B2 | `wf-review-action`：写明**处置时机与类型的对应**——① 路径（随 fail 轮同批）**只用于误报/重分类**；② 「已修复」只能随**修好+重查后的新一轮** decide 捎带；「同意修法但还没做」不写 `accepted` |
| B3 | `wf-repair-loop`（新）：读 `repair_scope` 的判读顺序、`launches[]` 逐轮看、存量 `inferred` 边界、`check_valid == false` 的两种走法及后果 |
| B4 | `wf-repair-loop`（新）：十个 token 的含义与目标轮、终局动作、并列出口如何选，以及**三条读法**（`usable_blockers` 非空≠不可用、`abandon_task` 常列≠推荐、`accepted` 仅表示结果已成立） |
| B5 | `wf-continue` / `wf-finish`：路由与收工前先读 `repair_scope` 与 `gate`，**不要试归档探路** |
| B6 | `wf-review-accept-unknown`：人与机制的分工——何时问人、呈现哪些不可核实证据、`release_allowed` 取值含义、未知 findings 一并豁免意味着什么、`quote` 如何采集 |

## 8. 范围边界（防跑偏，硬约束）

本文只回答 ⑥。不在范围（详见 `analysis/backlog-excluded-from-item6.md`）：
`slot`/`agent` 身份域（**A1 为前提**）、导入端证据身份与 `--restore`（**A4 为前提**）、
关闭链提出者（**A7**）、**finding 精确身份（A9）**、**缺 `report_digest` 的遗留记录（A6，已升为前置）**、`review-status` 的 ready/material 语义、
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

## 10. 已定项（2026-11-11 人裁）

| # | 问题 | 裁定 |
|---|---|---|
| D1 | 不可核实证据阻断用哪个码 | 复用 `WF_REVIEW_INVALID` + `facts.reason = "unverifiable_evidence"` |
| D2 | 人裁是否引入签名 | 不引入；沿用声明式 attestation（残余风险见 §2.2） |
| **D3（已定：选 A）** | light 关闭单个问题是否必须整轮审查？ | **接受成本**：A8 归 backlog 后补；⑥ 不声称交付「light 自主闭环修复」，该口径已写进 §4.1 |

> Q1=乙、Q2=甲 亦已定；D3 已于 2026-11-11 裁为**选 A**。**本文无待决项。**
