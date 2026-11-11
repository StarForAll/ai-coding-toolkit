# 提案（v24）：⑥ 只做「结构化未结事实」+ 一条人裁放行记录 + 文档裁定

> 状态：**待审 v24**（第二十三轮修正；Q1=乙、Q2=甲 已定）。前二十三版的形态与致命点见 §0。
>
> **阶段声明（2026-11-11 人裁）**：本文件处于**方案审查阶段**——**实现零改动**。
> 审查期间误改的实现已全部回退（`e49da16` → `8da2f23`）。下文凡提到"实现"均为**要求与验收**，
> 不代表已落地。**未经人明确"审查通过"，不得修改任何实现代码，也不得以跑测试/repro/release 重建来"确认"**
> ——规则见 `.trellis/spec/guides/review-phase-discipline.md`。

---

## 0. 二十三版形态演进（只记致命点）

| 版本 | 形态 | 致命点 |
|---|---|---|
| v1/v2 | 派生事实（"修复中"/"原因集合"） | 派生要复制门禁；定义与退出条件互斥；五态装不下 |
| v3 | 新增 `fixing` 阶段 | 身份矛盾（含 check 的五值 vs v42 无 check）；漏协议硬校验；pass→check 逼出重复 check |
| v4 | 事件写入 `repair` 标记 | 主路径清不掉；两失败源共用槽位；撞名 `repair.py` |
| v5/v6 | 两行 / 结构化 `unresolved` | 缺结论绑定；"未要求"遮住 blocking；缺"复杂未审查"行 |
| v7/v8 | 档位重排 | `gate` 只答步骤面；`pass_unbound` 死区；`invalidated` 死行 |
| v9/v10 | 当前轮优先 + 复用 `review-status` | 从未发起审查无命中路径；判定后证据失效；`round_complete` ≠ 可判定 |
| v11 | 三条自动退出 | 建在不存在的数据上（`imported` 无 findings）；"新轮 pass"可绕开关闭 |
| v12 | 两条出口（重发 / 人裁） | 人裁通道不存在（`authorize.ACTIONS` 固定五类、后写覆盖、无 `--choice`） |
| v13 | 人裁放行改独立记录 | 证据可被替换（删档换报告）；`launches` 实为 `[]`；性质测试域与 schema 不一致 |
| v14 | 证据身份约束 + 混槽位并列 | 暂存发现仍报 missing；验收 4 与 13d 相反；计数与 attestation 字段不一致 |
| v15 | 暂存发现口径 | 同一份已导入报告被二次认领；挂载点 `next_` 在 stale/单 provider 轮仍说"可判" |
| v16 | 只认领一次 + `ready` 对齐 | `ready` 没要求"已导入"；`unreadable` 被引用却无产出路径 |
| v17 | `ready` 收紧 + 读取健壮 | 只修两处 OSError（`all_findings`/`proposers`/`review-passed` 仍崩） |
| v18 | 全链路读取健壮 | `gates.py` 一处未修（`review-passed` 仍抛）；第 6 档未用 `round_ready` |
| v19 | 15 档表 + `round_ready` | 档位表自相矛盾/死档/归因错误；找不到"从未发起审查"的命中路径 |
| v20 | 删表 → 原子事实 | 材料就绪与判定资格混同；finding 身份按裸 id 汇总；`--restore` 改写历史绑定 |
| v21 | Q1/Q2 落位 | 缺摘要记录可被普通导入替换；遗留裸 id 会随未来轮次扩大关闭；`declared==0` 无原因 |
| v22 | 材料/资格分列 + restore 保原锚点 | schema 与实现脱节；验收计数假断言；`pending_unknown`/`accepted_by` 三处不对齐 |
| v23 | 缺摘要拒替换 + 裸 id 固定 | **§3 出口把"让流程继续"当成"解除阻断"**；槽位身份域未定义；普通重导 / 幂等重入 / `--restore` 三态差异未定；`stale` 报告的 findings 归属空心化 |
| **v24** | 解除语义两列化 + slot 身份域 + 三态差异表 + 归属矩阵 + 阻断作用域 | 本版重写 §1–§6（对应第二十二轮 P0/P1）：出口按"让流程继续/解除阻断"两列、`slot_key` 定义、普通导入/幂等重入/`--restore` 三态差异、三类 finding 归属互斥、code 优先级只作用于步骤预检之后 |

