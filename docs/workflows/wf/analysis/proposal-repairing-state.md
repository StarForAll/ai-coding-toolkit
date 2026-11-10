# 提案（v10）：⑥ 只做「结构化未结事实」+ 复用既有只读查询 + 一处机制修补

> 状态：**待审 v10**（第九轮修正）。前九版均被否；本版修：行可达性、判定后证据失效、
> 判定前置改为复用 `review-status`、不重构 `final_gate`、`cause` 结构与健壮性、
> **旧轮证据缺失导致的阻断逃逸**（机制修补）、技能层指引衔接、出口改为"事实 + 候选动作"。
> 本文件是决策提案，实现未开始。

---

## 0. 九轮审查的净结论（只记与本版有关的最后一条）

| 版本 | 致命点 |
|---|---|
| v1–v7 | 派生/阶段/标记/优先级方案逐个被否（详见历次提交说明） |
| v8 | `pass_unbound` 死区 |
| **v9** | **① 从未发起审查的路径无命中（`undecided` 没要求 launches 非空）**；**② 判定后引用报告被改仍显示"已通过"**；**③ `round_complete` 把"材料到位"当"可判定"（锚点失配/单 reviewer 必然被拒）**；**④ `open_findings` 的 `unavailable` 没有 `cause`/`round`，且 `file_digest` 只捕获 `FileNotFoundError`（PermissionError 会冲出 `status`）**；**⑤ 提取 `final_gate` 非步骤段拿不到"一次给全"（它本身逐项早退），还会丢 `ignore_action_id`**；**⑥ 技能层没有接上只读查询（`wf-finish` 直接 archive）**；**⑦ 出口写成固定命令序列，把已完成的工作压回去重做** |

---

## 1. 交付物：结构化事实 `unresolved`（挂 3 处）

| 挂载点 |
|---|
| `wf status`（含 `--short`） |
| `judgments show`（收工预览） |
| `wf review-status`（沿用既有命令，补 `unresolved.review` 片段） |

**不挂**其余任务级命令（成本无依据）；**已知死角**：`task-check` 失败走通用 except 层，不携带 `unresolved`（独立缺口，另案），替代路径 `wf status --short`。

### 1.1 判据（把 v9 的三个坑写死）

```
launches      = reviews.launches（列表）
active_round  = max(launch.round) if launches else None        # 空 → None，不取 0
result        = reviews.result
undecided     = active_round is not None and (result is None or active_round > result.round)
cited_round   = result.round if result else None
```

**v9 的坑 ①**：`undecided` 必须先要求 `active_round is not None`——否则"从未发起审查"会因 `max([])`/默认 0 提前落进 `imported_not_decided`，而 `not_started`/`none_required` 永远不可达。

### 1.2 取值优先级（**12 档（0–11）**，含固定归档行）

