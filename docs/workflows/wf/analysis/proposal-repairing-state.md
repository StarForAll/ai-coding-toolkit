# 提案（v8）：⑥ 只做「结构化未结事实」+ 只读门禁对齐 + 文档裁定

> 状态：**待审 v8**（第七轮修正）。前七版形态均被否；本版补：`gate` 查询的口径补齐、
> 优先级改为"当前轮优先"、报告不可读的真实短路径、撤回按份数删信息、撤回挂载面扩张、档数更正。
> 本文件是决策提案，实现未开始。

---

## 0. 七轮审查的净结论

| 版本 | 形态 | 致命点 |
|---|---|---|
| v1/v2 | 派生事实（"修复中"/"原因集合"） | 派生必须复制门禁；定义与退出条件互相矛盾；五态装不下 |
| v3 | 新增 `fixing` 阶段 | 身份矛盾；漏 `PHASE_VALUES`/`legal_positions`；pass→check 逼出重复 check |
| v4 | 事件写入 `repair` 标记 | 主路径清不掉；两失败源共用槽位；撞名 `repair.py`；无时间戳 |
| v5 | 两行只读事实 | 缺结论绑定；轻量任务"未要求"遮住 blocking；"出口见 next"不成立 |
| v6 | 结构化 `unresolved` | 缺"复杂从未审查"行；报告不可读出口执行不通；用"试归档"兜底有副作用；`--short` 旧字段撒谎 |
| v7 | 12 档优先级 + `gate` 契约 | **`wf gate --due before_archive` 只答步骤面，漏掉 blocking/escalated/未核实**；优先级把"旧结论"排在"当前轮进度"之前；`>8 份`就删信息缺乏依据；挂载面扩到 49 个构造点 |

**scope**：否掉的是七个具体设计，不断言"机器可读的未结态不可能"。

---

## 1. 交付物：结构化事实 `unresolved`

### 1.1 挂载点（**撤回 v7 的扩张**，只 4 处）

| 挂载点 | 说明 |
|---|---|
| `wf status`（含 `--short`） | `facts.unresolved` |
| `wf gate --due before_archive` | `facts.unresolved`（与只读门禁同一份计算） |
| `judgments show`（收工预览） | 两行文本（由同一结构渲染） |
| —— | **其余任务级命令不挂**。v7 写"任何返回任务 position 的结果都挂"会让 ~49 个构造点每次成功返回都付锚点重算（≈40 ms）与报告重解析，没有依据 |

**已知死角（如实声明）**：`task-check` 失败时抛 `TaskError`，走通用 except 层（`cli.py:2638`），**不携带 `unresolved`**。修它需要把 position/事实沿异常传或在命令层包装，属独立缺口（另案）。此处的替代路径是 `wf status --short`（<50 ms）。

### 1.2 schema

```json
"unresolved": {
  "check": {"usable": false,
            "reason": "archived|no_check|not_passed|invalidated_content_changed|anchor_mismatch|rule_changed|anchor_unavailable|structure_incomplete",
            "check_id": "A", "scope": "archive_gate", "detail": null},
  "review": {"state": "...11 值...", "round": 2, "launched": 2, "imported": 1, "required": 2,
             "open_blocking": [], "verdict": "pass|fail|invalidated|unavailable|null",
             "verdict_round": 1, "verdict_check_id": "A", "bound_to_current": true,
             "unreadable": [{"slot": "slot-a", "path": "…", "cause": "changed|missing|unreadable", "round": 2}]}
}
```

### 1.3 取值优先级（**11 档，命中即停；"当前轮"优先于"旧结论"**）

> "当前轮" = `reviews.launches` 中最大的 `round`；"报告齐" = 该轮已导入 slot 数 ≥ 该轮声明 slot 数。

| # | 条件 | `state` | 显示 | 出口 |
|---|---|---|---|---|
| 0 | `status == "archived"` | `archived` | 已归档，不再评估 | —— |
| 1 | 当前轮**未判定**且**报告未齐** | `awaiting_reports` | 第 N 轮已发起，报告 i/m | 等报告 / `review-status`（**不要**现在 decide，人数不齐会被拒） |
| 2 | 当前轮**未判定**且**报告齐** | `imported_not_decided` | 第 N 轮报告齐（i/m），尚未判定 | `review-decide` |
| 3 | 当前轮**引用**的报告不可读 | `reports_unreadable` | 第 N 轮 M 份报告不可读（cause） | 见 §3（cause 决定能否原地重导） |
| 4 | 当前轮 `open_blocking` 非空 | `open_blocking` | 未关闭 blocking N 条（id） | 按 K4b 由非提出者复核关闭 |
| 5 | 当前轮 `verdict == "fail"` | `verdict_fail` | 第 N 轮判 fail | 先修复/重查（见检查行），再重发审查 |
| 6 | 当前轮 `verdict == "unavailable"` | `verdict_unavailable` | 不可用 | 补真实审查 / 人确认异常归档 |
| 7 | 当前轮 `verdict == "pass"` 且 `bound_to_current` | `pass_bound` | 已通过（绑定当前检查） | —— |
| 8 | 无当前轮，`verdict == "invalidated"` | `invalidated` | 既有结论已失效（实施 CLI 变更） | 重发审查 |
| 9 | 无当前轮，`verdict == "pass"` 但 `bound_to_current == false` | `pass_unbound` | 结论来自旧检查（C1），当前检查未审查 | 检查可用→重发审查；不可用→先修复重查 |
| 10 | 无任何 reviews，`complexity == "complex"` | `not_started` | 未开始（复杂任务归档前必须审查） | `review-launch` |
| 11 | 无任何 reviews，非 complex | `none_required` | 未要求 | —— |

