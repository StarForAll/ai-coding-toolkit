# audit-and-fix-workflow-embedded-gaps

## Goal

基于 `/tmp/trellis-0.5.17-2` 这个已经执行过 `trellis init` 并嵌入 `docs/workflows/新项目开发工作流/` 的目标项目，核验用户列出的 6 个候选问题是否真实存在；若问题真实存在，则只在本仓库的 `docs/workflows/新项目开发工作流/` 内修复，必要时通过安装器补丁或源资产修正保证后续嵌入行为正确。

## What I already know

- 用户已明确本次判断对象是 `/tmp/trellis-0.5.17-2`，不是当前仓库自身运行中的 workflow。
- 修改边界被限定为 `docs/workflows/新项目开发工作流/`；任务目录可新增/维护文档。
- 本次是同版本维护审计：`trellis -v` 为 `0.5.17`，`commands/workflow_assets.py` 中 `COMPATIBLE_TRELLIS_VERSION` 也是 `0.5.17`。
- 已发现该工作流源内存在与候选问题相关的脚本、补丁、命令文档和单元测试资产，说明至少一部分问题可能已经被部分修复或需要复核而不是盲改。

## Assumptions (temporary)

- `/tmp/trellis-0.5.17-2` 可以作为可信的 workflow-installed state 证据来源。
- 当前用户希望尽可能多修真实问题，但不接受“顺手优化”式改动。
- 若问题根因属于 Trellis 原生基线而不是 workflow 自身，应在该 workflow 的安装器/补丁位进行修复，而不是修改仓库其他目录。

## Open Questions

- 无阻塞问题；先以证据优先方式完成核验，再按真实缺陷修复。

## Requirements (evolving)

- 对 6 个候选问题逐项做证据化结论：真实问题 / 误报 / 证据不足。
- 交叉核验 source repo、`/tmp` baseline 或 installed state、以及必要的运行时命令输出。
- 若确认问题存在，要继续搜索同类漂移点并一并修复。
- 修复必须限制在 `docs/workflows/新项目开发工作流/` 内，不能修改其他仓库目录。
- 修复后必须补齐最相关的回归验证，不得只改文档不验证脚本/测试。

## Acceptance Criteria (evolving)

- [ ] `audit-report.md` 记录每个候选问题的结论、证据层和验证动作。
- [ ] 所有真实问题都在 `docs/workflows/新项目开发工作流/` 中完成修复。
- [ ] 同类问题的传播范围被检查并在必要处同步修复。
- [ ] 运行与本次改动直接相关的验证命令，并如实记录 pass/fail/not run。
- [ ] 最终结论明确区分已完成、未完成、风险与后续建议。

## Definition of Done (team quality bar)

- 相关 Python/Markdown 资产已更新
- 与本次改动直接相关的单元测试或脚本验证已执行
- 没有越界修改 `docs/workflows/新项目开发工作流/` 之外的源码目录
- 结论与修复均能回指到可审计证据

## Out of Scope (explicit)

- 修改当前仓库实际运行中的 `.trellis/`、`.codex/`、`.claude/`、`.opencode/` 等 repo-local 运行时资产
- 做跨版本兼容性升级评估
- 清理与本次缺陷无关的风格问题或低价值优化

## Technical Notes

- 审计根目录固定为 `docs/workflows/新项目开发工作流/`
- 目标项目证据根目录固定为 `/tmp/trellis-0.5.17-2`
- 当前 CLI 为 Codex inline；不使用 sub-agent
- 需要重点关注 `commands/`, `commands/shell/`, `commands/test_*.py`, `commands/shell/test_*.py`, 以及 workflow 文档/skills/CLI 适配说明
