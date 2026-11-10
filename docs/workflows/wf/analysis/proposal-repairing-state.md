# 提案：以「修复中」显式事实替代 `fixing` 阶段（⑥-乙）

> 状态：**待审**（不是定稿）。供外部审查用；审查结论回来后再决定是否落地。
> 关联：v42 分析稿 `solution-review-2026-11-09.md`（§4.6/§7.1 与 S5）、机制稿 §2.2 阶段模型、
> 设计稿 §1.3、`protocol/states.json`；2026-11-09 人裁（四阶段保留、`fixing` 不落盘）。

---

## 1. 事实基线（都有代码/文档位置）

### 1.1 当前落盘形态

| 事实 | 位置 |
|---|---|
| 阶段枚举 = `plan/execute/check/finish` | `protocol/states.json` 的 `phase.enum`；`protocol.py:20` |
| 阶段模型原文：「检查 fail 留在 check、修复回 execute，内容或规范变化使旧结果失效时回 check 或 execute」 | `protocol/states.json` 的 `phase_model` |
| `check` 迁移行有三个去向：pass→finish / fail→**留在 check** / 修复完成→execute | `protocol/states.json` 的 `check` 迁移 `to[]` |
| `fixing` 全库不存在 | 全仓 grep 无该枚举值 |

### 1.2 与 v42 的冲突点

| v42 位置 | 原文 | 与本仓库现状 |
|---|---|---|
| K10（L107） | 「阶段只有 `plan/execute/fixing/finish`」 | 枚举不同 |
| S5（L123） | 「`plan → execute → fixing → finish`；**内容变化或 review 判 fail 进入 `fixing`**，由下一次 `task-check` 退出」 | 当前 review fail 不改变 phase |
| §7.1（L401） | 「持久阶段 `check`（v10）→ `fixing` 阶段 + revision（K3a）｜**不漏**：`check` 是动作不是状态，产物是 revision」 | **把当前做法登记为"已删除机制"** |

即：**不是文档滞后，而是两份权威对同一事实的相反登记**（人裁 vs v42 §7.1）。

### 1.3 现在怎么判断"正在修"——6 处分散推断（全部实测）

| 位置 | 代码 | 它在读什么 |
|---|---|---|
| `check.py:304` | `if check.get("result") != "pass"` | check 记录自身完整性 |
| `gates.py:339` | `if result.get("verdict") == "fail"` | 把 review fail 记成"复盘触发事实" |
| `gates.py:647` | `if current_check.get("result") != "pass" or not anchor` | 收工前核 check 可用（含 `invalidated`） |
| `gates.py:873` | `if check.get("result") != "pass"` | 归档口拦截 |
| `review.py:710` | `if check.get("result") != "pass"` | 发起审查前要求 check pass |
| `tasks.py:2456` | `if check["result"] == "pass"` | 写 `task.check-passed` 回执 |

**六个点各自解释"fail 意味着什么"**。这就是本任务的重复缺陷类型（同一事实多处推断 → 口径漂移）。

---

## 2. 问题陈述

采用 `fixing` 阶段能带来四件事：

1. **可观测**：状态一眼可见（`phase == fixing`），预览/`status` 不必推断；
2. **单一字段判断**：门禁只查 `phase`，不再各自读 `check.result`；
3. **文档一致**：与 v42 的 K10/S4/S5 对齐，审查不再重复报这条漂移；
4. **迁移表有落点**：`states.json` 可以声明"修复期允许/禁止哪些动作"。

不采用它的理由：枚举从 4 变 5 会牵动 **`phase` 引用 102 行**、`"check"/"execute"` 字面量 **61 处**、`states.json` **11 条迁移**、12 个测试文件；且**线性枚举与"多 reviewer 陆续交报告 + 你已在按首批 finding 修"并发场景天然冲突**（一个 `phase` 装不下"评审进行中"与"修复中"两件事）。

**本提案的目标：把上面 1–4 全部拿到，但不动枚举、不推翻人裁。**

---

## 3. 方案：`repairing` 作为显式派生事实

### 3.1 定义

> **修复中（repairing）**＝最近一次检查判 fail（可含被判失效），**或**最近一轮审查结论为 fail，
> 且此后尚未产生一次新的通过结果。

两个触发源都算：v42 说"内容变化或 review 判 fail 进入 fixing"——两者目的相同（有待修的失败）。

### 3.2 数据形状（派生，不落盘）