| # | 条件 | `state` | 显示 | 候选动作（**不是命令序列**，见 §5） |
|---|---|---|---|---|
| 0 | `status == "archived"` | `archived` | 已归档，不再评估 | —— |
| 1 | **`cited_round` 的引用报告不可读** | `reports_unreadable` | 第 N 轮结论引用的 M 份报告不可读 | 见 §3 |
| 2 | `undecided` 且该轮有不可读报告 | `reports_unreadable` | 第 N 轮 M 份报告不可读 | 见 §3 |
| 3 | `undecided` 且 `review-status` 显示该轮 slot 未到齐 | `awaiting_reports` | 第 N 轮已发起，报告 i/m | 等报告 / `review-status`；**报告永不到达时可 `review-decide --unavailable`（零导入也可用）** |
| 4 | `undecided` 且 `review-status` 全部 `imported` | `imported_not_decided` | 第 N 轮报告到位（i/m），尚未判定 | 执行判定；**若判定前置仍不成立（锚点失效/单 reviewer），`review-status` 已标出对应 slot 状态** |
| 5 | `blocking` 或 `blocking_unknown` 非空（跨轮聚合） | `open_blocking` | 未关闭 blocking N 条（id…）/ 另有 M 份报告不可核实 | 见 §4 的三条门禁出口 |
| 6 | `verdict == "fail"` | `verdict_fail` | 第 r 轮判 fail（绑定：当前检查 / 旧检查） | 事实：结论 fail；可修复后重查或重发审查，顺序由 AI 按当前进展决定 |
| 7 | `verdict == "unavailable"` | `verdict_unavailable` | 不可用 | 补真实审查 / 人确认异常归档 |
| 8 | `verdict == "pass"` 且 `bound_to_current` | `pass_bound` | 已通过（绑定当前检查） | —— |
| 9 | `verdict == "pass"` 且 `!bound_to_current` | `pass_unbound` | 结论来自旧检查（C1），当前检查未审查 | 事实：结论未绑定当前检查；重发 / 先重查由 AI 判断 |
| 10 | 无 `launches`，`complexity == "complex"` | `not_started` | 未开始（复杂任务归档前必须审查） | `review-launch` |
| 11 | 无 `launches`，非 complex | `none_required` | 未要求（可按需发起） | —— |

**v9 的坑 ②**：第 1 档**不看 `undecided`**——判定完成后引用报告被改/删，`review-passed` 步骤的三重摘要核对（`gates.py:697`）会拒，展示必须同步，否则又是"显示全绿、门禁必拦"。

**v9 的坑 ③**：第 3/4 档**不再自算"报告齐"**，直接用既有只读命令 `wf review-status`（`review.status_of_round`，S9）的 slot 状态（`missing/staged/imported/stale`）。它已经涵盖锚点失效（`stale`），因此不需要把"判定前置"复制进本提案——那正是 v1 被否的原因。

`verdict_invalidated` 作为**后缀标记**：仅当 `active_round is None` 时叠加显示（v9 无条件叠加，会与"新一轮正在等报告"命令冲突）。

---

## 2. 一处**机制修补**（不是展示）：证据不可核实 ≠ 没有缺陷

实测逃逸路径：`open_findings`（`review.py:184-197`）对不可读报告直接 `continue`，其 findings **不计入** `blocking`；`review-passed` 只核**结论引用**的报告；`final_gate`（`gates.py:904`）只在 `blocking` 非空时阻断。

> 于是：删掉一份带 blocking findings 的**旧轮**报告 → blocking 清零 → 归档放行，而那条 blocking 从未被 disposition 关闭。

提案要求一并修（否则本方案继承这个逃逸口，并把聚合结果称作"完整未结事实"）：

1. `open_findings` 增出 `blocking_unknown = [{slot, path, round, cause}]`（不可读报告**可能**含未处置 blocking）；
2. `final_gate` 在 `blocking_unknown` 非空时阻断归档（复用一个既有码 `WF_REVIEW_INVALID` 或 `WF_UNRESOLVED_BLOCKING`），出口三条：**重发该轮** / **`review-decide --unavailable` 留痕** / 人确认异常归档。

这条改动影响门禁，**必须单列为一个 K 级修补**并在裁定里登记（不是展示层的附带项）。

---

## 3. `cause` 与健壮性（v9 的数据基础不存在）

实测 `open_findings` 的三条分支都能确定 `cause`，但当前只写自由文本：

| 分支 | 当前 `reason` | 应给 `cause` |
|---|---|---|
| 摘要不一致 | `"report changed after import"` | `changed` |
| 文件不存在（`file_digest` 返回 None） | 同样落到 `"report changed after import"` | `missing` |
| 读取/O 错误 | `str(exc)` | `unreadable` |

同时 `records.file_digest` **只捕获 `FileNotFoundError`**，权限不足会抛出 `PermissionError` 直接冲出 `open_findings` → 一旦把它接到 `status`，排查工具本身会崩。修补：`open_findings` 内对 digest/读取统一 `except OSError` 并归为 `unreadable`。

