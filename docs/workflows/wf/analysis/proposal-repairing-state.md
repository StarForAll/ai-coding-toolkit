# ⑥「修复中/未结事实」可实现规格（v25）

> 状态：**待你确认**（自完善版；前 23 版演进见附录 A）。
> 阶段：**方案审查阶段，实现零改动**（规则见 `.trellis/spec/guides/review-phase-discipline.md`）。
>
> 本版与前 24 版的区别：不再按审查意见逐条补丁，而是**先把模型定死**（§2 数据模型、§3 计算事实、
> §4 操作契约、§5 阻断语义），再用自审清单（§10）自己找漏洞。§11 记录我自己这轮找到并修掉的问题。

---

## 1. 目标与非目标

### 1.1 要解决的问题（只有两条）

1. **事实可见**：AI 与人不必通过"跑一遍失败"才知道「检查能不能用、审查差什么、还有什么没结」；
2. **人裁可追溯**：当历史证据已无法核实而又必须收尾时，解除阻断这件事**必须有人签字并绑定到具体那份证据**。

### 1.2 明确不做（范围边界，避免无限扩张）

| 不做 | 理由 |
|---|---|
| 不引入 `fixing` 阶段、不加任务状态机 | 维持 2026-11-09 人裁的四阶段（v3/v4 已否） |
| 不做"档位/优先级分类器" | 机制只产事实，分类与顺序交 AI（v19 已否档位表） |
| 不复制 `decide` 的判定资格（人数/非实施者/输入成立性） | 那是 `review-decide` 的职责，复制即第二真相 |
| 不改 `final_gate` 的结构与执行顺序 | 改动会破坏"先提交后核"的既有语义；只在末尾追加一条 unknown 阻断 |
| 不做 `archive --dry-run` | 见 §7 Q4：会改变归档动作语义，属独立议题 |
| 不追求"AI 无法伪造人裁"的密码学保证 | 见 §4.4 信任模型：只能留痕可审计，机制不假装能做到 |
| 不替 AI 判断"两个 finding 是不是同一个问题" | 语义判断归 AI；机制只保证**身份**不串 |

### 1.3 成功判据

一个普通任务在**不读源码**的情况下，只看 `wf status --json` 的 `unresolved` 就能回答：

- 检查能不能用来收工？不能的话为什么？→ `check.reason`
- 审查差什么？为什么不能判？→ `review.slots` / `material_blockers` / `eligibility_hints`
- 还有什么没结？各自**阻断什么、不阻断什么**？→ `open_blocking` / `stale_findings` / `blocking_unknown` / `pending_unknown` / `nonstep` + §5 作用域表
- 唯一需要人做的事是什么？→ `pending_unknown` 的非空项（每项带 `round/slot_key/report_digest/cause`）

---

## 2. 数据模型（先定死，再谈行为）

### 2.1 持久化记录（只新增两处，其余全是计算）

| 字段 | 归属 | 语义 |
|---|---|---|
| `reviews.imported[].slot_key` | **新增** | 该报告的规范身份（见 §2.3）。读旧记录时按 §2.4 回退推导，**不回写** |
| `reviews.imported[].restored` | **新增**（可选） | 该次导入是"恢复历史身份"（`--restore`） |
| `reviews.unknown_acceptances[]` | **新增** | 人裁放行记录（§4.2） |

其余全部是**派生事实**，不落盘（避免"同一事实两处存"——v13/v15 的翻车根因）。

### 2.2 不变量（实现必须维持，测试直接断言）

| # | 不变量 |
|---|---|
| I1 | `open_blocking` / `stale_findings` / `blocking_unknown` **两两不相交**，且并集覆盖所有已导入报告里可解析出的 findings |
| I2 | `pending_unknown ≡ blocking_unknown.filter(accepted == false)`（同一函数产出，禁止独立实现） |
| I3 | `reports_ready ⟺ material_blockers 为空` |
| I4 | `slots[].slot_key` 与 `imported[].slot_key` 一一对应，且**分配后不再改变** |
| I5 | `unknown_acceptances` 的每条都能在当前 `blocking_unknown` 里找到 `(round, slot_key, report_digest)` 全等项，否则视为失效记录（不删、不计入解除） |
| I6 | `task.status == "archived"` 时，所有阻断类事实按"已终结"呈现，不再参与准入 |

