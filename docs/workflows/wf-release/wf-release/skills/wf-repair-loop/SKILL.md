---
name: wf-repair-loop
description: 修复态判读：读 repair_scope 的四组事实与 exits，决定下一步动作（重查/重判/重发/放行/终止）。
disable-model-invocation: false
---

# wf-repair-loop

`repair_scope` 是**事实集**，不是状态机：它同时给出全部四组事实与可执行出口，
**不排顺序**、不产生"等待评审"状态。怎么走由你判断；判断不是自由发挥，要按下面的事实读。

## 0. 「这条 blocking 真的修了吗」（判据，不是格式）

- **关闭证据必须指回那个问题**：用哪条证据、它为什么覆盖该问题。不拿"某条宽标准通过了"搪塞。
- 框架只核四件事实：引用存在、指向内容确实变了、验证确实通过、复核人不是提出者（K4b）；
  **是否真修好由你判**，依据写进 disposition 的 `reason` 与 `judgments add`（kind=关闭）。
  `evidence_refs` 用 `v/a/f/p/j` 或当前锚点差异里的 `d:`；`v:` 的 passed 以 Check 实际记录为准
  （计划只提供验证项定义），`s/g/h` 不作关闭证据。关闭会记 `check_id`：本次关闭只认这次 Check，
  不能借同名旧 passed；后来补证据用新的 accepted 覆盖旧空记录，或 amended 撤回关闭。
  **修复是改规则/基线**（spec 规则、`.wf/baseline.md`）时用 `p:<该路径>` 作证据——它必须已在
  交付面内，且规则变动会改锚点，需重跑 Check 后再关。
  旧轮把某项标 `unable` 不算死结：后续轮提交带证据的 `accepted` 即视为核实完成（不必回头改旧轮复核）。
- **"不处置"不是"关闭"**：blocking 无处置即阻断项，三条正路是 resolved / reclassification / task-abandon。
- **"同意某种修法但还没做"不能写 `accepted`**（finding 会立刻消失，light 又没有 C4 兜底）：保持 open，
  或写 `amended` + 理由（不关闭）。
- 人的挑战：「这条测试/这段改动，和这个问题是怎么对上的？」

## 1. 先读什么

```bash
<python> <项目根>/.wf/bin/wf.py status --short --json     # 四条件 + exits + 确定阻断
<python> <项目根>/.wf/bin/wf.py status --json             # 需要细节时再取全量 facts
```

`--short` 里的 `repair_scope` 是**原样过滤**：

| 字段 | 含义 |
|---|---|
| `conditions` | `C1_check_valid` / `C2_no_open_blocking` / `C3_no_unreleased_evidence` / `C4_review_bound_pass` 的真假 |
| `exits` | `[{condition, action, round}]`——机制产出的全部出口，没有优先级 |
| `blocking` | 与归档预检**同一个函数**给出的"还有哪些确定阻断"（`stage` 标明来自 nonstep 还是步骤面） |
| `open_blocking` | 未关闭的 blocking（每条带 `round`；已写 `rejected`/`amended` 的条目带 `disposition`，仍算**未关闭**） |
| `unverifiable` | 不可核实的证据（见 §3） |
| `rounds` | 逐轮决策（`inferred: true` 见 §4） |

## 2. 十个动作 token

`exits[].condition` 说明是哪个条件未满足，`action` 是要执行的动作：

| action | 对应命令 | 说明 |
|---|---|---|
| `rerun_check` | `task-check` | C1：当前检查不能用于完成任务（内容变了 / 规则版本变了 / 失效登记） |
| `record_disposition` | `review-decide --register-only --plan <file>`（只登记关闭）或带 `--main-review` 产生判定 | C2：关闭 blocking；只有 `accepted` 清零（见 `wf-review-action`） |
| `restore_bytes` | 找回原字节放回原路径 | C3：恢复后该条离开 `unverifiable`（不依赖身份） |
| `human_release` | `review-accept-unknown --file <决定.json>` | C3：只在该条 `release_allowed == true` 时出现 |
| `resume_inflight` | 继续该轮证据收集后 `review-import` / `review-decide` | C4：该轮 `blocked` 为空且未判定 |
| `redecide_round` | `review-decide --round <n>` | C4：该轮已判定但不是"当前绑定的 pass 轮" |
| `await_material` | 等材料到达 | C4：该轮 `blocked` 仅含 `material_missing` |
| `relaunch_review` | `review-launch` | C4：改变事实（新轮新报告），常列 |
| `pause_for_human` | `task-pause` | 终局动作之一 |
| `abandon_task` | `task-abandon` | 终局动作之一；**不得**把"当前推进不动"推成"应放弃" |

