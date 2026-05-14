# 修复 Trellis AGENTS 与 workflow 文档漂移

## Goal

修复本仓库中已经确认的 Trellis 规则文档漂移，确保 `AGENTS.md`、`.trellis/workflow.md` 与当前实际实现保持一致，减少后续维护者因错误文案而误判平台行为或运行前提。

## What I already know

- `AGENTS.md` 在本仓库中承担长期规则载体角色，不负责提供运行时 task/status 状态。
- Codex 的实时上下文来自 `.codex/hooks.json` + `.codex/hooks/inject-workflow-state.py`，并受 trusted project、用户级 hooks 开关和 `/hooks` 审批影响。
- `.trellis/workflow.md` 当前写明无 session identity 时 `task.py start` 会 fail，但实际实现是 degraded 成功路径：仍将状态从 `planning` 切到 `in_progress`。
- 当前 source repo 根 `AGENTS.md` 不应带 target-project 安装器托管的 `workflow-nl-routing` 区段。

## Assumptions (temporary)

- 本次修复覆盖已经被代码和配置证实的文案漂移，以及与该漂移直接相关的最小运行时/测试守护缺口。
- 允许新增最小必要测试，以防 workflow breadcrumb 合同再次静默漂移。

## Open Questions

- 无阻塞问题；按已确认证据直接修复。

## Requirements

- 更新 `AGENTS.md`，补全 Codex hooks 生效前提。
- 更新 `AGENTS.md`，将 root 级常用 Python 命令调整为当前仓库约定的解释器写法。
- 更新 `AGENTS.md`，收紧对 workflow-local source 目录的表述，避免把整个 workflow product source tree 误说成 shared-agents source。
- 更新 `.trellis/workflow.md`，纠正 `task.py start` degraded 模式的行为描述。
- 更新 `.trellis/workflow.md`，同步修复 Phase 1.4 操作指南中的 degraded 模式旧描述。
- 为 stale pseudo-status 提供明确 breadcrumb 行为，而不是回退到泛化提示。
- 增加一个仓库内真实存在的回归测试，约束 workflow breadcrumb 的关键 contract。

## Acceptance Criteria

- [ ] `AGENTS.md` 中对 Codex 激活边界的描述与 `.codex/config.toml` 当前注释一致。
- [ ] `AGENTS.md` 中列出的 Python 命令不再使用模糊的裸 `python3` 形式。
- [ ] `AGENTS.md` 中对 workflow-local source 的描述不再造成目录归属歧义。
- [ ] `.trellis/workflow.md` 中 `task.py start` 的说明与 `task.py` 实现一致。
- [ ] `.trellis/workflow.md` 中 Phase 1.4 的 degraded 模式说明与 `task.py` 实现一致。
- [ ] stale 任务状态不再只显示泛化 fallback breadcrumb。
- [ ] workflow breadcrumb 合同至少有一处仓库内自动测试守护。
- [ ] 相关文档改动通过基础验证，且不引入语法/格式错误。

## Definition of Done (team quality bar)

- 相关文档改动已完成
- 关键验证命令已执行并记录真实结果
- 不引入 target-project/source-repo 边界混淆

## Out of Scope (explicit)

- 不新增 `workflow-nl-routing` 到当前 source repo 根 `AGENTS.md`
- 不做与当前 breadcrumb / degraded 模式无关的 Trellis runtime 重构
- 不扩展到其他尚未证实的文档重写

## Technical Notes

- 主要证据文件：`AGENTS.md`、`.trellis/workflow.md`、`.trellis/scripts/task.py`、`.codex/config.toml`、`.codex/hooks.json`
- 相关边界文档：`docs/workflows/新项目开发工作流/commands/codex/README.md`、`CLI原生适配边界矩阵.md`
- 新发现：`.trellis/workflow.md` 顶部注释仍写 “The 4 [workflow-state:STATUS] blocks”，与当前 inline 变体数量不符，属于同类 contract 注释漂移。
