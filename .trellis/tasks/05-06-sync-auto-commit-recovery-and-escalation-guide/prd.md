# 同步自动提交失败恢复与提权修复指南

## Goal

更新 `docs/Trellis自动提交失败恢复与提权修复指南.md`，让它和本仓库当前实际使用的 Trellis 自动提交恢复链路、命令入口、平台覆盖面、验证方式保持一致，避免继续描述已经退役或与现状不符的路径。

## What I already know

- 目标文档已经存在，且定位为“可迁移到其他 Trellis 项目的独立修复指南”。
- 当前仓库已经实现两条恢复链：
  - `task.py archive` / `archive-commit-only`
  - `record-session-helper.py --resume` + `TRELLIS_AUTO_ESCALATE_COMMAND=...`
- `finish-work` 当前活跃入口存在于 `.agents/skills/trellis-finish-work/SKILL.md`、`.claude/commands/trellis/finish-work.md`、`.opencode/commands/trellis/finish-work.md`、`.qoder/commands/trellis-finish-work.md`。
- `.qoder/skills/trellis-finish-work/SKILL.md` 虽仍存在，但 frontmatter 是 `name: finish-work`、正文却是旧 pre-commit checklist，不能作为当前收尾主链入口。
- Qoder 目录下仍存在 `.qoder/skills/record-session/SKILL.md`，其内容与当前 `finish-work` 主链不一致，属于遗留入口；相比之下，`.agents/skills/record-session/SKILL.md` 已明确标成 legacy/manual fallback。
- 文档中“至少覆盖的平台”示例只列了 `.claude` 和 `.opencode`，未反映当前项目也维护 `.qoder` 面。

## Assumptions

- 用户要同步的是文档事实描述，而不是在本次任务里继续修改脚本实现。
- 这次变更以单文档更新为主，只在发现强耦合引用必须同步时再扩大范围。

## Open Questions

- 无阻塞问题；需求已经足够明确。

## Requirements

- [ ] 核对目标文档中所有“当前项目已采用/实际使用”的描述是否与仓库现状一致。
- [ ] 明确区分“当前仓库现状”和“可迁移到其他项目的最小改动包”。
- [ ] 同步平台入口覆盖面、遗留 `record-session` 现状、推荐验证命令与实际脚本调用方式。
- [ ] 避免把已退役路径继续表述成当前主路径。

## Acceptance Criteria

- [ ] `docs/Trellis自动提交失败恢复与提权修复指南.md` 中对脚本、命令和平台入口的描述可被当前仓库文件直接证实。
- [ ] 文档不再遗漏当前维护中的 `.qoder` 入口面。
- [ ] 文档对遗留 `record-session` 的表述与当前仓库状态一致，不再误导为主路径。
- [ ] 相关校验命令已实际运行并记录结果。

## Definition of Done

- 文档内容完成更新
- 相关检查命令已运行
- 结果如实记录为 pass / fail / not run

## Out of Scope

- 不修改自动提交实现逻辑本身
- 不处理与本任务无关的其他文档漂移

## Technical Notes

- 关键现状文件：
  - `docs/Trellis自动提交失败恢复与提权修复指南.md`
  - `.trellis/scripts/common/task_store.py`
  - `.trellis/scripts/task.py`
  - `.trellis/scripts/add_session.py`
  - `.trellis/scripts/workflow/record-session-helper.py`
  - `.trellis/scripts/workflow/metadata-autocommit-guard.py`
  - `.agents/skills/trellis-finish-work/SKILL.md`
  - `.claude/commands/trellis/finish-work.md`
  - `.opencode/commands/trellis/finish-work.md`
  - `.qoder/commands/trellis-finish-work.md`
  - `.qoder/skills/trellis-finish-work/SKILL.md`
  - `.agents/skills/record-session/SKILL.md`
  - `.qoder/skills/record-session/SKILL.md`
