# 修复新项目开发工作流状态机与终态门禁

## Goal

基于 `docs/workflows/新项目开发工作流/` 的实际源资产，对照 `/tmp/trellis-0.5.17-2` 这个已执行 `trellis init` 并嵌入该工作流的目标项目，验证用户列出的状态机、门禁、重入、嵌入自检与多平台副本一致性问题是否真实存在；对确认为真实缺陷的问题，在只修改 `docs/workflows/新项目开发工作流/` 的前提下完成补丁修复，并同步修复同类问题，确保后续目标项目嵌入时能按修正后的契约正常工作。

## What I already know

- 当前仓库是工作流源资产仓库，不是被嵌入后的目标项目。
- 本任务只能修改 `docs/workflows/新项目开发工作流/`；其他目录不能改。
- `/tmp/trellis-0.5.17-2` 是已嵌入该工作流的临时目标项目，可作为实际行为证据来源。
- 需要验证并尽可能修复以下候选问题：
  - `record-session` 终态门禁未真正覆盖 archive / add_session / 元数据清理闭环。
  - `workflow-state.py route` 与 `validate` 对 design / brainstorm / delivery / record-session 的语义分叉。
  - 非执行阶段重入策略过宽，只降级 warning。
  - 多平台副本同步只检查 patch marker，不检查语义一致性。
  - 强门禁仍保留 degraded / single-session fallback 兼容层。
- `workflow-audit` 版本门禁已通过：`COMPATIBLE_TRELLIS_VERSION=0.5.17`，本机 `trellis -v` 为 `0.5.17`。

## Assumptions (temporary)

- 本轮可以在当前仓库中运行本地脚本、单测和针对 `/tmp/trellis-0.5.17-2` 的只读检查。
- 如发现问题属于 Trellis 原生而非工作流源自身，可在该工作流的 installer / patch / helper 合适位置补丁修复，而不是修改仓库根部 `.trellis/` 运行时。
- 现有工作流尚缺少足够的状态机回归测试，需要优先补最小覆盖来约束修复。

## Open Questions

- 当前无阻塞性用户问题；先通过源资产与 `/tmp` 目标项目证据完成验证。

## Requirements (evolving)

- 仅修改 `docs/workflows/新项目开发工作流/` 内文件。
- 先验证候选问题真假，再修复真实问题；不得凭记忆直接改。
- 修复时必须考虑同类问题与旧任务兼容，不得把历史任务全部卡死。
- 若新增收尾证明、门禁字段或一致性检查，需要保证：
  - 有迁移/repair 路径，或只在进入相应阶段后强制。
  - `route`、`set`、`validate` 共享同一套阶段校验语义，避免再分叉。
- 多平台受支持面至少覆盖该工作流当前管理的 `Claude Code / OpenCode / Codex` 相关载体。
- 必须增加足以覆盖本轮修复风险面的回归测试或等价自动验证。

## Acceptance Criteria (evolving)

- [ ] 对每个候选问题给出“真实缺陷 / 非缺陷 / 当前保留风险”的证据结论。
- [ ] `record-session` 的前置交付门禁与收尾闭环证明被清晰区分，且不会因 `validate` 的无副作用设计而错误通过。
- [ ] `workflow-state.py` 的 `route`、`set`、`validate` 对阶段退出校验使用统一规则，至少消除 design / brainstorm / record-session 已知分叉。
- [ ] 非执行阶段重入策略按阶段类型收紧到明确契约，不误伤允许“阶段内补齐”的例外。
- [ ] 多平台副本的一致性检查不再只看 patch marker，能覆盖至少命令/技能正文语义漂移的关键面。
- [ ] 新增或调整的规则不会把旧任务无迁移地卡死，`repair` 或等价兼容路径仍成立。
- [ ] 针对本轮修复新增的自动验证通过。

## Definition of Done (team quality bar)

- 测试新增或更新，且验证过红绿闭环或等价失败/通过证明。
- 相关 lint / 单测 / 工作流验证命令已运行并记录真实结果。
- 若工作流文档契约发生变化，相关命令文档与说明同步更新。
- 只改动 `docs/workflows/新项目开发工作流/` 和当前任务目录。

## Out of Scope (explicit)

- 修改当前仓库根部 `.trellis/` 的实际运行时作为最终修复载体。
- 修改 `/tmp/trellis-0.5.17-2` 中的目标项目文件作为持久修复。
- 处理跨 Trellis 版本的大版本兼容性议题。
- 修复与本次状态机/门禁/副本一致性无关的普通文档或功能问题。

## Technical Notes

- 目标工作流根目录：`docs/workflows/新项目开发工作流/`
- 目标项目证据目录：`/tmp/trellis-0.5.17-2`
- 已定位的核心实现：
  - `commands/shell/workflow-state.py`
  - `commands/record-session.md`
  - `commands/install-workflow.py`
  - `commands/detect-embed-state.py`
  - `commands/workflow_assets.py`
  - `commands/shell/patch-*.py`
- 需要重点覆盖的路径：
  - `route` / `validate` / `set` 阶段门禁共享逻辑
  - `repair` 与历史任务兼容
  - `Claude/OpenCode/Codex` 的命令、skills、hook 载体一致性
