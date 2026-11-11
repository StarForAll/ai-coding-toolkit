# 提案（v23）：⑥ 只做「结构化未结事实」+ 一条人裁放行记录 + 文档裁定

> 状态：**待审 v23**（第二十一轮修正；Q1/Q2 已定）。
> 前二十二版的形态与致命点见 §0。
>
> **阶段声明（2026-11-11 人裁）**：本文件处于**方案审查阶段**——**实现零改动**。
> 审查期间曾误改的实现已全部回退（`e49da16`，回退到 `8da2f23`）；下文凡提到"实现"均为**要求与验收**，
> 不代表已落地。**未经人明确"审查通过"，不得修改任何实现代码**（`payload/`、`release/`、`scripts/tests/`）。

---

## 0. 二十二轮审查的形态演进与净结论

| 版本 | 形态 | 致命点 |
|---|---|---|
| v1/v2 | 派生事实（"修复中"/"原因集合"） | 派生要复制门禁；定义与退出条件互斥；五态装不下 |
| v3 | 新增 `fixing` 阶段 | 身份矛盾（含 check 的五值 vs v42 无 check）；漏协议硬校验；pass→check 逼出重复 check |
| v4 | 事件写入 `repair` 标记 | 主路径清不掉；两失败源共用槽位；撞名 `repair.py` |
| v5/v6 | 两行 / 结构化 `unresolved` | 缺结论绑定；"未要求"遮住 blocking；缺"复杂未审查"行 |
| v7/v8 | 档位重排 | `gate` 只答步骤面；`pass_unbound` 死区；`invalidated` 死行 |
| v9/v10 | 当前轮优先 + 复用 `review-status` | 从未发起审查无命中路径；判定后证据失效；`round_complete` ≠ 可判定 |
| v11 | 三条自动退出 | **建在不存在的数据上**：`imported` 记录不含 findings（已核实）；且"新轮 pass"可绕开关闭 |
| v12 | 两条出口（重发 / 人裁） | **人裁通道不存在**：`authorize.ACTIONS` 固定五类、存储一键一文件后写覆盖、无 `--choice`；文档三处残留"三条退出" |
| v13 | 人裁放行改为独立记录 + 混槽位并列 | **证据可被替换**：删文件后导入同轮同槽位另一份报告即可顶掉旧证据；`launches` 实为 `[]`；行 8 引用断链；性质测试枚举域与 schema 不一致 |
| v14 | 证据身份约束 + 混槽位并列 + 拆档 | 发现模式"已完成未导入"仍报 missing；验收 4 与 13d 相反；计数与 attestation 字段不一致；行 8 未标"重发不解除"；性质测试缺"轮次关系" |
| v15 | 暂存发现口径 | **同一份已导入报告被二次认领**（一份算两份到位、`ready_to_decide=True`）；挂载点 `next_` 在 stale/单 provider 轮仍提示"可判" |
| **v16** | 同一报告只认领一次 + `ready_to_decide` 对齐 | 仍漏两处：`ready` **没要求"已导入"**（staged 就算可判）；`unreadable` 被引用却无产出路径；边界声明与账本失真 |
| **v17** | `ready` 收紧 + 历史读取健壮 | 只修两处 OSError：`all_findings`/`proposers_from_imported`/`review-passed` 仍会让判定与 `--unavailable` 一起失效；`ready` 未要求锚点已核、也忽略“声明槽位之外”的导入报告；`staged` 与“可导入”混同；`unavailable` 两套形状 |
| **v18** | 全链路读取健壮 + `ready` 已核锚点 | **`gates.py` 一处未修**（`review-passed` 仍抛 `PermissionError`，`wf gate` 会崩）；第 6 档未用 `round_ready`、`extra_reports` 无承载；`staged` 文案没接 `importable`；「等来的报告可复用」与报告协议冲突；恢复后一律 `stale` 过绝；两条新测试失败原因相互遮蔽 |
| **v19** | 15 档表 + `round_ready` | 档位表相互矛盾/死档/归因错误；`round_ready` 混淆"材料就绪"与"判定资格"；finding 按裸 id 汇总；恢复无通道 |
| **v20** | 删表 + 原子事实 + `--restore` + finding 身份 | Q1（批量放行形状）、Q2（两类阻断分列）未定，schema 与验收无法定稿；`bound_to_current`、撤销/信任模型、`blocking_unknown` 产生范围仍缺 |
| **v21** | Q1/Q2 已定并落位 | 本版：§2.1 批次全有或全无、§2.2 code 优先级、§9 扩到 22 项、`open_findings` 增 `blocking_unknown`/`pending_unknown`（纯增量，门禁消费待批准） |
| **v22** | 材料/资格分列 + restore 保原锚点 + 关闭需精确身份 | 本版：`reports_ready` 去资格化、`material_blockers`/`eligibility_hints` 分列；`--restore` 保留原登记锚点（含默认扫描路径）；不可读条目保住登记摘要（否则放行死锁）；新增 disposition 歧义即拒、`all_findings` 同步精确身份；`gate` 缺项带 `fulfilled_by`；撤销不删记录；`task-abandon` 定位为终局出口；验收 26 项 |
| **v23** | 缺摘要不可替换 + 裸 id 固定 + schema 对齐 | 本版：§1.1 schema 与本版事实全面对齐（去 `accepted_by`、补 `pending_unknown`/`material_blockers`/`eligibility_hints`）；缺登记摘要的记录拒绝就地替换；遗留裸 id 只固定最早一轮；`declared==0` 给 `no_declared_slots`；发现式 restore 仅在已登记时传；§9 稠密编号 **36 项**（自计数） |
**已核实的产品级事实（含对 v11 错误引用的更正）**