**已核实的产品级事实（代码位置，供认定缺陷用；本提案不据此改代码）**

| 事实 | 位置 |
|---|---|
| `reviews.imported[]` **不含 findings**（只有 round/slot/report_path/report_digest/anchor[/agent/restored]） | `review.py:1131-1144` |
| 提出者索引若从记录读 findings 恒为空 → 关闭链断（既有缺陷） | `review.py:573` / `1043` |
| `reviews.result` **只保留最新一轮**；`attempts.outcome` 是尝试级摘要 | `review.py:1484` |
| `authorize.ACTIONS` 固定五类；授权按动作一文件、后写覆盖 | `authorize.py:20-26 / 73` |
| `final_gate` 纯只读；内部**逐项早退**；带 `ignore_action_id` | `gates.py:865 / 941` |
| `final_gate` 先跑步骤预检，缺项即返回，之后才读 `open_findings` | `gates.py:869-874 / 911` |
| 归档在 `final_gate` **之前**执行业务提交 | `tasks.py:3233` |
| `task-abandon` 不跑 `final_gate`，直接置 `terminal=abnormal` | `tasks.py:2732` |
| `changes_persisted_fact` 在未提交时返回缺项（**即使已有授权**） | `tasks.py:1006-1014` |
| `records.file_digest` 只捕 `FileNotFoundError`（权限故障会外溢） | `records.py:62` |
| `review-decide` 本轮报告循环里**直接**调 `file_digest`，在 try 之外 | `review.py:1304` |
| 声明槽位 `s1/s2` 与发现式 reviewer 名（`codex`）**两种 slot 值并存** | `review.py:343 / 1160` |

---

## 1. 交付物：`unresolved`（挂 3 处）

挂载：`wf status`（含 `--short`）、`judgments show`、`wf review-status`。其余任务级命令不挂。
**死角**：`task-check` 失败走通用 except 层（`cli.py:2638`），不带 `unresolved`（另案）。

### 1.1 schema（**v24：补 `stale_findings`、`legacy_ambiguous_closures`、`action_resumable`；`pending_unknown` 声明同源**）

```json
"unresolved": {
  "check": {"usable": false,
            "reason": "archived|no_check|not_passed|invalidated_content_changed|anchor_mismatch|rule_changed|anchor_unavailable|structure_incomplete",
            "check_id": "A", "scope": "archive_gate", "detail": null},
  "review": {
    "round": 2, "launched": 2, "imported": 2, "declared": 2,
    "slots": [{"slot": "s1", "slot_key": "s1", "declared": true,
               "state": "imported|staged|stale|missing|unreadable",
               "reason": null, "importable": null, "round": 2}],
    "reports_ready": false,                     // 只讲材料；空 blockers ⟺ true（见验收 7b）
    "material_blockers": [{"kind": "no_declared_slots|anchor_unavailable|anchor_unchecked|extra_report_stale|slot_not_imported|slot_unreadable",
                           "slot": "s1", "round": 2}],
    "eligibility_hints": [{"kind": "declared_lt_2", "declared": 1}],   // 资格提示，非材料事实

    // 三类 finding 归属，互不相交（见 §1.2 矩阵）
    "open_blocking":  [{"round": 1, "slot": "s1", "finding_id": "f1", "severity": "blocker"}],
    "stale_findings": [{"round": 1, "slot": "s1", "finding_id": "f2", "severity": "blocker",
                        "why": "报告可读但锚点不是当前 check（不可用于当前判定）"}],
    "blocking_unknown": [{"round": 1, "slot": "s1", "slot_key": "codex", "path": "…",
                          "report_digest": "sha256:…", "cause": "changed|missing|unreadable",
                          "accepted": false}],

    // 便利视图：**恒由 blocking_unknown 过滤得出**，禁止独立实现（见验收 7c）
    "pending_unknown": ["<blocking_unknown 中 accepted=false 的条目，结构相同>"],

    // 遗留裸 id 处置：歧义时**保留歧义**，不自动猜定（见 §2.4）
    "legacy_ambiguous_closures": [{"finding_id": "f1",
                                   "candidates": [[1, "s1", "f1"], [1, "s2", "f1"]],
                                   "note": "旧处置未带 round/slot，且候选不唯一；需人裁或补精确身份后重发"}],
    "verdict": "pass|fail|unavailable|invalidated|null",
    "verdict_round": 1, "verdict_check_id": "A",
    "bound_to_current": true, "bind_problems": []      // 口径 ≡ gates.review-passed
  },
  "nonstep": {"escalated": 0, "required_unverified": 0, "complexity_unconfirmed": false,
              "downgrade_incomplete": false, "dependencies_unmet": [], "debug_unruled": [],
              "action_incomplete": {"id": "…", "resumable": false},   // v24：resumable 由机制给
              "paused": false, "suspended": false}
}
```

