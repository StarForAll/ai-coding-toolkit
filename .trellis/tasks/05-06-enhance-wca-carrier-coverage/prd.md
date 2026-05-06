# enhance(workflow-capability-audit): 补齐 Claude/OpenCode 原生 skills 载体及次要 carrier 覆盖

## Problem

Trellis 0.5 基线创建了以下 carrier 表面，但 `build_workflow_dependent_rows()` 的 seed list 未覆盖：

1. `.claude/skills/` — Claude 原生 skills 载体（trellis-check、trellis-before-dev 等）
2. `.opencode/skills/` — OpenCode 原生 skills 载体
3. `.opencode/lib/` — OpenCode helper libraries（trellis-context.js、session-utils.js）
4. `.trellis/hooks/` — Trellis-side hooks 目录

此外，"claude-hooks-and-settings-carrier" 的 Claude evidence paths 包含 `.claude/hooks`（目录存在性检查），但不追踪具体 hook 脚本文件（inject-workflow-state.py、session-start.py、inject-subagent-context.py），导致目录存在但脚本缺失时仍显示 "adopted-compatible"。

## Impact

- 如果 Trellis 新版本改变了原生 skills 载体结构（新增/删除/重命名 skills），审计矩阵无法发现此变化
- hooks 目录粒度不足可能在基线矩阵中产生误导性 "adopted-compatible" 分类

## Requirements

1. 在 `build_workflow_dependent_rows()` 中新增 carrier 条目：
   - `claude-native-skills-carrier`：追踪 `.claude/skills/`
   - `opencode-native-skills-carrier`：追踪 `.opencode/skills/`
   - `opencode-lib-carrier`：追踪 `.opencode/lib/`
   - `trellis-hooks-carrier`：追踪 `.trellis/hooks/`

2. 更新 "claude-hooks-and-settings-carrier" 的 Claude evidence paths，将具体 hook 脚本文件加入追踪：
   - `.claude/hooks/inject-workflow-state.py`
   - `.claude/hooks/session-start.py`
   - `.claude/hooks/inject-subagent-context.py`
   - 保留 `.claude/settings.json` 和 `.claude/hooks`（目录级）

3. 同步更新 Spec 中的 "First-version dependent-surface coverage" 列表（`.trellis/spec/skills/workflow-capability-audit.md`）

4. 同步更新 SKILL.md 中 step A 描述的 carrier 名称列表

5. 补充或更新 scenario test 覆盖新增 carrier

## Scope

- `docs/workflows/新项目开发工作流/commands/workflow-capability-audit.py` — 扩展 seed list + hooks evidence paths
- `docs/workflows/新项目开发工作流/commands/test_workflow_capability_audit.py` — 补充/更新测试
- `.trellis/spec/skills/workflow-capability-audit.md` — 更新 carrier 列表
- `.claude/skills/workflow-capability-audit/SKILL.md` — 更新 carrier 名称列表
- `.agents/skills/workflow-capability-audit/SKILL.md` — 镜像同步
- 相关 references/tests — 同步更新

## Out of Scope

- anchor write-back bug 修复（属于 05-06-fix-wca-anchor-no-fix）
- managed-surface 行扩展（当前仅涉及 dependent-surface carrier）
