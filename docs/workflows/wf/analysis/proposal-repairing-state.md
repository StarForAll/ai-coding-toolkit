# 提案（v20）：⑥ 只做「结构化未结事实」+ 一条人裁放行记录 + 文档裁定

> 状态：**待审 v20**（第十九轮修正）。
> 前十九版的形态与致命点见 §0。**边界**：机制修补已先行落地若干项（见 §8"已完成"行），
> 其中**证据身份约束**与 **`review-status` 判定语义**已改变门禁/查询行为；
> 展示层（`unresolved` 档位与挂载）与**人裁放行记录尚未实现**。

---

## 0. 十九轮审查的形态演进与净结论

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
| **v19** | 全链路读取健壮 + 第 6 档接 `round_ready` | **档位表自身不自洽**（staged/stale 三处两个答案；`degraded_single` 被 6b 吞且归因错误）；`round_ready` 把"材料就绪"升格成"可判定资格"（实施者重叠、单 provider 都被漏）；finding 身份按裸 id 汇总（他轮同名 f1 被旧关闭覆盖）；恢复无执行通道；`file_digest` 根因未修；`bound_to_current` 口径未定义 |
| **v18** | 全链路读取健壮 + `ready` 已核锚点 | **`gates.py` 一处未修**（`review-passed` 仍抛 `PermissionError`，`wf gate` 会崩）；第 6 档未用 `round_ready`、`extra_reports` 无承载；`staged` 文案没接 `importable`；「等来的报告可复用」与报告协议冲突；恢复后一律 `stale` 过绝；两条新测试失败原因相互遮蔽 |
**已核实的产品级事实（含对 v11 错误引用的更正）**

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
  "review": {   // 只有原子事实，没有档位分类
             "reports_ready": false, "round_ready_blockers": [{"kind": "declared_lt_2"}],
             "round": 2, "launched": 2, "imported": 2, "declared": 2,
             "slots": [{"slot": "s1", "state": "imported|staged|stale|missing|unreadable", "round": 2}],
             "open_blocking": [{"finding_id": "f1", "severity": "blocker", "round": 1}],
             "blocking_unknown": [{"slot": "s1", "path": "…", "report_digest": "sha256:…",
                                   "round": 1, "cause": "changed|missing|unreadable",
                                   "accepted_by": null}],
             "verdict": "pass|fail|unavailable|invalidated|null",
             "verdict_round": 1, "verdict_check_id": "A",
             // 绑定口径 ≡ gates.review-passed：check_id 相等 **且** 引用报告三重摘要一致
             "bound_to_current": true, "bind_problems": []},
  "nonstep": {"escalated": 0, "required_unverified": 0, "complexity_unconfirmed": false,
              "downgrade_incomplete": false,
              "dependencies_unmet": [], "debug_unruled": [], "action_incomplete": null,
              "paused": false, "suspended": false}
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
| `review.reports_ready` | **材料就绪**：全部 `imported`、锚点已核、无额外报告问题 | 同上（**不宣称判定资格**） |
| `review.round_ready_blockers[]` | 材料就绪不成立的原因（`anchor_unavailable`/`anchor_unchecked`/`extra_report_stale`/`declared_lt_2`） | 同上 |
| `review.open_blocking[]` | 未关闭 blocking（finding 身份 = `(round, slot, id)`） | `review.open_findings` |
| `review.blocking_unknown[]` | 已导入但不可核实的报告（`cause`/`round`/`accepted_by`） | 同上 |
| `review.verdict` / `verdict_round` / `verdict_check_id` | 最新结论及其**绑定口径 ≡ `gates.review-passed`**（`check_id` 相等 **且** 引用报告三重摘要一致） | `reviews.result` + 同一摘要核 |
| `nonstep.*` | 八类非步骤事实（见 §1.1 表） | 各自既有投影 |

**为什么删表**（正面回答"会不会更难用"）：AI 需要的不是"第几档"，而是"哪些事实不成立、各自的原因"。原子事实已经带原因
（`reason` / `round_ready_blockers` / `cause` / `bind 口径`），比"命中第 6 档"信息量更大且不会互相遮蔽
（v19 的 `degraded_single` 被"报告齐但不可判"吞掉、归因还写成"锚点算不出"，就是表遮蔽事实的例子）。
**判定资格**（人数、非实施者、单 provider、输入成立性）仍由 `review-decide` 自己判——机制**不复制**这些条件。

### 1.2a 槽位发现口径（已实现）

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

**醒目说明**：这四组**不代表**"可判/可归档"，也不排斥其他动作；冲突时以门禁返回的 code + exits 与 `review-decide` 的结论为准。

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

### 2.2a 撤销与信任模型（必须声明）

- **撤销**：`wf review-accept-unknown --revoke --round N --slot S` 删除该条放行；撤销后 `blocking_unknown` 立即恢复阻断。
  放行**不会**因为删记录而"自然失效"以外的效果（不改报告、不改 disposition）。