### 1.2 三类 finding 归属矩阵（v24 修 b-P0-4：不留"静默消失"的口袋）

| 槽位状态 | 报告可解析？ | findings 归属 | 是否阻断归档 |
|---|---|---|---|
| `imported`（摘要一致、锚点=当前） | 是 | `open_blocking`（未关闭且 blocking） | 是（可走 K4b 关闭） |
| `imported` 但**锚点 ≠ 当前** | 是 | **`stale_findings`** | **否**（不是当前对象的问题，但**可见**） |
| `stale`（摘要被改写/删除） | 否/不可信 | `blocking_unknown`（`cause=changed/missing`） | 是（只能人裁放行或 abandon） |
| `unreadable`（权限/IO） | 否 | `blocking_unknown`（`cause=unreadable`） | 是（同上） |
| `staged` / `missing` | —— | 无 findings（还没导入） | 否 |

**`material_blockers` 与槽位五值的对应**（v24 补 b-P0-4）：

| blocker `kind` | 由哪类槽位/条件产生 |
|---|---|
| `no_declared_slots` | `declared == 0` |
| `anchor_unavailable` | 当前锚点算不出（`anchor is None`） |
| `anchor_unchecked` | 某槽位 `anchor_checked == false` |
| `slot_not_imported` | 槽位为 `staged` / `missing` / `stale`（尚未成为**当前可用的**已导入材料） |
| `slot_unreadable` | 槽位为 `unreadable` |
| `extra_report_stale` | 存在未被声明槽位认领、且已失效的已导入报告 |

> 口径：`slot_not_imported` 与 `slot_unreadable` 分开列，是为了让人一眼看出"补导入就能推进"与"要先修权限"。

### 1.3 槽位身份域（v24 补 b-P0-2：这是放行/撤销/匹配的身份根基）

| 概念 | 定义 |
|---|---|
| `slot`（声明槽位） | 审查发起时声明的槽位名（`s1/s2/…`） |
| `agent` | 报告的实际 reviewer 名（发现式导入时从文件名/头部取得，如 `codex`） |
| **`slot_key`（规范标识）** | **对外的唯一身份**：声明槽位已映射时为声明名；发现式额外报告未被声明槽位认领时，取 `agent`（无 agent 则取 `path` 基名去扩展名） |
| 位置分配的**顺序** | 按 round 目录下 `review-<agent>.md` 的**文件名升序**（`sorted()`）依次分配给未满足的声明槽位；顺序一旦分配即写入记录，**不因后续新增文件而重排** |
| 同一报告的两种指称 | 一律以 `slot_key` 为准；`slot`/`agent` 仅作事实字段保留，**不得**用作 acceptance/revoke 的匹配键 |

**放行、撤销、`blocking_unknown[]` 的匹配键统一为 `(round, slot_key, report_digest)`。**

### 1.4 展示分组（纯展示；v24 修 b-P2-15：**组命中时同时展示事实行**）

| 展示组 | 触发（仅展示） | **必须并排展示的事实行** |
|---|---|---|
| `已归档` | `status == "archived"` | 无 |
| `材料待补` | 槽位含 `staged`/`missing`/`stale`/`unreadable` | 每个槽位一行（state + `importable` + `reason`） |
| `有未结项` | `open_blocking` / `pending_unknown` / `stale_findings` / 任一 `nonstep` 非空 | 按类各一行（含 `resumable`、`eligibility_hints`） |
| `材料就绪` | `reports_ready` 且无未结项 | **必须同时展示 `eligibility_hints`**（否则人以为可收工、到 decide 才被拒） |

**无组命中时直接展示原子事实原文**（`launches` 为空、或 `imported` 齐但 `reports_ready=false` 等）。

---

