# PRD: Fix workflow-audit brainstorm reference names

## Problem

workflow-audit 的 SKILL.md、test、template 中引用的 brainstorm skill/command 名称与实际路径不一致：

| 位置 | 当前引用 | 实际路径 |
|---|---|---|
| `.agents/skills/workflow-audit/` 全部文件 | `brainstorm` | `.agents/skills/trellis-brainstorm/` |
| `.claude/skills/workflow-audit/` 全部文件 | `trellis:brainstorm` | 无 `.claude/commands/trellis/brainstorm.md`，skill 位于 `.claude/skills/trellis-brainstorm/` |
| spec Related Files | `.agents/skills/brainstorm/SKILL.md` | `.agents/skills/trellis-brainstorm/SKILL.md` |
| spec Related Files | `.claude/commands/trellis/brainstorm.md` | 不存在 |

运行时查找 brainstorm 入口会失败，导致 task-based 模式误触发 `Blocked / Dependency Unavailable`。

## Goal

将所有 brainstorm 引用更新为与实际路径一致的名称：

1. `.agents/` 侧：`brainstorm` → `trellis-brainstorm`
2. `.claude/` 侧：`trellis:brainstorm` → `trellis-brainstorm`（Claude Code 通过 skill 而非 slash command 消费该 skill）
3. spec Related Files：修正两条路径引用
4. spec Sync Rules 说明：更新示例，反映 `.agents/` 引用 `trellis-brainstorm` 而非 `brainstorm`

## Scope

涉及文件：
- `.trellis/spec/skills/workflow-audit.md`（行为语义层 + Related Files）
- `.claude/skills/workflow-audit/SKILL.md`
- `.agents/skills/workflow-audit/SKILL.md`
- `.claude/skills/workflow-audit/references/` 下 3 个含 brainstorm 引用的模板
- `.agents/skills/workflow-audit/references/` 下 3 个含 brainstorm 引用的模板
- `.claude/skills/workflow-audit/tests/` 下 5 个含 brainstorm 引用的测试
- `.agents/skills/workflow-audit/tests/` 下 5 个含 brainstorm 引用的测试

## Out of Scope

- 不创建 `.claude/commands/trellis/brainstorm.md`
- 不修改 workflow-capability-audit
- 不修改 workflow_assets.py

## Acceptance Criteria

- `.agents/` 侧全部文件中 brainstorm 引用名统一为 `trellis-brainstorm`
- `.claude/` 侧全部文件中 brainstorm 引用名统一为 `trellis-brainstorm`
- spec Related Files 路径指向实际存在的文件
- grep 验证无遗漏的旧引用
