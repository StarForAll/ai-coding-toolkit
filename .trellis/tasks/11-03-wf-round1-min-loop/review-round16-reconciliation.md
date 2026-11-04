# 第十六轮外部评审的复核与修正（1 项，含 2 个残留原因）

- 复核对象：外部评审第 16 轮 1 条（只读复验，未建任务）
- 处置编号 R53；实施与实跑见 `validation.md` §39

## 0. 结论

| # | 原判 | 复核 | 契约依据 | 处置 |
|---|---|---|---|---|
| 1 | 复杂产物门禁仍可通过「空文件」与「连字符占位」 | **成立（上一轮 R51 只修了一半）** | 机制稿 §2.3「规划必填还核非空和类型，删除标记留下空值不能通过」、§10.2「field 为非空 ASCII 字段名」 | R53 |

spec 停用（R52）本轮复验通过，无需再动。

## 1. 复核

两个原因都成立：

1. `complex_artifact_problems` 只判「存在 + 无标记」，**没有判非空**——两个空文件、或只有标题行，都能通过批准与开工。机制稿要求「删除标记留下空值不能通过」。
2. `MARKER_PATTERN` 是 `[A-Za-z0-9_]+`，**不接受连字符**，而发行模板自己就用 `{{WF_REQUIRED:data-flow}}`、`{{WF_REQUIRED:non-goals}}`、`{{WF_REQUIRED:verification-commands}}`、`example-good`/`example-bad`。所以这些占位既不参与成品校验，也不进入 `template_markers` 登记（`double_check` 的双向核对同样漏）。

机制稿 §10.2 对 field 的约束是「非空 ASCII 字段名」——连字符属 ASCII，放宽是符合契约的，不是新增语法。

## 2. 处置（R53）

- `MARKER_PATTERN` 扩为 `[A-Za-z0-9_-]+`：成品校验、`double_check`、发行 `template_markers` 登记一起生效。
- `complex_artifact_problems` 增加两层空判定：文件 `strip()` 为空记 `empty`；去掉标题行与空行后无内容记 `empty body`（只有标题也不算填完）。
- 原因码仍用 `WF_TEMPLATE_INCOMPLETE`，facts 逐份给 `artifact` 与 `reason`（`missing`/`empty`/`empty body`/`unfilled placeholders`，后者带具体 `fields`）。

## 3. 边界

- 不做语义评分：只判非空与占位，不判「写得好不好」。
- 不扩流程：仍在既有批准/开工两处复核，不新增步骤或状态。
- 标题行豁免只用于剥离计数，标题本身是占位项，仍受标记校验约束。

## 4. 对收口状态的影响

属「上一轮修复不完整」：同一契约（必填非空 + 标记集完整）只实现了一半。落地后需重跑批准/开工相关（CP1/CP2、R15/R17/R26/R44/R51）与三夹具全流程、F0。