- **信任模型（如实声明）**：该通道沿用既有 attestation 的信任模型——命令由持写权的 AI 会话执行，
  `by/quote` 是人话转录，**不是**密码学校验。它比普通 attestation 更接近"归档前最后一道闸门"，
  但本提案**不加**新的密码学保证；如需更强约束，需要另立机制（例如要求人直接在决定文件上签名）。

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
| `missing` | 取回原始字节后**恢复**：摘要与登记摘要一致即**按原身份恢复**（不要求与当前 check 锚点一致）；恢复后**由 `status_of_round` 按摘要 + 实际锚点重算**——内容与锚点都没变则回到 `imported`，锚点已变才是 `stale`（身份可用、当前不适用）；摘要不一致才需要新轮 / `--unavailable` |
| `unreadable` | 恢复可读后重导；否则新轮 / `--unavailable` |

健壮性（口径已更新为根因+5 处）：`open_findings` / `status_of_round` / `all_findings` / `proposers_from_imported` / `gates.review-passed` 都在函数内直接算摘要，而 `records.file_digest` 只捕获 `FileNotFoundError`（`records.py:62`）→ 权限不足会 `PermissionError` 冲出查询入口。五处统一归因；**根因**是 `records.file_digest` 只捕 `FileNotFoundError` → 新增 `file_digest_or_raise`（不吞 OSError），并规定**新调用点必须用它或自行归因**，否则下新增调用点会重演 `PermissionError` 冲出。

---

## 4. 只读门禁：不重构 `final_gate`

- `evaluate_cli` **保持原样**（步骤面只读预检，输出结构不变）；
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
| `wf-finish` | ① 读 `unresolved`：**区分**"阻断完成声明"与"允许续做原动作"——`action_incomplete` 若正是 **archive 自身**未完成，**应续做该动作**（门禁会排除本次动作），不得当作"必须先清空才能进入归档"；其余未结项先处理；② 仍跑 `wf gate --due before_archive`：**缺项由机制输出**（`facts.missing` + `unresolved`），skill 只写"按缺项处理"，**不复制**步骤集合与例外规则（避免门禁一变就漂移） |
| `wf-continue` | `in_progress/finish` 路由前先看 `unresolved`；有未结事实先处理，不直接引导收工 |

---

## 7. ⑥ 的实质处置：文档裁定（v42 不动）

新增 `analysis/ruling-repair-vs-fixing.md`：不引入 `fixing` 阶段（维持 2026-11-09 人裁）；**十九轮**审查证据摘要（§0 表）；与 v42 K10（L107）/S4（L122）/S5（L123）/§7.1（L401）差异逐条登记；记录两处语义压缩（`--short` 的 `task.check` 压成 `usable/reason`；`unresolved` 只报事实不报"能否结案"）；登记 §2 的放行记录与其绑定规则。

---

## 8. 影响面（含新增命令与记录字段）

| 项 | 数量 |
|---|---|
| 机制修补（K 级） | 2（① `blocking_unknown` + 放行记录 + `final_gate` 阻断；② **导入端证据身份约束**——已实现并回归） |
| **新增命令** | 1（`wf review-accept-unknown`，走既有 attestation 通道） |
| **任务记录新增字段** | 1（`reviews.unknown_acceptances[]`，逐报告 + 摘要绑定） |
| 读取健壮 5 处（含 `gates.review-passed`）+ `all_findings` 元组返回 + **`file_digest_or_raise` 根因变体** | **已实现** |
| 提取共享函数 | 1（`check_usability`） |
| `unresolved.nonstep` 九项事实 | 1 处（记录级读取） |
| 展示点 | 3 |
| skill 文本 | 2 |
| 协议码表 / `final_gate` 结构 / `authorize.ACTIONS` | **0** |
| 测试 | **18 项**（§9，全部针对原子事实） |
| **已完成**（机制侧，均已有回归测试；含 `d6bfb71`、`adb4715` 与本轮的 finding 身份绑定 / `reports_ready` 去伪 / `--restore` / `file_digest_or_raise`） | K4b 关闭链重解析报告（`7752520`）；`status_of_round` 发现模式槽位对应（`d6266c4`/`8b252db`）；**导入端证据身份约束**（`d198266`）；**同一报告不得二次认领 + `ready_to_decide` 与五档口径对齐**（本轮） |

---

## 9. 验收标准（全部针对**原子事实**，不再针对档位）