```json
"repairing": {
  "since": "<触发那一刻的时间>",
  "source": "check | review",
  "check_id": "<失败/失效的 check id>",
  "review_round": 2,          // source=review 时
  "revision": 7,              // 触发时的任务 revision
  "failed": [{"verification_id": "v1"}, {"finding_id": "f1"}],   // 已知失败项（可空）
  "exits": ["修复后重跑 task-check 产生新的通过结果",
            "按设计稿 §5.6 异常归档（人确认）"]
}
```

**为什么派生而不落盘**（这是本方案最关键的选择）：

- 落盘会形成**第二个真相**：`check.result` 与 `repairing` 可能不一致（谁先写、谁后改），而本任务已经反复踩"同一事实两处存"的坑（抽样死锁、回执账本都是这一类）；
- 派生保证"删掉再算必须等值"（K8 可重建）：`repairing` 完全由 `check` / `check_history` / `reviews` 导出，而这三者都在 committed 记录里；
- 若将来真的要落盘成 `phase=fixing`，**派生函数可以直接变成阶段推进器**，不需要重写判断逻辑。

### 3.3 单一实现（唯一判定处）

```python
# tasks.py
def repair_state(task):
    """修复中的显式事实；全库只在这里判定。返回 None 或 3.2 形状的 dict。"""
```

所有展示与门禁都调它，不再各写 `check.get("result") != "pass"`。

### 3.4 落点（三处，都是"读一处"）

| 落点 | 做法 | 为什么需要 |
|---|---|---|
| **结果对象 `position`** | `codes.position(..., repairing=None)`；`cli._position_for()` 与 `tasks.py` 的 position 生成点注入 | 66 处 `position(...)` 调用**不逐个改**，只在少数生成点注入；任何驱动方（含未来的多 agent 编排器）读 `position.repairing` 就知道"现在该修" |
| **`wf status` 与收工预览** | 各显示一行：`[修复中] check <id> 判 fail（第 2 轮审查 fail）；出口：修复后重跑 task-check / 人确认异常归档` | 人只看一屏；这是 `fixing` 的可观测性来源 |
| **`states.json` 迁移表** | 在 `check` 迁移行补子句：`from: {phase: check, condition: "结果 fail 或结果被判定失效"} → to: {phase: check, repairing: true}`；并写明出口 | 让"修复中"作为**迁移事实**有权威落点（这是 `fixing` 唯一的硬优势，不能不补） |

### 3.5 退出与边界（必须写死，避免又一处推断）

| 情形 | `repairing` |
|---|---|
| 从未跑过 check | `None` |
| 最新 check = pass，且无 fail 审查结论 | `None` |
| 最新 check = fail | **有**（`source=check`） |
| 最新 check 被后续变化判失效（`invalidated`） | **有**（`source=check`） |
| 最新一轮 review 结论 = fail | **有**（`source=review`） |
| review fail 后又跑了一次 pass check | `None`（已有新通过结果） |
| 任务暂停/挂起 | **仍为有**（暂停不消除失败事实），`status` 显示"暂停（修复中）" |
| 已归档（正常/异常） | `None` |
| 已重新规划（replan） | 由新 check 结果决定；replan 本身不清除失败事实 |

### 3.6 文档同批改（否则每轮审查重复报）

| 文档 | 改动 |
|---|---|
| 机制稿 §2.2 阶段模型段 | 增一句：「`check` 是阶段值；**修复中**是由 check 结果与审查结论派生的显式事实（不落盘），见 §9.4」 |
| 机制稿 §9.4 | 增一段：`repairing` 的派生依据、退出条件、三个落点 |
| **v42 分析稿 §7.1（L401）** | 把「持久阶段 `check`」从"已删除机制"改为**人裁口径**：`check` 是阶段值、`fixing` 不落盘、修复中由派生事实表达。**这一步必须做**，否则 v42 会把正确实现登记为"回归" |

---

## 4. 明确不做（避免僵硬）

| 不做 | 理由 |
|---|---|
| **不加"修复期准入规则"**（如修复期禁止扩面/禁止改标准） | 那层是 v42 反复警告的机械僵硬；同类风险已由 K6 第五类（扩面须人确认）与"改标准要 judgment"覆盖。`repairing` 已是显式事实，将来要加规则不必再改数据模型 |
| **不落盘、不改枚举** | 见 3.2；保持单一真相与 K8 可重建 |
| **不用 `repairing` 阻断任何动作** | 它的用途是**可见与可驱动**，不是新的门禁。归档口仍按现有 `check.result != pass` 拦（`gates.py:873` 不动） |