## 2. 人裁放行：独立记录（Q1=乙：一次一批、全有或全无）

### 2.1 记录形状

**命令**：`wf review-accept-unknown --task <id> --file <决定.json>`（需持写权）

```json
{"batch": "b-20261111-1",
 "acceptances": [
   {"round": 1, "slot_key": "s1", "report_digest": "sha256:…", "quote": "这份报告丢失的风险我认"},
   {"round": 2, "slot_key": "codex", "report_digest": "sha256:…", "quote": "改写过但内容我已通读"}
 ]}
```

写入 `reviews.unknown_acceptances[]` 每项一条：`{batch, round, slot_key, path, report_digest, cause, quote, by, at, source, attestation_digest, revoked}`。

| 规则 | 语义 |
|---|---|
| 原子性 | 任一项的 `(round, slot_key, report_digest)` 与**当前** `blocking_unknown` 不等 → **整批拒绝、零写入**，返回 `bad_items[{round,slot_key,expected,actual,reason}]` |
| **输入域（v24 补 b-P0-5）** | ① 指向**不存在于当前 `blocking_unknown`** 的 `(round, slot_key)` → **拒绝**（不做"预放行"：一条针对正常报告的 acceptance 会在它将来失效时自动生效，等于无限期放行）；② 同一 `(round, slot_key, digest)` 重复放行 → **幂等**（不新增记录，回报 `already_accepted`）；③ `--revoke --round --slot_key` 命中多条（不同 digest）→ **全部撤销**并回报 `revoked_count` |
| 允许子集 | 人可只列 2 份；未列出的仍阻断 |
| 批级共享 / 逐项独立 | `by/at/source/attestation_digest/batch` 批内共享；**`quote` 必须逐项** |
| 撤销 | `--revoke --round/--slot_key` 或 `--batch <id>` → 置 `revoked: true`（**不删记录**，留痕） |
| 缺摘要的遗留记录 | `imported` 条目没有 `report_digest` → 无法核对 → **不可放行**；出口见 §3（**只有 `task-abandon`**） |

### 2.2 阻断与解除：**两列分开写**（v24 修 b-P0-1 / a-1：上一版把"让流程继续"当成"解除"）

| 动作 | ① 让流程能继续 | ② 解除该条 `blocking_unknown` |
|---|---|---|
| `review-accept-unknown`（摘要全等） | 是 | **是**（唯一机械解除） |
| 重发新一轮（pass 且绑定当前 check） | 是（当前轮可判、可归档——若没有历史 unknown） | **否** |
| `review-decide --unavailable` | 是（把该轮标为不可用） | **否** |
| `review-import --restore`（摘要全等） | 是（恢复历史身份） | **否**（恢复只重建证据，不解除未知） |
| `task-abandon` | 是（终局） | **否**（不解除；只是不再需要解除） |

**因此对"缺摘要的遗留记录"**：无法放行、无法恢复证明、重发/不可用都不解除 → **唯一终点是 `task-abandon`**（或人重建该轮记录后另案处理）。§3 的出口表已按这条重写。

### 2.3 三种导入行为的差异（v24 补 b-P0-3）

| 路径 | 前置校验 | `anchor` 写入 | `restored` 标记 | 说明 |
|---|---|---|---|---|
| **普通导入**（该槽位无登记） | 报告锚点 == **当前** check 锚点 | 当前 `(check_id, anchor)` | 否 | 首次导入必须匹配当前对象 |
| **幂等重入**（该槽位有登记，摘要**相同**） | 只需摘要相同（**不再校验当前锚点**） | **保持原登记值**（不改写） | 否 | 同一份字节重入是"确认"，不是"重绑" |
| **`--restore`**（该槽位有登记，摘要**相同**） | 同上（摘要相同即可） | **保持原登记值** | **是** | 与幂等重入的差别只有 `restored` 标记与语义（明确表达"这是恢复")；不传 `--restore` 的普通重入行为等价但没有恢复意图记录 |

> 结论：`--restore` **不是**新权限，而是"把恢复意图落成事实"的显式开关。三态都不更新 `anchor`——否则 `status` 会把旧报告当当前材料，而 `decide` 核正文又拒（v20 的真实缺陷）。

### 2.4 遗留裸 id 的兼容裁定（v24 修 a-5 / b-P1-12：**歧义保留，不猜定**）

