# 修正 workflow-capability-audit skill 的兼容实现与规范闭环

## Goal

基于当前仓库真实生效的 Trellis runtime 与多 CLI 隐藏目录接线方式，审查并修正 repo-local maintainer skill `workflow-capability-audit`，确保它的入口文档、references、测试和补充 spec 与当前实现保持一致，并避免引入新的协议漂移或验证缺口。

## What I already know

* 当前仓库的 Trellis 真正运行时不在 `docs/workflows/**`，而在 `.trellis/workflow.md`、`.trellis/scripts/common/*`、`.trellis/.runtime/sessions/*` 以及各平台隐藏目录 carrier。
* active task 已经是 session-scoped 模型，主真源是 `.trellis/scripts/common/active_task.py`，而不是旧的全局 `.trellis/.current-task`。
* Codex 在本仓库默认遵循 `codex.dispatch_mode: inline`，`.codex/agents/*` 只是显式非 inline 路径的 carrier，不能被 skill 错误描述成默认执行路径。
* `workflow-capability-audit` 当前存在 `.agents/skills/` 与 `.claude/skills/` 两份 entry artifact，并依赖同目录下 `references/*`、`tests/*`，同时受 `.trellis/spec/skills/workflow-capability-audit.md` 约束。
* 目标 skill 当前与执行脚本 `docs/workflows/新项目开发工作流/commands/workflow-capability-audit.py` 大体对齐，但仍需进一步确认是否满足本仓库 skill 实现规范，尤其是结构完整性、输出契约表达、验证说明和跨副本同步闭环。

## Assumptions

* 本次允许修改 repo-local maintainer skill 相关文档与必要的补充文件。
* 若发现行为级不一致，需要同步更新 spec / references / tests，不能只改 `SKILL.md`。
* 若当前问题仅是 skill 文档结构不达标而非运行逻辑错误，则优先做最小修正，不扩大到无关脚本。

## Open Questions

* 当前 `workflow-capability-audit` 与本仓库 skill 实现规范相比，缺口是结构性文档问题、行为契约遗漏，还是与脚本/测试的真实漂移。
* 若要修复 skill，本次是否需要同步补齐 `Output`/`Validation`/`Examples` 一类规范面，还是已有 `references/` 与 `tests/` 已足够覆盖。
* 当前隐藏目录中的平台 carrier 变化，是否已经完整体现在 skill 的说明、runbook 和测试场景中。

## Requirements

* 深度分析 `.trellis/` 与 `.claude/`、`.codex/`、`.opencode/`、`.qoder/`、`.kiro/`、`.agents/` 的 Trellis 接线机制，并把与目标 skill 相关的真实约束提炼出来。
* 审查 `workflow-capability-audit` 当前 entry artifact、references、tests、supplement spec、执行脚本之间的闭环一致性。
* 找出 skill 相对“仓库内 skill 实现规范”和“当前 Trellis 机制”的实际兼容缺口。
* 给出最小且可验证的兼容修正方案；如落地修改，必须同步更新所有必要副本和验证面。
* 修复不能引入新的额外问题，尤其不能造成 `.agents` / `.claude` 双副本漂移、skill 与 spec 漂移，或测试面缺失。

## Acceptance Criteria

* [ ] 给出当前仓库 Trellis 运行机制的结构化说明，并能解释它如何约束 `workflow-capability-audit`。
* [ ] 明确列出 `workflow-capability-audit` 当前存在的兼容/规范问题。
* [ ] 若实施修改，`.agents/skills/` 与 `.claude/skills/` 的 skill 副本、必要 references/tests 与 spec 保持同步。
* [ ] 若实施修改，相关验证命令结果明确记录为 pass / fail / not run。
* [ ] 最终输出包含具体兼容修正方案、已完成项、未完成项与剩余风险。

## Definition of Done

* 相关 skill 文档结构与仓库规范一致
* 必要的 spec / reference / tests 同步完成
* 运行相关验证命令并如实报告结果
* 最终说明能解释为何这些修正不会额外引入新问题

## Out of Scope

* 不把本次任务扩展为整个 `docs/workflows/新项目开发工作流/` 的全面兼容审计
* 不无证据改动 `workflow-capability-audit.py` 的运行逻辑，除非发现必须修正的行为级不一致
* 不引入新的平台支持范围或新的 workflow root 支持

## Technical Notes

* 关键规范：
  * `.trellis/spec/skills/index.md`
  * `.trellis/spec/skills/workflow-capability-audit.md`
  * `.trellis/spec/platforms/codex-workflow-behavior.md`
* 关键运行时：
  * `.trellis/config.yaml`
  * `.trellis/workflow.md`
  * `.trellis/scripts/common/active_task.py`
  * `.codex/config.toml`
  * `.codex/hooks.json`
  * `.claude/settings.json`
* 目标资产：
  * `.agents/skills/workflow-capability-audit/**`
  * `.claude/skills/workflow-capability-audit/**`
  * `docs/workflows/新项目开发工作流/commands/workflow-capability-audit.py`
  * `docs/workflows/新项目开发工作流/commands/test_workflow_capability_audit.py`