**"当前轮未判定"的判据写死**（v7 未定）：`result` 为空，**或** `max(imported.round, launched.round) > result.round`。
第二条覆盖"decide 判 invalid 不写结论、`reviews.result` 滞留上一轮"的情形（`review.py:1350`）——否则会误显示"已通过"。

---

## 2. 数据来源（既有函数，不复制逻辑）

| 事实 | 来源 |
|---|---|
| `check.*` | `gates.py:631-654` 整段提取为 `check_usability(ctx, task)`，门禁改调它（行为不变） |
| `review.open_blocking` / `unreadable` | `review.open_findings(ctx, task)`（`unreadable` 带 `cause`） |
| 轮次进度 | `reviews.launches` / `reviews.imported` / `reviews.result` |
| `bound_to_current` | `result.check_id == (check or {}).id` |

两种"检查失效"分开：`invalidated_content_changed`（记录内事实）与 `anchor_mismatch`（现场重算）。

---

## 3. 报告不可读：按 `cause` 给真实短路径（v7 一刀切过严）

| `cause` | 能否原地恢复 | 出口 |
|---|---|---|
| `changed` | **不能**（`review.py:1117` 拒绝同路径不同摘要） | 重发**新一轮**（新轮次新路径） |
| `missing` | **能**：`existing_digest` 为空时导入放行重写（`review.py:1123-1125`） | 取回原始字节后**原地重导**；拿不到则 `--unavailable` |
| `unreadable` | **能**（同 missing，只要摘要未变） | 恢复可读后原地重导；仍不可读则 `--unavailable` |

**范围限定**：第 3 档只看**当前轮引用的报告**（与 `gates.py:690` 同口径）。旧轮报告被改不改变 `state`，只留 `unreadable[].round` 痕迹。

---

## 4. 只读门禁查询：口径必须补齐（v7 的"权威答案"不成立）

实测：`wf gate --due before_archive` → `evaluate_cli`（`gates.py:802`）只调 `evaluate(...)`，即**步骤面**（10 步）；而 `final_gate`（`gates.py:863`）在步骤之外**追加**：未关闭 blocking（轻量任务步骤直接跳过这条）、escalated 待答、required 未核实、复杂分级人确认、依赖未满足、debug 倍数未裁、暂停/挂起/动作未完成。

推演 v7 举的例子：**轻量任务 + phase=finish + 有未关闭 blocking** → `wf gate` 返回 `WF_OK` → 若 AI 据此归档，`tasks.py:3233` 会**先做业务提交**，`final_gate` 才拦。契约把 AI 送回了它要避免的副作用路径。

**修法（不新增命令）**：`evaluate_cli` 在 `due == "before_archive"` 且步骤面无缺项时，**只读地**追加 `final_gate` 的非步骤条件（`final_gate` 经核实**纯只读**：不 save、不 commit、不写 receipt），把它的 `(code, facts)` 一并返回。于是该命令成为归档门禁的只读等价物。

**契约（写进裁定与机制稿）**：

> `unresolved` 是事实；`next` 是位置指引（不感知失败事实）；**"能不能归档"的权威答案是 `wf gate --due before_archive`（含非步骤条件）**；三者冲突时以门禁返回的 code + exits 为准；**不要用"试归档"探路**（会先产生业务提交）。

文档同步清单随之增加一项：`gate` 命令在 `before_archive` 下的语义变化（从"只答步骤面"扩为"步骤面 + 非步骤条件"）。

---

## 5. 成本（实测；**撤回按份数删信息**）

| 点 | 成本 |
|---|---|
| `wf status` / `--short` / `judgments show` / `gate --due before_archive` | 锚点重算 **≈40 ms**（git 为主）+ `open_findings` **<1 ms**（5 份小报告实测 0.1 ms）→ 单次 **<50 ms** |