### 2.3 `slot_key`：唯一身份（本版新增，v24 之前的空洞）

| 概念 | 定义 |
|---|---|
| `slot` | 审查发起时声明的槽位名（`s1/s2/…`） |
| `agent` | 实际 reviewer 名（发现式导入从文件名/报告头取得，如 `codex`） |
| **`slot_key`** | **对外唯一身份**：<br>① 该报告被某个声明槽位认领 → 取声明名（`s1`）；<br>② 未被认领的"额外报告" → 取 `agent`；无 `agent` 时取路径基名去扩展名 |
| 认领顺序 | round 目录 `review-<agent>.md` 按**文件名升序**，依次分配给未满足的声明槽位；**分配即写盘**（`imported[].slot_key`），此后不重排 |
| 匹配键 | 放行 / 撤销 / `blocking_unknown` 一律用 `(round, slot_key, report_digest)`；`slot`/`agent` 只作事实展示，**不得**作匹配键 |

### 2.4 旧记录迁移（读时推导，永不回写）

| 旧记录形态 | 推导规则 |
|---|---|
| 有 `slot_key` | 直接用 |
| 无 `slot_key`、有 `agent` 且该 agent 与声明槽位一一对应 | `slot_key = 该声明槽位` |
| 无 `slot_key`、无 `agent` | `slot_key = slot`（历史槽位名） |
| 无法判断 | `slot_key = slot`，并在 `slots[]` 标 `legacy: true`（事实可见，不阻断） |

**迁移原则**：历史记录不重写；任何"因为现在读不到报告而改变身份"的行为都禁止（v23 的 `legacy_ambiguous_closures` 就靠这条）。

### 2.5 遗留裸 id 的关闭（歧义保留，不猜定）

| 情形 | 处置 |
|---|---|
| 旧 disposition 缺 `round/slot_key`，该 `finding_id` 在唯一 `(round, slot_key)` 出现 | 绑定并生效 |
| 同名出现在多个 `(round, slot_key)`（含同轮多槽位） | **不关闭任何一条** → 进 `legacy_ambiguous_closures` |
| 旧报告中该 finding 已不可重解析（文件丢失/不可读） | 同上（进歧义列表） |
| 新增 disposition | **必须**带 `round + slot_key`；缺失且存在同名多身份 → 拒绝并给候选 |

歧义的唯一出路：**补发一条精确 disposition**（`round + slot_key + finding_id`）。旧裸 id 记录保持不生效。

---

## 3. 计算事实（每项：输入 → 公式 → 输出）

| 事实 | 输入 | 公式 | 输出 |
|---|---|---|---|
| `check.usable/reason` | `task.check`（`result`/`rule_version`/`invalidated`/`anchor`）+ 当前锚点 | 直接复用 `gates` 的 `check-passed` 判定，**逐分支映射**到 8 个 reason（`archived`/`no_check`/`not_passed`/`invalidated_content_changed`/`anchor_mismatch`/`rule_changed`/`anchor_unavailable`/`structure_incomplete`） | `usable: bool`, `reason` |
| `review.slots[]` | `reviews.launches[round]` + `reviews.imported` + 报告文件状态 | 状态判定：<br>`imported` = 摘要一致且锚点=当前<br>`stale` = 摘要被改写/删除（`reason` 区分）或锚点≠当前<br>`unreadable` = 读取 OSError<br>`staged` = 文件存在未导入（`importable = 头部 status=done`）<br>`missing` = 无文件 | 每槽位 `{slot, slot_key, state, reason, importable, round}` |
| `review.reports_ready` | 上一步 | `全槽位 imported` ∧ `anchor_checked_all` ∧ `anchor != null` ∧ `无 extra_report_stale` ∧ `declared > 0` | bool |
| `review.material_blockers[]` | 上一步 | `reports_ready` 为真的是逐一收集每个假条件：`no_declared_slots` / `anchor_unavailable` / `anchor_unchecked` / `slot_not_imported` / `slot_unreadable` / `extra_report_stale`。**必须与 `reports_ready` 严格互补**（I3） | 列表 |
| `review.eligibility_hints[]` | `declared` | 当前仅 `declared_lt_2`（单 provider 不产生判定结论）。**只提示，不阻断** | 列表 |
| `review.open_blocking[]` | 全部 `imported` 报告（可解析、锚点=当前） | 未处置（无 accepted disposition）且 `severity ∈ blocking` | 列表（带 `round/slot_key/finding_id`） |
| `review.stale_findings[]` | 全部 `imported` 报告（可解析、锚点≠当前） | 同上筛选，但**不计入阻断** | 列表（带 `why`） |
| `review.blocking_unknown[]` | 全部 `imported` 报告（不可解析） | 每条带 `cause ∈ {changed, missing, unreadable}`、`report_digest`（**必须是登记摘要，不是现场摘要**）、`accepted` | 列表 |
| `review.bound_to_current` | `reviews.result` + 当前 `check.id` + 引用报告三重摘要 | `result.check_id == check.id` ∧ 引用报告 `result_digest == recorded == 现行文件摘要`；不满足时 `bind_problems` 逐项给原因 | bool + 列表 |
| `nonstep.*` | 各既有投影 | 九项：`escalated`（judgments 待答）/ `required_unverified`（`projection` 口径）/ `complexity_unconfirmed`（`plan.confirmed_source`）/ `downgrade_incomplete`（`gates` 降级检查）/ `dependencies_unmet`（`tasks.dependency_blockers`）/ `debug_unruled`（`gates.debug_pending`）/ `action_incomplete{id,resumable}` / `paused` / `suspended` | 九项 |
| `action_incomplete.resumable` | `task.action` | `action.name == "archive"` ∧ `action.state ∈ {applying, failed}` → true（与 `final_gate(ignore_action_id=当前动作)` 同一判据） | bool |