| 情形 | 处置 |
|---|---|
| 旧 disposition 无 `round`/`slot`，且该 `finding_id` 在**唯一**一个 `(round, slot_key)` 出现 | 绑定到该身份（可关闭） |
| 旧 disposition 无 `round`/`slot`，且同名出现在**多个** `(round, slot_key)`（含同轮不同槽位） | **不关闭任何一条**，进入 `legacy_ambiguous_closures`；出口：人裁确认 / 补精确身份后重发 disposition |
| 旧记录的**报告不可读**（无法重解析出 finding） | 该裸 id 无从绑定 → 同样进 `legacy_ambiguous_closures`（**不因"现在读不到"而改变绑定**，也不因此关闭） |
| 新增 disposition | **必须**带 `round + slot_key`；缺失且存在同名多身份 → 拒绝并列候选项 |

### 2.5 身份契约必须贯穿（v24 补 a-2：不只查询侧）

| 契约点 | 要求 |
|---|---|
| 提出者索引 | 键 = `(round, slot_key, finding_id)`；**禁止** `setdefault` 式"第一个提出者"覆盖 |
| 关闭复核（自证检查） | 以**该身份**的提出者为比较对象（同一 reviewer 在不同轮提出同名 finding 不算自证） |
| 判断骨架 / 引用空间 | 保留 `round`/`slot_key`；引用形如 `f:<round>:<slot_key>:<id>`，`f:<id>` 仅作遗留读入 |

---

## 3. `cause`、出口与健壮性（v24 重写出口语义）

### 3.1 三类不可核实证据的出口

| `cause` | ① 让流程继续 | ② 解除该条 unknown |
|---|---|---|
| `changed` | 重发新一轮（新证据可判） | **无机械路径** → 人裁放行 / `task-abandon` |
| `missing` | 取回原字节并 `--restore`（摘要一致）→ 恢复身份；或重发新一轮 | 同上 |
| `unreadable` | 恢复可读后 `--restore`；或重发新一轮 | 同上 |

**明确写死**：`--restore` 与重发**永远不解除**旧 unknown（§2.2）——它们是"让当前工作能继续"，不是"历史未知被消化"。

### 3.2 读取健壮性：**六处**（v24 补 a-6：上一版只列五处，漏了 `decide` 循环）

`open_findings` / `status_of_round` / `all_findings` / `proposers_from_imported` /
`gates.review-passed` / **`review-decide` 的本轮报告循环**（`review.py:1304`，其 `file_digest`
在 `try` 之外）——六处统一把 `OSError` 归类（缺失 → `missing`；权限/IO → `unreadable`），
不得让异常冲出查询或门禁入口。

**根因**：`records.file_digest` 只捕 `FileNotFoundError`。提案要求提供
`file_digest_or_raise`（不吞 OSError）并**规定新调用点必须用它或自行归因**；
验收用"枚举全仓 `records.file_digest(` 调用点并逐一确认归因"的审计断言来守（见 §9 #29）。

---

## 4. 只读门禁：不重构 `final_gate`（含 code 优先级的**作用域**）

- `evaluate_cli` 保持原样（步骤面只读预检）：**信封结构不变**，但 `facts.missing[]` 条目新增 `fulfilled_by`；
- **code 优先级只适用于"通过步骤预检之后"**（v24 修 a-4 / b-P1-4）：
  `final_gate` 先跑步骤、缺项即返回，之后才读 `open_findings`。因此"历史 blocking + pending_unknown +
  引用报告丢失"这条真实路径返回的是**步骤层**的 `WF_REVIEW_INVALID`（来自 `review-passed` 的摘要核对），
  §2.2 的 `WF_UNRESOLVED_BLOCKING` 优先只在**步骤全通过后**成立；
- **非步骤事实**见 `unresolved.nonstep`（九项）。`action_incomplete` 带 `resumable`：
  当该动作**正是**当前重入目标时 `resumable=true`（与 `final_gate(ignore_action_id=…)` 同一规则，
  由机制给事实，skill 只引用，不复述规则）；
- **契约**：`gate` = 步骤面预检；并读 `unresolved` 才是归档前完整依据；**gate 通过 ≠ 归档必成**
  （`repo_rules`/`delete` 无只读预检、业务提交先于门禁）；**不要用"试归档"探路**（会先提交）。
  该硬约束的机制化选项见 §10 Q4。