| # | 断言（机制侧可复算） |
|---|---|
| 1 | `check.usable/reason` 与 `gates` 判定逐值一致（`no_check`/`not_passed`/`invalidated_content_changed`/`anchor_mismatch`/`rule_changed`/`anchor_unavailable`/`structure_incomplete`）——**该映射表随实现给出**，不允许"照感觉命名" |
| 2 | 槽位五值可达：`imported`/`staged`（`importable` 取决 `status=done`）/`stale`（区分删除与改写）/`missing`/`unreadable`（权限故障归此，不崩入口） |
| 3 | 同一份报告不被二次认领：已导入记录的基名计入 `claimed` → `arrived` 不虚增 |
| 4 | **混合槽位**（`missing+staged+stale` 任意子集）都能被如实列出，且 `reports_ready` 为 false、`round_ready_blockers` 给出对应原因 |
| 5 | `reports_ready` **不宣称判定资格**：实施者重叠、单 provider 两种情形下，`reports_ready` 不因它们变 false，但 CLI 文案**不出现"可判"** |
| 6 | `declared == 1` → `round_ready_blockers` 含 `declared_lt_2`（不写成"锚点算不出"） |
| 7 | 未认领的额外导入报告失效 → `round_ready_blockers` 含 `extra_report_stale`；恢复该报告原字节后事实消失（对照组） |
| 8 | `bound_to_current` ≡ `gates.review-passed`：`check_id` 相等但引用报告被改写时，`bind_problems` 非空、`bound_to_current == false` |
| 9 | `open_blocking` 的 finding 身份 = `(round, slot, id)`：第 1 轮关闭不影响第 2 轮同名 finding；无 `round/slot` 的老记录按遗留形态仍可关闭 |
| 10 | `blocking_unknown` 只在**未放行**时阻断；`review-accept-unknown` 写入 `(round, slot, report_digest)` 全等记录后降级；摘要不同不匹配（记录级单测） |
| 11 | 证据身份不可替换：删文件后导入同轮同槽位另一份报告被拒（两条出口）；`--restore` 只在"摘要与登记一致"时放行且标 `restored`，不重绑当前 check |
| 12 | 权限故障（`PermissionError`）不让 `status`/`review-status`/`review-decide`/`wf gate` 崩溃：前两处归 `unreadable`，后两处给 `WF_REVIEW_INVALID` + 原因/出口 |
| 13 | `records.file_digest_or_raise` 存在且语义明确（不吞 OSError）；新调用点用安全变体或自行归因（§3） |
| 14 | `stale` 的 `reason` 区分"被删除"与"被改写" |
| 15 | `nonstep` **九项**齐全（含 `downgrade_incomplete`），`required_unverified` 复用 `projection` 口径 |
| 16 | 归档准入除 §2 的修补外与改动前一致；`--short` 的 `task.check` 已派生 |
| 17 | `action_incomplete` 为 archive 自身时**允许续做**（门禁排除本次动作），不构成"进入归档前必须清空"的循环 |
| 18 | **性质测试**（靶子=原子事实，不是档位）：槽位五值任意子集 × `declared∈{0,1,2,3}` × 锚点三态 × 额外报告三态 → 断言 `reports_ready == (全部 imported ∧ 锚点已核 ∧ 无额外问题 ∧ declared≥2)`；合法域由 `status_of_round` 的输出域定义（不引用展示分组） |

**计数核对**：本表 18 项；§8 的"测试"行必须与此一致（§11 #2）。

## 10. 留给审查者的问题（**标注是否阻塞落笔**）

> 阻塞项（未闭合则 §9 无法定稿）：Q1（一次确认能否覆盖多份 → 决定 §2 命令形状）、Q2（`blocking` 与 `blocking_unknown`
> 是否分列 → 决定 schema 与验收 10/11 的写法）。


1. §2 的放行记录要求人签一次/每份不可读报告；若同时有 3 份不可读，是否允许**一次确认覆盖多份**（决定文件里写多条）？
2. 第 8 档把 `blocking`（可关闭）与 `blocking_unknown`（只能重发/人裁放行）合档但出口分列——是否该拆两档？
3. `unresolved.nonstep` 复述了 `final_gate` 一半事实，算"该定死的口径"还是"复制门禁"？
4. `wf-review` 是否也需"先读 unresolved"的接入？`wf-finish` 的封闭规则（除 changes-persisted 外全算前置）是否要写进 `wf-continue`？

---

## 11. 定稿前固定核对清单（每次改版必跑）

这份文档连续六版的翻车点全部落在这四项上，不是设计问题——把它们固化成清单：

| # | 核对项 | 具体做法 |
|---|---|---|
| 1 | **版本表时序** | §0 表按 v1→vN 递增排列，最新版在最后且加粗；新增行必须与本版一致 |
| 2 | **计数一致** | 头注"前 N 版"、§0 标题"N 轮"、§7"第 N 轮"、档位数与表行数、验收条数与 §8 测试数——全部对齐 |
| 3 | **影响面登记** | 凡已落地的机制变更（commit 号）必须出现在 §8；门禁/查询行为变化要单独标注 |
| 4 | **边界声明** | 头部"实现未开始/部分落地"必须与 §8 的"已完成"行一致 |
