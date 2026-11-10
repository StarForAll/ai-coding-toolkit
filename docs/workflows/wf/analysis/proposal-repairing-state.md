# 提案（v4）：不做阶段、不做派生——用「事件写入的修复标记」

> 状态：**待审 v4**。前三版被三轮审查否掉，本版换掉方案形态本身，并把"选哪个模型"讲清。
> 本文件是决策提案，实现未开始。

---

## 0. 三轮审查的净结论（决定了 v4 的形态）

| 轮次 | 被否的点 | 教训 |
|---|---|---|
| v1 | 派生"修复中"自称能收敛 6 处判断；只凭任务记录派生覆盖不到内容变化；改 v42 原文破坏冻结核查 | 派生要复制门禁 |
| v2 | 派生定义与退出条件自相矛盾（`--unavailable` 无报告）；check 五态装不下（锚点重算失败/结构复核）；review 原因不全（材料缺口 fail、审查未绑定当前 check）；`no_check` 矫枉过正；误报 disposition 事实写错 | 派生态持续不完备 |
| v3 | "五档"实为含 `check` 的五值、与"v42 原样"自相矛盾；recheck 与验收 2 互斥；漏 `PHASE_VALUES`/`legal_positions` 两个**加载即崩**的硬校验；S5 的"内容变化→fixing"未实现；check fail 的错误返回仍无 position；把"锚点失配"当 fail 混淆输入失效与缺陷；材料缺口 fail 进 fixing 会逼出重复 check+重审；不迁移在途任务造成同一事实两种表示 | 改状态机把 AI 推向重复验证 |

**共同结论：无论是"派生事实"还是"新增阶段"，都在把 AI 推向"为了满足状态而多做一遍"**——这与本轮的硬要求（指导 AI 运行、不以复杂逻辑限定 AI）相反。

---

## 1. v4 方案：四阶段不动 + 一个"事件写入"的修复标记

| 维度 | 做法 |
|---|---|
| 阶段枚举 | **保持 `plan/execute/check/finish`**（与 2026-11-09 人裁一致；`protocol.py:20 PHASE_VALUES`、`legal_positions`、迁移表**全部不动**） |
| 新增 | `task.repair`：**由事件写入**的一小段事实（不是派生、不是阶段值） |
| 门禁 | **一律不改**：归档仍要求 `phase=finish` 且 check/review 门照旧；标记存在与否不改变任何准入 |
| 用途 | 只回答一个问题：**"最近一次失败是什么、该做什么才能继续"**，给 `wf status`、收工预览、以及命令返回的 `position.repair` |

### 1.1 写入与清除（生命周期写死，单一写点）

| 事件 | 写点（已知道结果的那段代码） | 动作 |
|---|---|---|
| `task-check` 产生 **fail** 结果 | check 写入路径 | 写 `repair = {kind: "check_failed", check_id, at, exit}` |
| `task-check` 产生 **pass** 结果 | 同上 | **清除** `repair`（若 `kind == "check_failed"`） |
| `review-decide` 判 **fail**（含材料缺口导致的 fail） | decide 写入路径 | 写 `repair = {kind: "review_failed", round, check_id, at, exit}` |
| 同一 check 上**重审通过** | 同上 | **清除** `repair`（若 `kind == "review_failed"` 且 `check_id` 相同） |
| `review` 结论被 **invalidated**（实施 CLI 变更） | launch 路径（`review.py:767` 已有该写点） | **不写** `repair`；只写一行提示"既有结论已失效，需重发审查"（**输入失效 ≠ 交付缺陷**，见 §4） |
| 锚点失配/输入不成立（`WF_REVIEW_INVALID` 且未产生 verdict） | —— | **不写** `repair`（同上） |

**关键：清除不要求重跑 check。** 材料缺口型 fail 的退出是"补齐材料 → 在同一 check 上重审通过"，不需要新 `check_id`，也不会触发"审查绑定当前 check"的连锁重审（这正是 v3 被否的 a-2）。