---

## 5. 候选动作：由 AI 从事实推出，机制不排顺序

机制只给事实与原因；顺序由 AI 决定。唯一硬约束仍是"不要试归档探路"与"判定资格由 `review-decide` 判"。

**阻断作用域（v24 补 a-7：别让"有未结项"变成"什么都不能做"）**

| 未结事实 | 阻断什么 | **不阻断什么** |
|---|---|---|
| `escalated`（判断待答） | 最终结论声明、归档 | 继续导入报告、调查、不依赖该判断的修复（v42 K10 原义） |
| `open_blocking` | 归档 | 继续工作、重查、重发审查 |
| `pending_unknown` | 归档 | 继续工作（含另一轮审查） |
| `stale_findings` | 不阻断归档 | —— （仅提示：那些问题针对旧对象） |
| `required_unverified` / `downgrade_incomplete` / `dependencies_unmet` / `debug_unruled` | 归档 | 继续工作 |
| `action_incomplete`（`resumable=true`） | 无（可直接续做） | —— |
| `eligibility_hints` | 判定结论（decide 判） | 材料准备、导入、重发 |

---

## 6. 技能层衔接（只引用机制事实）

| 技能 | 加一行 |
|---|---|
| `wf-finish` | 读 `unresolved` 与 `gate` 的 `fulfilled_by` / `action_incomplete.resumable`：标为"由目标动作完成"或 `resumable=true` 的**不是前置**；其余按 §5 的**作用域**判断——只挡完成声明与归档，不挡继续工作 |
| `wf-continue` | `in_progress/finish` 路由前看 `unresolved`：按 §5 作用域处理，不要把所有未结项当成"必须先清零" |

---

## 7. ⑥ 的实质处置：文档裁定（v42 不动）

新增 `analysis/ruling-repair-vs-fixing.md`：不引入 `fixing` 阶段（维持 2026-11-09 人裁）；本文件 §0 的审查演进摘要；与 v42 K10（L107）/S4（L122）/S5（L123）/§7.1（L401）差异逐条登记；记录两处语义压缩（`--short` 的 `task.check`、`unresolved` 只报事实不报"能否结案"）；登记 §2 的放行记录与其绑定规则、§2.4 的遗留兼容裁定。

---

## 8. 影响面（**全部为待实现项**）

| 项 | 数量 |
|---|---|
| 机制修补（K 级） | 2：① `blocking_unknown` + 放行记录 + `final_gate` 消费 `pending_unknown`；② 导入端证据身份约束 |
| 新增命令 | 2：`wf review-accept-unknown`（批次 + `--revoke`）；`wf review-import --restore` |
| 任务记录新增字段 | 2：`reviews.unknown_acceptances[]`；`imported[].restored` |
| **门禁/查询行为变化（单独标注）** | ① finding 身份收紧（旧裸 id 不再跨轮/跨槽位关闭）；② `gate` 的 `facts.missing[]` 增 `fulfilled_by`；③ `status_of_round` 的 `reports_ready` 语义（只讲材料）；④ 幂等重入不再改写 `anchor` |
| 读取健壮 | **六处**（§3.2）+ `file_digest_or_raise` |
| 提取共享函数 | 1（`check_usability`） |
| `nonstep` 九项事实 | 1 处（含 `action_incomplete.resumable`） |
| 展示点 | 3 |
| skill 文本 | 2 |
| 协议码表 | 0（**代价**：`pending_unknown` 复用 `WF_REVIEW_INVALID`，靠 `facts.reason` 消歧，见 §10 Q3） |
| 测试 | **40 项**（§9） |
| **已知限制（显式登记）** | ① 放行记录沿用 attestation 信任模型（AI 可转录/可伪造，无密码学保证），撤销亦无 attestation——见 §2.1 与 Q5；② `repo_rules`/`delete` 无只读预检；③ "不要试归档"只能是指引（Q4） |

---

## 9. 验收标准（**40 项**，稠密编号；每条可被后续实现验证）

