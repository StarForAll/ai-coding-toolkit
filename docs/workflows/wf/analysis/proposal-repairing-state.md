# 提案（v6）：⑥ 只做「结构化未结事实」两行 + 文档裁定

> 状态：**待审 v6**。前五版被五轮审查逐一否掉；本版按第五轮修正：补审查绑定、修优先级、
> 撤回不可靠的"出口见 next"、把"机器可读"落成明确 schema、区分两种"检查失效"。
> 本文件是决策提案，实现未开始。

---

## 0. 五轮审查的净结论

| 版本 | 形态 | 致命点（已核实） |
|---|---|---|
| v1 | 派生"修复中"+自称收敛 6 处判断 | 六处是六个命题；只凭记录覆盖不到内容变化；改 v42 原文破坏冻结核查 |
| v2 | 派生"不可结案原因集合" | 与退出条件自相矛盾；check 五态装不下；review 原因不全；`no_check` 矫枉过正 |
| v3 | 新增 `fixing` 阶段 | 身份矛盾（"五档"实为含 check 的五值）；漏 `PHASE_VALUES`/`legal_positions` 硬校验；pass 落 check 逼出重复 check |
| v4 | 事件写入 `repair` 标记 | 主路径清不掉（改码→C2→重审 pass 仍不清）；两失败源共用槽位；撞名 `repair.py`；无时间戳 |
| v5 | 两行只读事实 | 缺"结论是否绑定当前 check"；"轻量=未要求"会遮住已存在 blocking；"出口见 next"不成立 |

**scope 声明（修正 v5 的过度概括）**：以上五轮否掉的是**五个具体设计**，不能据此断言"机器可读的未结态不可能"。本版把事实做成结构化输出，正是要保留机器可读这条路。

---

## 1. 交付物：一个结构化事实 `unresolved` + 由它渲染的两行文本

### 1.1 事实 schema（机器可读的唯一形态）

```json
"unresolved": {
  "check": {
    "usable": false,
    "reason": "invalidated_content_changed | anchor_mismatch | not_passed | no_check | rule_changed | anchor_unavailable | structure_incomplete",
    "check_id": "20261110-…",
    "scope": "archive_gate",              // 本判定按"收工/归档门口径"（check-passed 门）
    "detail": null                         // anchor_unavailable / structure_incomplete 时放错误码或问题列表
  },
  "review": {
    "state": "open_blocking | verdict_fail | verdict_unavailable | stale_verdict | invalidated | ok | none",
    "open_blocking": [{"finding_id": "f1", "severity": "blocker"}],
    "verdict": "pass | fail | invalidated | unavailable | null",
    "verdict_check_id": "20261110-C1",
    "bound_to_current": false,             // 结论是否绑定当前 check
    "unavailable_reports": [{"slot": "slot-a", "path": "…"}]
  }
}
```

渲染文本（`wf status`、`judgments show`）**完全由该结构生成**，不再另写一套判定。

### 1.2 两行的取值优先级（把 v5 的"未要求"漏洞写死）

**审查行**（从上到下，命中即停）：

| 序 | 条件 | 显示 |
|---|---|---|
| 1 | `unavailable_reports` 非空 | `审查：N 份报告不可读（导入后被改动），需重新导入` |
| 2 | `open_blocking` 非空 | `审查：未关闭 blocking N 条（id…）` |
| 3 | `verdict == "fail"` | `审查：本轮结论 fail（第 r 轮）` |
| 4 | `verdict == "invalidated"` | `审查：既有结论已失效（实施 CLI 变更），需重发` |
| 5 | `verdict == "unavailable"` | `审查：不可用（需补真实审查或人确认异常归档）` |
| 6 | `verdict == "pass"` 且 **`bound_to_current == false`** | `审查：结论来自旧检查（C1），当前检查未审查，需重发` |
| 7 | `verdict == "pass"` 且 `bound_to_current` | `审查：已通过（绑定当前检查）` |
| 8 | 无任何 reviews，且 `complexity != "complex"` | `审查：未要求` |