**计算纪律**：每个事实**只有一个实现函数**；`pending_unknown` 由 `blocking_unknown` 过滤得出（I2）；
`reports_ready` 与 `material_blockers` 由同一函数同时产出（I3）。

---

## 4. 操作契约

### 4.1 `wf review-import`（含 `--restore`）

| 路径 | 前置 | 效果 | 错误 |
|---|---|---|---|
| 普通导入（该 `(round, slot_key)` 无登记） | 报告锚点 = **当前** check 锚点 | 写 `imported[]`，`anchor` = 当前 | `WF_REVIEW_INVALID`（锚点不符/摘要冲突） |
| 幂等重入（有登记、**摘要相同**） | 只需摘要相同（**不校验当前锚点**） | 不新增记录；`anchor` **保持原值**；不置 `restored` | —— |
| `--restore`（有登记、**摘要相同**） | 同上 | 同上，且置 `restored: true` | 摘要不同 → 拒绝（`恢复要求与登记摘要一致`） |
| 有登记、摘要**不同** | —— | 拒绝：**证据身份不可替换** | `WF_REVIEW_INVALID` + 出口（另开新轮 / abandon） |
| 有登记、`report_digest` 为 `null` | —— | 拒绝：身份不可证明 | `WF_REVIEW_INVALID` + 出口（另开新轮 / abandon） |
| 发现式批量导入 | —— | 仅当该 `(round, slot_key)` **已有登记**时按 `--restore` 语义处理；首次导入**不得**传 restore | —— |

### 4.2 `wf review-accept-unknown`（一次一批、全有或全无）

**输入**：`--task <id> --file <决定.json>`

```json
{"batch": "b-…",
 "acceptances": [{"round": 1, "slot_key": "s1", "report_digest": "sha256:…", "quote": "…"}]}
```

| 规则 | 语义 |
|---|---|
| 前置 | 持写权；每项必须能在当前 `blocking_unknown` 找到 `(round, slot_key, report_digest)` 全等项 |
| 原子性 | 任一项不满足 → **整批拒绝、零写入**，返回 `bad_items[{round, slot_key, expected, actual, reason}]` |
| 不做预放行 | 指向不存在的项 → 拒绝（否则它将来变 unknown 时会自动生效） |
| 幂等 | 同一键重复放行 → 不新增，回报 `already_accepted` |
| 效果 | 追加 `unknown_acceptances[]`（每项一条，含 `batch/by/at/source/quote/attestation_digest`） |
| 撤销 | `--revoke --round/--slot_key` 或 `--revoke --batch` → 置 `revoked: true`（**不删**）；同槽多 digest → 全撤并回报 `revoked_count` |
| 解除边界 | **只有**摘要全等的放行能解除；重发新一轮、`--unavailable`、`--restore` 都**不解除** |

