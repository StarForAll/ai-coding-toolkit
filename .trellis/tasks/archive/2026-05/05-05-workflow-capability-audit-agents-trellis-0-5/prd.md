# workflow-capability-audit: 新项目开发工作流升级到 agents + Trellis 0.5 兼容

## Goal

让 `docs/workflows/新项目开发工作流/` 在 `Trellis 0.5.x` 基线上完成一次真实的升级兼容改造，重点解决 Codex 载体模型从旧 shared-skill baseline 迁移到新 `trellis-*` skill + `trellis-*` agent 体系后的失配问题，并让 `workflow-capability-audit` / installer / upgrade 分析重新可运行。

## What I already know

* 版本门禁已通过：当前 `trellis -v` 为 `0.5.0-rc.3`，工作流锚点 `COMPATIBLE_TRELLIS_VERSION` 为 `0.4.0`。
* canonical audit 脚本 `docs/workflows/新项目开发工作流/commands/workflow-capability-audit.py --current-cli codex --json` 在受限沙箱里会因为 `trellis init` 的 Python 探测失败；在非沙箱环境里能进入 A/B 创建，但会在安装工作流到 `B` 时失败。
* 非沙箱下的真实失败点是：当前安装器仍要求 Codex 活动 skills 目录中存在 `start` / `finish-work` baseline skill，而 `Trellis 0.5.0-rc.3` 新基线中已经不存在这些 plain shared skills。
* 真实 `trellis init --claude --opencode --codex -u xzc -y` 新基线证据：
  * `.agents/skills/` 只包含 `trellis-before-dev`、`trellis-brainstorm`、`trellis-break-loop`、`trellis-check`、`trellis-continue`、`trellis-finish-work`、`trellis-meta`、`trellis-update-spec`
  * `.codex/agents/` 包含 `trellis-research.toml`、`trellis-implement.toml`、`trellis-check.toml`
  * `.codex/` 仍有 `config.toml`、`hooks.json`、`hooks/session-start.py`、`hooks/inject-workflow-state.py`
  * `AGENTS.md` 仍声明 `.agents/skills/` 与 `.codex/agents/` 是 Codex 的项目级工作流载体
* 现有源码中仍有大量旧假设：
  * `workflow_assets.py` 仍声明 `CODEX_PATCH_BASELINE_SKILLS = ["start", "finish-work"]`
  * `install-workflow.py` 在 Codex 路径上仍将 `start` / `finish-work` 视为必须存在的 baseline shared skills
  * `upgrade-compat.py` 与若干测试仍围绕 `.agents/skills/start`、`.agents/skills/finish-work` 建模
  * `workflow-capability-audit.py` 当前仍把 `.agents/skills/` 当成 OpenCode/Codex 的 shared-skills carrier，但尚未体现新 `trellis-*` baseline 与 agent-first 关系

## Assumptions (temporary)

* 对 `Trellis 0.5.x`，Codex 的 workflow 基线入口应以 `trellis-*` skills 为 baseline，而不是 plain `start` / `finish-work` shared skills。
* 本次工作优先修通“能力审计 + 安装/升级兼容”闭环，不在本任务内完成完整的文案重写，除非它是测试或行为正确性所必需。
* 若 workflow 自身仍需要自定义 phase router / check / delivery 等能力，Codex 侧应继续通过 workflow 自己写入 `.agents/skills/<phase>/SKILL.md` 或等价载体承载，但不能再假设 baseline 已经有 plain `start` / `finish-work`。

## Open Questions

* Codex 在这个工作流产品里，最终要保留 plain phase skills（如 `brainstorm`、`check`、`delivery`），还是要全面切到 `trellis-*` 入口再由路由层映射？先以代码与测试现实约束收敛。
* `workflow-capability-audit` 的 dependent capability 命名是否需要从 “shared-skills-deployment-carrier” 扩展为更明确的 “trellis-skills + implementation-agents + codex-hooks” 组合模型。

## Requirements

* 基于真实 `Trellis 0.5.0-rc.3` 基线重新定义 Codex 的兼容载体假设。
* 修复 `install-workflow.py`，使其不再错误要求缺失的 plain Codex baseline skills。
* 修复 `upgrade-compat.py` / `analyze-upgrade` 相关逻辑，使其对 Codex baseline 与 drift 分析符合新载体模型。
* 修复 `workflow-capability-audit.py` 或其支撑定义，使 canonical audit 能创建 A/B、安装 workflow、生成初始 `capability-report.md`。
* 更新相应测试，至少覆盖：
  * 安装器不再因为缺少 plain `finish-work` / `start` skill 而失败
  * Codex 基线与 workflow 共享 skills / agents 的新分析路径
  * capability audit 在新基线下可完成初始报告

## Acceptance Criteria

* [ ] `workflow-capability-audit.py --current-cli codex --json` 在非沙箱环境下能够完成完整初始审计并生成 `capability-report.md`
* [ ] Codex 兼容逻辑不再依赖不存在的 `.agents/skills/start/SKILL.md` 与 `.agents/skills/finish-work/SKILL.md` baseline
* [ ] 相关单元测试覆盖新基线模型并通过
* [ ] 若发现 durable knowledge，补充到相关 spec 或任务 research 中

## Definition of Done

* 相关 Python 脚本测试通过
* 变更后的行为与真实 `trellis init` 新基线一致
* 输出明确区分已完成、未完成、风险和后续动作

## Out of Scope

* 提升 `COMPATIBLE_TRELLIS_VERSION` 到 `0.5.0-rc.3` 的最终版本锚点晋升
* 与本次 Codex/agent 迁移无关的 workflow 文案重构
* 生产化提交与任务归档

## Technical Notes

* 关键文件：
  * `docs/workflows/新项目开发工作流/commands/workflow_assets.py`
  * `docs/workflows/新项目开发工作流/commands/install-workflow.py`
  * `docs/workflows/新项目开发工作流/commands/upgrade-compat.py`
  * `docs/workflows/新项目开发工作流/commands/workflow-capability-audit.py`
  * `docs/workflows/新项目开发工作流/commands/test_workflow_installers.py`
  * `docs/workflows/新项目开发工作流/commands/test_upgrade_analysis.py`
  * `docs/workflows/新项目开发工作流/commands/test_workflow_capability_audit.py`
* 真实基线 fixture：`/tmp/trellis-0-5-baseline-p2fO5L`
* 失败证据摘要已记录在 `research/baseline-findings.md`
