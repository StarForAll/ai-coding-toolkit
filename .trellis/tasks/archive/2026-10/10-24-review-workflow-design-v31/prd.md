# 深度审查 workflow-design v31 设计稿

## Goal

按 `docs/workflows/workflow-design.md` §0.1"设计稿自身的约束（审查与验收面）"的审查口径，对 v31 设计稿正文做深度审查，找出会在后续阶段（实现、对账、使用）被迫中途修改的改善点。

## Requirements

- 审查对象：`docs/workflows/workflow-design.md` v31 正文（§0–§10 + 附录），配套文档仅作交叉核对。
- 只受理 §0.1 审查口径 2 的四类来源：内部矛盾、跑不通、与不变量冲突、与真实场景不符。
- 遵循 `.trellis/spec/guides/design-review-thinking-guide.md`：先读决策日志（§0.1 事实边界、A/B 表、附录 C 修订史），候选经四过滤器 + 对抗性验证后才可发布。
- 每条结论引用具体 §/表/行，按 §0.1 口径 9 的格式输出（约束编号 + 证据 + 来源类型 + 影响 + 建议）。
- 输出必须包含"排除项"章节（低于门槛的候选 + 排除理由）与版本核对（只报告，不判缺陷）。
- 实事求是：有意取舍（§0.1 口径 3 清单）不当作缺陷；留白不算缺陷；实现层选择不算设计层缺失。

## Scope Exclusions

- `1.2-零补丁嵌入方案.md` 内容不审查（用户明确忽略）；仅按口径 8 核对其版本字段并报告漂移。
- 不修改 workflow-design.md 本身；审查发现只产出报告，是否出 v31.1 由用户决定。

## Acceptance Criteria

- [x] 全文（892 行）逐节通读，重点对 v31 新改规则（建边两端限活动区、进行中建边只阻收尾、三段路由、类型 2 限未归档）做端到端推演。
- [x] 每条主发现能写出作者反驳句且反驳不成立（guide Step 3）。
- [x] 版本核对：配套文档 `design` 字段 vs v31；派生图与实现方案版本漂移仅报告。
- [x] 产出审查报告（主发现 / 措辞精确项 / 排除项 / 版本漂移），保存到任务目录。
- [x] 向用户汇报结论，不擅自修订设计稿。

## Method Notes

- 已加载 spec：`.trellis/spec/guides/design-review-thinking-guide.md`（审查协议）、`.trellis/spec/index.md`、`.trellis/spec/docs/index.md`（失败模型边界）。
- 轻量任务，PRD-only。