### 4.3 `wf status` / `wf review-status` / `judgments show`（只读）

- `status --json`：`facts.unresolved`（§3 全部事实）+ `next`（位置驱动，不感知失败事实）；
- `status --short`：`task.check` 字段改为**派生**（`usable ? "usable" : reason`），不保留旧的 `result`；
- `review-status`：`reports_ready`/`material_blockers`/`eligibility_hints`/`slots`；`next_` 文案**不得**出现"可判"（资格由 `decide` 判）；
- `judgments show`：在收工预览里按 §5 作用域逐行列出未结事实。

### 4.4 信任模型（如实声明，不假装）

放行记录沿用 attestation：`by: human:` + `source` + `quote` + `attestation_digest`。
**它挡不住持写权的 AI 伪造**（决定文件本来就由 AI 写）；机制只保证：① 绑定到具体证据（摘要全等）；
② 留痕可审计；③ 撤销也必须留痕。**不宣称"AI 无法自签"**（v23 的假保证已删）。

### 4.5 归档门禁（`final_gate`，只加一条）

| 顺序 | 条件 | 返回 |
|---|---|---|
| 1 | 步骤面缺项（不变） | 该步骤的 code + `facts.missing[]`（`changes-persisted` 项带 `fulfilled_by: "archive_commit"`） |
| 2 | 未关闭 `blocking` | `WF_UNRESOLVED_BLOCKING` + facts（三类事实都带上） |
| 3 | **未放行 `pending_unknown`**（新增） | `WF_REVIEW_INVALID` + `facts.reason = "unverifiable_evidence"` + `blocking_unknown` + 出口 |
| 4 | 其余既有条件（escalated/required/降级/依赖/debug/动作…） | 不变 |

**优先级口径**：`WF_UNRESOLVED_BLOCKING` 优先于 unknown **仅在步骤面通过之后**成立——这是既有顺序，不额外承诺跨层优先级。

---

## 5. 阻断语义（作用域表：只挡该挡的）

| 事实 | 阻断完成声明 | 阻断归档 | **不阻断** |
|---|---|---|---|
| `escalated` | 是 | 是 | 继续导入/调查/不依赖该判断的修复（v42 K10 原义） |
| `open_blocking` | 否 | 是 | 继续工作、重查、重发审查 |
| `pending_unknown` | 否 | 是 | 继续工作（含另一轮审查） |
| `stale_findings` | 否 | 否 | ——（提示：那些问题针对旧对象） |
| `required_unverified` / `downgrade_incomplete` / `dependencies_unmet` / `debug_unruled` | 否 | 是 | 继续工作 |
| `action_incomplete.resumable=true` | 否 | 否 | 可直接续做 |
| `material_blockers` | 否 | 是（经步骤面） | 继续处理材料 |
| `eligibility_hints` | 否 | 否 | 材料准备、导入、重发 |
| `check.usable=false` | 是（不得声称可收工） | 是 | 继续工作、重查 |

**唯一硬约束**：不要用"试归档"探路（`tasks.py:3233` 会先业务提交）；需要"能不能归档"的只读答案时并读 `gate`（步骤面）与 `unresolved`。

---

## 6. 实现落点（批准后按此执行；本轮不动代码）

| 文件 | 改动 | 备注 |
|---|---|---|
| `records.py` | 新增 `file_digest_or_raise`（不吞 OSError） | 根因修复；新调用点必须用它或自行归因 |
| `review.py` | ① `slot_key` 推导与写盘；② 三类 finding 归属（`open_findings` 返回 `open_blocking`/`stale_findings`/`blocking_unknown`/`pending_unknown`）；③ 精确 finding 身份 `(round, slot_key, id)`（提出者索引、自证复核）；④ `imported` 证据身份约束 + 三态导入；⑤ `--restore`；⑥ `unknown_acceptances` 匹配与撤销；⑦ 六处读取健壮（含 `decide` 循环 `review.py:1304`） | 最大改动面 |
| `gates.py` | ① `check_usability` 提取（供 `unresolved` 与门禁共用）；② `facts.missing[]` 加 `fulfilled_by`；③ `final_gate` 末尾追加 `pending_unknown` 阻断；④ `review-passed` 摘要读取健壮 | 门禁行为变化：③④ |
| `cli.py` | `status`/`--short`/`review-status` 输出；`review-accept-unknown`（含 `--revoke`）；`review-import --restore` 接线 | 新增 1 命令 |
| `judgments.py` | 引用空间 `f:<round>:<slot_key>:<id>`；骨架保留 `round/slot_key` | 兼容 `f:<id>` 读入 |
| `templates/` | 不改（新增字段都是可选/派生） | —— |
| 发布 | 改完需重建发行树并通过字节复现校验 | 批准后一次性做 |

