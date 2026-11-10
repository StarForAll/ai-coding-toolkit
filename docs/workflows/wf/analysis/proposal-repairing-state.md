# 提案（v2）：以「不可结案原因」显式事实替代 `fixing` 阶段

> 状态：**待审 v2**。v1 被两份审查否掉了三处根基（收敛、派生充分性、文档改法），本版逐条修。
> 本文件只是决策提案，不是定稿；实现未开始。

---

## 0. v1 错在哪（先认账，避免"打补丁"）

| v1 主张 | 审查反驳 | 结论 |
|---|---|---|
| 「6 处读 `check.result` 收敛为 1 处」 | 六处是**六个不同命题**：结构完整性校验（`check.py:304`）、历史触发枚举（`gates.py:339`）、当前可用性含锚点比较（`gates.py:647`）、归档准入（`gates.py:873`）、审查发起前置（`review.py:710`）、刚写入 check 的局部事实（`tasks.py:2456`） | **撤回**。不再声称收敛，`repair_state` 只是**附加可见性事实** |
| 「只凭 check/check_history/reviews 派生」 | 最常见失效是**内容变化**（普通交付文件/spec/基线变了但记录没变）；现有实现靠重算锚点并比较（`check.py:118` + `gates.py:631`）才能发现 | **撤回**。派生必须带 `ctx` 并能重算锚点 |
| 「review fail 后新 pass check ⇒ repairing=None」 | `task-check` 不触碰 reviews；`open_findings()` 独立计算未处置 finding → 会出现"检查通过但 blocking 未关闭"，此时清除"修复中"是假状态 | **撤回**。改为由 `open_findings.blocking` 决定 |
| 「`since`/`revision` 可派生」 | `reviews.result` **没有时间戳**（`review.py:1425`）；`revision` 是保存计数器（`tasks.py:170`）不是内容版本 | **删除这两个字段** |
| 「改 v42 §7.1 那条登记」 | v42 是**逐字节冻结的外部决策记录**（仓库副本与 /tmp 原件 sha256 同为 `d06c57e7…cadd`）；且 K10/S4/S5 三处也写着 `fixing` | **改为不改原文**：新增带日期的人裁登记 + 指针 |
| 「position 只需约 3 处注入」 | 实测 `cli.py` 有 **32 处**直接 `codes.position(`，只有 **2 处**走 `_position_for` | **重写**接入方案，见 §4 |

数据勘误（v1 错、本版已改）：测试文件数实为 **73**（不是 12）；测试条数以 §7 为准（**7 条**，v1 的 §6 写 3 条是笔误）；v42 仓库文件名是 `solution-review-v42.md`（带日期名是 /tmp 侧原件）。

---

## 1. 新定义：`repairing` 不是一个状态，而是「当前不可结案的原因集合」

```
repair_state(ctx, task) -> {
  "repairing": bool,
  "reasons": [ {"kind": "check", ...} | {"kind": "review", ...} ],
  "exits": [ ... ]
}
```

`repairing = reasons 非空`。每个 reason **只引用已存在的投影**，不新增推断：

| reason.kind | 构成 | 来源（已有投影） |
|---|---|---|
| `check` | `state ∈ {no_check, not_pass, invalidated, anchor_mismatch, rule_version_mismatch}` | 把 `gates.py:631-650` 的判定**提取为函数**（行为不变），`repair_state` 复用同一实现 |
| `review` | `open_blocking[]`（未处置的 blocking finding）、`unavailable[]`（报告被改后不可用）、`verdict == unavailable` | `review.open_findings()` 原样复用 |

### 为什么这样定义能自动覆盖审查提的反例

| 审查反例 | 新定义下的结果 |
|---|---|
| 从未跑 check（a-1 反例 1） | `check.state = no_check` → `repairing = true`（`reasons` 非空），不再与门禁矛盾 |
| 内容改了、没重跑 check（a-2） | `anchor_mismatch` → `repairing = true` |
| review fail 后新 pass check、blocking 未处置（b-4 / a-3） | `open_blocking` 仍非空 → **仍为 true**，不会出现假"已修复" |
| 单份报告已导入、轮次尚未判定（a-5 边审边修） | 导入即计入 `open_findings`，blocking 未处置 → `repairing = true`（不需要 verdict 存在） |
| 审查不可用（`unavailable`） | 单独 reason，出口是"补真实审查 / 人确认异常归档" |
| 误报 finding 被 disposition 掉、未重跑 check | `open_blocking` 变空，但 `check.state` 仍 pass → `repairing = false`（正确：无需再改代码） |