**关键修正**：`未要求` **不再按复杂度直接给**——只要有 reviews 事实就按 1–7 显示。理由：`final_gate` 的 open-blocking 拦截不分复杂度（`gates.py:903`），轻量任务完全可能带着未关闭 blocking；把这类任务显示成"未要求"会直接与门禁矛盾。

**检查行**：`usable` 决定文案；`reason` 逐值对应一句人话（见 §3）。`scope` 固定为 `archive_gate`，避免"可复用"这种全称判断跨越两个口径。

---

## 2. 数据来源（都是既有函数，不复制逻辑）

| 事实 | 来源 | 说明 |
|---|---|---|
| `check.*` | 把 `gates.py:631-654`（`task.check-passed` 门的判定）**整段提取**为 `check_usability(ctx, task)`，门禁改为调它 | 行为一字不改；覆盖 无检查/未通过/规则版本变/`check.invalidated`/**锚点失配**/**锚点重算失败**/**结构复核不过** |
| `review.open_blocking` / `unavailable_reports` | `review.open_findings(ctx, task)` | 原样复用 |
| `review.verdict` / `verdict_check_id` | `reviews.result` | 已有字段 |
| `review.bound_to_current` | `result.check_id == (task.check or {}).id` | 与 `gates.py:690` 同一判据（仅比较，不复用其分支） |

**两种"检查失效"的区分**（v5 混淆处）：`invalidated_content_changed` 来自记录内事实（受控回 check 时写入 `check.invalidated`）；`anchor_mismatch` 来自**读取时现场重算**。二者的 `reason` 不同、测试分别构造。

---

## 3. 文案与"next"的关系（撤回 v5 的错误承诺）

v5 写"出口见 next"，这不成立：`next` 是**位置驱动**（`states.json` 的 `next_by_position`），不感知失败事实。例如 `in_progress/finish` 的 next 固定指向 `wf archive`，而此刻可能 check 不可复用或有未关闭 blocking。

**改为明确契约**（写进提案、裁定与机制稿）：

> `unresolved` 是**事实**；`next` 是**位置指引**；两者冲突时以**门禁返回的 code + exits** 为准。
> 典型情形：`phase=finish` + 未关闭 blocking → `next` 仍说 archive，但 archive 会返回 `WF_UNRESOLVED_BLOCKING` 并自带出口。这是既有设计（门禁自带 exits），不是需要路由的新问题。

---

## 4. 展示点与成本（给实测数字，不再二元化）

| 展示点 | 内容 | 实测成本 |
|---|---|---|
| `wf status`（完整） | `unresolved` 结构 + 两行文本 | 锚点重算 **≈40 ms**（git 调用为主）+ `open_findings` **<1 ms**（5 份小报告实测 0.1 ms） |
| `wf status --short` | 同上（两行 + `unresolved`） | 同上，单次 **<50 ms**；`--short` 的初衷是"避免整份 task.json 进上下文"，与这两行不冲突 |
| `judgments show`（收工预览） | 两行 | 同上 |

**降级约定**：报告很多时 `open_findings` 的成本随份数线性上升；若实测超出 200 ms，`--short` 可只带 `check` 行（`--short` 的 JSON 中 `unresolved.review` 置 `null` 并标 `"omitted": "cost"`），而不是让两行永远缺席。

---

## 5. ⑥ 的实质处置：文档裁定（v42 不动）

新增 `analysis/ruling-repair-vs-fixing.md`：

1. **结论**：不引入 `fixing` 阶段；维持 2026-11-09 人裁的四阶段；"未结事实"由 `unresolved` 承担；
2. **理由**：五轮审查证据（§0 表）；
3. **与 v42 的差异逐条登记**：K10（L107 枚举）、S4（L122 三态含 fail→fixing）、S5（L123 主干）、§7.1（L401 把持久 check 登记为已删除）；
4. **不写"单一布尔不可能"这类过度结论**，只记录"本仓库选定事实展示 + 门禁权威"这一取舍。

`v42` 原文一个字节不改（逐字节冻结，sha256 `d06c57e7…cadd`）。机制稿 §2.2/§9.4 各加一段指向该裁定，并写入 §3 的"事实 / next / 门禁"三者关系。

---

## 6. 明确不做

| 不做 | 对应审查 |
|---|---|
| 不新增阶段 / 不新增持久标记 / 不新增命令 | v3 a-1、v4 a-1/b-1、v4 a-6 |
| 不改 `position`（不加字段） | v2 §4.3、v4 a-5/b-5 |
| 不改 `next` | 本文 §3（改的是契约表述，不是实现） |
| 不在此提案修"错误返回 position 为空" | v4 a-4/b-4：独立缺口，单独提案 |

---

## 7. 验收标准（按第五轮要求逐个可构造）

| # | 断言 | 构造方式 | 防的失败 |
|---|---|---|---|
| 1 | `in_progress` 任务、无 check → `check.reason == "no_check"`、`usable == false`，归档仍被拦 | 新建任务直接 status | 把"没检查"当"没问题"；**限定 in_progress，避免把 plan 期噪声固化为断言** |
| 2 | 受控回 check（`task-check` 后内容变化触发失效写入）→ `reason == "invalidated_content_changed"` | 走 `finish-invalidate` 路径 | 记录内失效事实看不见 |
| 3 | execute 期改文件但不重跑 check → `reason == "anchor_mismatch"` | 改文件后直接 status | 现场失效看不见（与 #2 是不同分支） |
| 4 | 轻量任务 + 已导入 blocking 报告 → 显示 `open_blocking`，**不是"未要求"** | 轻量任务发起审查并判 fail | 轻量任务被"未要求"遮住（v5 a-2/b-1） |
| 5 | `verdict=pass` 但 `verdict_check_id != 当前 check` → `bound_to_current == false`，显示"需重发" | 审查通过后改码重跑 check | 旧结论被当成新结论（v5 a-1） |
| 6 | `verdict=invalidated` → 显示"结论已失效" | 改实施 CLI 后 status | 既不进 fixing 也不可见 |
| 7 | 归档准入与改动前**完全一致**（同一批用例结果不变） | 跑全量套件 | 展示被当门禁 |
| 8 | 任务记录与模板**无新增字段** | 检查 task.json 与模板 | 又引入需要生命周期维护的状态 |
| 9 | 5 份报告任务上 `wf status --short` 单次 < 200 ms | 计时断言 | 高频轮询退化 |

---

## 8. 风险与缓解

| 风险 | 缓解 |
|---|---|
| 提取 `check_usability` 动了门禁 | 纯提取（整段搬出），门禁侧先跑全量再改展示；不夹带语义变更 |
| 两行与 `next` 冲突仍会诱使无效调用 | §3 的契约 + 门禁自带 exits；裁定文件与机制稿同批写入 |
| `unresolved` 结构成为"第二套判定" | 它只复用门禁函数与既有投影；加一条不变量测试：`check.usable != gates` 在同一 task 上的判定结果不一致即失败 |
| 报告多时 `--short` 变慢 | §4 的降级约定 + 验收 9 的计时门槛 |

---

## 9. 留给审查者的问题

1. 优先级表把 `open_blocking` 排在 `verdict_fail` 之前：同一任务既有 fail 结论又有未关闭 blocking 时，先报哪个更有用？
2. `scope: "archive_gate"` 是否足够说明"这是收工口径，不是 review-launch 口径"？还是要另出一行 `review_launch_ok`（发起口径）？
3. §4 的降级约定（`--short` 省略 review 行）会不会让"最短视图"重新出现盲区？
4. 裁定文件里不写"单一布尔不可能"，只记取舍——是否足够挡住未来"好心加回状态机"的回归？
