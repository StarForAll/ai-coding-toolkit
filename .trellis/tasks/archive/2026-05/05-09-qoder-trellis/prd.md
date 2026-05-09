# 收口 qoder trellis 收尾兼容副本

## Goal

收口当前仓库中 Qoder 平台 Trellis 收尾相关入口的兼容副本，并同步修正收尾链路中 `finish-work` / `workflow.md` / 恢复指南之间的路径分叉，使其与当前 `.trellis` 运行机制、共享 skill 真源、以及恢复链路语义一致，避免继续传播旧的 `.current-task` / pre-commit checklist 语义，或继续保留 `add_session.py` 与 `record-session-helper.py` 的不一致。

## What I already know

- 当前仓库 Trellis 运行时以 `.trellis/.runtime/sessions/` 为 session-scoped active task 真源，不再以 repo-global `.trellis/.current-task` 为当前机制。
- `.agents/skills/trellis-finish-work/SKILL.md` 是当前共享的 `finish-work` 真源。
- `.agents/skills/record-session/SKILL.md` 已明确标成 legacy/manual fallback，并已切到 session-scoped pointer + helper/resume 语义。
- `.qoder/skills/trellis-finish-work/SKILL.md` 仍是旧的 pre-commit checklist，frontmatter 还是 `name: finish-work`。
- `.qoder/skills/record-session/SKILL.md` 仍保留旧 `.current-task` 与旧收尾校验方式。
- `docs/Trellis自动提交失败恢复与提权修复指南.md` 需要明确区分“当前状态”与“建议规则”，不能继续把已修正项写成未完成要求。
- `.trellis/workflow.md` 当前 wrap-up 链使用 `record-session-helper.py`，但共享 `trellis-finish-work` 真源与多个平台入口仍直接调用 `add_session.py`，存在真实路径分叉。

## Assumptions (temporary)

- 本次不改 `.trellis` 主运行时脚本，也不改 workflow 产品目录。
- `.qoder/skills/trellis-finish-work/SKILL.md` 与 `.qoder/skills/record-session/SKILL.md` 仍保留为兼容载体，而不是直接删除。

## Open Questions

- 无阻塞问题；范围和修正方向已明确。

## Requirements (evolving)

- 修正 `.qoder/skills/trellis-finish-work/SKILL.md`，使其语义与当前共享 `trellis-finish-work` 主链一致。
- 修正 `.qoder/skills/record-session/SKILL.md`，去掉旧 `.current-task` 语义，改为 session-scoped pointer 语义。
- 修正共享 `trellis-finish-work` 真源与各平台入口中的 Step 4 路径，使其与 `.trellis/workflow.md`、恢复指南、fallback 链一致。
- 同步更新 `docs/Trellis自动提交失败恢复与提权修复指南.md` 中对 Qoder 漂移现状的描述。
- 同步收口当前任务标题/PRD 中仍使用“漂移副本”的措辞。
- 处理根目录历史说明中容易误导当前机制判断的 `.current-task` 表述。

## Acceptance Criteria (evolving)

- [ ] `.qoder/skills/trellis-finish-work/SKILL.md` 不再保留旧 pre-commit checklist 主体，且 frontmatter 使用 `name: trellis-finish-work`
- [ ] `.qoder/skills/record-session/SKILL.md` 不再把 `.trellis/.current-task` 当作当前 close-out 校验依据
- [ ] 共享 `trellis-finish-work` 真源与当前维护的平台入口不再直接把 Step 4 写成 `add_session.py`
- [ ] 恢复指南中的“当前漂移现状”与修复后状态一致
- [ ] 对根目录历史说明补充足够边界，避免被误当作当前机制真源

## Definition of Done (team quality bar)

- 相关文档与 skill 副本语义一致
- 运行 `./scripts/validate-skills.sh` 通过
- 对改动文件运行 `git diff --check` 通过

## Out of Scope (explicit)

- 不修改 `docs/workflows/新项目开发工作流/**`
- 不重构 `.trellis/scripts/*`
- 不清理 `.codex/hooks/session-start.py` 等当前未接线但不错误的残留载体

## Technical Notes

- 共享 skill 真源：
  - `.agents/skills/trellis-finish-work/SKILL.md`
  - `.agents/skills/record-session/SKILL.md`
- 平台兼容副本：
  - `.qoder/skills/trellis-finish-work/SKILL.md`
  - `.qoder/skills/record-session/SKILL.md`
- 边界说明：
  - `AGENTS.md`
  - `.trellis/spec/docs/index.md`
  - `docs/Trellis自动提交失败恢复与提权修复指南.md`
