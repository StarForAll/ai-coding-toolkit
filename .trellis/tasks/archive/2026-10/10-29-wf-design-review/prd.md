# PRD：审查 wf-framework-design.md 设计文档

## Goal

对照 skills/Trellis/stop-that-shit/mcode-stack 四个参考项目，审查 docs/workflows/wf-framework-design.md 的可吸收点、不足、矛盾与缺漏，产出审查报告（只读分析，不改设计文档）。

## 背景

`docs/workflows/wf-framework-design.md`（509 行）是独立单人流程控制框架 wf 的设计共识定稿（2026-10-29），其设计输入声明包含四个上游项目：skills、Trellis、stop-that-shit、mcode-stack。定稿后需做一轮外部对照审查。

## 原始需求（审查不偏离初衷）

wf 框架的四条核心需求（审查必须以此为边界，不得偏离）：

1. 能够在一个项目中长期使用；
2. 能够在完全新建的项目或存量项目中使用；
3. spec 持续沉淀；
4. 单任务流程执行可控。

约束边界：单人 · 单机 · 单一工作线 · 多 AI CLI 交替 · skill 为核心 · 无 hook · 无常驻进程 · 无团队功能 · 不依赖 agent 宿主运行时特性。

## 审查范围与方法

- 精读被审文档 `docs/workflows/wf-framework-design.md` 全文；
- 精读同仓库设计输入 `docs/workflows/workflow-design.md`、`docs/workflows/workflow-implementation.md`（§8.5 审查契约为同源基准）；
- 实地考察 `~/projects/other/` 下 skills、Trellis、stop-that-shit、mcode-stack 四个项目的实际内容（由研究子代理完成，报告须引用具体文件路径）；
- 产出审查报告，落盘到本任务目录。

## Acceptance Criteria

- [ ] 报告对四个上游项目逐一给出"仍可吸收 / 无需吸收"的结论，每个吸收点有上游文件路径与理由；
- [ ] 报告列出文档不足、矛盾、缺漏，每条引用被审文档的章节号，并说明为什么重要（非鸡毛蒜皮）；
- [ ] 不偏离四条核心需求与无 hook / 无团队等硬边界；
- [ ] 审查为只读分析：不修改 `wf-framework-design.md` 本身；
- [ ] 实事求是：无关紧要的排版、措辞风格问题不列。

## 非目标

- 不重写或修改设计文档；
- 不评估实现层面的细节（字段 schema、命令名等属后续机制文档）；
- 不评估 Trellis 内嵌 wf 模块（wf-variant.md 那组）的去留。
