# 收敛 Trellis 升级引起的 git diff 并保留原编号

## Goal

收敛当前仓库因 Trellis 升级产生的工作树变更，保留确属正常升级的 runtime / hook / agent context 改动，回退与当前仓库合同不一致的阶段编号漂移，并按仓库既有规则处理 `.new` 候选文件与模板哈希派生文件。

## What I already know

* 当前工作树包含 57 个已跟踪修改和 9 个未跟踪 `.new` 文件，变化覆盖 `.agents/`、`.claude/`、`.codex/`、`.kiro/`、`.opencode/`、`.qoder/`、`.trellis/`。
* `.trellis/.version` 从 `0.5.0-rc.3` 升至 `0.5.0-rc.5`。
* 多个平台 hook 新增 `TRELLIS_HOOKS=0` / `TRELLIS_DISABLE_HOOKS=1` 的短路逻辑，属于一致性的 runtime 增强。
* `.trellis/scripts/common/active_task.py` 新增 `session-fallback` 解析逻辑，用于 class-2 子代理拿不到父会话 id 时，从唯一 session 文件推断当前任务。
* `.codex/agents/trellis-implement.toml`、`.codex/agents/trellis-check.toml`、`.qoder/agents/*` 对 class-2 平台新增 “先看 dispatch prompt，再 fallback 到 `task.py current --source`” 的任务路径解析说明。
* 多处文档/技能/命令文件把原有阶段编号改成了 `1.3/1.4/3.4` 等新口径。
* 当前 live `.trellis/workflow.md` 仍将计划阶段摘要表述为 “PRD、curate context、activate task”，并将 Finish 概括为 “Commit code, then archive + record session via /finish-work”。
* 仓库已有审计明确记录：`.trellis/workflow.md.new` 的 `3.1 -> 3.4` 与 `.trellis/scripts/task.py.new` 的 `1.2 -> 1.3` 属于不应盲合并的 phase-number drift。
* `.agents/skills/trellis-meta/references/local-architecture/generated-files.md` 已明确：当模板文件被用户修改时，`trellis update` 生成 `.new` 是正常保护行为，不代表这些文件应直接采用。

## Assumptions (temporary)

* 本任务应以当前仓库 live 合同为准，阶段编号继续使用原口径，而不是接受升级候选带来的新编号体系。
* `.new` 文件不是本次必须全部合并的“必选更新”；它们需要逐个判断并按当前合同处理。

## Open Questions

* 当前无阻塞性开放问题；`.new` 文件按实际差异逐个判断处理，不采用统一策略。

## Requirements

* 保留 `0.5.0-rc.5` 版本升级和与之配套的正常 runtime 兼容增强。
* 保留 `active_task` 的 `session-fallback` 逻辑。
* 保留 class-2 子代理新的任务定位说明。
* 回退所有阶段编号漂移，统一继续使用仓库原本编号口径。
* 去掉明显无价值的格式噪音，例如多余反引号。
* 每个 `.new` 文件都要基于实际差异单独判断：删除、保留待后续、择一采用，或与 live 文件合并。
* 在最终内容稳定后，同步 `.trellis/.template-hashes.json`。

## Acceptance Criteria

* [ ] 所有保留的 runtime / hook / agent context 改动仍在工作树中
* [ ] 所有 live 文件中的阶段编号恢复为仓库原本口径
* [ ] 不再保留无意义格式噪音
* [ ] 每个 `.new` 文件都按个别判断完成处理，并有一致、可解释的处置结果
* [ ] `.trellis/.template-hashes.json` 与最终保留文件一致

## Definition of Done (team quality bar)

* Relevant validations or consistency checks are run
* Resulting diff matches the intended classification
* No unrelated file changes are reverted
* Notes remain aligned with current workflow contract

## Out of Scope (explicit)

* 重写 `.trellis/workflow.md` 为一套新编号体系
* 接受未审查的 `.new` 候选内容
* 对与本次升级 diff 无关的历史脏工作树做清理

## Technical Notes

* 关键依据文件：
  * `.trellis/workflow.md`
  * `.trellis/tasks/archive/2026-05/05-05-audit-trellis-surfaces-outside-workflow/research/trellis-residual-surfaces.md`
  * `.agents/skills/trellis-meta/references/local-architecture/generated-files.md`
* 已定位的主要受影响 live 文件：
  * `.agents/skills/trellis-continue/SKILL.md`
  * `.claude/commands/trellis/continue.md`
  * `.opencode/commands/trellis/continue.md`
  * `.kiro/skills/trellis-continue/SKILL.md`
  * `.qoder/commands/trellis-continue.md`
  * `.qoder/hooks/session-start.py`
  * `.opencode/lib/session-utils.js`
  * `.kiro/hooks/inject-subagent-context.py`
  * `.agents/skills/trellis-finish-work/SKILL.md`
  * `.kiro/skills/trellis-finish-work/SKILL.md`
  * `.qoder/commands/trellis-finish-work.md`
