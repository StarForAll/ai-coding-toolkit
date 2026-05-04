# Analyze Trellis Usage And Workflow-Audit Fix Plan

## Goal

收敛并实现 `workflow-audit` 的修正规则，使其严格面向当前 workflow 产品的临时项目审计边界：只支持 `Claude Code`、`OpenCode`、`Codex` 三个 CLI；一旦检测到 Trellis 实际版本与 workflow 兼容锚点不一致，立即停止后续审计，并明确要求用户改用 `workflow-capability-audit` 做兼容升级分析。

## What I already know

- 本仓库当前 Trellis 基线版本为 `0.5.0-rc.3`，`trellis -v` 与 `.trellis/.version` 一致。
- `docs/workflows/新项目开发工作流/commands/workflow_assets.py` 当前兼容锚点仍为 `0.4.0`。
- 当前 workflow 产品的 managed subset 以 `workflow_assets.py` 为准，只覆盖 `claude`、`opencode`、`codex`。
- `.trellis/` 是本仓库 Trellis 本地控制面；`.codex/`、`.claude/`、`.opencode/`、`.kiro/`、`.qoder/` 等目录是不同 CLI 的承载与接线层。
- `workflow-audit` 当前已有 Codex handoff、临时项目 `/tmp` 审计、隐藏目录核对等约束，但尚未把“版本漂移立即终止并路由到 workflow-capability-audit”做成最前置硬门禁。

## Assumptions

- 本次修改只调整 `workflow-audit` 的行为合同、配套模板/测试，不直接改 `workflow-capability-audit` 的主流程。
- “实际版本不一致”指 workflow 兼容锚点与当前 Trellis 实际版本存在偏差，不论高低，只要不一致就不继续 `workflow-audit` 主流程。
- 这里的“分析对应的临时项目中相关联的内容”仍保留 `/tmp + trellis init + install-workflow.py` 的审计模型，但前提是版本一致。

## Open Questions

- 无。当前需求已足够明确，可以直接落地。

## Requirements

- `workflow-audit` 必须先做版本一致性门禁检查。
- 若 Trellis 实际版本与 workflow 兼容锚点不一致，`workflow-audit` 必须立即终止。
- 终止后必须明确指导用户改用 `workflow-capability-audit`，而不是继续做静态或运行时审计。
- `workflow-audit` 的默认支持面必须明确限定为 `Claude Code`、`OpenCode`、`Codex`。
- 临时项目审计时，相关隐藏目录与 CLI 结论也只围绕上述三 CLI 展开。
- spec、`.agents/skills/`、`.claude/skills/`、相关 references/tests 必须同步。

## Acceptance Criteria

- [ ] `workflow-audit` spec 明确写入版本一致性硬门禁与失败后的路由规则。
- [ ] `.agents/skills/workflow-audit/SKILL.md` 与 `.claude/skills/workflow-audit/SKILL.md` 同步反映该门禁。
- [ ] `workflow-audit` 明确声明支持范围仅为 `Claude Code`、`OpenCode`、`Codex`。
- [ ] 相关模板或测试覆盖“版本不一致立即终止并路由到 workflow-capability-audit”的场景。
- [ ] 至少运行与本次修改直接相关的验证命令，并据实报告结果。

## Definition of Done

- 相关 spec/skill/test 同步完成
- 必要验证命令已运行
- 输出不再允许把版本漂移问题留给 `workflow-audit` 自己继续判断

## Out of Scope

- 直接执行 `workflow-capability-audit` 的完整兼容升级流程
- 更新 `COMPATIBLE_TRELLIS_VERSION` 到新版本
- 改动当前 workflow 以外的其他 repo-local maintainer skills

## Technical Notes

- 行为源：`.trellis/spec/skills/workflow-audit.md`
- 执行面：`.agents/skills/workflow-audit/`、`.claude/skills/workflow-audit/`
- 版本与托管边界权威输入：
  - `docs/workflows/新项目开发工作流/commands/workflow_assets.py`
  - `docs/workflows/新项目开发工作流/CLI原生适配边界矩阵.md`
  - `docs/workflows/新项目开发工作流/装后隐藏目录与托管边界核对清单.md`
