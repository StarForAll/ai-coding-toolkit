# 审查 workflow-design v30 设计稿

## Goal

按 `docs/workflows/workflow-design.md` 自身的 §0.1（设计稿自身的约束：审查口径 1–9、A1–A6、B1–B10）对**当前 v30 全文**做深度审查，产出一份可按格式复核的缺陷报告，供作者在下一版一次性收敛，避免实现阶段被迫中途改设计稿。

## Requirements

1. 审查对象界限：
   - 审查对象是 `docs/workflows/workflow-design.md`（v30）正文 §0–§10 与附录 A/B/C。
   - `docs/workflows/1.2-零补丁嵌入方案.md` 本轮**不作为判定依据**（用户明确暂忽略），仅在必要时作为背景，不因其内容判设计稿缺陷。
   - `docs/workflows/依赖机制设计说明.md`（v30，`design: workflow-design.md v30`）是 §7 的同版配套文档，用于交叉核对，并按 §0.1 口径 6 处理：两者不同版只报版本不一致，不据此判缺陷。
   - `docs/workflows/workflow-design-全流程流转图.md` 是派生图，只作交叉核对与版本漂移报告。
2. 审查口径严格按 §0.1 口径 1–9 与 `.trellis/spec/guides/design-review-thinking-guide.md`：
   - 只受理四类来源：内部矛盾、跑不通、与不变量冲突、与真实场景不符；
   - 先判承载（设计稿 / 实现方案 / 目标项目），实现层与目标项目承载项只检查“交给谁、验收什么”是否写清；
   - 不受理个人偏好、工具选型、实现细节、未规定的留白、要求新增机制；
   - 不把 §0 事实边界列出的有意取舍当缺陷；
   - 区分“未规定”与“规定不清”。
3. 每条**入选**结论必须给出：约束编号（A/B/§）+ 证据（具体 §/表/行）+ 来源类型 + 具体影响（会在哪个阶段被迫改）+ 最小建议（补判定 / 删重复 / 改措辞；若须新增机制标注“超出本设计”）。
4. 报告必须区分三档：主要结论、措辞与精确性、已排除候选（含排除理由）；不得用同等置信度混排。
5. 每条主要结论发布前必须走完反证：在文档内及配套文档检索同一概念、沿文档自身出口走完场景、给出最简合规实现、写出作者可用一条 § 反驳的句子；能反驳则降级或排除。
6. 实事求是：鸡毛蒜皮、纯风格偏好不入主要结论；不为凑数量塞条目。
7. 只审查、不改 `docs/workflows/**` 正文；本轮不改设计稿内容。

## Acceptance Criteria

- [ ] 报告按 `.trellis/spec/guides/design-review-thinking-guide.md` 的 Output Template 组织（Review conclusion / Main findings / Wording and precision / Excluded (not defects) / Version drift）。
- [ ] 每条主要结论都带四要素（约束、证据、来源类型、影响）与最小建议，且证据能定位到具体 §/表/行。
- [ ] 每条主要结论都有反证记录（检索过的词、走过的出口、最简合规实现、作者反驳句），反驳成立者已降级或移入已排除表。
- [ ] 已核对版本三轴：设计稿 frontmatter `version` 与配套文档 `design` 字段；派生图版本漂移单独列为报告项。
- [ ] 明确给出 §0.1 承载判定的汇总（哪些条目不属设计稿承载），不让实现层缺陷混入设计稿缺陷。
- [ ] 结论中不含“一般来说 / 最佳实践”型依据，不含纯排版偏好。

## Notes

- 报告输出位置：`.trellis/tasks/10-24-review-workflow-design-v30/research/review-report.md`。
- 若审查发现需要改正文，本轮只在报告里给最小建议；是否落稿由用户决定。