### 明确不做的

- **不替换任何现有判断**（撤回 v1 的"六处收敛"与源码扫描断言）。六个点位语义不变，`repair_state` 只被"展示"与"下一步指引"消费。
- **不落盘**（仍是派生，避免第二真相）。
- **不加修复期准入规则**（拒绝扩面/改标准之类）——同类风险已由 K6 第五类与"改标准要 judgment"覆盖。
- **不改阶段枚举**（`phase` 引用 102 行、`"check"/"execute"` 字面量 61 处、`states.json` 11 条迁移、73 个测试文件含相关字面量）。

---

## 2. 数据形状（只保留可导出的字段）

```json
{
  "repairing": true,
  "reasons": [
    {"kind": "check", "state": "anchor_mismatch", "check_id": "20261110-…",
     "check_ended_at": "2026-11-10T12:00:00Z"},
    {"kind": "review", "open_blocking": [{"finding_id": "f1", "severity": "blocker"}],
     "round": 2}
  ],
  "exits": ["修复后重跑 task-check，使 check 重新可用",
            "对 blocking finding 按 K4b 关闭（非提出者复核）",
            "人确认按设计稿异常路径归档"]
}
```

**已删除**：`since`（审查侧无时间戳，无法重建；写入当前值会让派生结果随无关操作变化）、`revision`（保存计数器，不是内容版本）、`failed`（与 `open_findings` 的"未处置"语义混同）。
**保留** `check_ended_at`：`check` 记录自带 `started_at/ended_at`（`check.py` 结果写入处），属真实现有事实。

---

## 3. 退出条件（唯一）

> `repairing = false` ⇔ `check.state` 为 `ok` **且** `open_blocking` 为空 **且** 无 `unavailable` 报告。

按 §1 的构成，这等价于"当前检查可复用、且没有未关闭的阻断问题"。措辞上不再说"修复完成"——因为**检查通过不等于审查提的问题已解决**（a-3）。

---

## 4. `position` 接入（重写）

v1 说"少数生成点注入"与实测不符（32 处直接构造、仅 2 处走 `_position_for`）。本版改为**明确的两段式**：

1. **新增统一构造器** `tasks.position_for(ctx, task, **overrides)`：内部调 `codes.position(...)` 并填 `repairing`。
2. **只改任务级结果点位**（实测 18 处 `scope="task"` 构造在 `cli.py`，另有 `tasks.py` 内的任务级结果）：全部改用 `tasks.position_for`。**非任务级**结果（install / maintenance / session 等）**不带**该字段。
3. **缺省语义写死**：任务级结果**总是带** `position.repairing`（bool），非任务级**总是没有**；文档与测试各固定一条，杜绝"缺席 = 不在修"的歧义。
4. `review.py` 的 launch/context/import/decide（含 `review.py:1459` 的 fail 返回）属任务级，一并改用构造器——这是"修复中"最该出现的返回时刻。

---

## 5. `next` 指引联动（v1 缺失，b-6）

`protocol.next_for` 现在只看 挂起 > 暂停 > 位置 > 会话。接入后必须给出优先级，否则会出现"修复中 + 下一步归档"：

> 挂起 > 暂停 > **重新规划中（phase=plan）** > **修复中** > 位置 > 会话

- `phase=plan` 优先于修复中：replan 后旧 fail check 仍在，但人的决定是重新规划，此时横幅不应说"去修"（b-6 / a-6 的 replan 情形）；
- 修复中的 `next` 文案直接取 `repair_state.exits[0]`，不再另写一套。

---

## 6. `states.json` 的落点（改为正交声明）

v1 想在 `check` 迁移行加子句，但 `repairing` 为真时可处于 **plan（replan 后）/ execute（修复回做）/ check / finish（review fail 在 pass 之后）** 四种位置，写进 `check` 行会把事实登记窄（b-5）。

改为：在 `phase_model` 段落增一句——**「修复中与阶段正交：它由 check 可用性与未关闭 blocking 派生，可同时出现在 plan/execute/check/finish 任一处；阶段迁移表不因它新增边」**。迁移表仍是唯一权威，且不再被写窄。

