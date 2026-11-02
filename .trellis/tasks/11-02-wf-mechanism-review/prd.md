# 审查 wf-framework-mechanism 机制设计文档

## Goal

从实际开发（实现者）角度深度审查 `docs/workflows/wf-framework-mechanism.md`，以 `wf-framework-design.md`（设计稿）与 `wf-framework-charter.md`（charter）为要求与约束基准，找出机制稿中仍存在的不足、矛盾点与缺漏，并给出可落地的改进建议；后续可能在本任务内对发现的问题执行修复。

## Requirements

- 审查基准：机制稿的行为契约必须与设计稿/charter 一致；冲突按 charter T1 交人裁决，不由审查者自行改写上位规则。
- 不偏离初衷与核心：charter 四目标、T4 不可削减项、设计稿既有承诺不得以"实现麻烦/成本"为由被削弱；审查建议不得引入目标外机制。
- 实事求是：只报告影响实现正确性、契约一致性或可落地性的问题；排版、措辞等无关紧要项忽略。
- 审查视角：实现者视角——schema 可实现性、算法确定性、状态机完整性、跨文档字段/语义对应、恢复与幂等路径可走通。
- 审查对象与关联文件：wf-framework-mechanism.md（主体）、wf-framework-design.md、wf-framework-charter.md、wf-framework-design.index.md、wf-framework-design.sources.md、scripts/validate-wf-design.py（机检结果作为证据）。
- 产出：分级（矛盾/缺漏/改进建议）的审查发现清单，每条含定位、证据、影响与建议；落盘到任务目录供后续修复使用。

## Acceptance Criteria

- [ ] 已通读机制稿全文与设计稿/charter 全文，并核验机制稿 §0.1 四份输入哈希与实际文件一致
- [ ] 已运行 scripts/validate-wf-design.py 并将机检结果纳入证据（机检通过不等于语义审查通过）
- [ ] 审查发现逐条给出：机制稿/设计稿定位（章节+行号）、证据（引用原文）、影响面（实现/运行/上位一致性）、改进建议
- [ ] 发现分级明确：A=与上位文档的矛盾或语义冲突；B=实现不可判定/缺漏；C=可改进项；不把 C 级问题夸大为 A/B
- [ ] 审查报告落盘至本任务目录（findings.md），并向用户完整汇报
- [ ] 后续修复（若用户批准）以本清单为输入，逐条处置并留痕

## Notes

- 本任务为审查型任务，PRD-only；修复阶段若涉及上位文档（design/charter）修订，须按 charter T7 同批义务执行并另行确认。
- 机制稿 status 自称"2026-11-02 人工审查通过"，本审查是下一轮独立复审，结论只按已覆盖轴表述。