| # | 断言 |
|---|---|
| 1 | `check.usable/reason` 与 `gates` 判定逐值一致（8 个 reason 的映射表随实现给出） |
| 2 | 槽位五值可达（`imported`/`staged`(带 `importable`)/`stale`(区分删除改写)/`missing`/`unreadable`） |
| 3 | 同一份报告不被二次认领（`arrived` 不虚增） |
| 4 | 混合槽位任意子集如实列出；`reports_ready == false` 且 `material_blockers` 逐项给原因 |
| 5 | `reports_ready` **不含资格**：单 provider、实施者重叠时它**可以**为 true；CLI 文案不出现"可判" |
| 6 | 单 provider → `eligibility_hints` 含 `declared_lt_2`，**不**进 `material_blockers` |
| 7 | `declared == 0` → `material_blockers` 含 `no_declared_slots` |
| 8 | **等价不变量**：`reports_ready == (material_blockers == [])`（对声明槽位>0 与 =0 均成立） |
| 9 | **`pending_unknown` 同源**：恒等于 `blocking_unknown` 中 `accepted=false` 的子集（同一函数产出，无独立实现） |
| 10 | 槽位身份域：`slot_key` 为唯一匹配键；`(round, slot_key, digest)` 三者全等才匹配；位置分配按文件名升序且**分配后不重排** |
| 11 | `imported` 且锚点≠当前 → findings 进 **`stale_findings`**（可见、不阻断）；`stale`/`unreadable` → 进 `blocking_unknown`；三类互不相交 |
| 12 | finding 身份 = `(round, slot_key, finding_id)` 贯穿：`open_blocking`/`stale_findings`/提出者索引/自证复核/判断引用（`f:<round>:<slot_key>:<id>`） |
| 13 | 新增 disposition 缺 `round/slot_key` 且存在同名多身份 → **拒绝**并列候选 |
| 14 | 遗留裸 id：唯一身份 → 绑定关闭；多身份或报告不可读 → 进 `legacy_ambiguous_closures`，**不关闭任何一条** |
| 15 | `all_findings` 的 `closed` 亦按精确身份计算 |
| 16 | 批量放行成功：一次写 2 项（各带 `quote`）→ 同 `batch`，`pending_unknown` 清空 |
| 17 | 任一项坏 → **整批拒绝、零写入**，返回 `bad_items`（`expected`/`actual`/`reason`） |
| 18 | 子集放行：只列 1 份 → 该项 `accepted`，另一项仍在 `pending_unknown` |
| 19 | 撤销：`--round/--slot_key` 与 `--batch` 均置 `revoked: true`（不删记录）并恢复阻断；同槽多位点全撤并回报 `revoked_count` |
| 20 | **输入域**：acceptance 指向当前不存在的 `(round, slot_key)` → 拒绝（不做预放行）；重复放行同一键 → 幂等 `already_accepted` |
| 21 | 摘要不同**不匹配**（记录级单测，不构造非法路径） |
| 22 | 权限故障的不可读条目**带登记摘要** → 精确匹配的放行能解除 |
| 23 | 缺 `report_digest` 的遗留记录：普通导入被拒、放行不可用、`--restore` 亦不可用；出口只有 `task-abandon` |
| 24 | 证据身份不可替换：删档后导入同轮同槽位另一份被拒 |
| 25 | 三种导入差异符合 §2.3：普通导入写当前锚点；**幂等重入与 `--restore` 都不改写 `anchor`**；`--restore` 额外置 `restored` |
| 26 | 发现式导入的 `restore` **只在已登记时传**（首次导入绝不传） |
| 27 | 权限故障不让 `status`/`review-status`/`review-decide`/`wf gate` 崩溃（六处调用点全覆盖） |
| 28 | `pending_unknown` 非空 → `final_gate` 阻断（`WF_REVIEW_INVALID` + `facts.reason=unverifiable_evidence`） |
| 29 | **审计断言**：枚举全仓 `records.file_digest(` 调用点，逐一确认已归因（或改用 `file_digest_or_raise`）；新增调用点漏归因即失败 |
| 30 | 两类阻断同时存在 → **步骤预检通过后**先返回 `WF_UNRESOLVED_BLOCKING`，`facts` 同时带两类；**步骤未通过时**返回步骤层 code（优先级不跨层） |
| 31 | `stale.reason` 区分删除/改写；`no_declared_slots`/`slot_unreadable` 等 kind 与 §1.2 矩阵一致 |
| 32 | `nonstep` 九项齐全；`action_incomplete.resumable` 与 `final_gate(ignore_action_id=…)` 同规则 |
| 33 | `action_incomplete.resumable=true` 时**允许续做**（不构成"进入归档前必须清零"的循环） |
| 34 | 续做安全：业务提交先于门禁；重入按 `commit_grants` 幂等跳过（断言不重复提交） |
| 35 | 归档准入基线：口径 = **finding 身份收紧之后**（该收紧本身会拦下旧裸 id 跨轮任务） |
| 36 | 性质测试（原子事实）：槽位五值任意子集 × `declared∈{0,1,2,3}` × 锚点三态 × 额外报告三态 → `reports_ready == (全 imported ∧ 锚点已核 ∧ 无额外问题 ∧ 有声明槽位)`，且与 `material_blockers` 空等价 |
| 37 | 性质测试（归属）：任取报告集合，`open_blocking`/`stale_findings`/`blocking_unknown` 三类**两两不相交且并集覆盖全部已导入报告的可解析 findings**（无静默消失） |
| 38 | 放行记录字段完备性：`by` 必须 `human:` 前缀、`source` 必填、`attestation_digest` 入库（**不宣称"无法自签"**） |
| 39 | `task-abandon` 定位：不跑 `final_gate`、不解除 `pending_unknown`，只以 `terminal=abnormal` 收尾 |
| 40 | 展示：组标签命中时**同时**展示该组的事实行（`材料就绪` 必须展示 `eligibility_hints`）；无组命中时展示原子事实原文 |