v7 的"`>8` 份报告就省略 `unresolved.review`"**删除**：按每轮 2 份，第五轮就会触发，而这些报告可能很小；文档自己的实测也没有证明第九份起值得牺牲信息。**两行永远都在**，不设 `omitted` 字段（v7 引入的 `omitted: "cost"` 一并删除）。
若将来报告体量确实成为瓶颈，按"总字节阈值 + 实测数据"另立提案，而不是按历史长度删信息。

---

## 6. `--short` 的旧字段（沿用 v7 结论）

`--short` 现有 `"check": task.check.result`（`cli.py:726`）在锚点失配时仍输出 `"pass"`，与新事实并存即撒谎。
**改为从 `unresolved.check` 派生**（`usable ? "usable" : reason`），不保留旧字段；属该字段的语义变更，写进裁定。

---

## 7. ⑥ 的实质处置：文档裁定（v42 不动）

新增 `analysis/ruling-repair-vs-fixing.md`：① 不引入 `fixing` 阶段，维持 2026-11-09 人裁；② 七轮审查证据摘要（§0）；③ 与 v42 K10（L107）/S4（L122）/S5（L123）/§7.1（L401）差异逐条登记；④ 只记录取舍，不写"单一布尔不可能"。
机制稿 §2.2 / §9.4 加段：事实展示、`next` 定位、**只读门禁查询（含 before_archive 语义变化）**三者的边界。
v42 原文一字不改（sha256 `d06c57e7…cadd`）。

---

## 8. 影响面（v7 删掉的小节，恢复）

| 项 | 数量 |
|---|---|
| 提取共享函数 | 1（`check_usability`） |
| `evaluate_cli` 追加只读条件 | 1 处 |
| 展示点 | 3（status/`--short`、`judgments show`、`gate`） |
| 协议 / 门禁判定 / 模板 / position | **0** |
| 测试 | 10 条（§9） |
| 文档 | 1 份裁定 + 机制稿 2 段（含 `gate` 语义变化） |

---

## 9. 验收标准（10 条）

| # | 断言 | 防的失败 |
|---|---|---|
| 1 | `in_progress` + 无 check → `check.reason == "no_check"` | 把没检查当没问题 |
| 2 | 受控回 check → `invalidated_content_changed`；execute 期改文件未重查 → `anchor_mismatch`（两条分开构造） | 两种失效混淆 |
| 3 | 轻量任务 + 已导入 blocking → `state == "open_blocking"` | v5 "未要求"遮住 blocking |
| 4 | 复杂任务 + 无 reviews → `state == "not_started"` | v6 无行命中 |
| 5 | **1/2 报告到达 → `awaiting_reports`；2/2 到达未判 → `imported_not_decided`；且 decide 判 invalid 后仍为 `imported_not_decided`**（轮次比较） | v7 会提示注定失败的 decide；invalid 后误显示"已通过" |
| 6 | 当前轮报告齐并已判 pass（绑定当前 check）→ `pass_bound`；随后改码重查（新 check）→ `state` 退回 `pass_unbound` | 旧结论被当新结论 |
| 7 | `missing` 情况恢复文件后**原地重导成功**（不要求新轮）；`changed` 情况下原地重导被拒 | v7 一刀切强制新轮 |
| 8 | **轻量任务 + blocking：`wf gate --due before_archive` 返回 `WF_UNRESOLVED_BLOCKING`（不是 WF_OK）** | v7 契约把 AI 引向副作用路径 |
| 9 | 归档准入与改动前完全一致；`status=archived` 时 `state == "archived"` 且不显示 blocking | 展示被当门禁；归档边界（曾两次丢失） |
| 10 | `unresolved.check.usable` 与 `gates` 判定不一致 → 失败（不变量）；`--short` 的 `task.check` 已派生 | 展示与门禁漂移；旧字段撒谎 |

计时：不作断言，手动检查项（5 份报告下 `status --short` < 1 s）。

---

## 10. 留给审查者的问题

1. §4 扩展 `evaluate_cli` 会改变 `wf gate` 的语义（`before_archive` 从步骤面变成完整门禁）。这算不算"新增机制"（应走 K/S 登记）？
2. 第 5/6 档把 `verdict_fail` 与 `verdict_unavailable` 排在 `pass_bound` 之前，但把 `bound_to_current` 判断放在第 7 档——同一轮 fail 但检查已不可用时，是否该先显示检查侧原因？
3. §5 取消降级后，若某项目报告很大（几十 MB），`open_findings` 的 digest 成本会线性上升；是否需要一个只算"当前轮引用报告"的轻量版本作为前置优化？
4. 第 10/11 档用 `complexity` 判定"是否需要审查"，但轻量任务也可能被要求审查（人为发起）；此时无 reviews → 显示"未要求"，与"以后再发起"的意图并不冲突——这个措辞是否够准确？