**迁移影响（必须提前告知）**：finding 身份收紧后，历史上"裸 id 跨轮/跨槽位关闭"的任务会**重新出现 blocking**；补救路径 = 补发精确 disposition（§2.5）。这是**行为收紧**，不是 bug。

---

## 7. 遗留决策（真正需要你裁的，只有 3 条）

| # | 问题 | 默认若你不表态 |
|---|---|---|
| Q3 | `pending_unknown` 阻断是否新增协议码（36→37），还是复用 `WF_REVIEW_INVALID` + `facts.reason` 消歧？ | 复用（零协议改动） |
| Q4 | "不要试归档"保持指引，还是上 `archive --dry-run` / 把 `final_gate` 提到业务提交之前？ | 保持指引 + 登记为已知限制（改序会动归档语义，属独立议题） |
| Q5 | 放行信任模型：接受"AI 可转录/伪造 + 留痕可审计"，还是要求人直接在决定文件签名？ | 接受现状并登记 |

---

## 8. 验收（三类测试，共 40 项；批准后逐条落成测试）

**A. 单元/契约（22 项）**：检查 8 reason 映射（1）；槽位五值可达（2）；`slot_key` 推导与旧记录回退（3–5）；
三种导入差异（6–8）；证据身份不可替换（9）；缺摘要拒绝（10）；放行批次原子性/子集/幂等/撤销（11–15）；
`legacy_ambiguous_closures` 不猜定（16）；精确 disposition 接受、歧义拒绝（17–18）；`stale_findings` 可见不阻断（19）；
`bound_to_current` 与 `bind_problems`（20）；`action_incomplete.resumable`（21）；`task-abandon` 不解除（22）。

**B. 性质（6 项）**：I1 三类互斥且覆盖（23）；I2 `pending_unknown` 同源（24）；I3 `reports_ready ⟺ blockers 空`（25）；
I4 `slot_key` 稳定（26）；槽位五值 × `declared∈{0,1,2,3}` × 锚点三态 → `reports_ready` 公式（27）；
`archived` 短路（28）。

**C. 审计/防漂移（6 项）**：全仓 `file_digest(` 调用点白名单（29）；`gate` 输出结构只加 `fulfilled_by`（30）；
`status --short` 的 `task.check` 已派生（31）；`final_gate` 其余顺序未变（32）；六处读取在权限故障下不崩（33）；
`unresolved` 字段与 §3 表一一对应（34）。

**D. 文档自洽（6 项，本版即可自查）**：计数一致（35）；引用可达（36）；schema 与正文对齐（37）；
范围边界未被越界（38）；已知限制登记齐全（39）；阶段声明与实现状态一致（40）。

---

## 9. 不做的补救承诺（避免"看起来完成"）

- 不承诺"机制能替 AI 判断两处 finding 是否同一问题"；
- 不承诺"机制能证明人真的签过字"；
- 不承诺"gate 一次给全所有阻断"（它逐层揭示，`unresolved` 补全事实）；
- 不承诺"历史记录自动迁移"（只读时推导，不回写）。

---

## 10. 自审清单（**已落成项目规范**：`.trellis/spec/guides/proposal-self-review.md`）

> 下面的表是本次使用的版本；规范里的那十条是权威版本（含机械做法与反模式）。改方案前先按规范跑，交付时报"自查发现 N 处"。