## 10. 待决问题（标注是否阻塞落笔）

| # | 问题 | 阻塞？ | 若不决则默认 |
|---|---|---|---|
| Q3 | `pending_unknown` 阻断复用 `WF_REVIEW_INVALID`，还是新增一个码（协议 36→37）？ | 否 | 复用，`facts.reason=unverifiable_evidence` 消歧 |
| Q4 | "不要试归档探路"是保持指引，还是上 `archive --dry-run` / 把 `final_gate` 提到业务提交之前？ | 否 | 保持指引；理由见下 |
| Q5 | 放行记录的信任模型：接受"AI 可转录/可伪造 + 留痕可审计"，还是要求人直接在决定文件签名？ | 否 | 接受现状并登记为已知限制（§8） |

**Q4 的评估（v24 补：上一版只写指引没写为什么）**：`tasks.py:3233` 的提交先于门禁是既有语义（"先提交后核"
让失败也留下可审计的提交）。改成 `--dry-run` 或调换顺序都会改变归档的动作语义与回执形状，属独立议题；
当前选择"指引 + 门禁自带 exits"，代价是依赖会话纪律——**如实登记为已知限制**，不假装已被机制覆盖。

**已定（2026-11-11 人裁）**

| 项 | 决定 | 落点 |
|---|---|---|
| Q1 | 乙：一次一批、全有或全无；逐项 `quote`；子集允许；逐项/整批撤销 | §2.1 规则、§9 #16–#20 |
| Q2 | 甲：两类阻断分列（`open_blocking` / `blocking_unknown` / `pending_unknown`）+ 不变量 + code 优先级 | §1.1、§1.2 矩阵、§9（三类归属互斥、`pending_unknown` 同源、code 优先级作用域、blocking 阻断）|

---

## 11. 定稿前固定核对清单（每次改版必跑）

| # | 核对项 | 具体做法 |
|---|---|---|
| 1 | **版本表时序** | §0 表按 v1→vN 递增，最新版在最后且加粗 |
| 2 | **计数一致** | 头注"前 N 版"、§0 标题"N 轮"、§9 条目数、§8 测试行——四处同数（改表必须同时改四处） |
| 3 | **引用可达（v24 新增）** | 正文里出现的每个"§x / 验收 #n / 第 n 档"都必须能在文中解析到；**禁止跨版本编号残留**（v23 的 §10 引用了不存在的 10a–10d 就是反例） |
| 4 | **实现项登记** | 凡实现项（不论待实现）必须出现在 §8；门禁/查询行为变化单独标注 |
| 5 | **阶段与实现状态** | 头部阶段声明必须与 §8 一致；**审查阶段一律零改动**，出现实现 diff 必须先回退 |
| 6 | **schema 与正文对齐** | §1.1 的每个字段都要在 §1.2/§2/§4 有定义；正文提到的字段必须出现在 §1.1（v23 的 `ignore`、`accepted_by` 就是反例） |
