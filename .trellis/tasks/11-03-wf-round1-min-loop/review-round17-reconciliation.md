# 第十七轮外部评审的复核与修正（1 项）

- 复核对象：外部评审第 17 轮 1 条（只读复验）
- 处置编号 R54；实施与实跑见 `validation.md` §40

## 0. 结论

| # | 原判 | 复核 | 契约依据 | 处置 |
|---|---|---|---|---|
| 1 | 契约影响等条件不参与复杂度提议，分级可被削成 light | **成立** | 机制稿 §1.3「四个条件中任一为 true/unknown 即提出复杂分级」、设计稿 §4.3 | R54 |

前一条（空产物与连字符）本轮复验通过。

## 1. 复核

`_complexity_proposal` 只算治理面一项；批准流程随后把 `contract`/`acceptance`/`scope` 追加进 `reasons`，却**没有回头重算 `proposed`**。于是显式不给 `complexity` 时直接取 `light`，`reasons` 里明明记着 `contract=true`。因为后续门禁按 `plan.complexity` 决定是否要求三件套与强制审查，这是**分级缺陷**而非显示问题。

顺带暴露一处顺序问题：第一次产物检查用的是**旧** `task.plan.complexity`（新任务为 `None`），第二次才用新值——同一函数里判了两遍，前一遍用错值。

## 2. 处置（R54）

- `_complexity_proposal(ctx, task, block, extra_conditions)`：先汇总治理面与 `contract`/`acceptance`/`scope` 四项，任一 `true`/`unknown` 即提议 `complex`；常量 `COMPLEXITY_CONDITIONS` 固定这四项。
- 批准顺序改为：汇总条件 → 提议 → 定分级（人工指定只能降级）→ 降级须有 `reason`+`evidence` → **再**做产物检查（用最终 `complexity`）。
- 删掉先前那次用旧值的产物检查。

对照用例：只把 `contract` 由缺省改成 `true`（不指定 `complexity`）→ 要求复杂产物、补齐后 `plan.complexity=complex` 且 `reasons` 含 `contract`；`scope=unknown` 同判；显式 `light` 无降级信息被拒；给了理由与证据则通过并留痕；无条件仍为 `light`。

## 3. 边界

- 不新增条件、不新增原因码：四项就是机制稿已列的四项，出口仍是 `WF_TEMPLATE_INCOMPLETE`/`WF_SEMANTIC_DECISION`。
- 不改降级语义：仍由人给理由与证据，脚本只核齐全。
- 不判语义：条件值仍由调用方给出（不在本轮引入自动推断）。

## 4. 对收口状态的影响

属「既有分级契约只落实了一项」，会让复杂要求被静默绕开，收口前必修。落地后需重跑批准/开工（CP1/CP2、R15/R17/R26/R44/R51/R53）与三夹具全流程、F0。