### 1.2 与"派生"的区别（为什么这次不会自相矛盾）

- 标记**只在事件发生的那一刻写**，不重算 → 不存在"同一记录两种判定"（v2 的 A1）；
- 它**不声称**表达"能否结案"→ 不会被拿来和 `final_gate` 的条件比完备性（v2 的 B2）；
- 它**不复制** check 的五态/门禁分支 → 不会漏"锚点重算失败""结构复核"（v2 的 A5）；
- 它是**当前态**（不是历史事实），因此可以安全地为存量任务补写（§5）。

---

## 2. 需要动的地方（清单含"漏了就崩"的项，虽然本版不动它们）

> 本版**不碰**协议：`protocol.py:20 PHASE_VALUES`、`protocol.py:88` 的枚举比对、
> `protocol.py:104-113` 的 `legal_positions` 白名单、`states.json` 的迁移表与 `next_by_position` **全部不变**。
> （v3 漏掉的这两处硬校验会让加载直接 `ProtocolError`；v4 因为不动枚举，风险为零。）

| 类别 | 位置 | 改动 |
|---|---|---|
| 写点 | `tasks.py` 的 check 写入（fail/pass 两分支） | 写/清 `repair` |
| 写点 | `review.py` decide 的 fail/pass 两分支 | 写/清 `repair` |
| 清点 | `review.py:767`（invalidated） | 只写提示，不写 repair |
| 结果填充 | `cli.py:2628-2637` 的错误转结果 | **任务级命令的错误返回补 `position`**（当前为空）；这是 v3 的 a-4 缺口，本版正面解决 |
| 展示 | `wf status`、`judgments show`（收工预览） | 各加一行 `[修复中] …` 或"无" |
| 命令 | 新增 `wf repair show`（只读）/ `wf repair sync`（为存量任务补写，一次性、幂等） | 见 §5 |
| 测试 | 见 §6 | —— |

---

## 3. 为什么不选"加 `fixing` 阶段"（v3 被否的三条硬理由）

1. **方案身份无法自洽**：v42 K10 的枚举 `plan/execute/fixing/finish` **不含 `check`**，而现有实现与 `protocol.py` 硬校验都把 `check` 当正式阶段值。要么删 `check`（迁移表重排 + `in_progress/check` 的 next + 存量记录兼容 + 一批行为测试），要么承认是"第三种模型"——v3 两头占，因此被否。
2. **正常完成路径无闭环**：pass 之后是 `check` 还是 `finish`，v3 两处写反；若落 `check`，通往 finish 的唯一出口是**再跑一次同样的 check**（v38 元规则明确要砍的机械绕弯）。
3. **把 AI 推向重复验证**：材料缺口型 fail 进 fixing 后，退出需重跑 check → 新 `check_id` → 审查绑定失配 → 再重审一遍。这条是"复杂逻辑限定 AI"的典型。

**若将来仍要引入 `fixing`**：只需把 §1 的写点接到 `phase` 上，标记的生命周期即阶段迁移器；本方案不挡这条路。

---

## 4. 边界：哪些"失败"不进修复标记

| 情形 | 为什么不进 |
|---|---|
| 报告锚点失配 / 输入不成立（`WF_REVIEW_INVALID`，未产生 verdict） | 旧报告不适用只证明**需要重新审查**，不证明代码要返修 |
| `verdict = invalidated`（实施 CLI 变更，`review.py:767`） | 同上；它是输入失效。**但必须可见**：单独一行"既有审查结论已失效（实施 CLI 变更），需重发审查" |
| `verdict = unavailable` | 出口是"补真实审查 / 人确认异常归档"，不是返修 |
| 从未跑 check / 新任务 | 正确信号是"该做工作、该检查"，不是"该修"（v2 的 B1） |
| 已归档（含异常归档） | 终态优先；`status=archived` 时标记不展示 |