**出口按 `cause` 分派**（并补上"原地重导"的真实前置）：

| `cause` | 能否原地恢复 | 出口 |
|---|---|---|
| `changed` | 不能（`review.py:1117` 拒绝同路径不同摘要） | 重发新一轮 |
| `missing` | 视情况：需 `check-anchor` 一致且暂存目录仍在（`review.py:1043/1097`） | 取回原始字节后重导；否则新轮 / `--unavailable` |
| `unreadable` | 同上 | 恢复可读后重导；否则新轮 / `--unavailable` |

---

## 4. 只读门禁：**不重构 `final_gate`**，改为澄清契约

v9 想"提取非步骤段、两层一次返回"，但实测 `final_gate` 内部**逐项早退**（check pass → escalated → required → blocking → …），提取后也只能给"首个非步骤阻断"；且它带 `ignore_action_id`（归档时须排除当前动作，`tasks.py:3239`），提取易丢。

**本版决定**：

1. `evaluate_cli` **保持原样**（步骤面只读预检），不改 `wf gate` 的输出结构；
2. 非步骤事实由 `unresolved` 提供（blocking / blocking_unknown / escalated 计数 / required 未核实计数——都是记录读，不复制门禁分支）；
3. **契约**（写进裁定与机制稿）：

> `wf gate --due before_archive` 是**步骤面**的只读预检；**非步骤阻断**（未关闭 blocking、escalated、required 未核实、依赖、动作）见 `unresolved` 与各自投影。
> **gate 通过 ≠ 归档必成**：归档内还有 `repo_rules`/`delete` 确认、业务提交先于门禁等既有条件。
> 需要"完整能不能归档"时**并读两者**；**不要用"试归档"探路**（`tasks.py:3233` 会先做业务提交）。

这样一来，"提交前发现阻断"的落点在 §6 的技能层（先查再收工），而不是靠改门禁结构。

---

## 5. 出口写法：事实 + 候选动作，不写命令序列

v9 把出口写成"先修复重查，再重发审查"这类固定序列，会在"fail 来自 C1、C2 检查已完成"时要求重做已完成的工作；`invalidated` 后缀也会与"新一轮正在等报告"冲突。

**改为**：出口只列**候选动作 + 各自的前置事实**（例如 "重发审查（前置：当前检查可用）"、"先重查（前置：检查不可用）"），是否执行、按什么顺序，交给 AI 按当前进展判断。唯一保留的硬约束是**不要试归档探路**（有副作用）。

第 5 档的三条门禁出口与人不在场时的合法路径（异常归档）都要列出，展示面不得比门禁面窄。

---

## 6. 技能层衔接（v9 完全漏掉，属"指导 AI"的关键）

现状：`wf-continue` 按 phase 路由，`in_progress/finish` 直接请人调用 `wf-finish`；`wf-finish` 确认后直接 `archive` —— 于是"请人收工 → 归档先提交 → 才暴露阻断"的老路径仍在。

**改动**（两行 skill 文本，不新增状态、不新增命令）：

| 技能 | 加一行 |
|---|---|
| `wf-finish` | 归档前先 `wf status`（读 `unresolved`）与 `wf gate --due before_archive`；两者都无阻断再请求人确认收工 |
| `wf-continue` | `in_progress/finish` 路由前，先看 `unresolved`；有未结事实时先处理，不要直接引导收工 |

---

## 7. ⑥ 的实质处置：文档裁定（v42 不动）

新增 `analysis/ruling-repair-vs-fixing.md`：① 不引入 `fixing` 阶段（维持 2026-11-09 人裁）；② 九轮审查证据摘要；③ 与 v42 K10/S4/S5/§7.1 差异逐条登记；④ 记录两处**有意的语义压缩**：`--short` 的 `task.check` 从 `pass/fail` 压成 `usable/reason`、`unresolved` 只报事实不报"是否可结案"；⑤ 登记 §2 的机制修补（K 级）。

