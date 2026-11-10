# S6 收敛谓词核对（v42 S6 vs `gates.final_gate`）

v42 S6 的唯一定义（SKILL 与门禁共用这一句）：

```
done ⇔ check.pass(当前 revision)
      ∧ round(state=pass, revision=当前)
      ∧ ∄blocking∧open
      ∧ 全部 finding 已处置
      ∧ 累积变更已确认
      ∧ 无 required 未结案
      ∧ 提交已授权
```

## 逐项核对（读 `gates.py::final_gate` + `archive` 动作）

| # | 合取项 | 现状 | 结论 |
|---|---|---|---|
| 1 | `check.pass(当前 revision)` | `final_gate` 核 `task.check.result == "pass"`；锚点由 `task.check-passed` 步骤（`required_steps` 投影）核当前修订 | ✅ |
| 2 | `round(state=pass, revision=当前)` | `task.review-passed` 步骤核本轮结果与当前 check 锚点；complex 条件下才适用 | ✅（轻量任务本就无审查） |
| 3 | `∄ blocking ∧ open` | **没有核**：报告里的 findings 没有落盘（`imported` 只存 round/slot/path/digest/anchor），归档门禁不重解析报告 | ❌ **缺** |
| 4 | `全部 finding 已处置` | 同上；`decide` 只把 dispositions 追加进 `reviews.dispositions`，门禁不消费 | ❌ **缺** |
| 5 | `累积变更已确认`（4.6） | 无实现：`skeleton.cumulative.since_last_authorized` 现为 `None` | ❌ **缺**（属 4.6 的事实托底） |
| 6 | `无 required 未结案` | `evaluate(ctx, task, "before_archive")` 逐步骤核 `required_steps`，缺项即阻断 | ✅ |
| 7 | `提交已授权` | 在 `archive` 动作里核（`WF_COMMIT_NOT_AUTHORIZED`），不在 `final_gate` | ✅ |

## 第 3/4 项为什么不能只改门禁

事实不在记录里：findings 只在报告文件里，`reviews.imported` 没存。两种落法：

- **A（推荐）**：`skeleton` 与门禁都从 `imported[].report_path` 重解析报告（报告有 digest、导入后不可改），派生 `unaddressed_findings`；不新增字段，符合"投影可重建"（K8）。
- **B**：导入时把 `findings[]` 摘进 `reviews.imported[]`（记录变大、且与报告正文两处存同一事实）。

## 阻断 006：`blocking 无处置` 缺少阻断码

- **原因码**：`WF_SEMANTIC_DECISION`（要人裁"加码还是复用"）
- **决定性事实**：v42 K10 要求「blocking 无处置 → `unaddressed_blocking` 阻断项」，出口只有 `resolved`（按 K4b 非提出者复核）/ `reclassification`（人确认）/ `task-abandon`。机制稿 §11.1 的 35 枚码里**没有对应码**：`WF_CHECK_FAILED` 语义是"必要命令失败/未运行/内部审查未通过"，`WF_REVIEW_INVALID` 是"报告/人数/锚点不合格"，把"blocking 无处置"塞进任一枚都会改义（码值只增不改义）。
- **出口**：(a) 机制稿 §11.1 + `protocol/codes.json` 新增一枚 blocked 档码（例如 `WF_UNRESOLVED_BLOCKING`，出口=按 K4b 复核关闭 / 人确认重分类 / 异常归档）；(b) 复用 `WF_REVIEW_INVALID` 并接受语义变宽；(c) 暂不实现该项，v42 记偏差。
- **禁止的错误修复**：把"无处置"当"已处置"放行；用自由文本理由关闭 blocking（K4b 已禁）。
