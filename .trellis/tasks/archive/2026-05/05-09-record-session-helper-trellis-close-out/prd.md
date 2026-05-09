# 移除 record-session-helper 并恢复 Trellis 原生 close-out，含临时项目嵌入验证

## Goal

将当前仓库及 `docs/workflows/新项目开发工作流/` 中围绕 `record-session-helper.py` 的 close-out 设计恢复到 Trellis 0.5.9 原生能力，避免继续维护 Codex 专属 helper / metadata closure 分支；同时确保 workflow 源资产、安装/升级脚本、规范、文档与测试保持一致，并在 `/tmp/trellis-0.5.9` 临时项目上完成一次嵌入链路验证。

## What I already know

- 当前仓库内 `record-session-helper.py` 已不是孤立脚本，而是被写入 Codex skill、workflow 文档、安装器清单、升级检查、spec 契约和测试断言。
- 当前源仓库的 Codex 侧 `trellis-finish-work` 仍要求 helper，并采用“先 record，再 archive”的顺序。
- 当前源仓库的 Claude / OpenCode `finish-work` 已走 Trellis 原生 `add_session.py`，并采用“先 archive，再 add_session”的顺序。
- `/tmp/trellis-0.5.9` 已存在，可作为 Trellis 0.5.9 临时目标项目基线。
- `/tmp/trellis-0.5.9/.agents/skills/trellis-finish-work/SKILL.md`、`/.claude/commands/trellis/finish-work.md` 与 `/.trellis/scripts/add_session.py` 显示 Trellis 0.5.9 原生 close-out 路径为 `add_session.py`，不依赖 `record-session-helper.py`。
- `docs/workflows/新项目开发工作流/工作流嵌入执行规范.md` 与 `commands/install-workflow.py` 当前都明确要求：formal embed 不应由 Codex 主导执行。

## Assumptions (temporary)

- 本次“直接使用 Trellis 原生能力”不仅指当前源仓库 repo-local close-out，也指 `docs/workflows/新项目开发工作流/` 产物在目标项目中的 close-out 合同应回到 Trellis 原生 `finish-work` / `add_session.py` 路径。
- 历史归档与备份目录中的 helper 提及属于历史证据，不作为本轮活动源资产清理目标。
- `/tmp/trellis-0.5.9` 的验证应优先使用该目录现有基线，而不是重新创建新的临时项目。

## Open Questions

- 无阻塞产品决策；formal embed 验证按既有边界执行到正式嵌入前即停止，并给出可直接让用户在其他 CLI 中执行的 handoff 语句与命令。

## Requirements (evolving)

- 移除当前仓库活动源资产中对 `record-session-helper.py` 的运行时依赖。
- 不再保留 helper / recovery / metadata-closure 作为 close-out 辅助路径。
- 恢复 repo-local close-out 到 Trellis 原生 `finish-work` / `add_session.py` 路径。
- 恢复 `docs/workflows/新项目开发工作流/` 的目标项目 close-out 契约到 Trellis 原生 `finish-work`，而不是简单删除 helper 字样。
- 同步更新 workflow 安装/升级/检查脚本中的 helper 清单、分发逻辑、健康检查与测试断言。
- 同步更新 `.trellis/spec/`、workflow 文档、平台说明，消除“代码已删但规范仍要求 helper”的契约漂移。
- 修改完成后对 `docs/workflows/新项目开发工作流/` 进行嵌入链路验证，目标项目固定为 `/tmp/trellis-0.5.9`。
- runtime 验证保持现有合同：不改“Codex 不主导 formal embed”的边界。
- 在 `/tmp/trellis-0.5.9` 验证时，可执行到 formal embed 前的检测/预演步骤；在正式安装步骤前必须停下，并输出适合用户在 Claude Code / OpenCode / shell 中继续执行的 handoff 语句。

## Acceptance Criteria (evolving)

- [ ] 活动源资产中不再把 `record-session-helper.py` 作为 close-out 主入口或辅助入口。
- [ ] `trellis-finish-work`、相关 workflow command docs、安装器与升级检查对 close-out 的描述一致，并与 Trellis 0.5.9 原生 `finish-work` 行为对齐。
- [ ] `workflow_assets.py`、`install-workflow.py`、`upgrade-compat.py`、相关 helper/test 文件不再要求部署 `record-session-helper.py`。
- [ ] 相关 spec 与文档不再把 helper 当作当前 fresh baseline 契约。
- [ ] 相关自动化验证通过。
- [ ] 在 `/tmp/trellis-0.5.9` 上完成约定范围内的 workflow 嵌入前验证，并记录 formal embed handoff 语句、推荐执行命令、实际停止边界与结果。

## Definition of Done (team quality bar)

- Tests added/updated where needed
- Relevant validation commands run with results recorded truthfully
- Docs/specs updated where behavior changed
- Runtime embed pre-flight verification performed, with explicit external-CLI handoff before formal embed

## Out of Scope (explicit)

- 不清理 `.trellis/tasks/archive/**` 与 `.trellis/.backup-*/**` 中的历史文本证据。
- 不顺带重构与本次 helper 去除无关的 workflow 阶段逻辑。
- 不在本轮内修改 Trellis 上游源码或 `/tmp/trellis-0.5.9` 之外的其他临时项目。

## Technical Notes

- 关键源文件：`docs/workflows/新项目开发工作流/commands/workflow_assets.py`、`install-workflow.py`、`upgrade-compat.py`、`commands/shell/record-session-helper.py`、`commands/shell/metadata-autocommit-guard.py`
- 关键 repo-local 入口：`.agents/skills/trellis-finish-work/SKILL.md`、`.agents/skills/record-session/SKILL.md`、`AGENTS.md`
- 关键规范：`.trellis/spec/scripts/workflow-installer-upgrade-contracts.md`、`.trellis/spec/docs/index.md`、`.trellis/spec/commands/index.md`、`.trellis/spec/platforms/codex-workflow-behavior.md`
- 嵌入验证合同：`docs/workflows/新项目开发工作流/工作流嵌入执行规范.md`
- 已确认验证边界：保留现有“Codex 不主导 formal embed”合同；本轮只执行到 formal embed 前，并提供外部 CLI handoff 文案