---

## 7. 文档同步（不改 v42 原文）

| 动作 | 说明 |
|---|---|
| **新增** `analysis/ruling-repairing-vs-fixing.md` | 带日期的人裁登记：为什么选"派生事实"而非 `fixing` 阶段；逐条列出与 v42 **K10（L107）/ S4（L122）/ S5（L123）/ §7.1（L401）** 的差异与理由；文末给"若将来改回 `fixing`，本派生函数即阶段推进器"的迁移说明 |
| 机制稿 §2.2 阶段模型段 | 增一句「修复中与阶段正交」+ 指向上面那份裁定 |
| 机制稿 §9.4 | 增「`repair_state` 的构成、退出条件、三个落点（position / status+预览 / next）」 |
| v42 原文 | **一个字节都不改**（逐字节冻结的外部决策记录；仓库副本与 /tmp 原件 sha256 同为 `d06c57e7…cadd`） |

---

## 8. 影响面与工作量（实测）

| 项 | 数量 | 说明 |
|---|---|---|
| 新增 | `tasks.repair_state(ctx, task)` + `tasks.position_for(ctx, task)` | 2 个函数 |
| 提取 | `gates` 的 check 可用性判定 → 函数（行为不变） | 1 处重构 |
| 改点位 | `cli.py` 任务级 18 处 + `tasks.py` 任务级结果 + `review.py` 4 处 | 全部走 `position_for` |
| `protocol.next_for` | 加 `repairing`/`phase=plan` 优先级 | 1 处 |
| `states.json` | `phase_model` 一句 | 不加迁移边 |
| 文档 | 新增裁定 1 份 + 机制稿 2 段 | 不改 v42 |
| 测试 | **7 条**（见 §9） | —— |

---

## 9. 验收标准（7 条，每条对得上一个真实失败）

| # | 断言 | 防的失败 |
|---|---|---|
| 1 | 无 check 时 `repair_state(ctx, task).repairing is True`，`reasons[0].state == "no_check"` | v1 会把"没跑过"当"没在修" |
| 2 | 内容改动后（未重跑 check）`state == "anchor_mismatch"` 且 `repairing is True` | 最常见失效漏报 |
| 3 | review fail + 重跑 pass check + blocking 未处置 → `repairing is True` | "检查通过"被当成"问题已解决" |
| 4 | 单份报告已导入、轮次未判定、有未处置 blocking → `repairing is True` | 边审边修场景不可见 |
| 5 | blocking 全部按 K4b 关闭 且 check 可用 → `repairing is False` | 修完了还挂着 |
| 6 | `phase=plan`（replan 后）时 `next` 指向批准而非修复 | 与人的决定冲突的横幅 |
| 7 | 任务级结果都带 `position.repairing`（bool）；`install`/`maintenance` 结果不带 | "缺席"被读成"不在修" |

---

## 10. 风险与缓解

| 风险 | 缓解 |
|---|---|
| 展示层事实被误当门禁 | 归档口、审查前置、check 结构校验**一律不改**；文档与测试各固定一条"它不是门禁" |
| 两个来源（`gates` 判定 vs `repair_state`）漂移 | 提取为**同一个函数**，`gates` 与 `repair_state` 都调它 |
| 73 处相关测试受 position 变化影响 | 任务级结果多一个 bool 字段，不改既有字段；先跑全量确认 |
| 未来真要改回 `fixing` | `repair_state` 即阶段推进器：把它接到 `phase` 上，其余判断不重写 |

---

## 11. 留给审查者的问题（本轮新提，请重点质疑）

1. §1 用"不可结案原因集合"取代"是否在修复"——**这个改名是否掩盖了语义膨胀**（现在要维护 check 五种状态 + review 三种情形）？
2. §5 的优先级把"重新规划"排在"修复中"之前：若人 replan 后又想修，是否会被横幅误导？
3. §4 要求"任务级结果总带该字段"，会让错误返回体变大一档（66 处 position 中约 40 处是任务级）——是否值得？
4. §9 第 3 条依赖 `open_findings` 的 blocking 判定；若审查报告本身失效（`unavailable`）而 finding 不再可读，是否存在"越修越绿"的空档？
