# PRD: Clarify workflow-audit Three-Platform Scope

## Problem

`workflow-audit` 的 spec（`.trellis/spec/skills/workflow-audit.md`）已声明 supported surface 限于 Claude Code / OpenCode / Codex，且标注 "other CLIs are out of scope unless workflow_assets.py adds them"。但缺少显式列举排除的目录名和排除原因，导致：

1. 后续审计容易将 `.kiro/`、`.qoder/`、`.opencode/`(skill 路径) 等目录下无 workflow-audit 副本误判为覆盖缺失
2. 每次审计都需重新推导"为什么只覆盖三个平台"

## Goal

在 spec 的 Version Gate and Supported Surface 章节补充：

1. 显式列举当前排除的 repo-local CLI 目录（`.kiro/`, `.qoder/`）及排除原因
2. 说明 OpenCode/Codex 通过 `.opencode/` / `.codex/` / `.agents/` 路径承载，它们属于 trellis 管理面而非独立 CLI skill 部署面
3. 明确：三个平台覆盖是 design decision，不是缺漏，后续扩展仅由 `workflow_assets.py` 的 managed surface 合约驱动

## Scope

仅修改 `.trellis/spec/skills/workflow-audit.md` 的 "Version Gate and Supported Surface" 章节，追加 1-2 段说明。

同步更新 `.claude/skills/workflow-audit/SKILL.md` 和 `.agents/skills/workflow-audit/SKILL.md` 中对应章节（行为语义一致）。

## Out of Scope

- 不改动 workflow_assets.py
- 不在其他 CLI 目录部署 workflow-audit skill
- 不改动 workflow-capability-audit

## Acceptance Criteria

- spec 明确列出排除的 CLI 目录名和排除原因
- 三份文件（spec + 两个 SKILL.md）保持行为语义同步
- 修改后，审计者不会再将 .kiro/.qoder 下无 skill 副本视为缺陷