| # | 检查项 | 触发的问题 |
|---|---|---|
| 1 | 每个字段都有**唯一**产生函数？ | `pending_unknown` 曾被独立实现 |
| 2 | 每条规则都有**反向**规则？（继续 ≠ 解除） | §3 出口曾把重发当解除 |
| 3 | 每个身份都有**域定义**？（谁是谁） | `slot` vs `agent` vs `slot_key` |
| 4 | 每条路径都有**三态**？（首次/幂等/显式恢复） | 导入三态差异表 |
| 5 | 每类事实都有**归属**？（不许静默消失） | `stale` 报告 findings 曾无归属 |
| 6 | 每个错误都有**出口**？（且出口真的能解除） | 缺摘要记录的"重发出口"是死路 |
| 7 | 每个阻断都有**作用域**？（挡完成≠挡工作） | `escalated` 曾被写成"先处理" |
| 8 | 每处读者都有**健壮归因**？（不留裸 OSError） | `decide` 循环漏了 |
| 9 | 每个旧记录都有**迁移规则**？（且不回写） | 裸 id 兼容 |
| 10 | 每个数字/引用都能**解析**？ | 验收编号、轮次计数 |

---

## 11. 本轮自审发现并已修掉的问题（不靠外部审查）

| # | 我自己发现的问题 | 修法 |
|---|---|---|
| 1 | `imported[]` 没有持久化 `slot_key`，只靠推导会让"同一报告两种指称"重现 | §2.1 新增字段 + §2.4 读时回退、不回写 |
| 2 | 幂等重入时 `anchor` 是否改写没定义（v24 只写了 restore） | §4.1 三态表统一：都不改写 |
| 3 | `blocking_unknown.report_digest` 若要"现场摘要"则在文件删掉后为空，放行永远匹配不上 | §3 明确**必须是登记摘要** |
| 4 | `unknown_acceptances` 可能因 `--restore` 改摘要而失效，却没有"失效记录"口径 | I5：失效记录不删、不计入解除 |
| 5 | `stale`（锚点≠当前）报告里的 findings 既不入 blocking 也不入 unknown | §1.2/§3 新增 `stale_findings`（可见、不阻断） |
| 6 | `reports_ready` 与 `material_blockers` 可能不同步 | I3 等价不变量 + 同一函数产出 |
| 7 | `declared == 0` 时"不就绪且无原因" | `no_declared_slots` kind |
| 8 | `legacy_ambiguous_closures` 只有入口没有出口 | §2.5 唯一出路：补发精确 disposition |
| 9 | 归档在提交失败后重入是否重复提交没写清 | §4.5 #1 + `resumable` 判据（与 `ignore_action_id` 同规则） |
| 10 | 我自己把"验收 40 项"写成数字却没核对条目 | 本版条目与标题、§8 计数一致（§10 #10） |

---

## 附录 A：23 版演进（只记致命点，保留审查证据）

| 版本 | 形态 | 致命点 |
|---|---|---|
| v1/v2 | 派生事实 | 派生要复制门禁；定义与退出条件互斥 |
| v3 | `fixing` 阶段 | 身份矛盾（含 check vs v42 无 check）；漏协议硬校验 |
| v4 | 事件写入标记 | 主路径清不掉；撞名 `repair.py` |
| v5/v6 | 两行 / 结构化 `unresolved` | 缺结论绑定；"未要求"遮住 blocking |
| v7/v8 | 档位重排 | `gate` 只答步骤面；`pass_unbound` 死区 |
| v9/v10 | 当前轮优先 | 从未发起审查无命中；`round_complete` ≠ 可判定 |
| v11 | 三条自动退出 | 数据不存在（`imported` 无 findings）；"新轮 pass"可绕开关闭 |
| v12 | 两条出口 + 人裁 | 人裁通道不存在（`authorize.ACTIONS` 五类、后写覆盖） |
| v13 | 独立放行记录 | 证据可被替换；`launches` 实为 `[]` |
| v14/v15 | 证据身份 + 暂存发现 | 二次认领；旧结论当新结论 |
| v16/v17 | `ready` 收紧 | 材料/资格混同；`unreadable` 无产出 |
| v18/v19 | 读取健壮 + 15 档表 | 档位表自相矛盾、死档、归因错误 |
| v20 | 删表 → 原子事实 | 材料/资格混同；裸 id 身份 |
| v21/v22 | Q1/Q2 落位 | 缺摘要可替换；schema 与计数脱节 |
| v23 | 缺摘要拒替换 + 裸 id 固定 | 出口把"继续"当"解除"；槽位身份域未定义 |
| **v25** | **可实现规格（数据模型 + 计算事实 + 操作契约 + 作用域）** | 本版按 §10 自审清单自查，修掉 10 处（§11） |
