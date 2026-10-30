# 人工审查通过后的本地提交计划

用户先明确“人工审查通过，继续下一步”，随后确认按本计划完成本地提交、当前任务归档与会话记录。以下为已确认的 Phase 3.4 提交范围；执行结果由 Git 历史、任务归档状态和 journal 记录。

## 工作提交（依次）

1. `docs(wf): 重写单人流程框架设计并闭合审查问题`
   - `docs/workflows/wf-framework-design.md`
   - `docs/workflows/wf-framework-design.index.md`
   - `docs/workflows/wf-framework-design.sources.md`
   - `.trellis/tasks/10-30-wf-design-audit-r4/` 本任务的全部研究、规划、修订、验证与本计划
2. `docs(spec): 沉淀 wf 设计修订的语义消费与证据边界`
   - `.trellis/spec/docs/index.md`
   - `.trellis/spec/docs/wf-design-revision-gate.md`

## 工作提交后

按 Trellis 原生 finish-work：归档当前任务（该任务始终直接在 main 开发，使用其明确提供的直接主线任务归档路径），再记录会话 journal。两步会分别生成任务归档与 journal 的本地记录提交；journal 使用工作提交哈希，不把归档哈希当工作成果。

不推送、不创建 PR、不发布、不归档其他任务。`.agents/skills/grill-me/` 与 `skills-lock.json` 是用户原有未跟踪工作，明确排除。

确认后的下一工作阶段是机制设计/实现单元规划与三个夹具的验收设计；本批提交不包含框架实现代码，也不声明运行验收已完成。