| 事实 | 位置 |
|---|---|
| `reviews.imported[]` **不含 findings**（只有 round/slot/report_path/report_digest/anchor） | `review.py:1131-1144` |
| 提出者只能**重解析报告**得到（既有实现从记录读 findings 恒为空 → 关闭链断；本提案要求修） | `review.py:573` |
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
  "review": {                         // 只有原子事实，没有档位分类
             "round": 2, "launched": 2, "imported": 2, "declared": 2,
             "slots": [{"slot": "s1", "state": "imported|staged|stale|missing|unreadable",
                        "round": 2, "reason": null, "importable": null}],
             "reports_ready": false,                       // 只讲材料，不含资格
             "material_blockers": [{"kind": "no_declared_slots|anchor_unavailable|anchor_unchecked|extra_report_stale|slot_not_imported",
                                    "slot": "s1", "state": null, "round": null}],
             "eligibility_hints": [{"kind": "declared_lt_2", "declared": 1}],   // 资格提示，非材料事实
             "open_blocking": [{"finding_id": "f1", "severity": "blocker", "round": 1, "slot": "s1"}],
             "blocking_unknown": [{"slot": "s1", "path": "…", "report_digest": "sha256:…",
                                   "round": 1, "cause": "changed|missing|unreadable", "accepted": false}],
             "pending_unknown": ["<blocking_unknown 中 accepted=false 的条目，结构相同>"],
             "verdict": "pass|fail|unavailable|invalidated|null",
             "verdict_round": 1, "verdict_check_id": "A",
             "bound_to_current": true, "bind_problems": []},   // 口径 ≡ gates.review-passed
  "nonstep": {"escalated": 0, "required_unverified": 0, "complexity_unconfirmed": false,
              "downgrade_incomplete": false, "dependencies_unmet": [], "debug_unruled": [],
              "action_incomplete": null, "paused": false, "suspended": false}
}
```

`nonstep` **九项**全部**记录级只读**，且**复用既有事实计算口径**（"只读"说的是没有副作用，不能替代计算规则）：

| 字段 | 复用来源 |
|---|---|
| `escalated` | judgments 的待答项 |
| `required_unverified` | **`projection` 的未核实项计算**（含验收项 `required` 属性与 `unverified_resolutions`），不是"统计未通过条目" |
| `complexity_unconfirmed` | `plan.confirmed_source` |
| **`downgrade_incomplete`** | **`gates` 的独立降级检查**（降级理由/证据不完整时拒绝归档；轻量任务跳过 `review-passed`，这条照样拦） |
| `dependencies_unmet` | `tasks.dependency_blockers` |
| `debug_unruled` | `gates.debug_pending` |
| `action_incomplete` / `paused` / `suspended` | 任务记录 |

### 1.2 机制侧只提供**原子事实**（不再提供"档位分类器"）

十九版的死因几乎全部落在"档位表"上（互斥写错、死档、优先级矛盾、口径不对齐、归因错误）。而它的消费者是 AI：
AI 拿到原子事实后**完全有能力自行分类与排动作**——文档自己也写着"档位只决定先看哪一行事实"。
所以本版**删掉档位表**，机制只保证下面这些事实正确，分类与顺序交回 AI。

| 事实 | 语义 | 来源（单一实现） |
|---|---|---|
| `check.usable` / `reason` | 检查结果能否支撑收工（按归档门口径） | 提取 `gates` 的 `check-passed` 判定 |
| `review.slots[]` | 每个槽位 `imported/staged/stale/missing/unreadable` + `importable` + `reason` | `review.status_of_round` |
| `review.reports_ready` | **只讲材料**：全部 `imported` + 锚点已核 + 无额外报告问题（**不含**人数/资格条件） | `review.status_of_round` |
| `review.material_blockers[]` | 材料不就绪的原因：`anchor_unavailable` / `anchor_unchecked` / `extra_report_stale` / `slot_not_imported` | 同上 |
| `review.eligibility_hints[]` | **资格提示，不是材料事实**（当前只有 `declared_lt_2`）。边界：只放**机械可算**的提示，**不得**把 `decide` 的判定逐步复制进来 | 同上 |
| `review.open_blocking[]` | 未关闭 blocking（finding 身份 = `(round, slot, id)`） | `review.open_findings` |
| `review.blocking_unknown[]` | 已导入但不可核实的报告（`cause`/`round`/`accepted`） | 同上 |
| `review.verdict` / `verdict_round` / `verdict_check_id` | 最新结论及其**绑定口径 ≡ `gates.review-passed`**（`check_id` 相等 **且** 引用报告三重摘要一致） | `reviews.result` + 同一摘要核 |
| `nonstep.*` | 九项非步骤事实（见 §1.1 表） | 各自既有投影 |

**为什么删表**（正面回答"会不会更难用"）：AI 需要的不是"第几档"，而是"哪些事实不成立、各自的原因"。原子事实已经带原因
（`reason` / `material_blockers` / `cause` / `bind 口径`），比"命中第 6 档"信息量更大且不会互相遮蔽
（v19 的 `degraded_single` 被"报告齐但不可判"吞掉、归因还写成"锚点算不出"，就是表遮蔽事实的例子）。
**判定资格**（人数、非实施者、单 provider、输入成立性）仍由 `review-decide` 自己判——机制**不复制**这些条件。

### 1.2a 槽位发现口径（本提案要求，未实现）

暂存文件按**实际 reviewer 名**产出（`review-codex.md`），声明槽位是 `s1/s2`。`status_of_round` 做两层对应：

1. 已导入记录：按名称匹配，剩余按**位置**分配给未满足的槽位；
2. **未认领的发现式暂存文件**：按顺序分配给未满足的槽位，标 `staged`（`importable` 取决于头部 `status=done`）。

**同一份报告只能被认领一次**：已导入记录的 `report_path` 基名也计入 `claimed`。
`reports_ready` 还要求**该轮全部已导入报告**（含未认领的额外报告）摘要一致且锚点匹配——`decide` 会检查它们。

### 1.3 展示分组（**纯展示**，不承担判定）

若人要看一眼，`wf status` 用四组**展示**标签（由原子事实直接映射，不进机制、不被测试断言）：

| 展示组 | 触发条件（仅展示） |
|---|---|
| `已归档` | `status == "archived"` |
| `材料待补` | 槽位含 `missing`/`staged`/`stale`/`unreadable` |
| `有未结项` | `open_blocking` 或未放行的 `blocking_unknown` 或任一 `nonstep` 非空 |
| `材料就绪` | `reports_ready` 且无未结项 |

**无组命中时直接展示原子事实原文**（例如 `launches` 为空、或 `imported` 齐但 `reports_ready=false`）：宁可给三行原文，也不要
"什么标签都不显示"，否则人看 `status` 会丢掉"复杂任务从未审查"这类信号。

**醒目说明**：这四组**不代表**"可判/可归档"，也不排斥其他动作；冲突时以门禁返回的 code + exits 与 `review-decide` 的结论为准。

## 2. 人裁放行：**用独立记录，不用 `authorize`**（v12 的通道不存在）

v12 写"走既有 K6 授权通道"，实测三处都不成立：`ACTIONS` 固定五类（无 `review_unknown_accept`）、命令无 `--choice` 标志、授权**按动作一文件后写覆盖**（两份放行会互相覆盖）。因此改为**专用记录**：

### 2.1 记录形状（Q1=乙：**一次一批，全有或全无**）

**命令**：`wf review-accept-unknown --task <id> --file <决定.json>`（需持写权）

```json
{"batch": "b-20261111-1",
 "acceptances": [
   {"round": 1, "slot": "s1", "report_digest": "sha256:…", "quote": "这份报告丢失的风险我认，已核对本地副本"},
   {"round": 2, "slot": "codex", "report_digest": "sha256:…", "quote": "改写过但内容我已通读"}
 ]}