---

## 5. 兼容性论证（未来多 agent 审查）

未来形态大概率是**并行的、交错的**：A 交报告 → C 还没交 → 你已按 A 的 finding 修 → B 又提新 finding。

| 需要 | 线性 `fixing` | 本方案（正交标记） |
|---|---|---|
| 同时"评审进行中 + 修复中" | 装不下（`phase` 只能一个值） | 装得下：`reviews` 记评审，`repairing` 记修复 |
| 再加 `awaiting-review` / `disputed` 等 | 枚举膨胀，11 条迁移逐条改 | 加标记或 `reviews` 字段即可 |
| 驱动方读"该谁动" | 读 `phase` | 读 `position.repairing`（同样一处） |
| 每轮审查绑定哪次 check | 无关（靠 anchor） | 无关（靠 anchor） |

**真正的扩展性接缝不在阶段枚举**，而在：`anchor{check_id, check_anchor}` + `revision`（评审绑定）、`rounds[].round_ids` + `attempts[].outcome`（历史可重建）、`launch.slots[]`（多 reviewer 身份）、dispositions + 跨轮 proposers（K4b）。这些都已存在。

---

## 6. 影响面与工作量（实测）

| 项 | 数量 | 说明 |
|---|---|---|
| 新增判定函数 | 1 个 | `tasks.repair_state` |
| 收敛分散推断 | 6 处 → 1 处 | 见 1.3；其中 `gates.py:873` 的**拦截行为不变**，只把"为什么拦"的说明改为读同一事实 |
| `codes.position` | 加 1 个可选参数 | 66 处调用点不用逐个改 |
| `position` 注入点 | `cli._position_for` + `tasks.py` 少数生成点 | 约 3 处 |
| `states.json` | 1 处子句 | `check` 迁移行 |
| 文档 | 机制稿 2 段 + v42 §7.1 1 条改口径 | 见 3.6 |
| 测试 | 新增 3 条 | 见 §7 |

---

## 7. 验收标准（每条都能回答"它防的失败真实存在"）

| 测试 | 防的失败 |
|---|---|
| check fail 后 `wf status` 与预览出现「修复中」 | 之前人看不出"在修"，只能靠猜 |
| 同一状态下 `position.repairing.source == "check"` | 驱动方要自己推断 |
| review fail（无新 check）也进「修复中」，`source == "review"` | v42 说 review fail 进入 fixing；当前完全不可见 |
| 跑出一次 pass check 后 `repairing is None` | 修完了还挂着"修复中"（假状态） |
| 暂停期间仍显示「暂停（修复中）」 | 暂停把失败事实抹掉（丢事实） |
| 归档后 `repairing is None` | 归档后仍标"在修" |
| 归档口仍拒非 pass check（行为不变） | 有人把"可见事实"误当"门禁替代" |

---

## 8. 风险与缓解

| 风险 | 缓解 |
|---|---|
| 派生函数与既有 6 处判断出现口径差 | 6 处全部改为调它；新增一条断言"任一处不得再直接比较 check.result"（可用源码扫描，但只扫**函数级**、不扫排版——避免重演"锚排版"的假红） |
| `repairing` 被误用为门禁 | 文档与测试各写一条"它不是门禁"；归档口逻辑不动 |
| 未来真的要改成 `fixing` | 派生函数即阶段推进器，改枚举时把它接到 `phase` 上即可，判断逻辑不重写 |
| 与 v42 §7.1 的对立没销账 | 3.6 要求同批改 v42；不销账就每次审查重报 |

---

## 9. 留给审查者的问题（请重点质疑）

1. **`review fail` 也算"修复中"是否过头？** 有些 fail 结论可能只需改判断、不需改代码；把它标"修复中"会不会误导。
2. **"新的通过结果"作为唯一退出条件是否足够？** 例如人工核验结案（`verify resolve`）后在没重跑 check 的情况下应否退出。
3. **派生 vs 落盘**：本条选择了派生（单一真相）；若审查方认为"可观测性必须以持久字段呈现"，请给出如何避免第二真相。
4. **不加入准规则**是否会在多 agent 场景下失控（多个 agent 同时改）——注意 K2 单写者已经排除并发写。
5. **`position.repairing` 会让结果对象变大**：66 处调用点中绝大多数是错误结果，是否需要在"只在修复中才带该字段"（当前方案）与"始终带 null"之间选择。
