# workflow-audit: 新项目开发工作流 runtime embed validation

## Goal

基于现有临时目标项目 `/tmp/trellis-0.5.14-1`，验证 `docs/workflows/新项目开发工作流/` 在真实 Trellis 基线上嵌入后，目标项目中的 `AGENTS.md` 是否会与当前 workflow 产生冲突、分歧或漂移；本轮重点是运行态证据，而不是只看 source repo 静态文档。

## What I already know

* workflow 审计目标固定为 `docs/workflows/新项目开发工作流/`
* `COMPATIBLE_TRELLIS_VERSION` 为 `0.5.14`
* 本机 `trellis -v` 为 `0.5.15`
* 用户已明确允许本次审计忽略当前同 `major.minor` 的稳定 patch 差异；该放行仅限本轮审计，不构成兼容性背书
* 已完成一轮轻量静态审计，确认安装器只托管 `AGENTS.md` 中的 `workflow-nl-routing` 标记块，而不是整文件覆盖
* 用户要求不要预设 `CLAUDE.md` 必需，而是先基于现有 Trellis 目标项目与真实嵌入行为判断
* 当前主执行 CLI 是 Codex；按 `workflow-audit` 合同，若进入 formal embed step，需要在 Codex 边界停下并交接到 Claude Code 或 OpenCode 主会话

## Assumptions (temporary)

* `/tmp/trellis-0.5.14-1` 存在且可读
* `/tmp/trellis-0.5.14-1` 代表一个可用于 runtime 审计的 target project，而不是 source repo 副本
* 若该目标项目的 `.trellis/.version` 与当前 `trellis -v` 不一致，则需要按 `workflow-audit` 合同停止为 `Blocked / Version Drift`

## Open Questions

* `/tmp/trellis-0.5.14-1` 当前是否仍处于 clean `trellis init` baseline
* `/tmp/trellis-0.5.14-1/.trellis/.version` 是否与当前本机 `trellis -v` 一致
* 在 Codex 边界前，`detect-embed-state.py` 与 `install-workflow.py --dry-run` 对该目标项目给出的结论是什么
* 若 runtime 链路进入 formal embed step，是否需要交接到 Claude Code / OpenCode 才能继续收集最终证据

## Requirements (evolving)

* 必须先核对 `/tmp/trellis-0.5.14-1` 的 Trellis 基线状态
* 必须区分 `source repo`、`generated target project baseline`、`generated target project workflow-installed state`、`runtime command output`
* 必须重点判断 `AGENTS.md` 在目标项目中的真实落盘、校验、恢复、卸载行为
* 必须判断该行为是否与当前 workflow 文档、安装器合同和实际 CLI 入口模型一致
* 若运行到 Codex formal embed boundary，必须按合同停下并输出交接要求

## Acceptance Criteria (evolving)

* [ ] 已记录 `/tmp/trellis-0.5.14-1` 的存在性、Git/Trellis 基线状态和 `.trellis/.version`
* [ ] 已执行与记录 runtime 前置命令结果（至少包含 `detect-embed-state.py`，必要时含 `install-workflow.py --dry-run`）
* [ ] 已把静态审计结论与 `/tmp` 运行态证据合并到 `audit-report.md`
* [ ] 已明确当前是否存在 `AGENTS.md` 冲突 / 分歧 / 漂移的 confirmed issue
* [ ] 若被 Codex boundary 或 version drift 阻断，已形成可执行的 stop reason 和下一步建议

## Definition of Done (team quality bar)

* 审计结论基于真实证据，不靠记忆补洞
* 引用的 source repo / target project / runtime output 边界清晰
* 若 runtime 审计未完成，阻断原因和未验证项明确
* 审计报告能指导后续是否需要修脚本、修文档或做交接验证

## Out of Scope (explicit)

* 本轮不直接修改 workflow 源文件
* 本轮不重写 `COMPATIBLE_TRELLIS_VERSION`
* 本轮不绕过 Codex formal embed handoff 合同

## Technical Notes

* 关键 source files:
  * `docs/workflows/新项目开发工作流/commands/install-workflow.py`
  * `docs/workflows/新项目开发工作流/commands/upgrade-compat.py`
  * `docs/workflows/新项目开发工作流/commands/detect-embed-state.py`
  * `docs/workflows/新项目开发工作流/commands/workflow_assets.py`
  * `docs/workflows/新项目开发工作流/CLI原生适配边界矩阵.md`
  * `docs/workflows/新项目开发工作流/装后隐藏目录与托管边界核对清单.md`
* 官方对照来源:
  * Claude Code `CLAUDE.md` docs
  * OpenCode Rules / Skills docs
  * OpenAI Codex `AGENTS.md` / Hooks docs