```

写入 `reviews.unknown_acceptances[]` 的**每项一条**：

```json
{"batch": "b-20261111-1", "round": 1, "slot": "s1", "path": "review/…/s1.md",
 "report_digest": "sha256:…", "cause": "changed", "quote": "…",
 "by": "human:xzc", "at": "…", "source": "user-declared", "attestation_digest": "sha256:…",
 "revoked": false}
```

**规则**：

| 规则 | 语义 |
|---|---|
| 原子性 | 任一项的 `(round, slot, report_digest)` 与该轮该槽位**登记摘要不等** → **整批拒绝、零写入**，返回 `bad_items[{round,slot,expected,actual,reason}]` |
| 允许子集 | 人可只列 2 份；未列出的 `blocking_unknown` **继续阻断**（不放行不等于放行） |
| 缺摘要的遗留记录 | `imported` 条目没有 `report_digest`（老记录）→ 无法核对 → 只能 `task-abandon` 或重建该轮（新轮）。**有意的封闭**：机制不拿猜出来的摘要放行证据 |
| 批级共享 | `by/at/source/attestation_digest/batch` 批内共享；**`quote` 必须逐项**（每项是一份具体证据） |
| 撤销 | `--revoke --round N --slot S`（逐项）/ `--revoke --batch <id>`（整批）→ 置 `revoked: true`，**不删记录**（留痕） |

### 2.2 阻断与解除

| 环节 | 行为 |
|---|---|
| 阻断 | `open_findings` 增出 `blocking_unknown` / `pending_unknown`（纯增量）；`final_gate` 在 `pending_unknown` 非空时阻断（`WF_REVIEW_INVALID`）——**均属待实现项** |
| code 优先级（Q2=甲） | 两类同时命中时，**先**返回 `WF_UNRESOLVED_BLOCKING`（可关闭路径优先），`facts` 里同时带 `unavailable_reports` 与 `blocking_unknown`；处理完 blocking 再归档才会遇到 unknown |
| 放行 | 存在与 `(round, slot, report_digest)` **三者全等**的 acceptance → 该条降级为留痕，不再阻断 |
| 不放行 | **新轮 pass 与 `--unavailable` 都不解除**（第十一轮否掉的理由：前者绕开关闭、后者只证明做不成审查） |
| 显示 | `blocking_unknown[].accepted` 为 false 表示未放行（`pending_unknown` 即其子集）；放行的标"已由人放行（quote 摘要）" |

### 2.2a 撤销与信任模型（必须声明）

- **撤销**：`wf review-accept-unknown --revoke --round N --slot S`（或 `--batch <id>`）把该条置 `revoked: true`（**不删记录、留痕**）；撤销后该项立即回到 `pending_unknown`。
  放行**不会**因为删记录而"自然失效"以外的效果（不改报告、不改 disposition）。
- **信任不对称（如实声明）**：放行需要 `by: human:` + `source`，而**撤销无 attestation 要求**——持写权的 AI 可撤销人的放行；机制上撤销只让阻断回来（收紧而非放宽），故接受该不对称。

**信任模型（如实声明）**：该通道沿用既有 attestation 的信任模型——命令由持写权的 AI 会话执行，
  `by/quote` 是人话转录，**不是**密码学校验。它比普通 attestation 更接近"归档前最后一道闸门"，
  但本提案**不加**新的密码学保证；如需更强约束，需要另立机制（例如要求人直接在决定文件上签名）。

### 2.3 前置机制约束：导入端必须保证**证据身份不可替换**

实测漏洞：删掉某轮某槽位的报告后，导入一份"同轮、同槽位、同锚点但内容不同（不含原来的 blocking finding）"的报告，
入口返回 `WF_OK` 并覆盖该槽位的导入摘要 → `blocking` 与 `unreadable` 同时清零，**既无 disposition 也无人裁放行**。
放行记录管不到这一步：此时不是"旧放行被复用"，而是**旧证据被替换**。

修法（机制侧，待实现）：`import_report` 在写入前查"该轮该槽位是否已有导入记录"，
**已有则只允许幂等重入（摘要相同）**；摘要不同即拒，出口两条：另开新一轮 / `--unavailable` 留痕后由人处置。
这条约束把它从"AI 指引能否遵守"升级为"机械不可能"。

**为什么不再试图自动判定**：`reviews.result` 只保留最新一轮（`review.py:1484`），历史每轮 verdict 与其 check 绑定**不可重建**；"新证据是否足以承接旧问题"是判断，不是比较。解除必须有人签字，且签字绑定到具体那份证据。

---

## 3. `cause` 与健壮性

| `cause` | 出口 |
|---|---|
| `changed` | 重发新一轮（同路径不同摘要被拒，`review.py:1117`） |
| `missing` | 取回原始字节后**恢复**：摘要与登记摘要一致即**按原身份恢复**（不要求与当前 check 锚点一致）；恢复后**由 `status_of_round` 按摘要 + 实际锚点重算**——内容与锚点都没变则回到 `imported`，锚点已变才是 `stale`（身份可用、当前不适用）；摘要不一致才需要新轮 / `--unavailable` |
| `unreadable` | 恢复可读后重导；否则新轮 / `--unavailable` |

健壮性（口径已更新为根因+5 处）：`open_findings` / `status_of_round` / `all_findings` / `proposers_from_imported` / `gates.review-passed` 都在函数内直接算摘要，而 `records.file_digest` 只捕获 `FileNotFoundError`（`records.py:62`）→ 权限不足会 `PermissionError` 冲出查询入口。五处统一归因；**根因**是 `records.file_digest` 只捕 `FileNotFoundError` → 新增 `file_digest_or_raise`（不吞 OSError），并规定**新调用点必须用它或自行归因**，否则下新增调用点会重演 `PermissionError` 冲出。

---

## 4. 只读门禁：不重构 `final_gate`

- `evaluate_cli` **保持原样**（步骤面只读预检）：**信封结构不变**，但 `facts.missing[]` 条目新增 `fulfilled_by` 字段（见 §8 ②）——这是可见变化，不假装没有；
- 非步骤阻断由 `unresolved.nonstep`（九项）提供；
- **契约**：`wf gate --due before_archive` 是**步骤面**预检；非步骤阻断见 `unresolved`；两者**并读**才是归档前的完整依据；**gate 通过 ≠ 归档必成**（归档内还有 `repo_rules`/`delete` 确认、业务提交先于门禁）；**不要用"试归档"探路**（`tasks.py:3233` 会先做业务提交）。

---

## 5. 候选动作：由 AI 从原子事实推出，机制不排顺序

v19 的档位表承担了"排顺序"的职责，结果每版都在表上翻车。本版**机制不排顺序**：

- 机制只保证原子事实（§1.2）与各自的 `reason`/`cause`/`blockers`；
- AI 按这些事实自行决定先做哪件（例如"先导入 staged 报告 + 并行重发旧轮"）；
- 唯一硬约束仍是"**不要用试归档探路**"（有业务提交副作用），以及"判定资格由 `review-decide` 判"。

唯一需要单独强调的规则：

> 候选必须带**前置事实**（"重发（前置：当前检查可用）"），不得写成命令序列；多条候选并存时**并列列出**，由 AI 按当前进展选择顺序。

---

## 6. 技能层衔接

| 技能 | 加一行 |
|---|---|
| `wf-finish` | ① 读 `unresolved`：**区分**"阻断完成声明"与"允许续做原动作"——`action_incomplete` 先看 `gate` 给的 **`fulfilled_by`/`ignore` 事实**（机制输出）：标为"由目标动作完成"的缺项**不是前置**，可直接续做；其余未结项先处理；② 仍跑 `wf gate --due before_archive`：**缺项由机制输出**（`facts.missing` + `unresolved`），skill 只写"按缺项处理"，**不复制**步骤集合与例外规则（避免门禁一变就漂移） |
| `wf-continue` | `in_progress/finish` 路由前先看 `unresolved`；有未结事实先处理，不直接引导收工 |

---

## 7. ⑥ 的实质处置：文档裁定（v42 不动）

新增 `analysis/ruling-repair-vs-fixing.md`：不引入 `fixing` 阶段（维持 2026-11-09 人裁）；**二十二轮**审查证据摘要（§0 表）；与 v42 K10（L107）/S4（L122）/S5（L123）/§7.1（L401）差异逐条登记；记录两处语义压缩（`--short` 的 `task.check` 压成 `usable/reason`；`unresolved` 只报事实不报"能否结案"）；登记 §2 的放行记录与其绑定规则。

---

## 8. 影响面（含新增命令与记录字段）

| 项 | 数量 |
|---|---|
| 机制修补（K 级） | 2（① `blocking_unknown` + 放行记录 + `final_gate` 阻断；② **导入端证据身份约束**）——**均为待实现项** |
| **新增命令** | 2：`wf review-accept-unknown`（一次一批、全有或全无；`--revoke` 撤销）；**`wf review-import --restore`**（恢复历史身份） |
| **任务记录新增字段** | 2：`reviews.unknown_acceptances[]`（摘要绑定 + `batch` + `revoked`）；**`imported[].restored`** |
| **门禁/查询行为变化（单独标注）** | ① finding 身份收紧（旧裸 id 不再跨轮关闭同名 finding）→ 归档准入变严；② `gate` 的 `changes-persisted` 缺项新增 `fulfilled_by` 事实 |
| 读取健壮 5 处（含 `gates.review-passed`）+ `all_findings` 元组返回 + **`file_digest_or_raise` 根因变体** | 待实现 |
| 提取共享函数 | 1（`check_usability`） |
| `unresolved.nonstep` 九项事实 | 1 处（记录级读取） |
| 展示点 | 3 |
| skill 文本 | 2 |
| 协议码表 / `final_gate` 结构 / `authorize.ACTIONS` | **0** |
| 测试 | **36 项**（§9，稠密编号，逐项一条断言） |
| **既有缺陷（非本审查阶段的改动）** | 本次审查发现的产品级缺陷记录在 §0 与各节「为什么必须补」中；它们与本提案的实施项一并待批准后修。审查阶段的临时实现已全部回退（`e49da16`） |

---

## 9. 验收标准（**36 项**，全部针对原子事实）

| # | 断言 |
|---|---|
| 1 | `check.usable/reason` 与 `gates` 判定逐值一致（8 个 reason 的映射表随实现给出） |
| 2 | 槽位五值可达（`imported`/`staged`(带 `importable`)/`stale`(区分删除改写)/`missing`/`unreadable`） |
| 3 | 同一份报告不被二次认领（`arrived` 不虚增） |
| 4 | 混合槽位任意子集都能如实列出；`reports_ready == false` 且 `material_blockers` 逐项给原因 |
| 5 | **`reports_ready` 不含资格**：单 provider、实施者重叠时它**可以**为 true；CLI 文案**不出现"可判"** |
| 6 | 单 provider → `eligibility_hints` 含 `declared_lt_2`，**不**写进 `material_blockers` |
| 7 | 未认领的额外导入报告失效 → `material_blockers` 含 `extra_report_stale`；恢复原字节后消失（对照组） |
| 8 | `declared == 0` → `material_blockers` 含 `no_declared_slots`（不得出现"不就绪且无原因"） |
| 9 | `bound_to_current` ≡ `gates.review-passed`（`check_id` 相等 **且** 引用报告三重摘要一致）；被改写时 `bind_problems` 非空 |
| 10 | finding 身份 = `(round, slot, id)`；`open_findings` 条目带 `round`/`slot` |
| 11 | 新增 disposition 同名跨轮时只给裸 id → **拒绝**并列候选 |
| 12 | **遗留裸 id 只固定到最早一轮**：旧记录不随未来新增轮次扩大关闭范围（第 2 轮同名 finding 仍 blocking） |
| 13 | `all_findings` 的 `closed` 同样按精确身份计算 |
| 14 | 批量放行成功：一次写 2 项（各带 `quote`）→ 同 `batch`，`pending_unknown` 清空 |
| 15 | 任一项坏 → **整批拒绝、零写入**，返回 `bad_items`（`expected`/`actual`/`reason`） |
| 16 | 子集放行：只列 1 份 → 该项 `accepted`，另一项仍在 `pending_unknown` |
| 17 | 撤销：`--revoke --round/--slot` 与 `--revoke --batch` 均置 `revoked: true`（不删记录）并恢复阻断 |
| 18 | 摘要不同**不匹配**（记录级单测，不构造非法路径） |
| 19 | **权限故障的不可读条目也带登记摘要** → 精确匹配的放行**能**解除（否则死锁） |
| 20 | 缺 `report_digest` 的遗留记录：普通导入**被拒**（身份不可证明），出口只有 `task-abandon` 或另开新一轮 |
| 21 | 证据身份不可替换：删档后导入同轮同槽位另一份被拒；`--restore` 仅当摘要与登记一致时放行 |
| 22 | **`--restore` 保留原登记锚点**：check 换代后恢复 → 记录仍旧 `(check_id, anchor)`，`status` 判 `stale` |
| 23 | **发现式导入的 restore 只在已登记时传**：首次导入绝不传（否则撞"恢复要求已登记"前置，全部被拒） |
| 24 | 权限故障不让 `status`/`review-status`/`review-decide`/`wf gate` 崩溃 |
| 25 | 不变量（报告粒度）：同一 `(round, slot)` 不会既进 `blocking` 又进 `blocking_unknown` |
| 26 | 两类同时存在时 `final_gate` 先返回 `WF_UNRESOLVED_BLOCKING`，`facts` 同时带两者 |
| 27 | `stale.reason` 区分删除/改写；`file_digest_or_raise` 存在且新调用点必须用它或自行归因 |
| 28 | `nonstep` 九项齐全（含 `downgrade_incomplete`），`required_unverified` 复用 `projection` 口径 |
| 29 | 归档准入基线写明：**口径 = finding 身份收紧之后**（该收紧本身会拦下旧裸 id 跨轮任务） |
| 30 | archive 自身未完成时允许续做；`gate` 该项带 `fulfilled_by`（机制事实，skill 不复述规则） |
| 31 | 续做安全：业务提交先于门禁；门禁失败后重入按 `commit_grants` 幂等跳过（断言不重复提交） |
| 32 | 性质测试（靶子=原子事实）：槽位五值任意子集 × `declared∈{0,1,2,3}` × 锚点三态 × 额外报告三态 → `reports_ready == (全 imported ∧ 锚点已核 ∧ 无额外问题 ∧ 有声明槽位)`；`declared_lt_2` 只进 `eligibility_hints` |
| 33 | 放行记录字段完备性：`by` 必须 `human:` 前缀、`source` 必填、`attestation_digest` 入库；**不宣称"无法自签"** |
| 34 | `task-abandon` 定位：不跑 `final_gate`、不解除 `pending_unknown`，只以 `terminal=abnormal` 收尾 |
| 35 | schema 与实现对齐：`blocking_unknown[].accepted`（bool）+ `pending_unknown[]` + `material_blockers`/`eligibility_hints` 均在 §1.1；**无 `accepted_by`** |
| 36 | **计数自洽**：本表条目数 = §8 测试行 = 本节标题数字（改表必须同时改三处） |

## 10. 已定项与剩余问题

**已定（2026-11-11 人裁）**

| 项 | 决定 | 落点 |
|---|---|---|
| Q1 | **乙：一次一批、全有或全无**；逐项 `quote`；子集允许；逐项/整批撤销 | §2.1 记录形状、§2.2 规则、验收 10a–10d |
| Q2 | **甲：两类阻断分列**（`blocking` / `blocking_unknown` / `pending_unknown`）+ 不变量 + code 优先级 | §1.1 schema、§2.2 code 优先级、验收 14/15 |

**剩余（不阻塞落笔）**

1. `coordination`：`wf-review` 是否也需"先读 `unresolved`"接入？
2. `nonstep` 九项是否足够，还是应改为直接复用 `final_gate` 的事实集合？
3. `check` 的 8 个 reason 与 `gates` 分支的映射表，是否要与 `check_usability` 提取同批交付？（本提案要求"随实现给出"）

## 11. 定稿前固定核对清单（每次改版必跑）

从 v15 到 v23 共八版，翻车点全部落在这四项上（v21/v22/v23 的 schema 残留、计数错误、账本滞后也不例外）——把它固化成清单：

| # | 核对项 | 具体做法 |
|---|---|---|
| 1 | **版本表时序** | §0 表按 v1→vN 递增排列，最新版在最后且加粗；新增行必须与本版一致 |
| 2 | **计数一致** | 头注"前 N 版"、§0 标题"N 轮"、§7"第 N 轮"、档位数与表行数、验收条数与 §8 测试数——全部对齐 |
| 3 | **影响面登记** | 凡实现项（不论是否待实现）必须出现在 §8；门禁/查询行为变化要单独标注 |
| 4 | **阶段与实现状态** | 头部阶段声明必须与 §8 的实现状态一致；**审查阶段一律"零改动"**，任何实现 diff 都必须先回退 |