## 3. `launches[]` 逐轮看，`unverifiable[]` 按三态看

- `launches[]` 每轮一行：`{round, form, imported, declared, decided, blocked}`。
  `blocked` 是**已成立的事实列表**（`report_invalid` / `anchor_stale` / `implementer_overlap` /
  `insufficient_reviewers` / `material_missing`），不是分数、不做优先级合成。
  - `material_missing` = 还可能有材料到（已导入去重后仍 < 2）；
  - `insufficient_reviewers` = 已无更多材料可等（例如声明只有 1 个槽位）。
- `unverifiable[]` 每条带 `cause`（`missing` / `changed` / `unreadable`）与 `state`：
  - `unresolved`：未放行（C3 未满足，阻断归档）；
  - `accepted-risk`：已由人裁放行（**只**解除 C3，不等于"已处置/已关闭"）；
  - `consumed`：放行已失效（报告曾恢复又被再次损坏；需要新的放行决定）。
- `release_allowed` 取**当前** `complexity`：complex 的引用证据不可放行，light 的引用证据可放行。
  因此 complex→light 降级会翻转同一份损坏证据的放行资格；不要凭记忆，读现值。

## 4. `rounds[]` 的 `inferred` 边界

存量任务的 `rounds[]` 为空时，机制按 `result` **推断一条**（`inferred: true`、`decided_at: null`）。
推断只说明"最后一次判定是什么"，**其余轮次的历史不可知**：那些轮显示 `decided == false`
但不代表当时没判过。要处置这些轮，优先 `redecide_round` 取新事实，而不是沿用推断。

## 5. 四条容易误判的地方

1. **`check_valid == false` 必须先重查**：正式判定会拒绝失效 Check，不存在“先重判”的合法路径；
   内容/规则/失效登记处理完后重跑 Check，再判定。结论写入后再重查会让结论失绑，所以顺序是重查在前。
2. **fail 轮重判看未关闭项**：报告载荷可能仍是 fail，但本轮 verdict 由**未关闭** blocking
   推导。误报/重分类经复核写 `accepted`（未改内容、锚点仍匹配）后，同轮重判可转 pass；
   修正复核可追加（旧记录保留并标 `supersedes`），但 pass/unavailable 后不可替换。
   已修复的 finding 会改变内容，旧报告锚点失配，必须新 Check + 新轮。
3. **你的否定只清 C2**：把 finding 以 `accepted` 关闭可以让 `open_blocking` 清零，
   但 complex 任务的 C4 仍要求一次 `pass`——否定不能替代审查结论。
4. **`stale_extra` 非空**：判定之后该轮又导入了未被引用的报告。先读这些新报告，
   再决定重判（`redecide_round`）或在收工时说明为何不重判；不得跳过实质检查。

## 6. 换实施宿主

`review_binding` 的 CLI 校验只能比较 **launch 对 launch**：已发起过新 launch 时旧 pass 会被门禁拦住；
但**换了实施 CLI 却没有 launch** 时两边都是旧值，机制看不见这次交接。
所以换实施宿主时**先 `review-launch`**，再继续该轮审查。

## 7. 不要试归档探路

归档会先做业务提交；虽然 `archive` 现在有提交前只读预检（阻断会先于提交返回），
预检通过也**不等于**可以归档——步骤面、escalated 待答、required 未核实、依赖、debug 未裁
各自还有自己的门禁。要问"还差什么"就读 `status --short` / `gate --due before_archive`，
不要用 `archive` 试探。

## 纪律

- 运行纪律见 `.wf/workflows/session-flow.md`「运行约定」：身份只在请求信封里；不代人作答；入口输出是唯一判定源；解释器整会话固定、失效即停。
