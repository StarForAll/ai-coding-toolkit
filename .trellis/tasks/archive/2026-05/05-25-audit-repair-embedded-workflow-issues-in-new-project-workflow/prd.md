# 修复新项目开发工作流在目标项目中的阶段门禁与审计闭环缺陷

## Goal

基于 `/tmp/trellis-0.5.17-2` 的已嵌入实际行为，确认并修复 `docs/workflows/新项目开发工作流/` 中真实存在的阶段状态机、门禁校验、命令文档和安装后行为缺陷；修复只允许落在 `docs/workflows/新项目开发工作流/`。

## What I Already Know

- 审计对象是目标项目 `/tmp/trellis-0.5.17-2`，不是本仓库当前自用 workflow。
- 源工作流兼容版本 `0.5.17`，当前 `trellis -v` 也是 `0.5.17`，版本门禁通过。
- `docs/workflows/新项目开发工作流/commands/shell/` 是安装到目标项目 `.trellis/scripts/workflow/` 的强门禁脚本来源。
- `docs/workflows/新项目开发工作流/commands/*.md` 会变成目标项目的命令/skill 文档，是阶段退出指引与人工操作契约来源。
- 用户要求先完成分析和修复方案说明，再等待确认后继续改源码。

## Assumptions (Temporary)

- `/tmp/trellis-0.5.17-2` 足以代表当前源工作流嵌入后的真实行为。
- 若发现问题来自 Trellis 原生行为缺口，应在 workflow 安装层通过补丁或脚本/文档约束修复，而不是修改仓库外层 Trellis 源码。

## Open Questions

- 是否把 `status=completed` 视为合法退出态并允许继续切阶段，还是从 schema 与文档中彻底移除这个值。
- L0 直达 `implementation` 是要保留并补强工程化前置门禁，还是直接取消该快捷路径。

## Requirements (Evolving)

- 必须逐项判断用户列出的候选问题是否真实存在，不能直接采纳。
- 如果发现同类问题，需一并修复。
- 修复范围仅限 `docs/workflows/新项目开发工作流/` 与当前任务目录。
- 修复后要用当前 workflow 自带测试/验证命令证明行为收敛。

## Acceptance Criteria (Evolving)

- 给出每个候选问题的结论：真实缺陷 / 非缺陷 / 证据不足。
- 对真实缺陷给出具体修复文件、修复策略和回归验证方法。
- 经用户确认后，完成源码修改并通过相关验证。

## Out of Scope

- 修改本仓库根级 `.trellis/`、`.agents/` 或其他非 `docs/workflows/新项目开发工作流/` 目录源码。
- 把本次审计升级成跨版本能力兼容审计。

## Technical Notes

- 当前已拿到静态证据与 `/tmp/trellis-0.5.17-2` 运行时复现证据。
- 下一步在用户确认后，优先修改状态机脚本、validator 与对应命令文档，再补测试。