---

## 5. 存量任务（正面回答 v3 被否的 b-6 / a-6）

**做一次性幂等补写**，而不是"让两套表示长期并存"：

- `wf repair sync`：扫描所有 `in_progress` 任务；若最新 check 结果 fail 或最新 review 结论 fail，且无 `repair` 标记 → 补写（`at` 取记录的 `check.ended_at` / 审查结论已有时间；**没有时间的就留空并标 `at_unknown`，不编造**）。
- 幂等：已有标记不动；已通过的不写。
- 不改历史事实：`repair` 是当前态，不写入 `check_history`、不改既有 phase/result。
- 运行时机：升级后由人执行一次（或 `wf status` 首次运行时提示"建议执行 repair sync"）。

---

## 6. 验收标准（每条对得上一个真实失败）

| # | 断言 | 防的失败 |
|---|---|---|
| 1 | `task-check` fail → 任务记录出现 `repair.kind == "check_failed"`，**且该命令的错误返回里 `position.repair` 非空** | check fail 后无状态（v3 的 a-4） |
| 2 | 随后 `task-check` pass → `repair` 被清除 | 修完还挂着 |
| 3 | `review-decide` 判 fail（**材料缺口型、无 blocking finding**）→ `repair.kind == "review_failed"` | 审查失败不可见（v2 的 A6） |
| 4 | 补齐材料、**同一 check** 上重审通过 → `repair` 清除，且 `check_id` 未变 | 被迫重跑 check 的重复验证（v3 的 a-2） |
| 5 | `verdict=invalidated` / 锚点失配 → **不写** `repair`，但 status 有一行"结论失效，需重发审查" | 输入失效被当返修（v3 的 a-3） |
| 6 | 存在 `repair` 时归档仍被既有门禁按原规则拦（标记不参与准入） | 标记被误当许可 |
| 7 | 新任务（从未 check）无 `repair` 标记 | 新任务恒"修复中"（v2 的 B1） |
| 8 | `wf repair sync` 幂等：跑两次标记不变 | 补写制造重复/漂移 |
| 9 | 协议层零改动：`protocol.py` 与 `states.json` 未变，加载校验仍通过 | 撞 `PHASE_VALUES`/`legal_positions` 硬校验（v3 的 a-5/b-3） |

---

## 7. 风险与缓解

| 风险 | 缓解 |
|---|---|
| 标记与 `check` 记录不一致（第二真相） | 写点只有两处（check/review 的写入路径），清除也在这两处；加一条不变量测试：**存在 `repair=check_failed` 而当前 check 为 pass ⇒ 判实现错误**（暴露漂移，不静默） |
| 与 v42 K10/S4/S5 的差异未销账 | 新增裁定文件 `analysis/ruling-repair-marker.md`：说明"不采用 `fixing` 阶段、改用事件标记"的理由（三轮审查证据）；**v42 原文一字不改**（逐字节冻结） |
| 标记被当成门禁 | 归档/审查前置/check 结构校验一律不改；§6 第 6 条固化 |
| 体积/成本 | 只在任务级结果上带一个可选字段；错误返回补 position 是一次性通用改进（也让所有任务级错误更有用） |

---

## 8. 留给审查者的问题

1. `repair` 与既有 `check.result` / `reviews.result` 毕竟**同源**：单写点能否真正避免漂移？是否需要"读时校验 + 不一致即报错"而不只是测试覆盖？
2. §5 的 `at_unknown`（历史记录没有时间戳时留空）会不会让审计缺一环？是否接受"不编造时间"这个取舍？
3. 材料缺口型 fail 在同一 check 上重审通过即可清标记——**是否应该同时要求补的材料写入任务记录**（否则人无法复核"补了什么"）？
4. §4 把 `invalidated` 排除在标记外，只给一行提示：是否足够？它同样会让复杂任务"被拦但看不见"（只是改为看见了提示）。
