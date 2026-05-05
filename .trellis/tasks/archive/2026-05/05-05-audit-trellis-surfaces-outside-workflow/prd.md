# audit trellis surfaces outside workflow

## Goal

对当前仓库中的 Trellis 使用实现做一次深度审计，建立 `.trellis/` 与各隐藏平台目录的实际运行机制图谱，找出所有与 Trellis 关联但不属于 `workflow-audit` / `workflow-capability-audit` / `docs/workflows/新项目开发工作流` 的文件或目录，并判断哪些需要修正、为什么需要修正、应该如何修正。

## What I already know

* 当前仓库中的 Trellis 不是只存在于 `docs/workflows/新项目开发工作流`，而是由 `.trellis/` 运行层加 `.codex/`、`.claude/`、`.opencode/`、`.kiro/`、`.qoder/`、`.agents/skills/` 等平台接入层共同构成。
* `.trellis/workflow.md` 定义流程、Phase Index 与 `[workflow-state:*]` 块；`.trellis/scripts/` 提供 active task、session context、task lifecycle、workflow-phase 提取等实际运行逻辑。
* 当前项目内 `.trellis/.version` 为 `0.5.0-rc.3`。
* 本机 `trellis` CLI 执行 `trellis --help` 时提示 CLI 为 `0.4.0`，与项目版本不一致。
* 审计起点时仓库存在 `.new` 文件、多个 `.trellis/.backup-*` 目录、散落在 live 平台目录中的 `.backup` 文件，以及大量 `__pycache__`；当前 cleanup 后 live `.new` 已清零、live 平台目录散落 `.backup` 已删除，仅保留最新 `.trellis/.backup-*` 与忽略项 `__pycache__`。

## Assumptions (temporary)

* `__pycache__/` 目录属于运行缓存或可忽略产物，不作为 Trellis 机制漂移问题处理。
* `.trellis/.backup-*` 目录按当前治理目标只应保留最新一个，其余属于待清理历史残留。
* `.new` 文件不能统一判定为“应直接采纳”或“应直接删除”，必须逐个对比 live 文件与当前仓库契约后做决策。
* 不同平台下 agent/skill/command 文案或加载方式的差异，部分可能来自平台能力差异，部分可能来自升级未收敛或维护漂移，必须区分归因。

## Open Questions

* 无阻塞问题。当前范围和判断边界已足够继续审计。

## Requirements (evolving)

* 系统梳理 `.trellis/` 的运行机制，包括 workflow、task runtime、session context、active task、spec、library-lock、template-hash、hooks/support scripts。
* 系统梳理 `.codex/`、`.claude/`、`.opencode/`、`.kiro/`、`.qoder/`、`.agents/skills/` 等隐藏目录中 Trellis 接入面的实际职责。
* 枚举当前项目下所有与 Trellis 关联、但不属于 `workflow-audit` / `workflow-capability-audit` / `docs/workflows/新项目开发工作流` 的文件。
* 对本次审计中发现的 `.new` 文件逐个做“采纳 / 部分吸收 / 丢弃”的判断，并给出依据。
* 对跨平台 agent 差异逐项判断：是平台能力差异导致，还是维护漂移导致。
* 对 backup 策略给出明确建议：只保留哪个备份、其余如何处理。
* 明确哪些项需要立即修正，哪些项应记录但可暂缓。

## Acceptance Criteria (evolving)

* [ ] 输出当前仓库 Trellis 运行机制的分层说明，并指出关键实现文件。
* [ ] 输出一份“仓库内 Trellis 关联面”清单，且已排除 `workflow-audit` / `workflow-capability-audit` / `docs/workflows/新项目开发工作流`。
* [ ] 对本次审计中发现的 `.new` 文件逐一形成处理建议，并记录最终处置。
* [ ] 对跨平台 agent 差异逐项形成归因判断。
* [ ] 对 backup 保留策略形成明确结论。
* [ ] 最终建议区分“必须修”“建议修”“不建议修/忽略”。

## Definition of Done (team quality bar)

* 审计结论有对应的仓库证据支撑
* 文件路径与机制描述准确
* 不把缓存/忽略项误报为机制问题
* 修正建议能直接转化为后续执行任务

## Out of Scope (explicit)

* 不分析 `workflow-audit` 与 `workflow-capability-audit` 两个 skill 本身的行为正确性
* 不分析 `docs/workflows/新项目开发工作流` 目录内部工作流产品资产的业务逻辑
* 本任务当前阶段不直接修改 Trellis 实现文件，先完成审计与修正方案判断

## Technical Notes

* 关键 live 机制入口：
  * `.trellis/workflow.md`
  * `.trellis/config.yaml`
  * `.trellis/scripts/common/active_task.py`
  * `.trellis/scripts/common/session_context.py`
  * `.trellis/scripts/common/workflow_phase.py`
  * `.trellis/scripts/task.py`
* 关键平台接入入口：
  * `.codex/hooks.json`
  * `.claude/settings.json`
  * `.qoder/settings.json`
  * `.opencode/plugins/*.js`
  * `.kiro/agents/*.json`
  * `.codex/agents/*.toml`
* 当前用户已明确判定边界：
  * `__pycache__/` 忽略
  * backup 只保留最新版本
  * `.new` 文件需要一一判断
  * 平台 agent 差异必须先判断是否由平台差异导致