---

## 8. 影响面（含 v9 漏算的项）

| 项 | 数量 |
|---|---|
| 机制修补（K 级） | 1（`open_findings` 出 `blocking_unknown` + `final_gate` 据此阻断） |
| `open_findings` 结构化 `cause`/`round` + OSError 健壮 | 1 处 |
| 提取共享函数 | 1（`check_usability`） |
| `review-status` 增 `unresolved.review` 片段 | 1 处 |
| 展示点 | 3（status/`--short`、`judgments show`、`review-status`） |
| skill 文本 | 2（`wf-finish`、`wf-continue`） |
| 协议 / `final_gate` 结构 / 模板 / position | **0** |
| 测试 | 12 条（含 1 条性质测试，§9） |
| 文档 | 1 份裁定 + 机制稿 2 段 |

---

## 9. 验收标准（12 条，含**性质测试**）

| # | 断言 | 防的失败 |
|---|---|---|
| 1 | `in_progress` + 无 check → `no_check` | 把没检查当没问题 |
| 2 | 受控回 check → `invalidated_content_changed`；execute 期改文件未重查 → `anchor_mismatch` | 两种失效混淆 |
| 3 | **无 `launches` 的复杂任务 → `not_started`**；非 complex → `none_required` | **v9 坑①：未发起审查无命中路径** |
| 4 | **判定完成后引用报告被改 → `reports_unreadable`（不是 `pass_bound`）** | **v9 坑②：显示全绿、门禁必拦** |
| 5 | 1/2 报告到达 → `awaiting_reports`；`review-status` 全 `imported` 未判 → `imported_not_decided`；**单 reviewer 轮 → `review-status` 标 `stale`/不足，不生成本提案的"可判定"暗示** | **v9 坑③：把材料到位当可判定** |
| 6 | 已判定 pass 绑定 C1 → 改码重查产生 C2 → `pass_unbound` | v8 死区回归防护 |
| 7 | 第 1 轮 blocking 未关、第 2 轮 pass 绑定 → 仍 `open_blocking` | 跨轮聚合 |
| 8 | **删除带 blocking 的旧轮报告 → `blocking_unknown` 非空，且 `archive` 被拒**（三条出口） | §2 的逃逸口 |
| 9 | 报告不可读三类 `cause` 分别构造（`changed`/`missing`/`unreadable`）；**权限不足不再让 `status` 崩溃** | v9 坑④ |
| 10 | `wf gate --due before_archive` 输出结构**未变**（仍只答步骤面）；`unresolved` 里能看到非步骤事实 | 重构 `final_gate` 的风险（v9 坑⑤） |
| 11 | `archived` → `archived` 档且不显示 blocking；`usable` 与 `gates` 判定不一致即失败（不变量）；`--short` 的 `task.check` 已派生 | 展示被当门禁 / 旧字段撒谎 |
| 12 | **性质测试**：对判据输入的全组合（`launches` 有无 × `undecided` × 可读性 × blocking × verdict × bound × complexity）穷举，断言**必命中且仅命中一档** | 下一个死区（v8 就是死区） |

---

## 10. 留给审查者的问题

1. §2 的机制修补（不可读报告 → `blocking_unknown` → 阻断归档）会**新增一种归档阻断原因**，可能让"报告被误删"从"悄悄放行"变成"必须重发一轮"。这个代价是否接受？
2. 第 5 档把 `blocking` 与 `blocking_unknown` 合在同一档：是否该分开（前者可关闭、后者只能重发/留痕）？
3. 第 4 档依赖 `review-status` 的 slot 状态；若该命令本身将来演进（例如新增状态值），本档的"全部 imported"判定是否需要版本约束？
4. §6 只改两个 skill 文本；`wf-review` 等技能是否也需要同样的"先读事实"接入？
