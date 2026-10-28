# PRD：审查强度分流待决（G7）备注

## 背景

用户此前提出：单个任务里，简单任务按 Trellis 机制执行，复杂任务在 check 阶段引入多方 agent 审查。经分析（见 `research/deferred-review-intensity.md`）确认该要求**方向成立但写法不可直接落地**，用户裁决：**内容暂不变，留到下一个任务讨论更优方案**，本轮只在实现方案里留下备注与边界。

## 交付

在 `docs/workflows/workflow-implementation.md` 加两处（只加备注，不引入任何规则）：

1. **§9.6 新增 G7 行**：待决定位 + 五条下一任务不得放宽的边界 + 待裁决的两个具体问题（channel 编排 vs 报告契约；provider 不足 2 家时的降级）。
2. **§8.3 末尾一句指路**：任务级审查强度分流未定稿，见 §9.6 G7；定稿前复杂改动仍按 §8.4 实机验收 + `trellis-check`。

## 不做

- 不新增"审查强度分流"规则本身，不改 constraints、不改变体、不改 §4.3 skill 面、不改设计稿。
- 不引入 `trellis channel` 或 `multi-cli-review` 的任何强制依赖。

## 验收

| ID | 判据 |
|---|---|
| D1 | §9.6 存在 G7 行，含"待定/本轮不实施"与五条边界 |
| D2 | §8.3 有一句指向 §9.6 G7，且不引入新规则 |
| D3 | 文档内其他章节未被改动（`git diff` 只有这两处） |
| D4 | `trellis-library validate --strict-warnings`、`validate-skills.sh`、`get_context.py --mode phase` 全过 |
| D5 | 本轮分析落盘到 `research/deferred-review-intensity.md`，供下一个任务继承 |
