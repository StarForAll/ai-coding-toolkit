# workflow-audit-新项目开发工作流

## Goal

基于当前 Trellis `0.5.10` 的原生能力，审计 `docs/workflows/新项目开发工作流/` 在同版本前提下的维护质量，判断其中哪些设计是必要增强，哪些已经变成多余、错误、重复或不再需要的兼容层，并通过真实 `/tmp` 目标项目运行链路验证关键判断，而不是只依赖静态文档口径。

## What I already know

- 当前审计目标已固定绑定到 `docs/workflows/新项目开发工作流/`
- `docs/workflows/新项目开发工作流/commands/workflow_assets.py` 声明 `COMPATIBLE_TRELLIS_VERSION = "0.5.10"`
- 本机 `trellis -v` 输出为 `0.5.10`，不存在版本漂移，可继续进入同版本维护审计
- 当前 workflow 明确不是全量自维护 agent overlay，而是建立在 Trellis 原生能力之上的 subset：
  - 依赖 Trellis 原生 `trellis-implement` / `trellis-check`
  - 额外同步增强版 `trellis-research`
  - 继续维护 Claude/OpenCode/Codex 的阶段命令/skills、close-out patch、NL routing、workflow patch、helper scripts 等
- `install-workflow.py` 对首次 formal embed 有显式 Codex 门禁：未设置 `WORKFLOW_EMBED_EXECUTOR_CONFIRMED=1` 时拒绝正式安装；`--dry-run` 可继续
- `install-workflow.py` 的 Codex 策略是：
  - 共享 workflow skills 只写入 `.agents/skills/`
  - `.codex/skills/` 作为条件性 secondary carrier，只清理重复 shared skills
  - `trellis-continue` / `trellis-finish-work` patch 只打在活动 skills 目录
  - `parallel` 入口若存在则移除并保留备份
- `upgrade-compat.py --check` 被工作流定义为装后核对主入口，负责检查 shared skills/commands、baseline patch、helper scripts、workflow patch、NL routing、retired helper 残留等

## Assumptions (temporary)

- 真实 `trellis init --claude --opencode --codex` baseline 可能已经比文档描述更接近 workflow 期望状态，因此部分兼容逻辑可能只对旧目标项目有价值
- `.codex/skills/` 在 fresh baseline 中大概率不是默认主承载面，围绕它的清理逻辑可能主要是历史兼容而非当前必需
- 增强版 `trellis-research` 是否仍值得由 workflow overlay，需要结合 live baseline 与源仓库增强载体差异一起判断

## Open Questions

- fresh `trellis init` 实际落盘后，`.agents/skills/`、`.codex/skills/`、`.claude/commands/trellis/`、`.opencode/commands/trellis/` 的 baseline 具体是什么
- `detect-embed-state.py` 与 `install-workflow.py --dry-run` 的实际输出是否与文档口径完全一致
- 哪些“重复/多余”只是面向 legacy target 的兼容链路，哪些已经在当前 baseline 下没有实际价值
- Formal install 之前能否仅凭 dry-run 和 baseline 快照，就把某些问题从“怀疑”提升为“确认”

## Requirements (evolving)

- 完整执行 `workflow-audit` 的 Step 0 → Step 2 A/B/C
- 进入 task-based runtime 模式，不能停留在 lightweight static 结果
- 在 `/tmp` 创建真实 target project，执行 `trellis init` 并记录 baseline 快照
- 执行 `detect-embed-state.py` 和 `install-workflow.py --dry-run`
- 到达 formal embed 时遵守 Codex boundary，输出 handoff block，不越权执行正式安装
- 输出时必须区分：
  - 真正错误
  - 设计上重复但仍有兼容价值
  - 当前 baseline 下多余或不再需要
  - 因 Codex handoff 未完成而仍待验证的项

## Acceptance Criteria (evolving)

- [ ] 版本闸门与目标绑定结果明确
- [ ] 至少有一轮真实 `/tmp` baseline 运行验证证据
- [ ] `detect-embed-state.py` 与 `install-workflow.py --dry-run` 的行为被实际执行确认
- [ ] 输出中明确给出“多余 / 错误 / 重复 / 不需要”的分类依据
- [ ] Formal install 未在 Codex 中越权执行，且 handoff 需求被明确说明

## Definition of Done (team quality bar)

- 结论基于 source repo、generated target project、runtime command output 三层证据
- 明确写出已完成、未完成、阻断项
- 若某结论无法在当前 executor 下证实，保持 Evidence Gap，而不是猜测

## Out of Scope (explicit)

- 不直接修改 workflow source 文件
- 不进行跨 Trellis 版本兼容升级分析
- 不在当前 Codex 会话中执行 formal embed
- 不把 repo 自身隐藏目录状态误当成 target project 装后状态

## Technical Notes

- 审计契约来源：
  - `.trellis/spec/skills/workflow-audit.md`
  - `.agents/skills/workflow-audit/SKILL.md`
- 关键 source repo 文档：
  - `docs/workflows/新项目开发工作流/CLI原生适配边界矩阵.md`
  - `docs/workflows/新项目开发工作流/装后隐藏目录与托管边界核对清单.md`
  - `docs/workflows/新项目开发工作流/工作流嵌入执行规范.md`
  - `docs/workflows/新项目开发工作流/commands/workflow_assets.py`
  - `docs/workflows/新项目开发工作流/commands/install-workflow.py`
  - `docs/workflows/新项目开发工作流/commands/upgrade-compat.py`
  - `docs/workflows/新项目开发工作流/commands/detect-embed-state.py`

