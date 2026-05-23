# 审计并修复嵌入式新项目开发工作流

## Goal

针对 `docs/workflows/新项目开发工作流/` 这一“可嵌入目标项目的工作流源”做一次证据驱动的深度审计。以 `/tmp/trellis-0.5.17-2` 这个已经执行过 `trellis init` 并嵌入该工作流的临时目标项目为主要验证对象，判断用户列出的疑点及其同类问题是否真实存在；若确认存在，再在获得用户同意后仅修改 `docs/workflows/新项目开发工作流/` 内的源资产，并验证修复不会引入新的问题。

## What I Already Know

- 用户要求分析对象是 `/tmp/trellis-0.5.17-2` 的实际嵌入结果，不是当前仓库自身正在运行的 workflow。
- 用户明确限制修复范围只能是 `docs/workflows/新项目开发工作流/`；其他目录不能修改。
- 用户给出了一批“问题与思路”作为候选假设，要求先核实，不能直接当成既定事实。
- 当前仓库要求此类工作走 `workflow-audit` 路径，先做版本门禁、源/目标对照、证据归类，再决定是否修复。
- 当前仓库 `codex.dispatch_mode=inline`，本次任务不能使用子代理。

## Assumptions

- `/tmp/trellis-0.5.17-2` 当前仍保留可供取证的嵌入后状态。
- 当前 `trellis` 版本与该 workflow 的兼容锚点满足 `workflow-audit` 的 same-version 维护门禁，或至少属于该技能允许的继续审计范围。
- 用户这轮希望先拿到“真实问题/误报/同类问题”的审计结论和修复方案，再决定是否授权我实际修改 workflow 源文件。

## Open Questions

- 无阻塞性问题；先按本地证据链完成审计。

## Requirements

- 只审计并在必要时修复 `docs/workflows/新项目开发工作流/`。
- 审计时必须同时查看 source repo 与 `/tmp/trellis-0.5.17-2` 的生成结果。
- 用户给出的候选问题必须逐条判定为：真实问题 / 误报 / 需补充证据。
- 需要主动扩展搜索同类问题，不能只核对用户列出的条目。
- 在给出修复方案后，必须等待用户明确同意，之后才能修改 workflow 源文件。
- 如果问题属于 Trellis 原生层且不能直接改原生仓库，应评估是否需要在该 workflow 内以安装器/补丁方式修正。

## Acceptance Criteria

- [ ] 已完成版本门禁与审计边界确认。
- [ ] 已建立 source repo 与 `/tmp/trellis-0.5.17-2` 的对照证据。
- [ ] 已形成逐项判定清单：真实问题、误报、待补证据。
- [ ] 已给出只作用于 `docs/workflows/新项目开发工作流/` 的修复方案。
- [ ] 在未获用户同意前，不修改 workflow 源文件。
- [ ] 若用户同意修复，则后续仅在允许范围内实施并完成验证。

## Definition of Done

- 问题判定有明确证据来源和文件定位。
- 修复方案覆盖真实问题及其同类问题，不引入明显新漂移。
- 最终验证结果真实标注为 pass / fail / not run。

## Out of Scope

- 修改当前仓库自身 `.trellis/`、`.codex/`、`.claude/` 等正在使用的 Trellis 运行时逻辑。
- 修改 `/tmp/trellis-0.5.17-2` 之外的其他目标项目。
- 在未获用户同意前直接动 workflow 源文件。

## Technical Notes

- 审计目标根：`docs/workflows/新项目开发工作流/`
- 目标项目样本：`/tmp/trellis-0.5.17-2`
- 任务目录：`.trellis/tasks/05-23-audit-fix-embedded-new-project-workflow/`
