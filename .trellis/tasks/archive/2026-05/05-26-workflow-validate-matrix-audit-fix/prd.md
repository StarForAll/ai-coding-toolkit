# audit and fix workflow-validate-matrix skill

## Goal

审查 `skills/workflow-validate-matrix/` 的实现、文档、测试与其依赖的 workflow 安装契约，逐条判断用户列出的候选问题是否真实存在；仅修复证据充分的问题，并同步修补同类缺陷，避免引入新的验证盲区或协议漂移。

## What I already know

- 用户列出了 13 个候选问题，覆盖场景语义、cleanup、report 解析、CLI 适配层覆盖、重复安装阻断、BLOCKED 场景验证、schema_version 类型、profile/CLI 覆盖、uninstall、workflow.md 内容验证、embed_integrity 运行、临时目录清理与时间戳精度。
- `workflow-validate-matrix` 当前有 5 个场景，核心实现位于 `constants.py`、`scenario_setup.py`、`validation_runner.py`、`report_generator.py`、`validate-matrix.py`。
- 当前 post-install 仅校验 5 个 workflow 级文件存在；未见 CLI 适配层存在性/内容断言。
- `partial-failed-attempt` 目前只做 pre-check，不尝试验证安装命令在 BLOCKED 状态下是否真的被拒绝。
- `scenario_setup.py` 当前将 `workflow_schema_version` 写成整数 `2`。
- 报告校验器 `_parse_finding_blocks()` 以行前缀 `- **` 解析 finding 字段，语义上存在误匹配边界。

## Assumptions

- 本轮优先修复 skill 自身实现、测试和必要文档，不扩大到重构整个 workflow 安装体系。
- 如果候选问题属于“合理现状”或“超出当前 skill contract”，会明确标记为不修复并说明原因。
- 若发现 paired contract 受影响，需要同步检查 `workflow-repair` intake 兼容性，但尽量不扩大改动面。

## Open Questions

- 是否需要把重复安装阻断、CLI 适配层部署验证、内容级校验全部纳入矩阵主路径，还是只做最小关键增补。
- `partial-failed-attempt` 的最佳语义是“expected-block”还是保留 failed 并新增说明字段。

## Requirements

- 对用户列出的每个问题给出基于代码/契约的真实判断。
- 修复真实存在的问题，并覆盖同类问题。
- 保持 `workflow-scan-repair-v3` 报告协议不漂移，除非有充分必要且同步验证。
- 为新行为补充或更新单元测试；必要时补充矩阵运行时校验逻辑。
- 不引入破坏现有场景的假阳性。

## Acceptance Criteria

- [ ] 形成逐项判断清单，并有对应代码证据。
- [ ] 修复后的 `workflow-validate-matrix` 对真实缺陷有更强覆盖，尤其是阻断、CLI 适配层、报告解析等关键路径。
- [ ] 相关单元测试通过。
- [ ] 相关 repo 验证命令执行并据实汇报结果。

## Out of Scope

- 不重写整个 workflow 安装器。
- 不把矩阵扩展成完整的 `workflow-scan`/`workflow-audit` 替代品。
- 不引入与当前需求无关的大规模场景爆炸。

## Technical Notes

- 关键规范：`.trellis/spec/skills/workflow-validate-matrix.md`
- 关键实现：`skills/workflow-validate-matrix/{constants,scenario_setup,validation_runner,report_generator,validate-matrix}.py`
- 需要联动核查的 workflow runtime：`docs/workflows/新项目开发工作流/commands/`
